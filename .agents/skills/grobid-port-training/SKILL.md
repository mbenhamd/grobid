---
name: grobid-port-training
description: "Port GROBID trainers, evaluation and asynchronous model lifecycle. Use for training data generation, model registration, split/n-fold, job state, model export/import or quality reports."
---

# Training engineer

This is a repository-scoped skill for the GROBID Rust migration. Read the root AGENTS.md first. Resolve paths from the repository root, not the skill directory. Follow actual host permissions and the user's later instructions.

## Read only the relevant contracts

- `migration/audit/TESTING_AUDIT.md`
- `migration/adr/0011-training-and-evaluation.md`
- `migration/contracts/test-inventory.json`
- `migration/TEST_STRATEGY.md`

## Procedure

1. Read TrainerRegistry, TrainerRunner, AbstractTrainer, model-specific SAX/data generation and REST training processor. Include aliases and flavors, not only default model names.

2. Capture effective input-file order, alignment, feature/label streams, templates, split membership and parameters before training. Reproduce Java seeded shuffle and explicitly replay unseeded splits.

3. Implement train/evaluate/split/n-fold modes and model path behavior. Keep production/reference assets read-only; exercise .new/.old promotion and rollback on disposable directories.

4. Port metrics using fixed prediction fixtures including empty/zero-denominator cases. Assert complete expected TEI/report counts even when the evaluator exits zero.

5. Test enqueue, per-model alias locks, list/status, cancellation, orphaned/stale jobs, restart, model ZIP and training-artifact ZIP. Observe the native process, not only the future status.

6. Separate deterministic preprocessing/inference parity from stochastic training-repeatability claims. Run tiny smoke first, then expand all claimed trainers/profiles before S3.

## Required result

Submit exact data/split artifacts and hashes, lifecycle state tests, trainer coverage, compatible model-load predictions and complete metric reports with failures/skips.

## Failure rules

Do not silently correct source quirks while claiming literal behavior. Do not accept a job token or zero exit code as proof of successful training.

Use the coordinator ledger and evidence templates. Keep the distinction between source-derived observations, runtime observations and design decisions in every report.

