---
name: grobid-capture-oracle
description: "Build and capture a reproducible pinned Java GROBID oracle, including HTTP and intermediate model outputs. Use before porting a feature, refreshing reference fixtures, or investigating baseline nondeterminism."
---

# Oracle engineer

This is a repository-scoped skill for the GROBID Rust migration. Read the root AGENTS.md first. Resolve paths from the repository root, not the skill directory. Follow actual host permissions and the user's later instructions.

## Read only the relevant contracts

- `migration/TEST_STRATEGY.md`
- `migration/contracts/upstream-lock.json`
- `migration/contracts/api-inventory.json`
- `migration/adr/0001-freeze-reference-and-parity-scope.md`

## Procedure

1. Build or identify the exact pinned source and all runtime assets in a separate checkout. Record native binaries, model/lexicon/embedding hashes, effective config, locale, time zone and machine limits.

2. Run upstream discovery/tests and record skipped/failed counts. Probe service readiness and failed models. Do not substitute a release image with a different revision.

3. Create a request suite with exact method, path, Accept, ordered fields, repeated coordinates and input hashes. Use the actual processor behavior to resolve defaults. Keep live external-service traffic out of the offline suite.

4. Capture each candidate deterministic request three times. Record raw responses, status/media/headers and full provenance. Use parity.py capture/compare as a conservative starting point and read its --help.

5. Capture ALTO, ordered layout tokens, features, labels, clusters and linked structures. Use debugMode where supported but assert expected model and invocation coverage; add observational hooks only when uninstrumented results remain equal.

6. Classify variability by exact source field and cause. Propose a narrowly scoped comparator change separately. Never regenerate the old golden in place.

## Required result

Provide versioned raw captures, provenance manifest, reproducible commands, repeated-run differences and a coverage table linking each fixture to route/profile/feature. Runtime missing prerequisites remain blockers.

## Failure rules

Do not assume config YAML represents effective runtime values. Do not use a mutable Docker tag or dataset main as a lock. Do not let a capture with zero cases or transport errors pass.

Use the coordinator ledger and evidence templates. Keep the distinction between source-derived observations, runtime observations and design decisions in every report.

