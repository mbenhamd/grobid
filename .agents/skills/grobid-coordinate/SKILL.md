---
name: grobid-coordinate
description: "Coordinate the GROBID Rust rewrite across durable tasks and isolated worktrees. Use when starting or resuming the migration, delegating slices, integrating reviewed work, or preparing a milestone report."
---

# Coordinator

This is a repository-scoped skill for the GROBID Rust migration. Read the root AGENTS.md first. Resolve paths from the repository root, not the skill directory. Follow actual host permissions and the user's later instructions.

## Read only the relevant contracts

- `migration/AUTONOMOUS_RUNBOOK.md`
- `migration/plans/tasks.json`
- `migration/contracts/scope.json`
- `migration/state/HANDOFF.md`

## Procedure

1. Inspect Git worktrees, task leases, STOP state and existing dirty edits before assigning work. Use the coordinator checkout as the single ledger root.

2. Select the smallest dependency-ready task with clear owned paths. Read its source anchors and acceptance criteria. Resolve shared types and lockfile changes centrally before parallel work.

3. Delegate independent work with task ID, source SHA, owned paths, output/evidence locations and exact done criteria. Keep an independent reviewer available. Do not have several workers alter one serializer or golden corpus.

4. Integrate one reviewed commit at a time; rerun affected contracts and shared-fixture tests. Rebase conflicts through the owning worker when behavior is unclear.

5. Update feature status only from evidence. Separate static audits, self-tests, runtime captures, differential results, quality evaluation and benchmarks. Report blockers and continue another ready task.

6. Before a context limit, save a concise handoff with branch, commit, last passing command, first failure and next exact command. Recover expired leases explicitly after checking no owner is active.

## Required result

Submit an integration commit plus ledger/handoff, tested feature/profile counts, unresolved deviations and evidence hashes. A green package validator is not a parity milestone.

## Failure rules

Do not start translating the whole core while the oracle is unavailable. Do not approve a task you authored. Do not invent an outer scheduler or evade host permissions.

Use the coordinator ledger and evidence templates. Keep the distinction between source-derived observations, runtime observations and design decisions in every report.

