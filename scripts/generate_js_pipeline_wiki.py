"""
Slice 4 (garvis-6vlo): re-drive deepwiki-open's real wiki-generation flow with the retrieval-
starvation fix (relevant_files -> direct local file read, api/data_pipeline.py:get_local_files_context)
and WHY/footgun steering (docs/PIPELINE-FOOTGUNS-AND-RATIONALE.md injected into topically-relevant
pages). Reuses the ALREADY-DETERMINED wiki structure from slice 3 (same 6 pages, same titles/files —
still an accurate structure for this repo) so we don't re-spend an LLM call re-deriving it, but
regenerates every page's CONTENT fresh so the whole artifact is built consistently on the fixed
mechanism (not a patchwork of 4 old-FAISS pages + 2 new-direct-read pages).

Rescued from /tmp into this fork (garvis-9khs follow-up, 2026-07-05) as the reference
implementation of the pattern this repo's own retrieval-starvation fix + steering mechanism is
meant to drive — /tmp gets reaped, this script shouldn't have lived only there. Requires:
- deepwiki-open server running locally (see api/main.py), DEEPWIKI_EMBEDDER_TYPE=ollama.
- The pinned Claude Max account (DEEPWIKI_CLAUDE_ACCOUNT_DIR or the default) must be off its
  rate/session limit — a rejected call returns a short error string, not a real page.
- A previously cached structure response at STRUCTURE_CACHE_PATH (from an earlier
  determine-structure run) — this script does NOT re-derive the structure; see
  generate_cope_tools_wiki.py in this same directory for a from-scratch (structure + pages) runner.
"""
import json
import os
import re
import xml.etree.ElementTree as ET

import requests

BASE = "http://localhost:8055"
REPO_PATH = "/Users/dwillner/garvis/projects/sdk-review-pipeline"
PROVIDER = "claude-code"
MODEL = "claude-sonnet-4-6"
LANGUAGE = "en"
OWNER = "local"
REPO = "sdk-review-pipeline"
REPO_TYPE = "local"

EXTRA_EXCLUDED_DIRS = "\n".join([
    "./.garvis/",
    "./.stryker-tmp/",
    "./.stryker-tmp-clrf/",
    "./.stryker-tmp-cmdexp/",
    "./.stryker-tmp-cvg/",
    "./.stryker-tmp-diag2/",
    "./.stryker-tmp-s16/",
    "./reports/",
    "./undefined/",
])

FOOTGUNS_DOC = "docs/PIPELINE-FOOTGUNS-AND-RATIONALE.md"
# Pages whose topic maps onto the footguns doc's sections (steering, part 2 of the slice) — added
# to their relevant_files so the model actually has the WHY/tuning-rationale/failure-mode content
# in context, not just the code. Matched by exact page title from the slice-3 structure.
STEERED_PAGE_TITLES = {
    "Architecture Overview",
    "Pareto Optimization and Policy Evolution",
    "CLR (Contrastive Label Revision) and Polish Stages",
    "Backend Infrastructure and Flight Control",
}
# Per-page extra source files, beyond the page's own structure-determined relevant_files, needed
# to GROUND a specific footguns-doc claim in real code the model can actually cite (never just take
# the doc's word for it). review-pipeline.js already covers hard facts 3/5/7 for Architecture
# Overview and resource-lock.js already covers hard fact 6 for Backend Infrastructure — both are
# already in those pages' file lists, so no extra entry needed there.
EXTRA_GROUNDING_FILES = {
    "Pareto Optimization and Policy Evolution": ["review-pipeline.js"],  # GATE_TOLERANCE (fact 7)
    "CLR (Contrastive Label Revision) and Polish Stages": [
        "core/stabilization-profile.js",  # fact 8: stabilization always-on
        "variant-prep.js",  # fact 9: fiat-gen comment-vs-behavior divergence
    ],
}


