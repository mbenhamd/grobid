# GROBID core audit for a Rust compatibility rewrite

## Scope and evidence

Audited upstream: `grobidOrg/grobid`, commit **`f313f7010773fe8113cbb0f7a774960450a850d0`**, commit timestamp **2026-11-04T09:45:14+01:00**. This is a static source audit of the current tree, with targeted reads of the core pipeline, model adapters, configuration, tokenization, layout, serialization, matching and related build files. It is **not** a runtime parity result, a performance measurement, or a claim that all model binaries have been loaded. The sparse checkout was used for source analysis; the native/model file inventory comes from the Git tree. The versioned source has precedence over stale prose in documentation.

The core production source inventory is **238 Java/Kotlin files and 76,789 physical lines**, including comments and blank lines. Some of the largest files are `BiblioItem.java` (4,737 lines), `FullTextParser.java` (3,681), `TEIFormatter.java` (2,875), `HeaderParser.java` (1,664), `Segmentation.java` (1,345), and `CitationParser.java` (1,102). These are scope measurements, not effort estimates. `model-inventory.json` records model profiles and source checksums; no model weights were evaluated.

## 1. What the rewrite actually replaces

The critical path is a cascade:

1. A service processor borrows a Java `Engine` and creates a request-specific `GrobidAnalysisConfig`.
2. `Engine` delegates to lazy `EngineParsers`; the full-text route calls `FullTextParser`.
3. `DocumentSource.fromPdf` launches the **native pdfalto executable**, which writes ALTO plus optional annotations, metadata, outline and image files.
4. `Document.addTokenizedDocument` parses ALTO through `PDFALTOSaxHandler` into pages, blocks, layout tokens and graphics; separate handlers consume auxiliary XML.
5. `Segmentation` computes document statistics and **line-level** features, runs its tagger and builds document zones.
6. Header regions go through header tagging and nested author, affiliation and date parsing. The abstract is additionally structured with the full-text model.
7. The bibliography is segmented into individual references, parsed by the citation model and optionally consolidated in a batch.
8. Body and annex regions get token-level full-text labels; figure/table parsers, equation extraction and relabeling heuristics operate on those labels. Reference/footnote callout postprocessing follows.
9. `TEIFormatter`, `BiblioItem` and related data classes serialize text, metadata, links, coordinates, funding, acknowledgements, availability/conflict/contribution statements, notes, tables, figures and references. Optional sentence segmentation modifies the mixed-content TEI tree.

This is visible directly in the full-text orchestrator, not an inferred architecture. [Full-text pipeline][S1] [Parser lifecycle][S2] [PDF extraction][S3] [ALTO parsing][S4] [Segmentation][S5]

**Consequence:** a Rust HTTP layer around the same Java engine is only a server migration. A complete JVM-free inference path must replace the Java/Kotlin layout processing, features, parsers, heuristics and serialization as well. Keeping pdfalto, Wapiti and the existing Python/TensorFlow models initially can still yield a JVM-free Rust application; it does not yield a pure-Rust dependency stack. These are distinct milestones and must have separate completion claims.

## 2. Source-backed performance candidates

No production traces or timings were supplied, so none of these is a measured bottleneck on the user's server.

