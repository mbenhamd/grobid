# ADR 0012: Bound work and account for the complete process tree

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

HTTP concurrency, engine admission, native workers and PDF subprocesses use different resources. Dropped cancellation or unbounded queues can make a faster microbenchmark unstable in sustained ingestion.

## Decision

Use explicit admission limits, deadlines, bounded worker queues, unique temp directories and child process groups. Keep blocking work off async reactor threads. Preserve external overload/status semantics while logging intentional safety deviations.

## Alternatives considered

Rejected: unbounded spawn per request; timeout only the HTTP future; ignore native/Python memory; optimize process isolation away before parity.

## Validation and exit criteria

Test overload/recovery, slow consumers, interrupted uploads, worker death, child cleanup, repeated malformed documents, full disk and shutdown with active jobs. Run staged soak and verify RSS/FD/child/temp trends.

## Consequences

Resource budgets may limit peak throughput, but they make steady capacity measurable. Cancellation improvements can differ from optimistic upstream training status and must be disclosed.

## Source anchors

- [grobid-core/src/main/java/org/grobid/core/factory/GrobidPoolingFactory.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/factory/GrobidPoolingFactory.java)
- [grobid-core/src/main/java/org/grobid/core/document/DocumentSource.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/document/DocumentSource.java)
- [grobid-service/src/main/java/org/grobid/service/process/GrobidRestProcessTraining.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-service/src/main/java/org/grobid/service/process/GrobidRestProcessTraining.java)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

