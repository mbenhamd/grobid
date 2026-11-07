# Target architecture and migration boundaries

## Design purpose

Keep the document/model contract stable while replacing Java orchestration, transformations and service code in Rust. The native extractor and inference runtimes form explicit, hash-pinned boundaries. This lets the team isolate implementation drift from changes in PDF extraction or model behavior.

The upstream maps and exact quirks are in `audit/`. This document is the proposed implementation design, not a claim that the Rust components already exist.

## Crate map

| Proposed crate | Responsibility | Boundary and tests |
| --- | --- | --- |
| `grobid-compat` | UTF-16 indices, Java numeric/string/regex compatibility, locale and ordered collections | Pure fixture differentials against Java utility outputs |
| `grobid-types` | Immutable document/layout/token, spans, geometry, model IDs and config types | Serialization round trips, index/geometry invariants |
| `grobid-config` | Upstream YAML, effective per-getter model/flavor resolution, asset manifest | Java effective-config snapshots; absent/partial override cases |
| `grobid-pdf` | Isolated pdfalto subprocess, limits, ALTO and sidecars, resource cleanup | Exact argv/environment; output/exit-code/lifecycle corpus |
| `grobid-features` | Lexicons and per-model feature generation | Exact rows/columns, line separators, token alignment |
| `grobid-models` | Labeler/classifier traits and model registry | Wapiti/DeLFT differential labels and lifecycle |
| `grobid-wapiti-sys` | Minimal C bindings/build adapter only | ABI/ownership/sanitizers/concurrency; no document logic |
| `grobid-pipeline` | Parser cascade and clustering, bibliographic/author links, geometry | Stage-by-stage document state oracle |
| `grobid-tei` | TEI, BibTeX and other supported serializers | Mixed-content, ID graph, exact fields/order/escaping |
| `grobid-integrations` | Crossref/glutton, language and sentence adapters | Recorded network contract and detector goldens |
| `grobid-service` | HTTP, multipart, admission, health, metrics and shutdown | Actual route/content/status/default matrix |
| `grobid-training` | Registry, data alignment, trainers, promotion, jobs and evaluation | Fixed split/data artifacts, lifecycle and metric parity |
| `grobid-cli` | Batch, train/eval, config inspection and diagnostic entrypoints | Command/argument/output/exit-code fixtures |

Start with fewer crates if necessary to reduce build friction, but preserve these module boundaries. Split only when an ownership or compilation benefit is concrete. Keep HTTP types out of the pipeline and model-specific buffers out of generic document types. Pin the Rust toolchain and dependency versions when scaffolding; commit `Cargo.lock`. These are architectural choices, not assertions about the latest available crate releases.

## Proposed runtime

Use an async HTTP runtime for transport and bounded admission. Hand CPU/native work to explicit blocking workers. Assign each request a cancellation/deadline context and unique temporary directory. A document owns immutable layout tokens and indexed spans; avoid copying the same text through every stage, but only optimize after the first parity baseline. Do not introduce a new intermediate representation that loses layout/style fields.

`pdfalto` remains a subprocess. Pin executable, language data, `xpdfrc`, flags and environment, including temp directory behavior. Wapiti uses an audited C ABI shim or isolated process if necessary; the choice follows investigation of the actual fork, not an assumption that existing JNI symbols are directly reusable. A DeLFT worker runs the same Python package, model files and preprocessing without Java. First reproduce its serialized scheduling, then measure batching or multiple workers as a separate change.

Suggested interfaces are contracts, not ready-to-compile code:

```rust
trait SequenceLabeler {
    // Input represents exact upstream feature rows and sequence boundaries.
    fn label(&mut self, input: &FeatureSequence, ctx: &RequestContext)
        -> Result<LabeledSequence, ModelError>;
}

trait DocumentExtractor {
    fn extract(&self, pdf: &InputPdf, options: &PdfOptions,
               ctx: &RequestContext) -> Result<ExtractedDocument, PdfError>;
}
```

Do not add `Send + Sync` to those traits until the adapter can meet the contract. Whether models are immutable and shareable or need per-worker state must be established from native source and a concurrent differential run. Define errors at the originating layer and map them at the service boundary; keep diagnostic details separate from externally observed bodies.

## Freeze the data plane

The oracle must export PDF sidecars, ordered `LayoutToken` snapshots, features, label sequences, clusters, bibliographic/link structures and serialized outputs. Current `debugMode` is a useful partial source of feature/label dumps; it is not a complete token/layout oracle, and overloads can miss captures. Assert the expected model names and invocation counts before trusting a debug trace.

Treat all offsets as typed units. Preserve page indexing separately from PDF page selection arguments and coordinate conventions. Carry a source-token span through transformations so a bad TEI field can be traced back to its first divergent token/label. Do not merge words, normalize whitespace or replace the PDF extractor simply because the final text appears similar.

## Profiles and optional boundaries

The primary initial lane uses the committed default CRF configuration. A second lane uses the full DeLFT configuration; a third evaluates the evaluation configuration independently rather than assuming it equals full. Flavors and supported detector/classifier alternatives add required rows. Preserve configured-but-disabled classifier behavior distinctly from active model inference.

The legacy Java library is a separate external surface. A Rust shared library with an optional thin Java/JNI facade can preserve selected Java embedding APIs while the standalone server remains JVM-free. Inventory all exposed methods and serialization expectations before choosing this route. No Java facade is built into this starter kit. If its scope proves disproportionate, obtain an explicit scope decision and keep S3 blocked; never silently redefine "whole repository" as "two HTTP endpoints".

## Integration rules

Freeze common types and trait signatures before parallel implementation. Every shared-interface change must include migration notes and fixture compatibility. Use serial integration into the coordinator branch. Keep upstream code as the readable reference until all milestones pass. A runtime fallback to the Java oracle is permitted only in development with prominent counters and tests asserting it is disabled for release.

See ADRs 0002, 0003, 0005, 0007, 0010 and 0015 for alternatives and consequences.
