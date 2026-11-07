---
name: grobid-profile-performance
description: "Profile and optimize a parity-verified GROBID Rust workload. Use for Java/Rust performance comparisons, batching, allocation reduction, concurrency sizing, memory or soak tests."
---

# Performance engineer

This is a repository-scoped skill for the GROBID Rust migration. Read the root AGENTS.md first. Resolve paths from the repository root, not the skill directory. Follow actual host permissions and the user's later instructions.

## Read only the relevant contracts

- `migration/PERFORMANCE.md`
- `migration/audit/CORE_AUDIT.md`
- `migration/adr/0013-quality-and-performance-gates.md`

## Procedure

1. Verify output parity and matched workload/profile/assets before timing. Record hardware, quotas, native/Python process trees and cache/warmup policy.

2. Measure admission, pdfalto, ALTO, features, per-model queue/execution, matching/consolidation, serialization and I/O. Separate cold startup from warm operation.

3. Identify the dominant measured cost; propose one change with a causal hypothesis. Retain behavior tests and do not reduce requested work.

4. Run paired randomized-order release measurements with raw successful/failed request records, percentiles, throughput, CPU and total memory. Use confidence intervals and predeclared gates.

5. Perform both capacity/concurrency sweeps and arrival-rate overload tests. Account for coordinated omission and failures. Benchmark instrumented and production binaries separately.

6. Run bounded soak with leak trends, cancellation and failure recovery. Preserve actual logs and stop criteria; report environment blocks rather than guessed speedups.

## Required result

Submit baseline and candidate manifests, raw paired observations, uncertainty intervals, quality check, stage explanation, regression risks and the exact scope of any speed claim.

## Failure rules

Do not compare CRF to full or consolidate-on to off and attribute the difference to Rust. Do not optimize a non-dominant layer based only on its language.

Use the coordinator ledger and evidence templates. Keep the distinction between source-derived observations, runtime observations and design decisions in every report.