| Stage | What the source establishes | What to measure before changing it |
|---|---|---|
| PDF extraction | A subprocess performs PDF decoding; default timeout is 120 s, memory limit 6,096 MB. Image extraction is conditional. | Child wall/CPU time, page count, output size, peak RSS including the child, storage latency, image handling. A Java-to-Rust change does not remove this work. |
| DeLFT scheduling | `JEPThreadPool` uses **one `newSingleThreadExecutor`**; `call` submits and blocks on `future.get()`. Sequence-tagging calls through this singleton are serialized at the submission level. TensorFlow kernels may still use internal parallelism. | Queue wait versus actual model execution, per-model calls/request, CPU/GPU utilization and batch lengths. This is a concrete candidate for independent Python workers or batching, after parity. |
| Wapiti inference | It is already native code, reached through SWIG/JNI. `TaggerFactory` caches a tagger by model; `WapitiModel.label` trims output and changes separators. | Native decoding time versus Java feature generation, data copying and string rebuilding. Do not assume each engine owns a separate set of model weights. |
| Server admission | Engine borrowing is synchronized; pool exhaustion blocks up to the configured wait. Defaults are concurrency 10 and `poolMaxWait: 1` second. Pool max idle is zero. | Request queue latency, active engines, 503 responses, cold/repeated parser allocation, fair admission under saturation. |
| Consolidation | It makes external Crossref or Glutton requests. Current Crossref code applies tier-dependent submission spacing, concurrency limits and backoff; batch citation processing waits for results. | Disable consolidation for the local CPU benchmark, then benchmark recorded responses and separately measure live external latency. Network speedup must not be attributed to Rust. |
| Output construction | Significant Java string building, regular expressions, matching and document-object transformations remain after tagging. | Per-stage CPU/allocation profiles, especially large bibliography, tables and full-text documents. |
| First request | Parsers/models and some lexicons are lazy; `modelPreload` affects the service. | Cold startup, ready-to-serve time, first-request latency and warmed steady state separately. |

Sources: [JEP executor][S6], [DeLFT label path][S7], [Wapiti wrapper][S8], [Tagger cache][S9], [Engine pool][S10], [default configuration][S11], [Crossref policy implemented in GROBID][S12], [lexicon loading][S13]. The Crossref rates in source are implementation defaults, not a statement about future external service policy.

Instrumentation should emit a request trace with queue wait, PDF conversion, ALTO parse, feature generation per model, model queue wait, model execution, consolidation, postprocessing, TEI serialization and asset packaging. Record hardware, binary/model hashes, document bytes/pages, configuration, thread counts and CPU/GPU runtime. Use wall and CPU time; measure peak and steady memory over the whole process tree. Amdahl's law applies to whatever fraction actually changes.

## 3. Model and profile inventory

`grobid.yaml` and `grobid-full.yaml` each contain **21 entries**: 13 base sequence models, 6 explicitly configured segmentation/header variants, and 2 disabled classifier entries. The Git tree contains **21 `model.wapiti` files and 21 `model_weights.hdf5` files**. Counts of configured entries, available binary artifacts and enum values are different things. There are additional extension/legacy enum names without corresponding default supported models. [Configurations][S11] [Model registry and flavor lookup][S14]

| Base model | Default `grobid.yaml` | `grobid-full.yaml` | DeLFT architecture when selected by that profile |
|---|---|---|---|
| `segmentation` | Wapiti | Wapiti | Configured alternative is `BidLSTM_CRF_FEATURES`; long-sequence CRF is the active default. |
| `fulltext` | Wapiti | Wapiti | No DeLFT definition in these entries. |
| `header` | Wapiti | DeLFT | `BidLSTM_ChainCRF_FEATURES` |
| `reference-segmenter` | Wapiti | DeLFT | `BidLSTM_ChainCRF_FEATURES` |
| `name-header` | Wapiti | Wapiti | Alternative `BidLSTM_CRF_FEATURES` |
| `name-citation` | Wapiti | Wapiti | Alternative `BidLSTM_CRF_FEATURES` |
| `date` | Wapiti | Wapiti | Alternative `BidLSTM_CRF_FEATURES` |
| `figure` | Wapiti | Wapiti | Alternative `BidLSTM_CRF` |
| `table` | Wapiti | Wapiti | Alternative `BidLSTM_CRF` |
| `affiliation-address` | Wapiti | DeLFT | `BidLSTM_CRF_FEATURES` |
| `citation` | Wapiti | DeLFT | `BidLSTM_CRF_FEATURES` |
| `patent-citation` | Wapiti | DeLFT | `BidLSTM_CRF_FEATURES` |
| `funding-acknowledgement` | Wapiti | DeLFT | `BidLSTM_CRF_FEATURES` |
| `copyright` | Disabled (`engine: wapiti`) | Disabled (`engine: wapiti`) | Only a DeLFT classifier exists; configured architecture `gru`. |
| `license` | Disabled (`engine: wapiti`) | Disabled (`engine: wapiti`) | Only a DeLFT classifier exists; configured architecture `gru`. |

