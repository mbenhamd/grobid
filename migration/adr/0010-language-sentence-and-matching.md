# ADR 0010: Treat language, sentence and citation matching as algorithms

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

Default Cybozu and OpenNLP behavior plus layout-aware sentence corrections influence output. Alternative Lingua/Pragmatic/BlingFire profiles exist. Citation resolution uses Lucene analysis/ranking and range heuristics.

## Decision

Inventory each enabled algorithm, resources and config. Port default behavior with fixture/intermediate parity and retain optional profiles as required coverage. Reproduce analyzer/ranking/tie behavior where observable; evaluate native implementations only against those contracts.

## Alternatives considered

Rejected: generic sentence splitting, a different language library or a simple bibliography dictionary as untested substitutes; leaving a Java helper and claiming JVM-free runtime.

## Validation and exit criteria

Test protected citation spans, superscripts, initials/abbreviations, mixed languages, RTL/CJK, ambiguous author-year candidates, numeric ranges and candidate ordering. Include detector failure/empty text and runtime resource loading.

## Consequences

These helpers can be disproportionately hard relative to their line count. If equivalent JVM-free implementation is unavailable, the profile remains blocked and the milestone scope must be stated.

## Source anchors

- [grobid-core/src/main/java/org/grobid/core/lang/impl/OpenNLPSentenceDetector.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/lang/impl/OpenNLPSentenceDetector.java)
- [grobid-core/src/main/java/org/grobid/core/utilities/SentenceUtilities.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/utilities/SentenceUtilities.java)
- [grobid-core/src/main/java/org/grobid/core/utilities/matching/ReferenceMarkerMatcher.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/utilities/matching/ReferenceMarkerMatcher.java)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

