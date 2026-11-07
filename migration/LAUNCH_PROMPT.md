# Paste this into the coding agent in your GROBID fork

You are implementing the GROBID Rust migration described by the repository's `AGENTS.md` and `migration/` kit. Carry out the work, not merely a plan. The user has authorized reversible local implementation, dependency setup within available permissions, isolated worktrees, tests, profiling, and commits. Do not deploy or publish without separate authorization.

Start by reading `AGENTS.md`, `migration/START_HERE.md`, `migration/state/STATUS.md`, `migration/state/HANDOFF.md`, and `migration/plans/tasks.json`. Use the relevant repository skills in `.agents/skills/` explicitly if the host does not discover them. Confirm the pinned upstream SHA and preserve existing user changes. Run the package validator, then select the first dependency-ready task and keep progressing.

Act as coordinator. Delegate disjoint investigations or implementation slices to available agents, retain an independent reviewer, and integrate sequentially. If subagents are unavailable, implement serially and record the independent-review gate as pending; do not impersonate another reviewer. Use the coordinator's durable task ledger across worktrees. Read `taskctl.py --help` rather than inventing commands.

First establish the Java oracle, artifact/profile hashes, repeated baseline captures and full route/feature matrix. Then build and port real Rust vertical slices, starting with utility semantics and raw text services, followed by pdfalto/ALTO, header/references/full text, remaining features, and training/evaluation. Preserve native engines and model assets initially. Keep exact feature/label/token and output differential tests at every stage. Never count a Java proxy, stub, skipped feature, empty suite, or altered golden as completion.

The objective includes a JVM-free Rust server. Distinguish that from a wholly Rust dependency graph. Preserve Cybozu/OpenNLP or optional detector behavior with evidence; do not silently retain a JVM and pass the milestone. Treat current source observations as hypotheses until exercised. Report deterministic equivalence and bounded corpus coverage honestly; do not promise equivalence for every possible document.

After each slice, run decisive verification, save logs and hashes, request independent review, commit the accepted result, and update task state and handoff. When blocked, record the failing command, evidence and smallest missing prerequisite, then continue other ready work. Do not repeatedly retry the same failure. Respect `migration/state/STOP`, resource budgets and all host permission controls.

Continue until all applicable milestones are verified or all remaining tasks have documented external blockers. Before any session/context limit, leave a committed or explicitly described worktree state, a durable handoff, and the exact next command. On a resumed session, reconstruct state from files and evidence rather than guessing what the previous agent did.

At each milestone, report implemented features, tested profiles/case counts, mismatches, skipped/blocked scope, actual measured performance, and the next milestone. Do not use the words "perfect parity", "complete", or "faster" unless the stated scope and attached evidence justify them.
