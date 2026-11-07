# Durable handoff

## Current checkpoint

This is the initial instruction-package checkpoint. No implementation worktree, Java oracle process, Rust binary or completed migration task exists in the package. The audited upstream SHA is `f313f7010773fe8113cbb0f7a774960450a850d0`.

## Next action

From the installed fork run:

```bash
python3 -B migration/tools/check_kit.py
python3 -B migration/tools/taskctl.py next
```

Read T000's acceptance criteria, inspect existing Git changes/remotes/toolchains, claim T000, and follow the oracle-capture skill. Establish runtime facts before porting. Preserve any user edits already present in the fork.

## Replace this section at each checkpoint

Record active task and worker; coordinator and worker worktree paths; branch/base/result commits; clean or dirty status; last passing command; exact failing command and first mismatch; input/profile/model hashes; log/artifact locations; active processes; lease expiry; blockers; and next exact command. Distinguish committed work from uncommitted edits. Do not overwrite immutable evidence or summarize an unexecuted test as passing.