Do not implement a fictitious Wapiti copyright or license classifier. `HeaderParser` calls `LicenseClassifier` only when the configured copyright engine is `delft`; the classifier itself creates two DeLFT classifier models. It thresholds probabilities above 0.5. The default and full profiles leave this path inactive. Explicitly enabled optional profiles still need coverage if claimed supported. [Classifier activation][S15]

### Flavor semantics

The flavor enum contains `blank`, `article/light`, `article/light-ref`, `sdo/3gpp` and `sdo/ietf`. Case-insensitive flavor lookup returns null for unrecognized text. Configured segmentation variants are `article-light`, `article-light-ref` and `sdo-ietf`; configured header variants use those same three suffixes. `header-article-light-ref` explicitly stays Wapiti in the default config but inherits DeLFT in the full profile. `header-sdo-ietf` explicitly stays Wapiti in both. Two full-text flavor Wapiti files exist even though they lack dedicated YAML entries. The 3GPP enum declaration is not evidence of a shipped trained model. [Flavor enum and disk check][S14]

`getModelFlavor` selects a flavored model only if an engine-specific disk check succeeds, otherwise it returns the base model. Wapiti uses slash-separated `models/<folder>/model.wapiti`; DeLFT uses a hyphenated model name plus architecture directory. Engine and architecture walk backward through hyphenated ancestors independently. Thus absence of model files, changed model engine and missing inherited architecture all affect output.

Do **not** simply recursively merge the YAML and call that the effective configuration. `getGrobidEngineName` and `getDelftArchitecture` explicitly do field-level prefix lookup. Other getters first select the nearest available model entry and may return `-1` or a default when its nested DeLFT fields are absent. [Property resolution][S16]

A second source-level compatibility candidate needs an oracle probe: `DeLFTModel` converts hyphens to underscores for Python variable names, then passes that normalized name to runtime max-length and batch-size getters; `modelMap` is keyed by the original YAML names. For hyphenated model names, this appears to leave saved-model runtime defaults in effect instead of YAML overrides. Record the actual Python model configuration on the Java baseline before deciding whether to preserve or intentionally change this behavior. [DeLFT initialization][S17] [Model map keys][S18]

`blank` processing builds ALTO-derived raw text into a simple TEI paragraph without the normal labeling cascade. Nevertheless its Java constructor calls the `FULLTEXT` parser superclass, which can initialize that tagger. A smoke check that only observes loaded models is insufficient to prove which models actually ran. [Blank parser][S19]

## 4. Compatibility traps that must become tests

### 4.1 Strings, offsets and token features

**UTF-16 semantics are observable.** `GrobidDefaultAnalyzer` advances offsets by Java `String.length()`. `PDFALTOSaxHandler.addToken` does the same. ALTO subtoken widths are divided proportionally by those lengths. `TextUtilities.prefix/suffix` uses Java substring positions. Rust byte counts and Unicode scalar counts therefore disagree on non-BMP characters. Represent byte, code-point and UTF-16 offsets as distinct types; build a tested conversion layer. Supplementary letters/emoji can split surrogate pairs in legacy prefix features, so capture what is actually passed through JNI, including encoding replacement behavior. Do not guess. [Tokenizer][S20] [ALTO subtoken widths][S21] [Prefix/suffix][S22]

