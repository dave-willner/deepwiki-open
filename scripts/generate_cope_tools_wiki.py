"""
garvis-9khs: drive deepwiki-open's real wiki-generation flow (structure-determination + per-page
content, same verbatim prompt shapes as generate_js_pipeline_wiki.py) over projects/cope-tools-py —
the Python CLR+Pareto package that replaced the JS pipeline's sdk-review-pipeline core. Unlike the
JS-pipeline script, this one runs FULLY FROM SCRATCH: no prior cached structure is assumed, and the
WHY/footguns steering content is wired into pages by a KEYWORD heuristic rather than an exact-title
list, since the page titles aren't known ahead of a real run.

Steering-doc correction (2026-07-10, lead ruling): the doc does NOT live in cope-tools-py/docs/ — it
was never authored there. The real, actively-maintained steering content is
projects/cope-data-adapter/skill-internal/SKILL-LAYER-GUIDANCE.md (CD's doc, updated 2026-07-06). Per
the no-duplicate-copies ruling it is neither copied nor symlinked into cope-tools-py; instead this
driver reads its content directly off disk at fire time and INLINES it client-side into steered
pages' prompts (see STEERING_DOC_PATH / load_steering_doc() / generate_pages()) — never through the
server's relevant_files/get_local_files_context, whose path-traversal guard correctly refuses to
resolve a path outside REPO_PATH (by design; not weakened here).

Rescued into this fork from /tmp (2026-07-05, /tmp reaps) so "run one command when the account
window opens" is actually true — the durable copy IS the one to run, not a /tmp scratch copy.

One thing this script does that generate_js_pipeline_wiki.py didn't need: re-globbing the current
mutants* dir names fresh before EVERY call (structure-determination AND page-generation) — this repo
has dynamically-named mutation-testing scratch dirs (mutants/, mutants.gate-aside-<timestamp>/,
~194MB each, possibly actively written by a concurrent session) that would otherwise flood the
structure prompt, and they're actively appearing/disappearing so a one-time glob would go stale.

/local_repo/structure gap fix (garvis-11z.17, 2026-07-10): the endpoint used to have NO exclusion
param at all (unlike prepare_retriever), so this script used to re-filter file_tree lines client-side
after the fact. The endpoint now accepts the same excluded_dirs param prepare_retriever/
read_all_documents does — this script just forwards excluded_dirs_payload() to it, same as it always
did for the page-generation calls. One mechanism (server-side, _clean_directory_token-based), not two.

Requires: deepwiki-open server running locally, DEEPWIKI_EMBEDDER_TYPE=ollama, and the pinned
account (DEEPWIKI_CLAUDE_ACCOUNT_DIR or the default) off its rate/session limit.
"""
import glob
import json
import os
import re
import xml.etree.ElementTree as ET

import requests

BASE = "http://localhost:8055"
REPO_PATH = "/Users/dwillner/garvis/projects/cope-tools-py"
PROVIDER = "claude-code"
MODEL = "claude-sonnet-4-6"
LANGUAGE = "en"
OWNER = "local"
REPO = "cope-tools-py"
REPO_TYPE = "local"

STRUCTURE_CACHE_PATH = "/tmp/cope-tools-wiki-structure-raw.txt"
PAGES_META_PATH = "/tmp/cope-tools-pages-meta.json"
OUTPUT_CACHE_PATH = "/tmp/cope-tools-wiki-full.json"

# Dirs that are never source, regardless of what mutants* variant currently exists.
STATIC_EXTRA_EXCLUDED_DIRS = ["./.garvis/", "./.pytest_cache/", "./.ruff_cache/"]

# Real, maintained location — NOT inside cope-tools-py (never copied/symlinked there; no-duplicates
# ruling + don't drop files into another conversation's active production repo). Absolute path, read
# once and inlined client-side into steered pages' prompts.
STEERING_DOC_PATH = "/Users/dwillner/garvis/projects/cope-data-adapter/skill-internal/SKILL-LAYER-GUIDANCE.md"
# The page titles aren't known ahead of a from-scratch run, so steering-page selection is a keyword
# match against each page's title+description (case-insensitive) rather than an exact-title list —
# any page whose topic plausibly touches the skill-layer contract (the CLR/relabel/optimize verbs,
# fiat construction, the sequencing rules) gets the steering content inlined into its prompt.
STEERING_KEYWORDS = (
    "clr", "relabel", "optimiz", "fiat", "pareto", "architecture", "overview", "verb", "sequenc",
)


