# ADR 0016: Record behavior changes without forging parity

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

Some upstream behaviors are unsafe, inconsistent or runtime-specific: optimistic native training cancellation, incomplete evaluation exits, generated metadata and JVM metrics. Blindly duplicating every bug is not always desirable.

## Decision

Keep a versioned deviation ledger with source observation, oracle evidence, safety/compatibility reason, exact affected contract, mode/version boundary, tests and approval. Fix local hazards through safer operations. Report Rust runtime metadata honestly; maintain compatible routes/counters where feasible.

## Alternatives considered

Rejected: silently fix a quirk and still claim byte equivalence; fake JVM metrics or version provenance; weaken checks to match a broken evaluator; remove an endpoint without a scope record.

## Validation and exit criteria

For each deviation replay the original and new behavior, test both the changed and unchanged paths, and expose it in the release matrix. A literal-equivalence claim remains blocked for intentionally changed rows.

## Consequences

Useful improvements can ship with clearly bounded compatibility. Honest deviations are preferable to false parity claims, but they must not become a catch-all for unfinished implementation.

## Source anchors

- [grobid-service/src/main/java/org/grobid/service/process/GrobidRestProcessTraining.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-service/src/main/java/org/grobid/service/process/GrobidRestProcessTraining.java)
- [grobid-core/src/main/java/org/grobid/core/document/TEIFormatter.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/document/TEIFormatter.java)
- [.github/workflows/evaluation.yml](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/.github/workflows/evaluation.yml)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

