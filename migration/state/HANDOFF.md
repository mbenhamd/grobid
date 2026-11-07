# Durable handoff

## Current checkpoint (2026-11-07)

- **Coordinator checkout:** `/Users/mbenhamd/Projects/grobid` on branch `rust/migration-kit`. Remotes:
  - `origin`: `github.com/mbenhamd/grobid`, a public fork
  - `upstream`: `grobidOrg/grobid`
- **Oracle checkout:** `/Users/mbenhamd/Projects/grobid-oracle`. It is a shallow fetch of `f313f7010773fe8113cbb0f7a774960450a850d0` and is clean, including ignored files. Never build in a way that dirties tracked files, and never train into it.
- **Last completed task:** T000, result commit `4382437ae`, approved and `done`.
  - Worker branch: `rust/T000-freeze-source`
  - Worktree: `/Users/mbenhamd/Projects/grobid-wt/T000`, which can be removed.
- **Toolchains:**
  - JDK: `/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home`, version 21.0.13.0.3. Pass it as `JAVA_HOME` explicitly; the user's shell profile is not modified.
  - Gradle: wrapper 9.6.1.
  - Rust: rustc 1.88.0.
- **Active processes:** none. **Leases:** none.

## Carry-forward from the T000 review (fix in the named task; do not edit T000 evidence)

- **T002:**
  - Hash the Gradle 9.6.1 distribution. The wrapper has no `distributionSha256Sum` (F1).
  - Record the JDK file hash and user-level build config: `~/.gradle`, `~/.m2`, `JAVA_TOOL_OPTIONS`, `GRADLE_OPTS` (F2).
  - Capture the Maven runtime dependency closure and built jar hashes.
- **T003:**
  - Map config models, flavors and engines to the files they actually load (F3).
  - Record pdfalto's fontconfig configuration and the installed fonts (F10).
  - Re-check `host-environment-lock.json` before trusting captures. pdfalto arm64 links the Homebrew packages fontconfig 2.18.3, freetype 2.15.0, libpng 1.6.59, gettext and brotli, so **do not `brew upgrade` them**.
  - Record gettext and brotli versions explicitly (F5).
- **Capture-script hygiene for future capture scripts (F4):**
  - Assert expected counts, such as exactly 8 critical hashes and equal lengths before `zip`.
  - Verify probe output strings, not only exit codes.
  - Use `--ignored` in post-run status checks.
  - Keep host-tool output in a runtime-observed section (F6).
- **Process (F8):** integrate a worker branch into the coordinator branch only after approval. The ledger requires the evidence files to be in the coordinator root at submit time, so stage them there without committing, or submit from a coordinator-local merge that is not pushed until approval.
- **Privacy (F9):** evidence logs contain the hostname `mbenhamd-5.local` and home paths. The fork is public.

## Failed approaches

- The first T000 result commit `8b6e922` omitted all `*.log` evidence because of the root `.gitignore`. Fixed by `migration/evidence/.gitignore` (`!*.log`). The ledger hash check caught the omission.

## Next action

```bash
cd /Users/mbenhamd/Projects/grobid
python3 -B migration/tools/check_kit.py
python3 -B migration/tools/taskctl.py next
```

Then claim T002 (build and start the Java oracle in `/Users/mbenhamd/Projects/grobid-oracle` with the JDK above, CRF profile `grobid.yaml`). T001 (scope reconciliation) and T004 (corpus) are independent and can run in parallel.
