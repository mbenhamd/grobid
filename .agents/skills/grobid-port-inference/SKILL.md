---
name: grobid-port-inference
description: "Implement and validate JVM-free Wapiti and DeLFT model adapters. Use for native FFI, Python worker IPC, model loading, flavor/runtime resolution or inference concurrency."
---

# Inference engineer

This is a repository-scoped skill for the GROBID Rust migration. Read the root AGENTS.md first. Resolve paths from the repository root, not the skill directory. Follow actual host permissions and the user's later instructions.

## Read only the relevant contracts

- `migration/audit/CORE_AUDIT.md`
- `migration/contracts/model-inventory.json`
- `migration/adr/0005-wapiti-native-adapter.md`
- `migration/adr/0006-delft-worker-and-inference-parity.md`

## Procedure

1. Inventory actual model files and effective engine/architecture lookup, including fallback. Keep configured disabled classifiers distinct from runnable sequence models.

2. Inspect the pinned Wapiti fork's native API and build. Define allocator/free pairs, mutability, lifetime and per-call buffer ownership before writing bindings. Prefer a narrow C shim; do not assume JNI exports form the desired ABI.

3. Freeze exact input feature bytes and native output adaptation. Compare every active model on known sequences before parallelizing model calls.

4. For DeLFT use the same Python/runtime/models/embeddings and preprocessing. Reproduce naming, row reconstruction, short predictions, max-length/batch behavior and labels. First serialize calls like the oracle.

5. Test process crash, failed model load, cancellation, stale worker, reload and missing flavored assets. Validate thread/process safety with concurrent differential runs and sanitizers where available.

6. Only after parity, profile shared models, batching and worker counts with complete process-tree accounting. Keep any ONNX/new runtime experiment in a separate branch and gate.

## Required result

Submit model/asset hashes, ABI/IPC contract, exact feature→label comparisons, concurrency/lifecycle evidence and measured adapter overhead if claimed.

## Failure rules

Do not retrain, quantize or replace a decoder to fix a mismatch. Do not add unsafe Send/Sync without proof. Do not infer current ONNX support from a workflow name.

Use the coordinator ledger and evidence templates. Keep the distinction between source-derived observations, runtime observations and design decisions in every report.

