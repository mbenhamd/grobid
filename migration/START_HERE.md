# Start the GROBID Rust parity migration

## What this package is

This is a source-audited execution kit for agents working in a GROBID fork. It contains a root `AGENTS.md`, 11 repository skills, 16 ADRs, a 60-task dependency graph, detailed source/API/model/test inventories, feature coverage, comparison and autonomous-work rules, and tested Python tooling. It is **not a Rust implementation or a completed Java/Rust benchmark**.

The audit freezes `grobidOrg/grobid` commit `f313f7010773fe8113cbb0f7a774960450a850d0`, dated 2026-11-04, declared source version `0.9.2-SNAPSHOT`. Large runtime assets and external evaluation corpora were inventoried where possible, not loaded/executed. Every implementation task starts pending.

The strategy is to preserve existing pdfalto/Wapiti/DeLFT behavior while replacing Java/Kotlin orchestration, transformations, models' feature/preprocessing logic, service code and remaining Java-only helpers. A JVM-free Rust service can initially retain C/C++ and Python dependencies. An all-Rust dependency graph would require a separate much larger migration.

## Install into a fork

Download `install_grobid_rust_parity_kit.py`. Place it outside your fork or in a temporary location. From your fork's root:

```bash
python3 /path/to/install_grobid_rust_parity_kit.py --target . --plan
python3 /path/to/install_grobid_rust_parity_kit.py --target .
python3 -B migration/tools/check_kit.py
python3 -B -m unittest discover -s migration/tools/tests -v
```

The installer embeds all package files, uses no network, runs no shell commands, preserves identical existing files, and refuses to overwrite differing files or follow symlink destinations. If `AGENTS.md` already exists, install into an empty review directory with `--allow-nonrepo`, then have the coding agent integrate the migration guide with your existing instructions. Do not discard the existing guide to avoid a collision.

The alternative `.tar.gz` download has the same content in a `grobid-rust-parity-kit/` directory. Extract it into a separate review folder first, then copy the content into your fork after checking conflicts. No model weights, PDFs, credentials or compiled native libraries are bundled.

These skills belong to this repository. They are not installed globally into your personal skill collection. Agents whose hosts do not discover `.agents/skills/` should explicitly read the appropriate `SKILL.md`; the root guide and task entries name it.

## Start the agent

Open `migration/LAUNCH_PROMPT.md` and paste its content into your coding agent while the fork is its working directory. The prompt tells it to act, establish the oracle, use the task graph, delegate disjoint slices, verify changes and resume from durable files. It does not require you to choose every crate or approve routine local steps.

A short launch instruction is:

```text
Read AGENTS.md and migration/LAUNCH_PROMPT.md and carry out the migration.
Start with T000, establish the pinned Java oracle, and keep progressing
through dependency-ready tasks using the repository skills. Use isolated
worktrees and independent review. Do not replace goldens, weaken comparators,
hide unsupported features or call a Java proxy a completed Rust rewrite.
Checkpoint every validated slice and before a session limit.
```

For days of unattended work, your coding host must provide persistent execution or an external session-restart scheduler. The files make restarts recoverable; they do not extend session/token limits or grant missing credentials. Have the scheduler start ordinary permitted sessions with the same launch prompt, honor the STOP signal and stop when only external blockers remain. Avoid an unbounded “retry on any error” loop.

## Read the audit before changing architecture

| File | Purpose |
| --- | --- |
| `audit/CORE_AUDIT.md` | Pipeline, native boundaries, model profiles, source-level bottlenecks and parity traps |
| `audit/API_AUDIT.md` | Exact handler/media/default/error behavior and administrative surfaces |
| `audit/TESTING_AUDIT.md` | Existing tests, ignored coverage, trainers, evaluation, assets and runnable harness details |
| `contracts/api-inventory.json` | Source-derived endpoint variants with parameters and source locations |
| `contracts/model-inventory.json` | Three configuration profiles, inherited engine/architecture observations and model assets |
| `contracts/test-inventory.json` | Comment-aware test declaration inventory; not execution results |
| `contracts/upstream-asset-index.json` | 506 Git-tree asset identities; runtime SHA-256 capture remains pending |
| `FEATURE_MATRIX.csv` | Feature/route/model rows to track cases and evidence |
| `adr/` | 16 explicit design and parity decisions |

All relative paths in this table are relative to `migration/`. Source facts are pinned to the audited commit. Architecture choices and thresholds are labeled as project decisions.

## Bootstrap the reference

