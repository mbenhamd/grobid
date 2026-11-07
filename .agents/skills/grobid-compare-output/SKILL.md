---
name: grobid-compare-output
description: "Create or extend strict GROBID output comparisons while preserving document content and relationships. Use for TEI/XML, JSON, BibTeX, debug traces, ZIP assets, PDF annotations or nondeterminism diagnosis."
---

# Comparator engineer

This is a repository-scoped skill for the GROBID Rust migration. Read the root AGENTS.md first. Resolve paths from the repository root, not the skill directory. Follow actual host permissions and the user's later instructions.

## Read only the relevant contracts

- `migration/TEST_STRATEGY.md`
- `migration/adr/0008-output-comparison-and-volatility.md`
- `migration/contracts/comparison-policy.json`

## Procedure

1. Start with raw bytes and full request/provenance identity. Prove a mismatch arises from baseline variability by repeating Java, not from comparing different configurations.

2. For XML preserve text/tails, order, namespaces, all meaningful attributes, IDs and links. Add only an exact field-specific volatility rule with type/cardinality checks and source reference.

3. If generated IDs differ, construct a bijection and require identical local link topology. Test duplicate IDs, dangling targets, changed references and structural position. Do not erase ID attributes.

4. For JSON reject duplicate keys and non-finite values, preserve array order and define endpoint numeric semantics. For ZIP reject duplicate/traversal members and compare complete logical content under size limits.

5. For annotation PDFs compare object/link/geometry/page/render evidence before allowing metadata-only byte differences. Text extraction alone is insufficient.

6. Add mutation tests that deliberately alter text, whitespace, dates, coordinates, links, arrays and assets and must fail. Version and independently review comparator changes separately from implementation fixes.

## Required result

Submit a narrowly specified comparator, repeated-Java evidence, raw/normalized artifacts, positive controls and adversarial mutation tests. Record every allowed difference.

## Failure rules

Do not blanket-ignore timestamps/UUIDs/whitespace or relax tolerances to clear a Rust failure. Default unknown differences to failure.

Use the coordinator ledger and evidence templates. Keep the distinction between source-derived observations, runtime observations and design decisions in every report.

