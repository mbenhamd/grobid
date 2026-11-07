# ADR 0013: Require equal-work quality and measured performance

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

The user's symptom is slowness, but no production traces were supplied. Native decoding or external calls may dominate. Aggregate quality scores and throughput can be distorted by omitted/failed documents.

## Decision

Gate quality and performance separately. Require complete corpus output and zero unexplained deterministic drift before speed claims. Benchmark paired release builds with fixed hardware, assets, workload and flags; include all processes. Predeclare effect and uncertainty criteria.

## Alternatives considered

Rejected: claim 5–10× because Rust is faster; benchmark only an empty HTTP handler; omit failed requests from accounting; switch model profile or requested features between implementations.

## Validation and exit criteria

Run field/document quality reports and held-out differential cases, then at least ten paired measurement rounds with latency, throughput, CPU/RSS and error counts. Run 24-hour soak before release and a longer candidate run for sustained ingestion.

## Consequences

Parity can be delivered before a speed gain. If measured unchanged work dominates, optimization must target scheduling/native/inference boundaries explicitly rather than relabel a shell rewrite as a performance success.

## Source anchors

- [.github/workflows/evaluation.yml](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/.github/workflows/evaluation.yml)
- [doc/benchmarks/Benchmarking.md](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/doc/benchmarks/Benchmarking.md)
- [grobid-core/src/main/java/org/grobid/core/jni/JEPThreadPool.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/jni/JEPThreadPool.java)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