def chat_stream(prompt_text, relevant_files=None):
    payload = {
        "repo_url": REPO_PATH,
        "type": REPO_TYPE,
        "provider": PROVIDER,
        "model": MODEL,
        "excluded_dirs": EXTRA_EXCLUDED_DIRS,
        "messages": [{"role": "user", "content": prompt_text}],
    }
    if relevant_files is not None:
        payload["relevant_files"] = relevant_files
    r = requests.post(f"{BASE}/chat/completions/stream", json=payload, stream=True, timeout=600)
    r.raise_for_status()
    full = ""
    for chunk in r.iter_content(chunk_size=None):
        if chunk:
            full += chunk.decode("utf-8", errors="replace")
    return full


def main():
    # --- Step 1: reuse a previously-cached structure response (same repo, same pages still make sense) ---
    STRUCTURE_CACHE_PATH = "/tmp/pipeline-wiki-structure-raw.txt"
    if not os.path.exists(STRUCTURE_CACHE_PATH):
        raise SystemExit(
            f"FAILED: no cached structure response at {STRUCTURE_CACHE_PATH}. This script only "
            "regenerates PAGE CONTENT against an already-determined structure; run a fresh "
            "structure-determination pass first (see generate_cope_tools_wiki.py's Step 1/2 for the "
            "from-scratch pattern) and save the raw response to this path, or adapt this script."
        )
    with open(STRUCTURE_CACHE_PATH) as f:
        structure_response = f.read()
    print(f"=== Step 1: reusing cached structure response ({len(structure_response)} chars) ===")

    xml_text = structure_response.strip()
    xml_text = re.sub(r"^```(?:xml)?\s*", "", xml_text)
    xml_text = re.sub(r"```\s*$", "", xml_text)
    match = re.search(r"<wiki_structure>.*</wiki_structure>", xml_text, re.DOTALL)
    if not match:
        raise SystemExit("FAILED: could not locate <wiki_structure> in the cached response")
    root = ET.fromstring(match.group(0))

    wiki_title = root.findtext("title", default="Untitled Wiki")
    wiki_description = root.findtext("description", default="")
    pages_meta = []
    for page_el in root.find("pages").findall("page"):
        page_id = page_el.get("id")
        title = page_el.findtext("title", default=page_id)
        importance = page_el.findtext("importance", default="medium")
        file_paths = [fp.text for fp in page_el.findall("./relevant_files/file_path") if fp.text]
        related = [r.text for r in page_el.findall("./related_pages/related") if r.text]
        pages_meta.append({
            "id": page_id, "title": title, "importance": importance,
            "filePaths": file_paths, "relatedPages": related,
        })

    print(f"Wiki title: {wiki_title!r}")
    print(f"Pages: {len(pages_meta)}")
    for p in pages_meta:
        steered = " [+footguns doc]" if p["title"] in STEERED_PAGE_TITLES else ""
        print(f"  - {p['id']}: {p['title']} (files={len(p['filePaths'])}){steered}")

    # --- Step 2: generate each page's content, fixed mechanism + steering ---
    generated_pages = {}
    for i, p in enumerate(pages_meta):
        print(f"=== Step 2.{i+1}: generating page '{p['title']}' ===")

        relevant_files = list(p["filePaths"])
        if p["title"] in STEERED_PAGE_TITLES:
            relevant_files = relevant_files + EXTRA_GROUNDING_FILES.get(p["title"], []) + [FOOTGUNS_DOC]

        file_list_md = "\n".join(f"- [{fp}]({fp})" for fp in relevant_files) or "- (no specific files listed)"
        is_steered = p["title"] in STEERED_PAGE_TITLES
        closing_instruction = (
            '7. WHY and Footguns: docs/PIPELINE-FOOTGUNS-AND-RATIONALE.md is one of the '
            'RELEVANT_SOURCE_FILES for this page. Where its content bears on this page\'s topic, '
            'include a dedicated "## Footguns and Rationale" section (or fold into an existing '
            'section) that captures the WHY behind the design and the concrete failure modes it '
            'warns about — quote or closely paraphrase the specific guidance, don\'t just gesture '
            'at "there are footguns."'
            if is_steered
            else '7. Conclusion: End with a brief summary paragraph.'
        )
        page_prompt = f"""You are an expert technical writer and software architect.
Your task is to generate a comprehensive and accurate technical wiki page in Markdown format about a specific feature, system, or module within a given software project.

You will be given:
1. The "[WIKI_PAGE_TOPIC]" for the page you need to create.
2. A list of "[RELEVANT_SOURCE_FILES]" from the project that you MUST use as the sole basis for the content. You have access to the full content of these files.

CRITICAL STARTING INSTRUCTION:
The very first thing on the page MUST be a `<details>` block listing the `[RELEVANT_SOURCE_FILES]` you used to generate the content.
Format it exactly like this:
<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

{file_list_md}
</details>

Immediately after the `<details>` block, the main title of the page should be a H1 Markdown heading: `# {p['title']}`.

Based ONLY on the content of the [RELEVANT_SOURCE_FILES]:

1. Introduction: Start with a concise introduction (1-2 paragraphs) explaining the purpose, scope, and high-level overview of "{p['title']}" within the context of the overall project.
2. Detailed Sections: Break down "{p['title']}" into logical sections using H2/H3 Markdown headings, explaining architecture, components, data flow, or logic.
3. Mermaid Diagrams: Use Mermaid diagrams (flowchart TD, sequenceDiagram, etc.) to visually represent architectures/flows where useful.
4. Tables: Use Markdown tables to summarize key features, parameters, or configuration options where relevant.
5. Source Citations: For significant information, cite the specific source file(s), e.g. `Sources: [filename.ext]()`.
6. Technical Accuracy: All information must be derived SOLELY from the [RELEVANT_SOURCE_FILES]. Do not invent or use unrelated external knowledge.
{closing_instruction}

IMPORTANT: Generate the content in English language.

WIKI_PAGE_TOPIC: {p['title']}
"""
        content = chat_stream(page_prompt, relevant_files=relevant_files)
        generated_pages[p["id"]] = {
            "id": p["id"],
            "title": p["title"],
            "content": content,
            "filePaths": relevant_files,
            "importance": p["importance"],
            "relatedPages": p["relatedPages"],
        }
        print(f"  content length: {len(content)} chars")

    # --- Step 3: persist via the real cache endpoint ---
    print("=== Step 3: POST /api/wiki_cache ===")
    wiki_structure_payload = {
        "id": "wiki-1",
        "title": wiki_title,
        "description": wiki_description,
        "pages": list(generated_pages.values()),
        "sections": None,
        "rootSections": None,
    }
    cache_request = {
        "repo": {
            "owner": OWNER, "repo": REPO, "type": REPO_TYPE,
            "token": None, "localPath": REPO_PATH, "repoUrl": REPO_PATH,
        },
        "language": LANGUAGE,
        "wiki_structure": wiki_structure_payload,
        "generated_pages": generated_pages,
        "provider": PROVIDER,
        "model": MODEL,
    }
    save_resp = requests.post(f"{BASE}/api/wiki_cache", json=cache_request, timeout=60)
    print("save status:", save_resp.status_code, save_resp.text[:300])

    # --- Step 4: verify round-trip ---
    print("=== Step 4: GET /api/wiki_cache (verify round-trip) ===")
    get_resp = requests.get(
        f"{BASE}/api/wiki_cache",
        params={"owner": OWNER, "repo": REPO, "repo_type": REPO_TYPE, "language": LANGUAGE},
        timeout=30,
    )
    cached = get_resp.json()
    assert cached is not None, "wiki cache round-trip returned null — not persisted"
    assert cached["wiki_structure"]["title"] == wiki_title
    assert len(cached["generated_pages"]) == len(generated_pages)
    print(f"VERIFIED: cached wiki has {len(cached['generated_pages'])} pages, title={cached['wiki_structure']['title']!r}")

    with open("/tmp/pipeline-wiki-full-v2.json", "w") as f:
        json.dump(cached, f, indent=2)
    print("Full cached wiki written to /tmp/pipeline-wiki-full-v2.json")
    print("GATE: regenerated with retrieval-starvation fix + WHY/footgun steering")


if __name__ == "__main__":
    main()
