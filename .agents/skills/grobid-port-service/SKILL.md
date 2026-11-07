---
name: grobid-port-service
description: "Implement GROBID HTTP and administrative compatibility in Rust. Use for routes, multipart, media negotiation, defaults, error mapping, health, metrics, assets or server shutdown."
---

# Service engineer

This is a repository-scoped skill for the GROBID Rust migration. Read the root AGENTS.md first. Resolve paths from the repository root, not the skill directory. Follow actual host permissions and the user's later instructions.

## Read only the relevant contracts

- `migration/contracts/api-inventory.json`
- `migration/audit/API_AUDIT.md`
- `migration/adr/0007-http-and-config-contract.md`
- `migration/adr/0016-deviations-and-honest-runtime-metadata.md`

## Procedure

1. Read each route annotation and called processor. Turn each method/consumes/produces variant into runtime cases. Include debug, training, model downloads, patents and annotations.

2. Capture actual status/media/body for absent Accept, wildcard Accept, bad booleans/numbers, omitted/duplicate fields and empty inputs. Preserve unusual effective defaults rather than standardizing them.

3. Keep request extraction/validation separate from pipeline invocation. Move CPU/native work to bounded workers and propagate cancellation/deadlines through explicit ownership.

4. Test saturated admission, initialization/model failure, CORS, selected response headers, download filenames and binary bodies. Include admin port and root console behavior in the scope matrix.

5. Expose honest Rust runtime diagnostics. Preserve compatible counters/routes; record JVM-specific metric differences explicitly. Do not spoof reference build identity.

6. Assert release requests never fall back to the Java oracle, including error paths and optional profiles.

## Required result

Submit route-to-case coverage, captured/observed contracts, HTTP differentials, concurrency tests and an explicit unimplemented/intentional-difference list.

## Failure rules

Do not equate HTTP 200 with feature parity. Do not use typed framework validation defaults without verifying they match current GROBID errors.

Use the coordinator ledger and evidence templates. Keep the distinction between source-derived observations, runtime observations and design decisions in every report.

