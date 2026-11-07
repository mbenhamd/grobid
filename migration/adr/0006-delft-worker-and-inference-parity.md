# ADR 0006: Replace JEP with a pinned DeLFT worker boundary

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

JEP uses a singleton single-thread executor. Python model preprocessing and decoding affect labels, and versions differ between some build paths. A guessed ONNX export does not preserve the current behavior.

## Decision

Start a JVM-free Python worker using the same DeLFT/TensorFlow/model/embedding assets and explicit framed IPC. Preserve model names, runtime config lookup behavior, feature channels, sequence handling and label reconstruction. Start serialized; tune batches/workers only after prediction parity.

## Alternatives considered

Rejected: switch to ONNX/Candle/tch, quantize or retrain during the initial port; infer shipped ONNX support from a stale CI file; share unsafe interpreter state across arbitrary threads.

## Validation and exit criteria

Run feature/label differentials for every DeLFT model and flavor, sequence truncation/chunk boundaries, empty input, short predictions, missing architecture, worker crash/restart and resource accounting. Dump effective runtime values from Java before correcting suspected config bugs.

## Consequences

Python remains a runtime dependency. Worker isolation helps failure control but IPC and duplicated weights may cost memory. Any later backend conversion needs separate quality and deterministic inference gates.

## Source anchors

- [grobid-core/src/main/java/org/grobid/core/jni/JEPThreadPool.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/jni/JEPThreadPool.java)
- [grobid-core/src/main/java/org/grobid/core/jni/DeLFTModel.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/jni/DeLFTModel.java)
- [grobid-core/src/main/java/org/grobid/core/jni/DeLFTClassifierModel.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/jni/DeLFTClassifierModel.java)
- [Dockerfile.delft](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/Dockerfile.delft)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

