# ADR 0011: Include the training and evaluation lifecycle

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

The repository provides trainer registries, aliases/flavors, data generation, async jobs, model promotion and evaluation. Splits and training are not universally deterministic. Some runner/cancellation quirks affect behavior.

## Decision

Port deterministic data/feature preparation and metric calculations exactly. Record split membership; reproduce Java seeded shuffles when required. Keep training parameter/artifact interoperability separate from stochastic weight equality. Preserve aliases, job locks, state, custom paths and export/import.

## Alternatives considered

Rejected: declare parity after inference alone; use the same numeric seed with a different PRNG and assume the split matches; accept a successful HTTP enqueue as successful training; demand universal byte-equal neural weights.

## Validation and exit criteria

Run tiny end-to-end training smoke plus all applicable trainers in the full gate. Validate split/features, native params, promotion/reload/rollback, stale locks, cancellation, model download and reports. Assert output counts and metrics even when tools exit zero.

## Consequences

Training adds significant runtime and corpus requirements. Fixing unsafe cancellation or ineffective CLI branches is a separately declared behavioral deviation; run destructive lifecycle cases only on disposable model directories.

## Source anchors

- [grobid-trainer/src/main/java/org/grobid/trainer/TrainerRegistry.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-trainer/src/main/java/org/grobid/trainer/TrainerRegistry.java)
- [grobid-trainer/src/main/java/org/grobid/trainer/AbstractTrainer.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-trainer/src/main/java/org/grobid/trainer/AbstractTrainer.java)
- [grobid-trainer/src/main/java/org/grobid/trainer/TrainerRunner.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-trainer/src/main/java/org/grobid/trainer/TrainerRunner.java)
- [grobid-service/src/main/java/org/grobid/service/process/GrobidRestProcessTraining.java](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-service/src/main/java/org/grobid/service/process/GrobidRestProcessTraining.java)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

