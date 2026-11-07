# Verification strategy

## Two independent questions

1. **Behavioral compatibility:** Does Rust produce the same result and observable service behavior as the pinned Java implementation on the same requests, profiles and assets?
2. **Extraction quality:** Does the output retain the same document-level and field-level quality against labeled JATS/NLM/TEI data?

Both must pass. An aggregate F1 score can conceal field swaps and document regressions. Exact comparison against Java can reproduce an upstream extraction error, so it does not alone establish scientific accuracy. Report both, with per-document and per-feature differences.

## Test layers and required outputs

| Layer | Required cases | Acceptance |
| --- | --- | --- |
| Pin/build | Source, binaries, models, lexicons, config, toolchains, corpus | Immutable hashes; successful startup; no failed model loads |
| Utility | UTF-16/Unicode, regex, number/date, whitespace, tokenizer, lexicons | Exact deterministic outputs and offsets |
| Extractor | PDF→ALTO/sidecars, selected pages, clipping, graphics, limits/exits | Exact command/env and stable sidecar contract; failure mapping |
| Features | Every configured active sequence model and flavor | Identical feature columns, rows and boundaries |
| Inference | Wapiti, DeLFT, classifiers, runtime limits and batch edges | Identical deterministic labels; justified baseline volatility only |
| Pipeline | Segmentation, header, names, affiliations, dates, citations, fulltext | Equal ordered spans, fields, clusters, links and geometry |
| Output | TEI, BibTeX, JSON, ZIP, annotation PDF, debug, training artifacts | Exact or narrowly approved semantic contract; no hidden drops |
| HTTP | All annotated variants, negotiation/defaults, invalid inputs, overload | Status/media/headers/body behavior matches observations |
| Training | Registry/flavors, split, n-fold, paths, artifacts, locks and jobs | Deterministic prep parity plus separately assessed training repeatability |
| Quality | All four evaluation corpora and difficult/held-out documents | No unexplained per-document drift or per-field score regression |
| Resource | Cancellation, timeouts, repeated failures, startup/shutdown, long run | Bounded queues, no leaked resources, no unreported lost requests |
| Performance | Same successful work, matched profiles/hardware/concurrency | Predeclared effect/uncertainty gates; no quality tradeoff |

## Corpus plan

Keep four sets separate: existing upstream regression fixtures; a legal synthetic edge corpus; versioned end-to-end evaluation collections; and a user-authorized workload corpus representative of production. Track SHA-256, provenance/license, page count, language/layout features, expected failure/success and feature coverage for every item. Do not redistribute user documents by default.

The official evaluation dataset describes 1,943 PMC, 2,000 bioRxiv, 1,000 PLOS and 984 eLife articles (~5,927 total). Resolve an immutable dataset revision before downloading. Validate actual file/document counts; do not infer them from the dataset name. Keep train/dev/evaluation splits and any publication overlap visible. Hold out a regression set from iterative tuning.

Required edge families include: single/multi-column; short/long; rotated and cropped pages; ligatures/astral/combining marks; RTL/CJK; superscripts/subscripts; hyphenated line wraps; numbered/author-year/mixed citations; missing/duplicate references; shared author affiliations; multi-page tables; figures with vector/bitmap assets; formulas; footnotes/annexes; funding/availability/conflict/contribution statements; malformed/encrypted/image-only/empty PDFs; unusual fonts; full disk; truncated uploads; duplicate/repeated multipart fields; and concurrent duplicate submissions. An image-only PDF may be an expected unsupported/empty case; adding OCR changes the contract and belongs in a separate feature mode.

Choose smoke cases to cover every route, media variant and model dependency. Expand into a full option matrix: consolidation levels, raw fields, coordinate tags, sentence segmentation, TEI IDs, debug mode, page ranges, asset generation, flavors and detectors. Use pairwise combinatorial coverage for interactions plus exhaustive boundary/known-risk cases; do not claim exhaustive coverage of all combinations. Every matrix row records the tested combinations and the uncovered space.

## Oracle discipline

Capture each deterministic candidate at least three times on the same machine before freezing. Pin process locale/timezone and model initialization parameters where the reference supports them. Record any clock, random, PRNG, GPU kernel or external-service variation. Freeze HTTP request bytes/logical fields and output bytes together. Capture status and meaningful headers even for failures. Keep transport errors separate from expected HTTP errors.