**Normalization is domain-specific, ordered and context-sensitive.** It is not a blanket NFC/NFKC operation. The code normalizes selected whitespace, CRLF/newline characters, dashes, underscores, vertical lines, bullets and parentheses. It preserves some chemical middle dots depending on surrounding characters; the separate `removeSpaces` method deliberately avoids renormalizing an already normalized subtoken. Normalize at exactly the same boundary. Tests should include `MgSO4·12H2O`, full-width punctuation, ligatures, combining marks, nonbreaking spaces, zero-width nonjoiner, CRLF and line breaks. [Unicode rules][S23]

**Whitespace tokens are data.** The default tokenizer uses `StringTokenizer(..., delimiters, true)` and returns delimiters. The label/token synchronizer assigns following whitespace/newline tokens to the preceding labeled container and throws when non-whitespace tokens disagree. Removing whitespace before storing layout tokens destroys output reconstruction. [Tokenizer][S20] [Synchronizer][S24]

**Feature rows are an ABI to trained models.** Column order, capitalization categories, prefix/suffix order, numeric bins, lexicon membership, line/block boundaries, font changes and callout features must match exactly. `FeaturesVectorFulltext.printVector`, for example, emits lexical/lowercase fields, four prefixes, four suffixes, layout/font properties, capitalization/digit flags, punctuation, relative positions, graphic proximity and callout/superscript fields. Several declared fields are commented out of serialization. Match actual emitted columns, not field declarations or comments. Freeze and hash lexicons, templates and normalization rules along with weights. [Full-text features][S25] [Lexicon resources][S13]

The source uses default-locale lowercasing and formatting in places. Pin the baseline JVM locale/timezone and record it; include locale fixtures where compatibility is promised. Do not silently substitute Unicode case folding or locale-independent parsing everywhere and assume it is equivalent.

### 4.2 Labels and sequence boundaries

**GROBID's `I-` marks the beginning of an entity.** Bare labels are continuations. DeLFT `B-` maps to GROBID `I-`, DeLFT `I-` maps to the bare label, and `O` maps to `<other>`. Adjacent identical labels with a start marker form distinct clusters. A standard IOB implementation copied into Rust will merge/split entities incorrectly. [Label constants and conversion][S26] [Clustering][S27]

Preserve blank-line sequence boundaries and order of sequences. Wapiti output is trimmed and ordinary spaces replaced with tabs. DeLFT adds predictions back to original feature rows; if predictions run short, Java writes `<other>` for the excess rows. That behavior deserves a regression case, plus a diagnostic flag, rather than being silently replaced with truncation. A semantic failure must not be normalized out by the comparator. [Wapiti adaptation][S8] [DeLFT row reconstruction][S7]

### 4.3 PDF extraction and geometry

Preserve the **same pdfalto executable and flags** before considering a replacement PDF library. Current defaults include `-fullFontName -noLineNumbers`, conditional `-discardClippedText`, `-onlyGraphsCoord` when images are disabled, optional annotations/outline and `-filesLimit 2000`. The source requires pdfalto >=0.6.3 for `-discardClippedText`. Page range flags are only appended when the supplied values are positive. Compare page-range boundary behavior through the HTTP oracle as well as the core method. [PDF command construction][S3]

Conversion exit 5 is accepted with a warning (ALTO was written, streaming disabled); exit 4 is a write failure and 98 allocation failure. Server/thread modes do not classify every failure identically. Pin the mode. Test timeouts, child termination, interrupted requests, missing executable/library, malformed/truncated ALTO, empty blocks, token/block limits and cleanup after every failure. Do not convert all nonzero statuses into one generic parse error. [PDF subprocess status mapping][S28]

The ALTO XML reader intentionally ignores malformed/unmappable UTF-8 sequences in the main ALTO stream; annotation/outline/metadata parse failures may only warn. A strict Rust XML reader may reject inputs Java tolerates. Capture those cases and decide any hardened-mode deviation explicitly. [ALTO reader][S4]

Coordinates are part of the product contract: page index, top/left origin conventions, boxes spanning lines/pages, proportional subtoken widths, superscript/subscript and rotated-font handling. `BoundingBox.toString` formats coordinates to two decimal places; lists join boxes with `;`. JSON representation exposes numeric coordinates separately. Compare both underlying geometry and each wire representation; do not hide coordinate differences behind an arbitrary large tolerance. [Geometry serialization][S29]

