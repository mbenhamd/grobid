---
name: grobid-port-pipeline
description: "Port GROBID parser cascades and document structures to Rust. Use for segmentation, headers, references, fulltext, funding statements, figures, tables, equations, citations or flavor behavior."
---

# Pipeline engineer

This is a repository-scoped skill for the GROBID Rust migration. Read the root AGENTS.md first. Resolve paths from the repository root, not the skill directory. Follow actual host permissions and the user's later instructions.

## Read only the relevant contracts

- `migration/audit/CORE_AUDIT.md`
- `migration/ARCHITECTURE.md`
- `migration/TEST_STRATEGY.md`
- `migration/adr/0010-language-sentence-and-matching.md`

## Procedure

1. Trace Engine→EngineParsers→selected parser and nested parsers. Identify line-level versus token-level features, order of calls and config propagation.

2. Port one connected vertical slice using frozen layout/features/labels, preserving data structures and source spans. Compare the first intermediate divergence rather than only the final TEI.

3. Preserve author/affiliation/email association, bibliography metadata, callout range expansion, ambiguous candidate ranking, body/annex IDs and raw fields.

4. Read Kotlin LabelUtils alongside Java fulltext code. Test invalid/adjacent figure/table relabeling, incomplete figure/table rejection, formula numbering and retained text.

5. Handle availability, funding, conflict and contribution statements plus notes/annexes. Do not treat rare labels as optional because aggregate F1 barely changes.

6. Verify blank/light/light-ref/IETF and fallback behaviors from actual assets/config. Include language/sentence corrections and citation-link graph invariants.

## Required result

Submit source-linked stage contracts, deterministic intermediate diffs, relevant ported upstream tests and document-level fixtures covering the connected slice.

## Failure rules

Do not use generic NLP helpers as untested replacements for Lucene/OpenNLP/Cybozu behavior. Do not claim a flavor is supported merely because its enum exists.

Use the coordinator ledger and evidence templates. Keep the distinction between source-derived observations, runtime observations and design decisions in every report.

