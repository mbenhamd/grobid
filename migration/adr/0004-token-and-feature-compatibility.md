# ADR 0004: Treat tokens and feature rows as compatibility interfaces

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

Offsets and subtoken widths use Java UTF-16 string length. Whitespace is retained. Feature files are position-sensitive input to existing model weights. GROBID I- is an entity-start marker.

## Decision

Create typed byte/scalar/UTF-16 offsets and port normalization/tokenization in source order. Preserve exact layout properties, sequence boundaries, feature columns, label conversion and clustering before optimizing storage.

## Alternatives considered

Rejected: global NFKC/whitespace cleanup; Rust byte indices as Java offsets; generic IOB clustering; deriving feature columns from field declarations rather than emitted printVector code.

## Validation and exit criteria

Golden-test astral/combining/RTL/CJK/ligature/NBSP cases, font/superscript boundaries, blank lines and repeated same-label entities. Compare exact Java and Rust tokens, feature rows and labels.

## Consequences

Compatibility utilities may intentionally retain surprising legacy behavior. Optimizations must maintain their contracts. New normalized behavior belongs in an opt-in versioned mode.

## Source anchors

- [grobid-core/src/main/java/org/grobid/core/analyzers/GrobidDefaultAnalyzer.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/analyzers/GrobidDefaultAnalyzer.java)
- [grobid-core/src/main/java/org/grobid/core/sax/PDFALTOSaxHandler.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/sax/PDFALTOSaxHandler.java)
- [grobid-core/src/main/java/org/grobid/core/features/FeaturesVectorFulltext.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/features/FeaturesVectorFulltext.java)
- [grobid-core/src/main/java/org/grobid/core/tokenization/TaggingTokenClusteror.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/tokenization/TaggingTokenClusteror.java)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

