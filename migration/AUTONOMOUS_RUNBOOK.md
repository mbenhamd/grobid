# Durable autonomous execution

## Roles

The coordinator maintains the dependency graph, shared types, fixture policies and integration branch. Implementers own one small vertical slice in a separate worktree. The oracle/testing worker controls reference capture and failure localization. An independent reviewer reruns the decisive tests at the submitted commit. With four agent slots, use coordinator/reviewer plus up to three workers; do not spawn workers that will all edit the same core module.

Long runs are a sequence of recoverable tasks. The host may terminate sessions, expire credentials or reach budgets. This kit supplies durable state and a restart prompt; it does not supply a privileged background agent or bypass any host control.

## Bootstrap sequence

1. Inspect the installed kit and existing fork instructions. Run `python3 migration/tools/check_kit.py` and the supplied Python tests.
2. Use `taskctl.py next` to select a ready task. Claim it in the coordinator checkout with a stable worker ID and lease duration.
3. Establish a detached oracle checkout of the pinned SHA outside the implementation worktree. Never benchmark a moving upstream branch. Fetch only needed dependencies/assets, keeping their provenance and cost visible.
4. Verify the Java build and service before porting implementation. If the toolchain/container runtime or assets are unavailable, mark that task blocked; proceed with independent static utilities/tests rather than fabricate a baseline.
5. Freeze shared contracts, then scaffold Rust and implement the first raw-text vertical slice. Do not spend the first several days translating unexercised code.

## Worktree ownership

Each task names owned paths and dependencies. Use one branch/worktree per implementation task. Shared task state lives in the coordinator checkout, not separately in each Git worktree. Pass `--root /absolute/coordinator/checkout` to the task tool. Workers must not edit a common lockfile, root manifest, comparison policy or golden corpus concurrently. Coordinate those changes through a dedicated integration task.

Do not assume Git makes concurrent writes to the same worktree safe. Never use broad `git add .`, destructive reset/clean or force-push. Stage the task's explicit files. Keep fixture/model archives and credentials out of source commits. Store run metadata, report hashes and reproducible commands; use a durable artifact store for large outputs when one is available.

## Task lifecycle

`pending → running → submitted → done`, with `blocked` and `failed` visible states. A running task has an owner, lease and heartbeat. Submission records the exact commit, complete evidence and artifact hashes. Approval requires a different reviewer and decisive rerun evidence. A stale lease must be inspected and explicitly reclaimed; never steal active work automatically.

The supplied ledger serializes local file updates and enforces dependency/owner/evidence checks. It is a workflow guard, not an authentication system: independent review still depends on actual separate agent/human execution. Keep it under coordinator control. A worker is not allowed to rewrite state or evidence to bypass checks.

## Evidence packet

Use `templates/EVIDENCE.json`. Include at least one decisive command and its raw log, command timestamps/exit status, source/result commits, input/profile identifiers, changed paths, test case counts, mismatch and skip counts, and hashed outputs. Documentation-only investigation tasks can use source-inventory/validation commands; inference tasks require actual oracle and Rust runs. A template with unfilled values is invalid evidence.

Capture a failing case before debugging. Save both outputs and find the first divergent stage: extractor → layout → tokenization → features → labels → clusters → semantic objects → serialization → transport. Fix the originating behavior, not the downstream assertion. Never “repair” output by hardcoding a fixture-specific answer.

## Checkpoints and restarts

After each reviewed slice, update status and handoff. Before context exhaustion or a time limit, record: task/branch/commit; worktree path; last passing command; current failing command and first mismatch; files changed; current process/artifact locations; lease ownership; blockers; and next exact command. If the work is not ready to commit, state that explicitly and preserve the dirty worktree. Do not discard it to produce a clean-looking handoff.

On restart, inspect processes/worktrees and reclaim stale tasks only after confirming no live owner. Recompute any evidence whose binary/input hashes no longer match. Read the last recorded failure before retrying. Do not reconstruct state from a chat summary alone.

## Budgets and stopping

The coordinator sets disk, memory, CPU/GPU concurrency and time budgets after reading the environment. Default to four active agents and one expensive training/evaluation job until capacity is measured. Do not silently acquire paid services or upload a production corpus. Allow long tools to yield so progress remains observable.

Three attempts at the same failure signature require a changed diagnosis or documented blocker. If only external prerequisites remain, stop with their exact names and recovery commands. If a requested scope change or irreversible action is necessary, finish all reviewable local work first and ask a concrete question. Routine Rust crate choices and reversible fixes do not need repeated permission.

Creating `migration/state/STOP` requests a safe checkpoint and stop at the next boundary. The external scheduler must also stop launching sessions. A user cancellation takes precedence over the backlog.

## Reporting cadence

During interactive work report meaningful findings regularly. For unattended runs write a compact checkpoint after each task and a milestone report at least every work block. Include completed/remaining tasks, verified feature/profile counts, mismatches/skips, blocked prerequisites, resource usage and next task. Distinguish static audit, harness self-tests, Java tests, Rust tests, differential tests, quality evaluation and performance runs.

## Completion audit

Use the independent release reviewer to reconstruct the claimed milestone from manifests and fresh test runs. Verify there is no production JVM dependency or hidden fallback. Trace every required feature row to cases and evidence. Inspect all deviations, skipped tests and nondeterminism rules. Only after the milestone passes may the coordinator describe it as achieved. Publish/deploy remains a separately authorized action.
