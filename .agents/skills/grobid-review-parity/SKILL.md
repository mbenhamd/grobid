---
name: grobid-review-parity
description: "Independently review a GROBID Rust migration task or release claim from source and evidence. Use before approving ledger submissions, changing parity policy or declaring a milestone."
---

# Independent reviewer

This is a repository-scoped skill for the GROBID Rust migration. Read the root AGENTS.md first. Resolve paths from the repository root, not the skill directory. Follow actual host permissions and the user's later instructions.

## Read only the relevant contracts

- `AGENTS.md`
- `migration/TEST_STRATEGY.md`
- `migration/contracts/scope.json`
- `migration/templates/REVIEW.json`

## Procedure

1. Use a fresh worktree at the submitted result commit. Inspect the base/result diff, task acceptance, source anchors and immutable input/profile hashes.

2. Rerun the decisive command rather than trusting the author's summary. Inspect discovered/executed/skipped counts and verify hashes of all logs/output artifacts.

3. Trace the feature row through handler, pipeline, native backend and serializer. Search for stubs, Java fallbacks, fixture-specific outputs, dropped options and tests that mirror implementation.

4. Inspect comparator/golden/scope changes separately. Challenge broad normalization and ignored failures. Test at least one adverse fixture that would reveal the claimed class of defect.

5. Check runtime JVM-free claims, native lifetime/resource behavior and total-process performance scope where applicable. Compare source declarations with actual supported assets.

6. Approve only a complete bounded task. Otherwise return specific evidence and required changes, preserve the submitted commit record, and keep the milestone blocked. Never approve your own implementation under a different label.

## Required result

Provide reviewer identity, result commit, exact rerun commands/log hashes, findings, decision, unresolved limitations and task/milestone coverage. Approval must match the submitted SHA.

## Failure rules

Do not convert incomplete coverage to a pass because a deadline is near. A task can be useful and still require changes.

Use the coordinator ledger and evidence templates. Keep the distinction between source-derived observations, runtime observations and design decisions in every report.