Current TEI provenance includes a generated application timestamp; optional IDs and some footnote IDs use random keys. Do not confuse these with publication dates, bibliography IDs or citation targets. Initially let strict comparison fail. Add a reviewed comparator that permits only the exact proven volatile field and validates its format/cardinality; for IDs require a bijective renaming that preserves the entire link graph. Preserve raw outputs alongside normalized comparison artifacts. Version the comparator and test it with deliberate mutations that must fail.

For XML preserve all mixed-content spaces and tails. Do not globally strip whitespace, sort child nodes, remove namespaces or ignore attributes. The starter XML comparator pairs canonicalization with namespace-declaration bindings and their element positions, because a namespace may carry meaning only inside a QName-valued attribute or text node. Declaration order at one element may differ; relocation or redundant declarations conservatively remain unequal until a vocabulary-aware rule is reviewed. For JSON reject duplicate keys/non-finite numbers and keep array order; define numeric representation requirements per endpoint. For ZIP compare safe member names and uncompressed bytes recursively, while recording archive metadata separately. For PDFs compare annotation objects/geometry/link targets/page counts and rendered overlays; byte inequality alone may reflect container metadata but is not permission to ignore substantive content.

## Source-specific probes that must not be lost

The API audit identifies cases whose ordinary defaults can hide a regression:

- Exercise all combinations of raw-copyright and raw-citation flags on the assets route; source argument order interchanges them.
- Probe BLANK fulltext with requested IDs, sentence segmentation, coordinates and debug, which the resource branch does not forward normally.
- Test funding response negotiation and actual Content-Type separately; annotation and processor declarations differ.
- Exercise full/failed/killed training results with and without report.txt, and concurrent alias spellings that can share model artifacts but have distinct request-name locks.
- Cover debug output under XML/BibTeX/ZIP negotiation and an empty/fully filtered capture returning 204.
- Inject annotation failure and inspect pool/stream cleanup rather than requiring a resource leak for literal parity.

These are source-derived probes, not reproduced runtime results. Preserve observable quirks or declare a reviewed deviation; never silently fix them while reporting exact equivalence. See `audit/API_AUDIT.md` for pinned source locations.

## Existing tests

The source audit enumerates test declarations and ignored classes. Port assertions based on their behavior, including useful fixture cases from ignored tests, but keep the original ignore reason visible. Existing upstream tests are a seed, not proof of complete coverage. Run both JUnit generations and Kotlin tests where configured. Record discovered, executed, passed, failed and skipped counts separately. Preserve platform-specific reasons.

The current upstream end-to-end evaluation can fail without a nonzero `jatsEval` exit. Independently assert expected TEI counts, complete score reports and required metrics. The provided migration gates must also reject absent outputs and empty comparisons. A moving dataset `main` and merely printing score deltas are insufficient for a release gate.

## Fuzzing and metamorphic checks

After deterministic ports, add bounded fuzzing for ALTO/XML parsers, token/feature parsers, citation ranges, multipart, ZIP paths and config. Run sanitizers on the native boundary where supported. Persist minimal reproducers and tests. Useful invariants include unique IDs, all local links resolving, spans inside their token/page bounds, finite coordinates, no bytes lost during split/rejoin under the upstream normalization policy, and request isolation. Do not impose an attractive invariant that contradicts observed upstream behavior without a deviation decision.

## Training verification

Capture exact training example ordering, alignment, features, templates, split membership, validation selection and model path resolution. Reproduce Java's seeded random shuffle where used; record membership for unseeded splits. Compare trainer metrics on fixed predictions before running expensive training. Distinguish artifact format/loadability, inference output parity and stochastic training quality. Test `.new`/`.old` promotion, locked models, cancellation/restart, custom paths and legacy runner oddities on throwaway asset directories.

## Gate policy

The default is zero unexplained deterministic mismatches and zero missing mandatory cases. Statistical tolerances are not a substitute for labels/links/metadata equality. If reference nondeterminism prevents deterministic equality, freeze an explicit bounded semantic claim and review it independently. The full release report includes every deviation and blocked feature. A held-out Java reference run and independent Rust rerun are required before the final claim.

The starter harness is deliberately conservative and incomplete: it supports capture and several basic comparators, not the complete feature matrix, PDF object comparator, volatile ID bijection, labeled evaluation or load generator. Tasks in `plans/tasks.json` implement those missing capabilities before their release gates can pass.
