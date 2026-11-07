# ADR 0014: Use recoverable tasks and independent evidence review

Status: Accepted as migration plan; implementation and runtime validation pending.
Date: 2026-11-06.
Reference: GROBID f313f7010773fe8113cbb0f7a774960450a850d0.

## Context

A multi-day session can terminate or lose context. Parallel agents can overwrite shared work or optimize tests until they pass. Prompt text alone cannot keep a host process alive or prove correctness.

## Decision

Use dependency-ordered tasks, isolated worktrees, owner leases, atomic coordinator ledger, STOP handling, immutable evidence, independent review and serialized integration. Resume from files and exact commits. Keep retries bounded and blockers explicit.

## Alternatives considered

Rejected: a single enormous 'rewrite everything' prompt; multiple agents in one mutable working tree; self-approval; altering goldens/gates to clear a failure; claiming an unattended runtime is guaranteed.

## Validation and exit criteria

Exercise ledger dependency/lease/STOP/tamper/review rejection behavior. A fresh agent must reconstruct a task from artifacts and rerun the decisive command without prior chat context.

## Consequences

Coordination overhead is deliberate. The task tool is a guard, not an identity-security system. Session launches and credentials are provided by the user's host and remain subject to its controls.

## Source anchors

- [.github/workflows/evaluation.yml](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/.github/workflows/evaluation.yml)
- [grobid-core/src/test](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-core/src/test)
- [grobid-service/src/test](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-service/src/test)
- [grobid-trainer/src/test](https://github.com/grobidOrg/grobid/blob/f313f7010773fe8113cbb0f7a774960450a850d0/grobid-trainer/src/test)

Source anchors establish the upstream context. The Rust design, thresholds and workflow rules above are project decisions, not claims made by upstream.

