---
name: grobid-port-text
description: "Port GROBID string, Unicode, tokenizer, lexicon and raw-text parsing behavior to Rust. Use for compatibility utilities, date/name/affiliation/citation services or feature-row mismatches."
---

# Text compatibility engineer

This is a repository-scoped skill for the GROBID Rust migration. Read the root AGENTS.md first. Resolve paths from the repository root, not the skill directory. Follow actual host permissions and the user's later instructions.

## Read only the relevant contracts

- `migration/audit/CORE_AUDIT.md`
- `migration/adr/0004-token-and-feature-compatibility.md`
- `migration/TEST_STRATEGY.md`

## Procedure

1. Trace the exact Java/Kotlin method and upstream tests for the selected behavior. Read adjacent callers to understand null/empty handling and normalization order.

2. Define typed byte, scalar and UTF-16 offsets. Capture non-BMP, combining, ligature, NBSP, CRLF, CJK and RTL examples before implementing.

3. Preserve delimiters and whitespace tokens. Port ordered Unicode cleanup rather than applying global normalization. Capture Java locale/case/regex and substring behavior where observable.

4. Freeze lexicon content and lookup rules. Generate exact feature rows and sequence separators; compare emitted columns rather than translating unused class fields.

5. Use the original model backend and label conversion for the first raw-text vertical slice. Add HTTP integration only after utility/feature/label parity localizes failures.

6. Exercise adjacent same-label entities, blank sequences and malformed/empty inputs. Confirm GROBID I- is entity start; keep DeLFT conversion separate.

## Required result

Submit source-linked utilities, exact text/offset/feature goldens, executed regression tests, service fixture comparisons and a list of unresolved Java semantics.

## Failure rules

Do not trade broken UTF-16 behavior for idiomatic Rust indexing without a deviation record. Do not insert fixture-specific postprocessing or silently replace the model.

Use the coordinator ledger and evidence templates. Keep the distinction between source-derived observations, runtime observations and design decisions in every report.

