# GROBID testing, training, evaluation, and dependency audit

Audit date: 2026-11-06. Upstream: `grobidOrg/grobid`, commit `f313f7010773fe8113cbb0f7a774960450a850d0` (2026-11-04), declared version `0.9.2-SNAPSHOT`. This is a source audit, not a performance measurement or a successful execution of the upstream test suite. Source and test files were inspected locally; large model/corpus blobs were inventoried from the Git tree rather than downloaded. The accompanying `test-inventory.json` records the inventory and source URLs. All recommendations below are proposed acceptance rules, not claims that the rewrite has passed them.

## 1. What the repository actually contains

A Git-tree inventory at the pinned commit finds 13,904 tracked entries. Java/Kotlin production source counts are 238 in `grobid-core`, 32 in `grobid-service`, and 69 in `grobid-trainer`. The trainer is a real subsystem and cannot disappear from an unqualified whole-project parity claim.

| Test module | Java/Kotlin test-source files | Files containing `@Test` | Uncommented `@Test` declarations | `@Ignore` declarations |
|---|---:|---:|---:|---:|
| Core | 100 | 94 | 714 | 28 |
| Service | 10 | 9 | 55 | 2 |
| Trainer | 9 | 9 | 63 | 1 |
| Total | 119 | 112 | 832 | 31 |

These are comment-aware lexical **declaration** counts, not test discovery, execution, or passing counts. They include 26 `@Test` declarations inside seven ignored core classes. Some test-source files are setup helpers, commented experiments, or benchmarks. The build's comment describing a previous local run of 812 tests across 109 classes is historical evidence, not the current audited count. See [build.gradle:285–321](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/build.gradle#L285-L321).

There are 68 non-Java/Kotlin test-resource entries in core, 15 in service, and eight in trainer. These counts include resources of different kinds and must not be presented as document counts. The trainer dataset tree contains 12,134 entries, including 26 `.template` files; it contains XML annotations, raw feature data, links/placeholders, and editorial files, not 12,134 unique PDFs.

| Training dataset family | Tracked entries |
|---|---:|
| acknowledgment | 1 |
| affiliation-address | 1,132 |
| citation | 472 |
| date | 358 |
| ebook | 3 |
| entities | 357 |
| figure | 46 |
| fulltext | 417 |
| funding-acknowledgement | 5 |
| header | 3,398 |
| name | 1,170 |
| patent | 288 |
| reference-segmenter | 284 |
| segmentation | 4,136 |
| shorttext | 16 |
| table | 51 |

Reproduce tree-derived counts with `git ls-tree -r --name-only <pinned-sha>`; do not infer coverage from file totals. Before training, enumerate actual examples, shared files and symlinks, filtering rules, encoding, and train/eval memberships using the upstream loaders.

## 2. Existing tests are valuable but do not establish complete parity

The existing suite supplies useful executable examples for feature generation, tokenization, SAX parsing, bibliographic objects, date/name/affiliation parsers, citation context processing, table geometry, sentence splitting, model statistics and web content negotiation. Kotlin tests also cover fulltext behavior and funding acknowledgements; a Java-only scan misses eight Kotlin test files.

Several prominent coverage limitations are explicit in source:

