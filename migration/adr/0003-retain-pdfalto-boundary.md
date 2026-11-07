# ADR 0003: Keep the pinned PDF extractor as an isolated process

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

PDF layout tokens, coordinates and block grouping feed trained feature extractors. A different parser can change every downstream prediction. Current pdfalto options and exit-code handling have recently changed.

## Decision

Use the same executable, language resources, xpdfrc, flags, temp-directory semantics and page-range behavior as the oracle. Preserve subprocess isolation and observable error mapping. Move PDF parser replacement into a later separately evaluated experiment.

## Alternatives considered

Rejected: swap in PDFium, MuPDF, a Rust parser or OCR and assume text similarity implies parity; run an unsafe PDF decoder in the HTTP process merely to avoid process startup.

## Validation and exit criteria

Freeze ALTO/sidecar outputs, argument arrays and environment. Test exits 4/5/98, timeout, clipping, images on/off, page boundaries, malformed XML, child cleanup and resource limits in the selected execution mode.

## Consequences

Retaining C/C++ limits how much work a language rewrite can accelerate, but prevents mass feature drift. License/redistribution notices remain separately tracked. Child resource usage belongs in performance totals.

## Source anchors

- [grobid-core/src/main/java/org/grobid/core/document/DocumentSource.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/document/DocumentSource.java)
- [grobid-core/src/main/java/org/grobid/core/document/Document.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/document/Document.java)
- [grobid-home/config/grobid.yaml](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-home/config/grobid.yaml)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

