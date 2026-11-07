# ADR 0002: Separate JVM-free service from all-Rust dependencies

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

The user wants a faster Rust rewrite with all features. GROBID is a Java/Kotlin pipeline around C/C++, Python/TensorFlow and language/sentence tooling. A Rust reverse proxy preserves a Java dependency, while removing every non-Rust dependency changes a much larger scope.

## Decision

Replace server and pipeline behavior in Rust. Permit pinned native pdfalto/Wapiti and a Python DeLFT worker initially. Require no JVM in the claimed standalone runtime, including detectors, Lucene-dependent matching and hidden fallback. Track S0–S4 milestones and Java embedding compatibility independently.

## Alternatives considered

Rejected: mark a Java RPC wrapper complete; rewrite all models/PDF decoding before obtaining an oracle; describe native/Python reuse as a pure-Rust implementation.

## Validation and exit criteria

Audit runtime process tree, dynamic dependencies, images and fault paths; fail if disabling the Java oracle breaks production handling. Run every declared profile and optional detector path.

## Consequences

Early parity milestones remain practical, but all enabled Java-only helpers must be ported before the JVM-free gate. A separate optional Java facade can support library clients without being part of server deployment.

## Source anchors

- [grobid-core/src/main/java/org/grobid/core/document/DocumentSource.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/document/DocumentSource.java)
- [grobid-core/src/main/java/org/grobid/core/jni/DeLFTModel.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/jni/DeLFTModel.java)
- [grobid-core/src/main/java/org/grobid/core/utilities/matching/ReferenceMarkerMatcher.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/utilities/matching/ReferenceMarkerMatcher.java)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