def load_steering_doc():
    with open(STEERING_DOC_PATH) as f:
        content = f.read()
    mtime = os.path.getmtime(STEERING_DOC_PATH)
    print(f"Loaded steering doc: {STEERING_DOC_PATH} ({len(content)} chars, mtime={mtime})")
    return content


def current_mutants_dirs():
    """Dynamically-named mutation-testing scratch dirs — re-globbed fresh each call since a
    concurrent session may be actively creating/removing mutants.gate-aside-<timestamp>/ dirs."""
    return sorted(
        f"./{os.path.basename(p)}/"
        for p in glob.glob(os.path.join(REPO_PATH, "mutants*"))
        if os.path.isdir(p)
    )


def excluded_dirs_payload():
    return "\n".join(STATIC_EXTRA_EXCLUDED_DIRS + current_mutants_dirs())


def is_scratch_path(rel_path):
    """Post-hoc SANITY CHECK only (garvis-11z.17) — the structure endpoint now does the real
    filtering server-side via excluded_dirs, so the model never sees a scratch-dir path to pick in
    the first place. This is a cheap, genuinely-different second check: if a page's model-chosen
    filePaths ever DOES contain a scratch-dir entry despite that, something is wrong (a mismatch
    between excluded_dirs_payload() and what the server actually excluded, a live mutants* dir
    appearing between the structure call and here, etc.) and it's worth a loud warning rather than
    silently generating a page from a mutation-testing scratch file."""
    first_component = rel_path.split(os.sep)[0]
    return (
        first_component.startswith("mutants")
        or first_component in (".garvis", ".pytest_cache", ".ruff_cache")
        or first_component.endswith(".egg-info")
    )


def is_steering_candidate(page):
    haystack = f"{page['title']} {page.get('description', '')}".lower()
    return any(keyword in haystack for keyword in STEERING_KEYWORDS)


def chat_stream(prompt_text, relevant_files=None):
    payload = {
        "repo_url": REPO_PATH,
        "type": REPO_TYPE,
        "provider": PROVIDER,
        "model": MODEL,
        "excluded_dirs": excluded_dirs_payload(),
        "messages": [{"role": "user", "content": prompt_text}],
    }
    if relevant_files is not None:
        # Any truthy relevant_files list (even a single cheap file) routes this call through the
        # direct local-file-read fix instead of the old FAISS-retrieval path — for the
        # structure-determination call specifically, this ALSO sidesteps prepare_retriever's
        # unconditional full-repo embedding indexing, which buys nothing here since the file_tree
        # + README are already inlined in the prompt text itself.
        payload["relevant_files"] = relevant_files
    r = requests.post(f"{BASE}/chat/completions/stream", json=payload, stream=True, timeout=600)
    r.raise_for_status()
    full = ""
    for chunk in r.iter_content(chunk_size=None):
        if chunk:
            full += chunk.decode("utf-8", errors="replace")
    return full


