# ADR 0001: Freeze the reference and bound the parity claim

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

Source HEAD, Docker tags, model assets and evaluation datasets can move independently. Finite tests cannot establish equivalence for every possible PDF. Current source is 0.9.2-SNAPSHOT; using an older release image would compare the wrong program.

## Decision

Pin f313f7010773fe8113cbb0f7a774960450a850d0 and independently fingerprint models, binaries, lexicons, config, embeddings, toolchains and corpus. Maintain immutable request/response/stage baselines. Define parity by verified route/feature/profile/corpus rows, not by an unqualified adjective.

## Alternatives considered

Rejected: track master continuously; accept a tag as an immutable artifact; equate passing compilation or average F1 with behavioral parity. Upstream upgrades become separately reviewed migrations.

## Validation and exit criteria

Verify actual build revision and hashes; capture Java/Java repeats; reject missing assets, empty suites and changed requests. No golden regeneration by implementation workers.

## Consequences

The baseline is more expensive to prepare, but it isolates implementation drift. New upstream fixes require deliberate rebaselining. The final report must state corpus scope, nondeterminism and uncovered cases.

## Source anchors

- [gradle.properties](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/gradle.properties)
- [grobid-home/config/grobid.yaml](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-home/config/grobid.yaml)
- [.github/workflows/evaluation.yml](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/.github/workflows/evaluation.yml)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

