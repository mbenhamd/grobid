# ADR 0008: Preserve content and links while isolating proven volatility

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

TEI includes application time, version metadata and generated IDs. XML canonicalization cannot by itself remove nondeterminism. Broad whitespace/ID/date removal can conceal severe extraction and linkage regressions.

## Decision

Retain raw bytes. Default to strict comparison; permit only source-backed, repeated-Java-proven volatility rules with exact field/cardinality/type constraints. For generated IDs require bijection and identical link topology. Give each body type an explicit comparator.

## Alternatives considered

Rejected: strip all when/xml:id/target/coords; sort XML children; collapse mixed text; round all coordinates; compare only extracted plain text; compare ZIP bytes as the sole asset test.

## Validation and exit criteria

Comparator tests must detect missing/duplicate IDs, broken targets, altered bibliographic dates, whitespace tails, coordinates, child order, duplicate JSON keys and ZIP traversal/duplicates. Specialized PDF annotation object/render checks must precede semantic PDF equivalence.

## Consequences

A conservative starter harness will fail on genuine reference volatility until comparator extensions are reviewed. This is preferable to a false pass. Raw evidence stays available to audit every allowance.

## Source anchors

- [grobid-core/src/main/java/org/grobid/core/document/TEIFormatter.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/document/TEIFormatter.java)
- [grobid-core/src/main/java/org/grobid/core/layout/BoundingBox.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/layout/BoundingBox.java)
- [grobid-core/src/main/java/org/grobid/core/data/BiblioItem.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/data/BiblioItem.java)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