Asset handling also has semantics: files are copied or JPEG/PPM converted to PNG depending on `preprocessImages`, SVGs are skipped in a relevant copy path, and graphic references are rewritten to asset paths. Validate archive member names, image pixel data, graphic links and cleanup separately from ZIP timestamps/compression bytes. [Assets][S30]

### 4.4 Higher-level extraction and output

The normal full-text pipeline relabels invalid repeated figure/table starts, rejects incomplete figures/tables, sometimes reverts their text to paragraphs, reassigns body IDs and separately processes annex figures/tables/equations. Kotlin `LabelUtils` implements part of this behavior; a Java-only port checklist misses it. [Full-text postprocessing][S1] [Kotlin relabeling][S31]

Citation callouts are not a simple integer-to-reference dictionary. `ReferenceMarkerMatcher` distinguishes author/year, numeric and unknown styles; range expansion is bounded by `MAX_RANGE = 20`; matching uses Lucene `ClassicAnalyzer`, term queries and ranked results. Replace that with an independently tested equivalent matcher, preserving ambiguous-candidate ordering and tie behavior. A newer search engine's default ranking is not a compatible substitute. [Reference marker matching][S32] [Lucene matching][S33]

Sentence splitting is a separate inference dependency. The default OpenNLP adapter loads `grobid-home/sentence-segmentation/openNLP/en-sent.bin`, constructs a detector per call, converts spans and trims them. `SentenceUtilities` prevents sentence boundaries inside protected spans and attaches some superscript citation markers. `TEIFormatter` reconstructs mixed-content `<s>` elements around references. A generic Rust sentence segmenter changes the output contract. Cybozu language profiles and any configured alternative detector are additional artifacts. [OpenNLP adapter][S34] [Sentence corrections][S35]

TEI includes inherently variable producer metadata: `TEIFormatter` inserts current UTC time at `application/@when`, version/revision and request parameters; optional text IDs use generated keys. `generateIDs=false` does not establish that all IDs in every output are deterministic. Preserve graph structure: stable bibliography/figure/table/note IDs and every `target` edge are meaningful. Permit only narrowly enumerated, source-justified normalizations, with a one-to-one generated-ID mapping and target rewriting. Never erase all IDs, all attributes or all whitespace. XML canonicalization alone does not solve nondeterminism and broad whitespace normalization destroys mixed-content text. [Producer metadata][S36] [Request analysis flags][S37]

Full-text reference consolidation mode 1 calls `BiblioItem.correct`; mode 2 only injects identifiers. External response order, validation, failure and timeout behavior matter. Use a deterministic replay transport preserving the exact request/response fixtures; independently test a small authorized live smoke suite if needed. [Consolidation in full-text pipeline][S1]

## 5. Native and language-runtime boundary plan

Recommended staged target, explicitly a design proposal:

| Boundary | First compatibility implementation | Later optimization condition |
|---|---|---|
| pdfalto | Execute the exact pinned binary with preserved options, resource limits, output handlers and cleanup. | A different extractor must pass layout-token, feature, label, TEI and geometry gates on the frozen corpus. |
| Wapiti | Build a narrow C ABI shim from the **GROBID-specific Wapiti fork**, retain exact models/templates, use opaque handles and explicit buffer ownership. | Rust CRF decoding only after exact labels, score/tie behavior, model loading and feature/template expansion are proven. |
| DeLFT | Keep the pinned Python/TensorFlow/DeLFT model stack in a supervised local worker with a versioned feature-input/prediction-output protocol. Reproduce padding, batching, max-length and BIO conversion. | ONNX or native Rust inference is a separate model-runtime migration with its own numeric, decode and end-to-end gates. HDF5 weights are not a guarantee of lossless automatic export. |
| Sentence/language inference | Port or adapt the actual chosen algorithms and artifacts; use a declared temporary bridge only while building parity. | Replacement algorithms require explicit feature scope and quality comparison; a retained JVM bridge means the JVM-free gate is still red. |
| Matching/serialization | Port deterministic behavior in small units with token/structure snapshots. | Optimize allocations/indexing only while the differential tests stay green. |

