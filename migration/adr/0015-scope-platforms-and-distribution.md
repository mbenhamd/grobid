# ADR 0015: Track legacy surfaces, platform coverage and notices explicitly

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

The repository contains current, optional, deprecated and inactive components. Java embedding, batch CLI, CRF++ branches and enum-only flavors differ from active default server routes. Bundled native/data assets do not share a single license.

## Decision

Inventory and classify every discovered surface. Default milestone scope includes current documented and active optional behavior; track legacy branches separately without deleting them. Record explicit disposition for Java embedding and source-only trainers. Preserve platform matrix and per-artifact notices.

## Alternatives considered

Rejected: infer support from an enum or stale workflow; call every bundled binary Apache-2.0; silently omit training/CLI/health/UI/platform behavior; promise binary-compatible Java JARs from a Rust executable.

## Validation and exit criteria

Trace feature rows to source and runtime cases, validate Linux x86-64/arm64 and macOS x86-64/arm64 where upstream supports them, and verify packaging assets/licenses. Any unsupported combination remains a visible gap.

## Consequences

Strict whole-repository claims may require extra facade/compatibility work. Linux-first development is allowed, but it does not silently narrow release support. Public benchmark rights do not authorize redistribution of arbitrary user PDFs.

## Source anchors

- [Readme.md](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/Readme.md)
- [LICENSE](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/LICENSE)
- [.github/workflows/ci-build-unstable.yml](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/.github/workflows/ci-build-unstable.yml)
- [doc/Grobid-java-library.md](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/doc/Grobid-java-library.md)
- [doc/Grobid-batch.md](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/doc/Grobid-batch.md)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

