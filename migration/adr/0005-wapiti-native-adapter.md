# ADR 0005: Preserve the Wapiti decoder before considering a Rust CRF

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

Existing models were trained for a specific Wapiti fork and feature template/encoding behavior. JNI artifacts are not evidence of a stable C ABI. Native model ownership and thread safety need investigation.

## Decision

Build a minimal audited C shim over the pinned Wapiti source, or use an isolated adapter process if a safe ABI cannot be established. Keep weights and feature bytes fixed. Isolate unsafe code and record allocator, lifetime, mutation and concurrency contracts.

## Alternatives considered

Rejected: reimplement Viterbi/model loading from memory; assume libwapiti JNI exports equal a general-purpose C API; add Send/Sync to silence compiler restrictions.

## Validation and exit criteria

Compare fixed features→labels across all supported models, sequence lengths and concurrency. Exercise invalid models, reload, cancellation, repeated failures and sanitizers. Prove output lifetime/freeing and cache behavior.

## Consequences

Native inference remains a dependency. A pure Rust decoder can later replace it only after model-format, floating-point/tie-breaking and training/interoperability parity.

## Source anchors

- [grobid-core/src/main/java/org/grobid/core/jni/WapitiModel.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/jni/WapitiModel.java)
- [grobid-core/src/main/java/org/grobid/core/jni/WapitiWrapper.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/jni/WapitiWrapper.java)
- [grobid-core/src/main/java/org/grobid/core/engines/tagging/TaggerFactory.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/engines/tagging/TaggerFactory.java)
- [doc/Recompiling-and-integrating-CRF-libraries.md](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/doc/Recompiling-and-integrating-CRF-libraries.md)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