The JNI library file is not itself a promised stable Rust C ABI. Inspect/export a supported narrow wrapper; do not call arbitrary JNI entry points as if they were ordinary C model APIs. Establish Wapiti thread-safety and allocator ownership from the fork and sanitizers before implementing `Send`/`Sync`. Use bounded workers and per-request cancellation; never let a stalled Python task or child process outlive its budget indefinitely. [GROBID-specific Wapiti fork][S38]

The DeLFT Dockerfile pins TensorFlow **2.17.1**, DeLFT **0.4.7** and JEP **4.3.1**, while Gradle declares JEP **4.3.2**. It preloads GloVe resources through a registry. Container builds also use mutable package downloads/base tags. A Git SHA alone therefore does not fix the entire runtime: record image digest, complete Python environment, embeddings/preprocessors/model files, native hashes, resource registry, architecture and GPU details. These are observed pins in this commit, not recommendations for arbitrary new deployments. [Docker runtime][S39] [Gradle JEP declaration][S40]

CRF++ still has Java code and native artifacts, but upstream documentation says its use has not been supported since 0.4. Distinguish active server parity, optional configured backends and historical Java compatibility. Do not mark legacy code as implemented just because an enum and a class exist; record unsupported/untested surfaces explicitly. [Legacy status][S38]

## 6. Intermediate oracle the repo already provides

`debugMode` is particularly valuable for this port. `AbstractParser.labelAndCapture` records the raw tagger result in `DebugLabelingCollector`: token + feature columns + predicted label. The collector preserves model-key insertion order and invocation order within each model; repeated citation invocations remain separate list entries. This provides a usable intermediate differential surface before TEI output. [Capture hooks][S41] [Collector contract][S42]

Coverage is not automatic: paths that use no-config overloads can omit captures, and `DebugCaptureContext` warns about these. Assert the expected model keys and invocation/row counts for each fixture. A missing capture is a failing evidence gap, not an empty successful result. Add a test-only exporter for ALTO-derived layout-token properties, document zones, exact feature input before labeling, parsed entities and final link graph. Keep the original oracle build immutable; instrumentation should be in a separate, fingerprinted oracle variant and prove the instrumentation does not alter normal output.

Useful layered gates:

1. **Extraction gate:** same PDF/options -> same normalized ALTO and layout-token sequence/properties.
2. **Feature gate:** same layout/raw text -> identical feature rows and sequence boundaries.
3. **Backend gate:** same feature bytes and model hashes -> same per-token labels; verify empty, long and multi-sequence cases.
4. **Parser gate:** same tokens and labels -> same entities, document pieces, figure/table decisions and citation graph.
5. **Output gate:** same structures -> exact contract bytes where deterministic; narrowly normalized TEI/JSON/ZIP comparisons where justified.
6. **End-to-end gate:** all declared routes/options/profiles across frozen, licensed test corpora, including adversarial/error cases, with zero unexplained mismatches.
7. **Runtime gate:** concurrency, cancellation, bounded memory/temporary storage, restart, error behavior and process cleanup match the declared compatibility and reliability contract.
8. **Performance gate:** warmed and cold comparisons under identical quality/model/options, including full process memory and tail latency; no speedup claims if output coverage differs.

The baseline itself must be run repeatedly to characterize nondeterminism. Keep deterministic fixture comparisons separate from quality metrics on expert annotations. Matching Java output proves implementation compatibility on the corpus; F1 against gold annotations measures extraction accuracy. Neither proves equivalence for every possible future PDF.

## 7. Recommended work partition

Port boundaries that are independently testable; prevent simultaneous edits to shared models or global source modules.