* `DeLFTTaggerIntegrationTest` is class-ignored because it needs a JEP/DeLFT environment. Its sole test only invokes date parsing and prints output. [Source:30–61](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/test/java/org/grobid/core/engines/tagging/DeLFTTaggerIntegrationTest.java#L30-L61).
* `engines/EngineTest` and `GrobidPropertiesTest` are class-ignored; `UnicodeUtilTest` is also class-ignored. Preserve these as audit gaps until behavior is captured from the oracle, not as proof of correct behavior.
* The Crossref integration test is ignored because the remote API is unreliable. A live third-party API cannot be the sole reproducible baseline. [ConsolidationIntegrationTest:47](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/test/java/org/grobid/core/utilities/ConsolidationIntegrationTest.java#L47).
* The REST patent ST.36 test is ignored. One BibTeX references example has `@Ignore` but no active `@Test`, so blindly subtracting ignored annotations from test annotations is wrong. [GrobidRestServiceTest:203–210,426–427](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-service/src/test/java/org/grobid/service/tests/GrobidRestServiceTest.java#L203-L210).
* Several success-path service tests check only that a response is non-null. Others assert content types, exact BibTeX fields, debug sections, and unknown debug models. The former are smoke checks, not output equivalence. [Service tests:100–200](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-service/src/test/java/org/grobid/service/tests/GrobidRestServiceTest.java#L100-L200).
* The author-affiliation suite explicitly marks an intended but unimplemented behavior: rescuing an orphan affiliation can associate it with an author whose footnote marker did not claim it. An agent must not use this disabled desired behavior as the frozen oracle expectation. [AuthorAffiliationAssignerTest:172–194](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/test/java/org/grobid/core/data/util/AuthorAffiliationAssignerTest.java#L172-L194).
* `PragmaticSentenceOffsetsBenchmark` is intentionally ignored and explicitly has no assertions on timing. It is not a release performance gate. [Source:27–48](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/test/java/org/grobid/core/lang/impl/PragmaticSentenceOffsetsBenchmark.java#L27-L48).

Port tests where they constrain behavior, but additionally build differential fixtures from each public operation, model profile, and relevant option. Keep an explicit feature-to-test mapping: `not captured`, `captured`, `implemented`, `passing`, and `blocked` are different states. A missing model, skipped test, empty corpus or unsupported endpoint cannot count as a pass.

## 3. Build, CI, and dependency baseline

The pinned build uses Java 21, Kotlin 2.4.10, Gradle 9.6.1, JUnit 4 through Vintage plus JUnit 5, Mockito, XMLUnit and JaCoCo. Tests share one JVM per test task (`forkEvery=0`), a 1 GiB heap, explicit Mockito instrumentation and native library paths. A rewrite comparison must separate Java cold start, model cold load and steady-state request latency. [Build plugins and toolchain](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/build.gradle#L28-L34), [toolchain and test dependencies](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/build.gradle#L184-L244), [wrapper](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/gradle/wrapper/gradle-wrapper.properties#L1-L9).

The regular CI matrix runs Ubuntu x86-64, Ubuntu ARM64, macOS ARM64 and macOS Intel with Temurin 21. It runs `spotlessCheck`, `assemble test`, and publishes XML test reports. Coverage runs only on the Ubuntu x86-64 leg; other legs pass `-PskipCoverage`. There is no reason to replace this with a Linux-only inference smoke test and still describe full platform parity. [ci-build-unstable.yml:10–65](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/.github/workflows/ci-build-unstable.yml#L10-L65).

Native and runtime dependencies must be pinned separately from Java source:

* The Git tree includes 86 model-directory entries, 13 native-library entries, 266 pdfalto entries, 50 lexicon entries, 53 language-detection entries and 38 sentence-segmentation entries. A sparse checkout lacking them is not evidence they are absent upstream. Record SHA-256 of the actual selected artifacts as well as their Git object identities.
* Wapiti is GROBID's specific fork with JNI/SWIG mappings and fixes. CRF++ is deprecated and explicitly unsupported in documentation, despite remaining code, factory branches and binaries. Declare whether the rewrite covers current documented runtime, every compiled legacy branch, or both; do not silently make a legacy branch disappear. [CRF library documentation:3–11,61–71](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/doc/Recompiling-and-integrating-CRF-libraries.md#L3-L11).
* The DeLFT image installs Python 3.11, TensorFlow 2.17.1, DeLFT 0.4.7 and Python JEP 4.3.1. The Gradle Java JEP artifact is 4.3.2. Capture this actual combination rather than normalizing the versions in prose. The image preloads GloVe 840B embeddings from an external registry; weights alone are insufficient for inference. [Dockerfile.delft:94–157](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/Dockerfile.delft#L94-L157), [build.gradle:255](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/build.gradle#L255).
* `.github/workflows/ci-build-manual-onnx.yml` references `Dockerfile.onnx` and an ONNX-specific branch; that Dockerfile, ONNX models and an ONNX tagger are absent from this pinned main tree. The workflow file alone is not evidence of shipped ONNX parity. [Workflow:1–16,64](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/.github/workflows/ci-build-manual-onnx.yml#L1-L16).

External services include Crossref and optionally biblio-glutton. Their live data, rate limiting, retries, timeouts and network latency are part of operating behavior; use replayed, versioned responses for deterministic comparisons and separate live integration runs. The default YAML selects Crossref, a Cybozu language detector and OpenNLP sentence splitting; other implementations need their own profile coverage. [Configuration:30–93](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-home/config/grobid.yaml#L30-L93).

## 4. Training and model lifecycle are required features

`TrainerRegistry` has 26 recognized names: 18 standard/alias names and eight flavor names. Aliases include `affiliation`/`affiliation-address` and `patent`/`patent-citation`. The REST processor claims the lowercased requested model name, not the resolved trainer identity; exercise concurrent alias requests because they can refer to the same artifact with distinct claim keys. Canonicalizing those locks is a potential safety improvement that needs a declared deviation. Standard families are affiliation, chemical, citation, date, figure, fulltext, funding acknowledgement, header, monograph, citation names, header names, patent citations, reference segmentation, document segmentation, shorttext and table. Flavor names cover fulltext light/light-ref, header IETF/light/light-ref and segmentation IETF/light/light-ref. The registry is shared by CLI and REST. [TrainerRegistry:23–76](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-trainer/src/main/java/org/grobid/trainer/TrainerRegistry.java#L23-L76).

The CLI supports train, evaluate, split/train/evaluate and n-fold evaluation. Relevant controls include incremental training, split ratio, fold count, Wapiti epsilon/window/iterations and custom model path. Gradle registers 22 model-training tasks plus JATS/TEI evaluation and DOI-matching tools. [TrainerRunner:34–218](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-trainer/src/main/java/org/grobid/trainer/TrainerRunner.java#L34-L218), [build.gradle:651–825](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/build.gradle#L651-L825).

Full parity must cover:

1. TEI annotation parsing into labeled examples; exact token/label alignment, example boundaries, sequence labels and feature columns; CRF template interpretation and lexicon lookups.
2. Training dispatch to Wapiti/DeLFT, parameter propagation, incremental loading, model-format compatibility and prediction with generated models.
3. Evaluation metrics at token, field and instance levels, including empty inputs and zero denominators; train/eval split membership and n-fold grouping.
4. Default `.new`/`.old` model replacement, explicit output path behavior, rollback and reload behavior. Do not pretend two `renameTo` calls with warning-only failure handling are a transactional swap. [AbstractTrainer:113–195](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-trainer/src/main/java/org/grobid/trainer/AbstractTrainer.java#L113-L195).
5. REST async task creation, per-model claims, listing, token status, restart behavior, failure, cancellation and ZIP model download; generation of zipped training artifacts from input PDF. No task may be marked done just because HTTP accepted it.

Important nondeterminism and quirks:

* Random split selection uses `Math.random()`; n-fold loading uses Java's `Collections.shuffle(..., new Random(839374947498L))`. A Rust RNG with the same integer seed is not the same sequence. Reproduce Java PRNG/shuffle semantics or record and replay explicit split membership for the comparison. [AbstractTrainer:534–587,797–809](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-trainer/src/main/java/org/grobid/trainer/AbstractTrainer.java#L534-L587).
* Trainers commonly call `File.listFiles()` without sorting. A reproducibility harness should capture effective file order before changing it; order can influence training and split membership.
* Training weights are not a sensible universal byte-equivalence target across hardware/framework kernels. Require exact data/features/labels/parameters and same-runtime interoperability first; separately establish repeated-run variability and a preregistered quality bound for any stochastic backend change. Fixed existing weights and deterministic decoding should still produce exact labels.
* `killTraining` explicitly warns that interrupting the Java future may leave native training running. It can report `killed` optimistically. Fixing process cancellation is desirable, but is a documented behavior change, not evidence of literal parity. [GrobidRestProcessTraining:464–506](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-service/src/main/java/org/grobid/service/process/GrobidRestProcessTraining.java#L464-L506).
* The `TrainerRunner` n-fold `-o` branch checks an existing path but does not run evaluation; the split-training implementation uses default model paths even though CLI accepts a custom path. Capture observed behavior and record a decision before implementing a different contract. [TrainerRunner:183–214](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-trainer/src/main/java/org/grobid/trainer/TrainerRunner.java#L183-L214), [AbstractTrainer:211–253](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-trainer/src/main/java/org/grobid/trainer/AbstractTrainer.java#L211-L253).

The current training tests already encode important restart and stale-lock behavior: orphaned `ongoing` files must not appear in live task listings; cancellation can update stale status; traversal-like tokens are rejected; completed tokens retain their status. Preserve these checks and add native worker termination/cleanup assertions for any deliberately safer implementation. [Training task tests:53–120](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-service/src/test/java/org/grobid/service/process/GrobidRestProcessTrainingTasksTest.java#L53-L120).

## 5. End-to-end evaluation and why it is insufficient alone

The canonical evaluation collection is now `sciencialab/grobid-evaluation` on Hugging Face, not just the historical Zenodo archive. Nominal collections total 5,927 articles:

| Collection | Articles | Main role |
|---|---:|---|
| PMC_sample_1943 | 1,943 | Diverse journals, publisher layouts |
| biorxiv-10k-test-2000 | 2,000 | Preprints and statement annotations |
| PLOS_1000 | 1,000 | Publisher layout, explicit author-affiliation links |
| eLife_984 | 984 | Publisher layout and richer reference XML |

[Source: dataset documentation:13–71](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/doc/End-to-end-evaluation.md#L13-L71). These are nominal upstream counts; the downloaded immutable manifest must establish the actual eligible PDFs and gold XML. The external dataset was not downloaded or scored during this audit.

The evaluation has field-level strict/soft/Levenshtein/Ratcliff-Obershelp matching, instance-level results and citation-context evaluation. It scores selected fields and has per-corpus exclusions where gold data is not usable. Thus matching F1 can hide incorrect document ordering, coordinates, whitespace, omitted unsupported fields, broken IDs or links, ZIP assets, HTTP behavior and training regressions. **Gold quality and Java/Rust differential equivalence are separate gates.** The latter compares the Java output to Rust output; the former compares each to independent annotations.

Upstream CI supports CRF/DeLFT profiles, light flavors and optional glutton consolidation; it shards prediction and scores the aggregate. The source currently sets dataset revision to moving `main`, so pin a dataset commit and file SHA-256s in the rewrite. [evaluation.yml:25–89](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/.github/workflows/evaluation.yml#L25-L89).

A critical gate defect to avoid copying: the evaluation task can exit zero after processing errors. Upstream CI verifies nonzero TEI output but only warns when fewer TEIs than PDFs were produced; it checks that the score report contains a heading. The report comparison script renders deltas without enforcing a regression threshold. A successful workflow therefore does not imply all documents processed or no accuracy regression. [evaluation.yml:373–390,450–469](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/.github/workflows/evaluation.yml#L373-L390), [compare_reports.py:199–212](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/.github/scripts/evaluation/compare_reports.py#L199-L212).

## 6. Proposed evidence gates

### Gate A: reproducible oracle

Lock source commit, complete effective YAML, model/lexicon/template/embedding/native binary hashes, platform, CPU features, locale, timezone, framework versions and compiler/build flags. Run the same case at least twice against Java to detect instability. Freeze raw request/response bytes and stage outputs. Keep consolidation disabled in the offline profile; build an independent replay profile for each recorded network interaction. Do not call a skipped or unavailable profile passing.

### Gate B: contract and deterministic stages

Test every route/method/consumes/produces combination; defaults, missing and repeated fields, malformed numbers/booleans, unsupported flavors, unknown debug model, content negotiation, empty input, 204/400/409/500/503 behavior, status/error media types, filename headers, saturation and cleanup.

At algorithm boundaries compare exact layout tokens, page/block identity, coordinates as represented by the baseline, UTF-16 offsets, normalization, feature rows, label sequences and parsed intermediate structures. Compare fixture cardinality and stable document identity before comparing scores. Port the upstream tests but keep the independent differential fixtures immutable to implementation agents.

### Gate C: serialization and artifacts

Byte comparison is the default. For XML, conservative canonicalization may remove attribute-order or equivalent lexical differences, but must preserve mixed-content whitespace, text/tails, order, IDs, targets and coordinates. For JSON, compare structure with array order and numeric values; reject duplicate keys and non-standard NaN/Infinity. For ZIP, compare complete logical member sets and contents while ignoring only container metadata, detecting duplicates and traversal entries. Preserve all raw bytes alongside any normalized view. PDF annotations require bytes initially, followed by a separately validated semantic PDF comparator if baseline metadata makes bytes unstable; do not treat a text extractor as a PDF annotation comparator.

No global UUID removal, whitespace collapse, numeric rounding, coordinate epsilon or deletion of timestamps is allowed just to make mismatches disappear. Any normalization needs independent Java/Java evidence, an exact field scope, cross-reference preservation tests and a documented semantic reason. Detect empty test sets, missing cases, duplicate identifiers, malformed fixtures, unexplained skips and request-hash mismatches as failures.

### Gate D: quality and training

Run all four immutable evaluation corpora on both implementations with identical profiles and inputs. Require no unexplained per-document output differences for deterministic stages, no new document failures and no field-level regression hidden by averaging. Preserve every per-document discrepancy for triage. For stochastic replacement backends, define and review the variability experiment and acceptance threshold before results are observed; this yields bounded empirical parity, never mathematical proof on arbitrary PDFs.

Train a small representative model end to end, validate model loading in the alternate implementation, compare generated feature/label streams and fixed-weight predictions, test saved model rollback and a full async lifecycle. Expand to every supported trainer/profile before claiming whole-project parity. Count unsupported legacy cases explicitly.

### Gate E: performance and durability

Use identical machine/container quotas, corpus, profile, worker count, request options and native artifacts. Report cold startup, model load and warm request p50/p95/p99 separately; throughput in documents/s and pages/s; completed/failed/timeout counts; total CPU time; service plus child-process RSS; allocations; I/O; queue delay; time in pdfalto, preprocessing, tagging, postprocessing and consolidation. Pair runs and repeat with shuffled order. Do not change the OCR/native converter, weights, precision, features or consolidation between speed comparisons unless clearly reported as a separate experiment.

First measure the user's slow workload. Java is only one part of the pipeline; a Rust HTTP shell cannot remove time in native PDF processing, deep models or remote consolidation. The README's historical 10.6 PDF/s report is not a current benchmark for the user's hardware. [Readme:85–97](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/Readme.md#L85-L97).

Use a staged soak: bounded concurrency under steady load, bursts, deliberate overload, worker failures, timeout/cancellation and repeated large/pathological PDFs. Check that engine slots, file handles and subprocesses return to baseline and temporary files are removed; test service restart during training and inference. Choose speed targets after baseline capture; enforce parity before crediting a speedup.

## 7. License and data provenance

The project documents Apache-2.0 for its code, CC0 for documentation and CC-BY for annotations. Preserve attribution and per-file exceptions during translation. [Readme:139–145](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/Readme.md#L139-L145). The evaluation docs describe the source materials and additional annotations as CC-BY; maintain original article provenance in corpus manifests. Do not infer that arbitrary production PDFs are redistributable simply because the public benchmark is reusable.

The separate [pdfalto repository](https://github.com/kermitt2/pdfalto) declares GPL-2.0. The GROBID Apache license is not a license statement for every binary, font map, model, embedding or runtime bundled with it. Keep an artifact/license manifest and the separately invoked converter's notices; investigate each redistributed dependency's own license at its pinned revision. This audit does not establish complete third-party license clearance.

## 8. Audit limits and immediate work

No upstream Java tests, model training, full-document extraction, throughput benchmark or Rust/Java comparison was executed here. No Rust implementation exists as a consequence of this audit. The next runnable milestone is a pinned Java oracle, repeatable fixtures, an executable comparison harness and honest baseline reports. Only after that should feature agents port one bounded slice at a time and submit evidence to a separate integration/review loop.

## 9. Included runnable HTTP harness

`migration/tools/parity.py` is a standard-library-only Python 3.10+ tool. The implemented self-tests are in `migration/tools/tests/test_parity.py`. The 29 self-tests were actually run successfully using `python3 -m unittest discover -s migration/tools/tests -v`. They use local HTTP fixtures and synthetic XML/JSON/ZIP data; they do **not** establish that Java or Rust produces correct GROBID output.

### Suite schema

```json
{
  "schema_version": 1,
  "suite_id": "raw-date-smoke",
  "profile": "crf-offline",
  "cases": [
    {
      "id": "date-normal",
      "method": "POST",
      "path": "/api/processDate",
      "headers": [["Accept", "text/plain"]],
      "encoding": "form",
      "fields": [["date", "23 November 2019"]],
      "expected_status": 200,
      "comparator": "bytes"
    }
  ]
}
```

Case IDs are safe filename stems and unique. Paths are encoded origin-relative HTTP paths; base URLs contain only scheme/host/port. The default method is GET, encoding is `none`, expected status is 200 and comparator is `bytes`. Prefer explicit values in production manifests. Unknown keys, `skip` flags, duplicate case IDs and empty suites fail validation. Optional informational keys are suite `description` and case `description`, `tags`, `covers`.

`headers` and `fields` are ordered arrays of string pairs, preserving duplicate field names. `encoding: "multipart"` accepts these fields plus `files: [{"field":"input","path":"../corpus/paper.pdf","filename":"paper.pdf","content_type":"application/pdf"}]`. File paths resolve relative to the suite JSON. The generated multipart body uses a deterministic boundary; fields precede file parts. To test deliberately malformed or specifically interleaved multipart bytes, use `encoding:"raw"`, `body_file:"request-body.bin"` and an explicit Content-Type header. Transport-owned headers cannot be overridden. GET/HEAD bodies are deliberately unsupported by this initial tool.

`compare_headers` adds header names to compare; Content-Type is always included and its values are compared exactly, so charset differences are visible. Other transport headers, including dates and server implementation names, remain in evidence but are not comparison defaults. An intentionally empty body requires `allow_empty_body:true`; this is useful for a recorded 204 response and should be narrow. JSON comparison keeps array order, rejects duplicate keys/NaN/Infinity, distinguishes booleans from numbers, and compares numeric values exactly using decimal arithmetic. XML comparison pairs C14N with namespace-declaration bindings and element positions, preserves text whitespace, comments, order, IDs and coordinates, rejects DTDs, and performs no ID/time/coordinate masking. The namespace evidence prevents false passes when a prefix carries meaning only inside an attribute or text value; equivalent declaration relocation is conservatively unequal. ZIP comparison ignores archive order/compression/timestamps but requires the same named members and exact contents, with traversal, duplicates, symlinks, conflicting paths, member-count and expanded-byte guards. It does not canonicalize XML inside an archive.

### Provenance and commands

`--provenance` is a required nonempty JSON object with a nonempty `compatibility` object. Fill that object with the shared pinned source baseline, model manifest, effective configuration, corpus revision and extractor SHA-256. The Java and Rust `implementation`/build fields should differ. The harness enforces exact equality of the shared compatibility object and suite profile; it records the rest as evidence rather than assuming it can verify what a remote process actually loaded. The project's bootstrap gate must verify those declarations against the running process and files.

```bash
python3 migration/tools/parity.py capture \
  --suite migration/cases/raw-date-smoke.json \
  --base-url http://127.0.0.1:8070 \
  --provenance migration/local/oracle-provenance.json \
  --out migration/evidence/java-001

python3 migration/tools/parity.py capture \
  --suite migration/cases/raw-date-smoke.json \
  --base-url http://127.0.0.1:8072 \
  --provenance migration/local/rust-provenance.json \
  --out migration/evidence/rust-001

python3 migration/tools/parity.py compare \
  --oracle migration/evidence/java-001 \
  --candidate migration/evidence/rust-001 \
  --report migration/evidence/compare-001.json
```

The example suite/provenance paths above are illustrative input names; create them with real fields before running. Capture accepts `--timeout` (default 120 seconds) and `--max-bytes` (default 256 MiB). Requests are sequential. There are no retries, redirect following, proxy-environment use or implicit decompression. Only loopback origins are allowed unless the caller explicitly passes `--allow-remote` for an authorized server. The output directory must not exist; comparison reports are also created without overwriting an existing report.

Each run contains `suite.json`, `provenance.json`, `manifest.json` and request/response binary files. Fingerprints cover logical request method/path/headers/body digest and response status/reason/ordered headers/body digest. The request origin is deliberately separate so Java and Rust can listen on different ports. Payload files retain exact bytes. Manifests record elapsed time and all failures. Comparisons verify payload/envelope/fixture hashes, complete case membership, request equivalence, selected headers and the explicit comparator. Exit code 0 means success, 1 means a failed capture/comparison, and 2 means invalid inputs or an execution/setup error.

Initial limits: this is not a load generator, stage-trace collector, training-token workflow runner, PDF annotation semantic comparator, schema validator or complete endpoint corpus. XML outputs with independently generated timestamps/IDs may fail Java-versus-Java; capture and investigate that before introducing a narrowly justified normalization. Equal raw output for a tiny suite does not satisfy full feature or release gates.