The coordinator should inspect its existing clone/remote and fetch the pinned commit if absent, then create an isolated detached oracle worktree. A typical command in an already fetched fork is:

```bash
git worktree add --detach ../grobid-java-oracle f313f7010773fe8113cbb0f7a774960450a850d0
python3 -B migration/tools/verify_upstream.py --source ../grobid-java-oracle
```

The verifier checks HEAD, tracked cleanliness and eight critical source-file hashes. It does not attest runtime assets. T002–T003 build GROBID, resolve native/DeLFT dependencies, capture effective config and fingerprint all active assets. Follow the pinned `build.gradle` and Dockerfiles; do not assume an available `0.9.1` image equals this source.

The user’s actual production GROBID version and workload have not been supplied. Before claiming a speed improvement, capture that deployment's version/profile/flags/hardware. If it differs, retain it as an additional performance baseline or deliberately choose a second locked compatibility target. Do not silently mix its outputs with the audited master baseline.

## Use the starter capture harness

Python 3.10+ is sufficient for supplied tooling; `taskctl.py` uses Unix file locks, so the initial coordinator targets Linux/macOS. Rust and GROBID runtimes are installed by the implementation tasks, not by the kit installer.

Create `migration/evidence/java-provenance.json` and `rust-provenance.json` from `templates/provenance.example.json`, replacing all unknowns with captured facts. Both need an identical nonempty `compatibility` object containing the baseline/source/assets/config/corpus/profile IDs. Their `implementation` sections should truthfully differ. Provenance is caller-declared metadata; it must be independently verified, not simply copied from a template.

With real servers running, capture identical suites:

```bash
python3 -B migration/tools/parity.py capture \
  --suite migration/cases/raw-smoke.json \
  --base-url http://127.0.0.1:8070 \
  --out migration/evidence/java-raw-001 \
  --provenance migration/evidence/java-provenance.json

python3 -B migration/tools/parity.py capture \
  --suite migration/cases/raw-smoke.json \
  --base-url http://127.0.0.1:8072 \
  --out migration/evidence/rust-raw-001 \
  --provenance migration/evidence/rust-provenance.json

python3 -B migration/tools/parity.py compare \
  --oracle migration/evidence/java-raw-001 \
  --candidate migration/evidence/rust-raw-001 \
  --report migration/evidence/raw-comparison-001.json
```

Port 8072 above is a proposed local candidate port, not an upstream requirement. The first meaningful use is Java-versus-Java repeats. `raw-smoke.json` contains source-derived starter requests; T005 must verify their observed outcomes. `pdf-smoke.json` references the fixture already present at `grobid-service/src/test/resources/sample1/sample.pdf` in your fork. It can fail repeated output comparisons because full TEI contains producer timestamps and generated IDs. That is intentional: T007 must establish and implement narrow volatility handling.

The harness initially supports bytes, conservative XML, JSON and ZIP member comparisons. It preserves repeated form fields, binary uploads, statuses, content types and selected headers. It fails incomplete/altered captures, request or compatibility mismatches, unexpected statuses and unapproved empty bodies. It does not implement stage trace capture, a generated-ID graph comparator, PDF semantic comparison, labeled quality evaluation or a load generator. Those remain explicit tasks.

## Track tasks and resume

```bash
python3 -B migration/tools/taskctl.py next
python3 -B migration/tools/taskctl.py claim --task T000 --worker coordinator
python3 -B migration/tools/taskctl.py heartbeat --task T000 --worker coordinator
```

From worker worktrees pass `--root /absolute/path/to/coordinator-checkout` before the subcommand. Submit and approve with the evidence/review schemas and commands in `AUTONOMOUS_RUNBOOK.md` and `taskctl.py --help`. Record actual commits/logs/artifacts; placeholders and an executed count of zero are rejected. The tool checks workflow consistency and hashes, not the truth of a claimed identity or execution. Independent review must run commands and inspect Git itself.

Create `migration/state/STOP` to request a safe stop; remove it deliberately to resume. `list` and `next` remain readable. The agent must save a handoff before ending a session. All 60 tasks are pending in this delivered package because the Rust migration has not been run.

## Success criteria

Read `TEST_STRATEGY.md` and `PERFORMANCE.md`. Require zero unexplained deterministic differences on the declared coverage, complete output counts, independent labeled quality, every required route/profile/trainer, supported platform packaging and reliable long-run behavior. A speed claim requires matched work and measured uncertainty. Passing a finite corpus supports a bounded empirical claim, not a proof for every possible PDF. Scope changes and intentional safety differences remain visible in the release report.