- **Oracle/config owner:** fingerprint all artifacts, capture effective configuration, profile availability, debug dumps and admissible nondeterminism; maintain the capability manifest.
- **Text/layout owner:** UTF-16 compatibility, normalization, ALTO SAX semantics, geometry, page/block/token IDs and resource limits.
- **Feature/backend owner:** feature serializers, lexicon matching, native Wapiti bridge, supervised DeLFT protocol and exact label semantics.
- **Parser/output owner:** small text parsers first, then bibliography/header, full-text structure, figures/tables, sentence segmentation and TEI/BibTeX/annotation serialization.
- **Integration/release owner:** REST variants, assets, training/API lifecycle, differential CI, packaging, process model and performance.

Do not parallelize changing both sides of a differential test. Freeze the oracle and review normalization changes separately. If a task cannot obtain its upstream model, fixture or algorithm, record the missing capability as blocked with concrete evidence and work on another ready task. No stub, constant output, fallback to Java or skipped test can satisfy the JVM-free parity gate.

## Source references

All code links below are pinned to the audited commit.

[S1]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/engines/FullTextParser.java#L96-L435
[S2]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/engines/EngineParsers.java#L35-L303
[S3]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/document/DocumentSource.java#L71-L240
[S4]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/document/Document.java#L310-L445
[S5]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/engines/Segmentation.java#L110-L174
[S6]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/jni/JEPThreadPool.java#L34-L85
[S7]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/jni/DeLFTModel.java#L154-L248
[S8]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/jni/WapitiModel.java#L28-L85
[S9]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/engines/tagging/TaggerFactory.java#L39-L88
[S10]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/factory/GrobidPoolingFactory.java#L57-L118
[S11]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-home/config/grobid.yaml#L13-L385
[S12]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/utilities/crossref/CrossrefClient.java#L60-L222
[S13]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/lexicon/Lexicon.java#L50-L307
[S14]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/GrobidModels.java#L37-L241
[S15]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/engines/HeaderParser.java#L369-L379
[S16]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/utilities/GrobidProperties.java#L920-L1055
[S17]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/jni/DeLFTModel.java#L49-L108
[S18]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/utilities/GrobidProperties.java#L279-L299
[S19]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/engines/FullTextBlankParser.java#L51-L145
[S20]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/analyzers/GrobidDefaultAnalyzer.java#L61-L123
[S21]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/sax/PDFALTOSaxHandler.java#L480-L554
[S22]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/utilities/TextUtilities.java#L1267-L1295
[S23]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/utilities/UnicodeUtil.java#L188-L264
[S24]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/tokenization/TaggingTokenSynchronizer.java#L90-L136
[S25]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/features/FeaturesVectorFulltext.java#L64-L186
[S26]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/jni/DeLFTModel.java#L502-L513
[S27]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/tokenization/TaggingTokenClusteror.java#L77-L104
[S28]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/document/DocumentSource.java#L279-L373
[S29]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/layout/BoundingBox.java#L255-L275
[S30]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/engines/Segmentation.java#L177-L273
[S31]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/kotlin/org/grobid/core/utilities/LabelUtils.kt#L21-L100
[S32]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/utilities/matching/ReferenceMarkerMatcher.java#L49-L185
[S33]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/utilities/matching/LuceneIndexMatcher.java#L118-L173
[S34]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/lang/impl/OpenNLPSentenceDetector.java#L44-L80
[S35]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/utilities/SentenceUtilities.java#L118-L251
[S36]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/document/TEIFormatter.java#L942-L965
[S37]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/engines/config/GrobidAnalysisConfig.java#L52-L114
[S38]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/doc/Recompiling-and-integrating-CRF-libraries.md#L3-L63
[S39]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/Dockerfile.delft#L94-L154
[S40]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/build.gradle#L246-L256
[S41]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/engines/AbstractParser.java#L73-L105
[S42]: https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/engines/config/DebugLabelingCollector.java#L27-L62
