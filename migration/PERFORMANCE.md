# Performance experiment plan

## Hypothesis, not a promise

Rust may reduce Java allocation, object traversal, feature generation, serialization and coordination overhead. Native pdfalto, native Wapiti, neural inference and external consolidation can still dominate. The source also shows a single-worker JEP executor and synchronized pool acquisition; both are profiling candidates, not measurements of this user's installation.

For an unchanged serial fraction `f`, replacing the remainder with an infinitely fast implementation bounds the serial speedup by `1 / f`. For example, if measured unchanged work is 80% of latency, that bound is 1.25×. This is an explanatory Amdahl-law example, not a measured GROBID fraction and not a bound on a redesign of concurrency/batching.

## Baseline record

Record CPU model/allocated cores, ISA, NUMA, RAM/cgroup limits, GPU/driver/runtime, storage and temporary filesystem, OS/kernel, native library hashes, JVM heap/GC, Rust release flags, container image digests and all process counts. Use an exact workload manifest with successful document/page/token counts and failed/cancelled request counts. Freeze profile, flags, server/client concurrency, cache state, warmup policy and consolidation mode.

Separate at least four experiments: CRF without consolidation; full DeLFT profile without consolidation; deterministic recorded consolidation; and small authorized live consolidation. Include cold startup/model loading separately from warmed steady state. Native or Python workers are part of Rust's total process tree for RSS/CPU/GPU accounting.

## Measurement method

1. Establish output parity for the exact benchmark inputs and options first.
2. Run fixed warmup until a declared criterion is met. Exclude it identically on both sides.
3. Run paired randomized-order Java/Rust rounds on the same hardware. Use at least ten measured rounds for release performance claims; choose corpus size so process jitter is small relative to run time.
4. Record wall time, successful docs/s and pages/s, p50/p95/p99 total latency, queue wait, each stage, CPU time, peak and steady RSS, GPU utilization/memory, temporary bytes, errors, retries and timeouts. Preserve raw observations, not just averages.
5. Use a closed-loop concurrency sweep for capacity planning and an open-loop arrival-rate test for tail latency/overload. Account for coordinated omission. Do not let requests dropped/failed early improve throughput or percentiles.
6. Report paired ratios with a bootstrap confidence interval. Keep per-document outliers, stage breakdowns and expected error cases. Benchmark uninstrumented release binaries after profiling separately.

## Default proposed acceptance

Correctness is mandatory. A `faster` release claim additionally requires the lower 95% confidence bound of successful-work throughput ratio to exceed 1.20 for the declared primary workload, no p95 latency regression beyond measured noise at the same offered load, and no unexplained total-process peak memory regression above 5%. These are project policy choices, not upstream guarantees. A 2× gain is an exploratory target, not a commitment.

If a different workload or target is chosen, record it before optimizing and before inspecting the final benchmark comparison. Do not lower the target to relabel a failed experiment. Ship a parity milestone separately if speed is not yet improved. End-to-end results with live services must be presented with their latency variability; do not attribute an external API's faster day to Rust.

## Optimize only measured costs

Candidate changes after parity include compact indexed layout storage, fewer string copies, faster XML/TEI streaming, precompiled lexicons/patterns, request admission/backpressure, shared immutable models with proven safety, isolated DeLFT batching/workers, and avoiding duplicate intermediate files when the contract permits it. Each change has a one-variable experiment and a full relevant differential rerun. Changing PDF extraction, weights, algorithms or quality is a separate experiment.

## Reliability run

Before release run a minimum 24-hour representative soak and an explicit high-load overload/recovery test. For the user's intended sustained ingestion, schedule a longer 72-hour candidate run once the shorter one passes. Test cancellation, restarts and failure injection during the soak. Check trends in all-process RSS, file descriptors, child count, queue age and temp disk rather than only start/end values. Set budgets before running, and stop on concrete leak/error thresholds. A multi-day agent session is not itself a service soak test.
