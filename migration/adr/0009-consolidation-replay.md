# ADR 0009: Separate deterministic consolidation from live service behavior

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

Crossref/glutton latency, data, rate limits and errors change independently of the parser. Bibliographic enrichment can alter otherwise correct model output and dominate latency.

## Decision

Preserve request creation, modes, response parsing, validation/enrichment and failure policy using versioned recorded responses for offline parity. Run a separate small authorized live integration lane and explicitly report its external variability.

## Alternatives considered

Rejected: call live APIs from every differential test; disable consolidation only for Rust; ascribe lower remote latency to language speed; send the user's corpus to a new service without authorization.

## Validation and exit criteria

Cover no-match, partial records, DOI-only/full enrichment, timeouts, rate limiting/backoff, batch ordering, malformed responses and author/ORCID corrections. Verify headers/secrets handling without storing credentials.

## Consequences

Offline parity is reproducible. Live-service conformance remains a separate monitored dependency. Any change to requests, retries or rate limits is reviewed against actual service requirements and local behavior.

## Source anchors

- [grobid-core/src/main/java/org/grobid/core/utilities/Consolidation.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/utilities/Consolidation.java)
- [grobid-core/src/main/java/org/grobid/core/utilities/crossref/CrossrefClient.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/main/java/org/grobid/core/utilities/crossref/CrossrefClient.java)
- [grobid-home/config/grobid.yaml](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-home/config/grobid.yaml)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

