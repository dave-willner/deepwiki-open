# Distaff wiki corpus manifest (garvis-9sfk, 2026-07-10)

Curated-file-list corpus mode (JM ruling, OPTION 1) — this directory IS the corpus fed to
`generate_wiki.py` as `repo_path`. Code files are structurally absent: only role docs, design-record
docs, and rendered bead/decision text are present, so the wiki's LINK-not-recover boundary against
wikis/jacques-core-system + wikis/jacques-core-hooks is enforced by construction, not convention.

This exact list is what JM needs verbatim for the ekve.3 / registry-row-5 manifest.

## roles/ (symlinks — no duplicate copies, per the 2026-06-26 standing decision)
- roles/evaluation-role.md -> jacques-core/core-system/core-hooks/roles/evaluation-role.md
- roles/attention-role.md -> jacques-core/core-system/core-hooks/roles/attention-role.md
- roles/cos-role.md -> jacques-core/core-system/core-hooks/roles/cos-role.md
- roles/supervisor-role.md -> jacques-core/core-system/core-hooks/roles/supervisor-role.md
- roles/execution-role.md -> jacques-core/core-system/core-hooks/roles/execution-role.md
- roles/adjutant-role.md -> jacques-core/core-system/core-hooks/roles/adjutant-role.md
- roles/decision-recap-format.md -> jacques-core/core-system/core-hooks/roles/decision-recap-format.md
- roles/bicameral.md -> jacques-core/core-skills/core-system-skills/bicameral/bicameral.md

## design-records/ (symlinks)
- design-records/fleet-invariants.md -> jacques-core/core-knowledge/core-goals/fleet-invariants.md
- design-records/thread-lifecycle-procedures.md -> jacques-core/core-knowledge/core-system-knowledge/thread-lifecycle-procedures.md
- design-records/conv-format-ladder.md -> jacques-core/core-knowledge/core-system-knowledge/conv-format-ladder.md
- design-records/ledger-taxonomy.js -> jacques-core/core-system/core-hooks/utilities/ledger-taxonomy.js
- design-records/example-beads-decisions-view.md -> temporary-jacques/conversations/wt/conv-b9e49457/beads-decisions.md
  (a real, representative compiled beads-decisions view — documents the DCS ledger-taxonomy mechanism
  with one concrete instance rather than the abstract schema alone)

## scars/ (rendered — `bd show <id>` output, materialized as text; NOT vault duplicates, this is DB
## content synthesized into corpus text for the wiki run, same pattern as the steering doc's own
## provenance rendering)
- scars/bead-532.md      <- bd show garvis-532      (epic body only; 273-child list elided/noted)
- scars/bead-532-336.md  <- bd show garvis-532.336   (main-2 migration incident + root-cause fix)
- scars/bead-532-338.md  <- bd show garvis-532.338   (asleep-while-alive limbo scar)
- scars/bead-532-339.md  <- bd show garvis-532.339   (stage() false-success scar)
- scars/bead-tv0l.md     <- bd show garvis-tv0l      (LL strategy rulings, rounds 1-4 + addendum —
                                                        "rounds 3-4" = the asleep-while-alive incident
                                                        + the heavy-to-start/cheap-to-move lesson)
- scars/bead-f2kz.md     <- bd show garvis-f2kz      (imposter-class root-cause: resume mis-picks a
                                                        teammate session as lead)
- scars/bead-4bjl.md     <- bd show garvis-4bjl      (action->execution rename lineage)
- scars/bead-1nhu-5.md   <- bd show garvis-1nhu.5    (reflection->evaluation rename lineage)

## Steering doc (inlined per-page client-side, NOT part of the corpus/relevant_files set — same
## pattern as every prior wiki run)
jacques-core/core-knowledge/core-system-knowledge/distaff-wiki-steering.md

## Explicitly excluded by design (LINK, don't re-cover)
- All per-file code already covered by wikis/jacques-core-system and wikis/jacques-core-hooks.
- Domain-pair-specific systems (robodex, pipeline) — out of scope per the steering doc.
