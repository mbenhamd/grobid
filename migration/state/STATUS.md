# Migration status

Updated 2026-11-07 (coordinator `claude-coordinator`).

## Scope decision (user, 2026-11-07)

The first target is **S1_RUST_CRF_SERVICE: JVM-free, CRF first**. The Rust server replaces all Java. The pinned native pdfalto and Wapiti are retained. DeLFT/Python deep models are deferred to S2. A pure-Rust replacement of pdfalto/Wapiti is out of scope until separately gated. The user approved installing JDK 21 (Homebrew `openjdk@21`) solely to build the pinned Java oracle natively on macOS arm64.

## Evidence-backed state

- **T000 Freeze source and environment: done.**
  - Result commit `4382437ae7a41a5898187ebc4ea73f9c717614bb`.
  - Independent review by `claude-reviewer-T000`, another Claude instance, not a human (`migration/evidence/T000/review/review.json`).
  - The oracle checkout `/Users/mbenhamd/Projects/grobid-oracle` is at the pinned SHA and tree `a59943da`, and is clean.
  - 8/8 critical source hashes and 506/506 asset-index blobs match.
  - The host environment lock is in `migration/contracts/host-environment-lock.json`.
- Java runtime oracle: not built, not started (T002).
- Runtime-loaded model/native/config hashes: not captured (T003).
- Corpus: not built (T004).
- Rust implementation: not started.
- Java/Rust parity, labeled quality, training parity, benchmarks and soak: not executed.

Dependency-ready: T001, T002, T004.

Keep this file consistent with `task-state.json` and the feature matrix. Never convert static inventory counts into test-pass claims.