def get_local_repo_structure(path, excluded_dirs=None):
    params = {"path": path}
    if excluded_dirs:
        params["excluded_dirs"] = excluded_dirs
    r = requests.get(f"{BASE}/local_repo/structure", params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def determine_structure():
    print("=== Step 1: fetching local file tree + README (server-side excluded_dirs, garvis-11z.17) ===")
    structure_info = get_local_repo_structure(REPO_PATH, excluded_dirs=excluded_dirs_payload())
    file_tree = structure_info["file_tree"]
    readme = structure_info.get("readme", "") or "(no README.md found)"
    print(f"file_tree entries: {len(file_tree.splitlines())}")

    determine_structure_prompt = f"""Analyze this repository cope-tools-py and create a wiki structure for it.

1. The complete file tree of the project:
<file_tree>
{file_tree}
</file_tree>

2. The README file of the project:
<readme>
{readme}
</readme>

I want to create a wiki for this repository. Determine the most logical structure for a wiki based on the repository's content.

IMPORTANT: The wiki content will be generated in English language.

When designing the wiki structure, include pages that would benefit from visual diagrams, such as:
- Architecture overviews
- Data flow descriptions
- Component relationships
- Process workflows
- State machines
- Class hierarchies

Return your analysis in the following XML format:

<wiki_structure>
  <title>[Overall title for the wiki]</title>
  <description>[Brief description of the repository]</description>
  <pages>
    <page id="page-1">
      <title>[Page title]</title>
      <description>[Brief description of what this page will cover]</description>
      <importance>high|medium|low</importance>
      <relevant_files>
        <file_path>[Path to a relevant file]</file_path>
        <!-- More file paths as needed -->
      </relevant_files>
      <related_pages>
        <related>page-2</related>
        <!-- More related page IDs as needed -->
      </related_pages>
    </page>
    <!-- More pages as needed -->
  </pages>
</wiki_structure>

IMPORTANT FORMATTING INSTRUCTIONS:
- Return ONLY the valid XML structure specified above
- DO NOT wrap the XML in markdown code blocks (no ``` or ```xml)
- DO NOT include any explanation text before or after the XML
- Ensure the XML is properly formatted and valid
- Start directly with <wiki_structure> and end with </wiki_structure>

IMPORTANT:
1. Create 4-6 pages that would make a concise wiki for this repository
2. Each page should focus on a specific aspect of the codebase (e.g., architecture, key features, setup)
3. The relevant_files should be actual files from the repository that would be used to generate that page
4. Return ONLY valid XML with the structure specified above, with no markdown code block delimiters"""

    if os.path.exists(STRUCTURE_CACHE_PATH):
        print(f"=== Step 2: reusing already-saved structure response from {STRUCTURE_CACHE_PATH} ===")
        with open(STRUCTURE_CACHE_PATH) as f:
            structure_response = f.read()
    else:
        print("=== Step 2: determining wiki structure (real LLM call, provider=claude-code) ===")
        structure_response = chat_stream(determine_structure_prompt, relevant_files=["README.md"])
        # Only cache a response that actually looks like the expected XML — never cache an error
        # string, or a future re-run would silently reuse a bad cached "structure" forever.
        if "<wiki_structure>" in structure_response:
            with open(STRUCTURE_CACHE_PATH, "w") as f:
                f.write(structure_response)
        else:
            print("NOT caching — response doesn't contain <wiki_structure>:")
            print(structure_response[:500])
    print(f"structure response length: {len(structure_response)} chars")

    xml_text = structure_response.strip()
    xml_text = re.sub(r"^```(?:xml)?\s*", "", xml_text)
    xml_text = re.sub(r"```\s*$", "", xml_text)
    match = re.search(r"<wiki_structure>.*</wiki_structure>", xml_text, re.DOTALL)
    if not match:
        print("RAW STRUCTURE RESPONSE (no <wiki_structure> found):")
        print(xml_text[:2000])
        raise SystemExit("FAILED: could not locate <wiki_structure> in the response")
    root = ET.fromstring(match.group(0))

    wiki_title = root.findtext("title", default="Untitled Wiki")
    wiki_description = root.findtext("description", default="")
    pages_meta = []
    for page_el in root.find("pages").findall("page"):
        page_id = page_el.get("id")
        title = page_el.findtext("title", default=page_id)
        description = page_el.findtext("description", default="")
        importance = page_el.findtext("importance", default="medium")
        file_paths = [fp.text for fp in page_el.findall("./relevant_files/file_path") if fp.text]
        related = [r.text for r in page_el.findall("./related_pages/related") if r.text]
        pages_meta.append({
            "id": page_id, "title": title, "description": description, "importance": importance,
            "filePaths": file_paths, "relatedPages": related,
        })

    print(f"Wiki title: {wiki_title!r}")
    print(f"Pages determined: {len(pages_meta)}")
    for p in pages_meta:
        steered = " [+steering doc]" if is_steering_candidate(p) else ""
        print(f"  - {p['id']}: {p['title']} (importance={p['importance']}, files={len(p['filePaths'])}){steered}")
        for fp in p["filePaths"]:
            if is_scratch_path(fp):
                print(f"    !! WARNING: model picked a scratch-dir file despite filtering: {fp}")

    if not pages_meta:
        raise SystemExit("FAILED: zero pages parsed from wiki_structure")

    with open(PAGES_META_PATH, "w") as f:
        json.dump(pages_meta, f, indent=2)
    print(f"Wrote {PAGES_META_PATH}")

    return wiki_title, wiki_description, pages_meta


def generate_pages(pages_meta):
    steering_content = load_steering_doc()
    generated_pages = {}
    for i, p in enumerate(pages_meta):
        print(f"=== Step 3.{i + 1}: generating page '{p['title']}' ===")

        steered = is_steering_candidate(p)
        # relevant_files stays repo-only — this is what the server actually reads off disk via
        # get_local_files_context; the steering doc lives OUTSIDE REPO_PATH and is never sent here.
        relevant_files = list(p["filePaths"])
        # citation_files is what the reader sees cited on the page (the <details> block) — includes
        # the steering doc's real path when steered, for citation honesty, even though it wasn't
        # fetched via the server's relevant_files mechanism.
        citation_files = relevant_files + [STEERING_DOC_PATH] if steered else relevant_files

        file_list_md = "\n".join(f"- [{fp}]({fp})" for fp in citation_files) or "- (no specific files listed)"
        steering_block = ""
        closing_instruction = '7. Conclusion: End with a brief summary paragraph.'
        if steered:
            steering_block = f"""

ADDITIONAL STEERING CONTEXT — WHY and sequencing rules, inlined from {STEERING_DOC_PATH} (the
skill-layer's actively-maintained design-rationale doc; not one of the RELEVANT_SOURCE_FILES above,
but authoritative on the WHY and call-sequencing for the CLR/relabel/optimize verbs and fiat
construction where this page's topic touches them):
<steering_doc path="{STEERING_DOC_PATH}">
{steering_content}
</steering_doc>
"""
            closing_instruction = (
                f'7. WHY and Sequencing: the ADDITIONAL STEERING CONTEXT block below (from '
                f'{STEERING_DOC_PATH}) is authoritative on the WHY behind this design and the '
                'intended call sequencing. Where its content bears on this page\'s topic, include a '
                'dedicated "## Design Rationale and Sequencing" section (or fold into an existing '
                'section) that captures the WHY, the intended call sequencing, and any concrete '
                'rules it states — quote or closely paraphrase the specific guidance, don\'t just '
                'gesture at "there are rules."'
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
{steering_block}
IMPORTANT: Generate the content in English language.

WIKI_PAGE_TOPIC: {p['title']}
"""
        content = chat_stream(page_prompt, relevant_files=relevant_files)
        generated_pages[p["id"]] = {
            "id": p["id"],
            "title": p["title"],
            "content": content,
            "filePaths": citation_files,
            "importance": p["importance"],
            "relatedPages": p["relatedPages"],
        }
        print(f"  content length: {len(content)} chars")
    return generated_pages


def persist_and_verify(wiki_title, wiki_description, generated_pages):
    print("=== Step 4: POST /api/wiki_cache ===")
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

    print("=== Step 5: GET /api/wiki_cache (verify round-trip) ===")
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

    with open(OUTPUT_CACHE_PATH, "w") as f:
        json.dump(cached, f, indent=2)
    print(f"Full cached wiki written to {OUTPUT_CACHE_PATH}")
    print("GATE: cope-tools-py wiki generated end-to-end with retrieval-fix + WHY/sequencing steering")


def main():
    wiki_title, wiki_description, pages_meta = determine_structure()
    generated_pages = generate_pages(pages_meta)
    persist_and_verify(wiki_title, wiki_description, generated_pages)


if __name__ == "__main__":
    main()
