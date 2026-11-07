# ADR 0007: Use observed service behavior and effective config

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

Documentation, annotations and processor implementations can disagree. Media negotiation, defaults, repeated fields and malformed input behavior are client-visible. Config getter inheritance is not uniform.

## Decision

Inventory every live annotated handler and resource, then capture real requests. Preserve method/path/consumes/produces variants and processor-effective behavior. Expose Rust config validation without inventing a YAML deep-merge semantic. Record static observations and runtime observations separately.

## Alternatives considered

Rejected: rebuild only processFulltextDocument; treat a parameter annotation as its full behavior; silently standardize every boolean/integer error; assume all flavor fields inherit the same way.

## Validation and exit criteria

Replay raw text, PDF, patent, annotations, ZIP, debug, health, admin and training cases with missing/duplicate/invalid inputs, absent/wildcard Accept and load exhaustion. Snapshot effective model config, fallback and asset selection.

## Consequences

A few awkward upstream behaviors may need explicit compatibility shims. Hardening or nicer errors can be offered in a separate mode with a deviation record rather than hidden under a parity label.

## Source anchors

- [grobid-service/src/main/java/org/grobid/service/GrobidRestService.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-service/src/main/java/org/grobid/service/GrobidRestService.java)
- [grobid-core/src/main/java/org/grobid/core/utilities/GrobidProperties.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/utilities/GrobidProperties.java)
- [grobid-core/src/main/java/org/grobid/core/engines/config/GrobidAnalysisConfig.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/engines/config/GrobidAnalysisConfig.java)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

