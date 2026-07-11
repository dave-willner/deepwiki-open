"""
Generic, parameterized wiki-generation driver — genericized from generate_cope_tools_wiki.py
(garvis-9khs) for the Jacques self-documentation arc (garvis-11z.18/.19, 2026-07-10). Same proven
flow (structure-determination -> per-page generation -> wiki_cache persist+round-trip verify), same
retrieval-fix pattern (relevant_files routes through the direct local-file-read path, never FAISS for
content), same server-side excluded_dirs/included_dirs (garvis-11z.17) instead of client-side
re-filtering, same client-side steering-doc inlining pattern (never through the server's
relevant_files, whose path-traversal guard correctly refuses paths outside REPO_PATH).

Per-target specifics (repo path, steering doc, steering keywords, extra exclusions, cache paths) live
in a small config dict passed at the bottom of this file or via a thin per-target wrapper script that
imports run() and calls it with its own config — kept as ONE shared engine, not N copies, since the
logic itself (XML parsing, retrieval-fix wiring, steering inlining, persist+verify) is identical
across every target and was already proven correct twice (JS pipeline wiki, cope-tools-py wiki).

Requires: deepwiki-open server running locally, DEEPWIKI_EMBEDDER_TYPE=ollama, and the pinned account
(DEEPWIKI_CLAUDE_ACCOUNT_DIR or the default) off its rate/session limit.
"""
import json
import os
import re
import xml.etree.ElementTree as ET

import requests

BASE = "http://localhost:8055"
PROVIDER = "claude-code"
MODEL = "claude-sonnet-4-6"
LANGUAGE = "en"
REPO_TYPE = "local"


def load_steering_doc(steering_doc_path):
    with open(steering_doc_path) as f:
        content = f.read()
    mtime = os.path.getmtime(steering_doc_path)
    print(f"Loaded steering doc: {steering_doc_path} ({len(content)} chars, mtime={mtime})")
    return content


def is_steering_candidate(page, steering_keywords):
    haystack = f"{page['title']} {page.get('description', '')}".lower()
    return any(keyword in haystack for keyword in steering_keywords)


def chat_stream(config, prompt_text, relevant_files=None):
    payload = {
        "repo_url": config["repo_path"],
        "type": REPO_TYPE,
        "provider": PROVIDER,
        "model": MODEL,
        "excluded_dirs": "\n".join(config["excluded_dirs"]),
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


def determine_structure(config):
    print("=== Step 1: fetching local file tree + README (server-side excluded_dirs, garvis-11z.17) ===")
    structure_info = get_local_repo_structure(
        config["repo_path"], excluded_dirs="\n".join(config["excluded_dirs"])
    )
    file_tree = structure_info["file_tree"]
    readme = structure_info.get("readme", "") or "(no README.md found)"
    print(f"file_tree entries: {len(file_tree.splitlines())}")

    determine_structure_prompt = f"""Analyze this repository, {config["repo_description"]}, and create a wiki structure for it.

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

    structure_cache_path = config["structure_cache_path"]
    if os.path.exists(structure_cache_path):
        print(f"=== Step 2: reusing already-saved structure response from {structure_cache_path} ===")
        with open(structure_cache_path) as f:
            structure_response = f.read()
    else:
        print("=== Step 2: determining wiki structure (real LLM call, provider=claude-code) ===")
        structure_response = chat_stream(config, determine_structure_prompt, relevant_files=["README.md"])
        # Only cache a response that actually looks like the expected XML — never cache an error
        # string, or a future re-run would silently reuse a bad cached "structure" forever.
        if "<wiki_structure>" in structure_response:
            with open(structure_cache_path, "w") as f:
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
    # Hardening (garvis-9sfk gate finding): the model reliably escapes '&' inside its OWN generated
    # <title>/<related> boilerplate but is not reliable about escaping a literal '&' that shows up in
    # prose it's transcribing/paraphrasing (e.g. "System & Design Wiki") — a bare '&' is not valid XML
    # and ET.fromstring hard-fails with "not well-formed (invalid token)" on it. Sanitize any '&' that
    # isn't already part of a recognized entity reference (&amp; &lt; &gt; &apos; &quot; or a numeric
    # &#123; / &#x1F;) before parsing. This is a real, reusable engine fix (every future wiki target
    # can hit this the same way), not a one-off workaround for this run.
    sanitized_xml = re.sub(r"&(?!(?:amp|lt|gt|apos|quot|#\d+|#x[0-9a-fA-F]+);)", "&amp;", match.group(0))
    try:
        root = ET.fromstring(sanitized_xml)
    except ET.ParseError:
        print("RAW STRUCTURE RESPONSE (ParseError even after & sanitization):")
        print(sanitized_xml[:2000])
        raise

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
        steered = " [+steering doc]" if is_steering_candidate(p, config["steering_keywords"]) else ""
        print(f"  - {p['id']}: {p['title']} (importance={p['importance']}, files={len(p['filePaths'])}){steered}")

    if not pages_meta:
        raise SystemExit("FAILED: zero pages parsed from wiki_structure")

    with open(config["pages_meta_path"], "w") as f:
        json.dump(pages_meta, f, indent=2)
    print(f"Wrote {config['pages_meta_path']}")

    return wiki_title, wiki_description, pages_meta


def generate_pages(config, pages_meta):
    steering_doc_path = config["steering_doc_path"]
    steering_content = load_steering_doc(steering_doc_path)
    generated_pages = {}
    for i, p in enumerate(pages_meta):
        print(f"=== Step 3.{i + 1}: generating page '{p['title']}' ===")

        steered = is_steering_candidate(p, config["steering_keywords"])
        # relevant_files stays repo-only — this is what the server actually reads off disk via
        # get_local_files_context; the steering doc lives OUTSIDE repo_path and is never sent here.
        relevant_files = list(p["filePaths"])
        # citation_files is what the reader sees cited on the page (the <details> block) — includes
        # the steering doc's real path when steered, for citation honesty, even though it wasn't
        # fetched via the server's relevant_files mechanism.
        citation_files = relevant_files + [steering_doc_path] if steered else relevant_files

        file_list_md = "\n".join(f"- [{fp}]({fp})" for fp in citation_files) or "- (no specific files listed)"
        steering_block = ""
        closing_instruction = '7. Conclusion: End with a brief summary paragraph.'
        if steered:
            steering_block = f"""

ADDITIONAL STEERING CONTEXT — WHY and sequencing rules, inlined from {steering_doc_path} (an
actively-maintained design-rationale doc; not one of the RELEVANT_SOURCE_FILES above, but
authoritative on the WHY and intended sequencing where this page's topic touches it):
<steering_doc path="{steering_doc_path}">
{steering_content}
</steering_doc>
"""
            closing_instruction = (
                f'7. WHY and Sequencing: the ADDITIONAL STEERING CONTEXT block below (from '
                f'{steering_doc_path}) is authoritative on the WHY behind this design and the '
                'intended sequencing. Where its content bears on this page\'s topic, include a '
                'dedicated "## Design Rationale and Sequencing" section (or fold into an existing '
                'section) that captures the WHY, the intended sequencing, and any concrete rules it '
                'states — quote or closely paraphrase the specific guidance, don\'t just gesture at '
                '"there are rules."'
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
        content = chat_stream(config, page_prompt, relevant_files=relevant_files)
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


def persist_and_verify(config, wiki_title, wiki_description, generated_pages):
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
            "owner": config["owner"], "repo": config["repo"], "type": REPO_TYPE,
            "token": None, "localPath": config["repo_path"], "repoUrl": config["repo_path"],
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
        params={"owner": config["owner"], "repo": config["repo"], "repo_type": REPO_TYPE, "language": LANGUAGE},
        timeout=30,
    )
    cached = get_resp.json()
    assert cached is not None, "wiki cache round-trip returned null — not persisted"
    assert cached["wiki_structure"]["title"] == wiki_title
    assert len(cached["generated_pages"]) == len(generated_pages)
    print(f"VERIFIED: cached wiki has {len(cached['generated_pages'])} pages, title={cached['wiki_structure']['title']!r}")

    with open(config["output_cache_path"], "w") as f:
        json.dump(cached, f, indent=2)
    print(f"Full cached wiki written to {config['output_cache_path']}")
    print(f"GATE: {config['repo']} wiki generated end-to-end with retrieval-fix + WHY/sequencing steering")


def run(config):
    wiki_title, wiki_description, pages_meta = determine_structure(config)
    generated_pages = generate_pages(config, pages_meta)
    persist_and_verify(config, wiki_title, wiki_description, generated_pages)
