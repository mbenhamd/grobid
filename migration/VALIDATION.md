# Validation performed on the delivered migration kit

Prepared 6 November 2026. These checks validate the instruction package and supporting Python tools. They do **not** establish a running Java oracle, a Rust implementation, extraction parity, model quality, or a speed improvement.

## Executed checks

| Check | Result | Evidence |
| --- | --- | --- |
| Python tool tests | 49 passed, zero failed, zero skipped | `validation/python-tests.txt` |
| Package structure and source paths | 60 tasks; acyclic dependencies; 11 skills; 16 ADRs; 168 feature rows; 45 API handlers; two valid starter suites | `validation/structure-check.json` |
| Upstream source lock | Exact pinned HEAD, no tracked edits, eight critical source-file hashes match | `validation/source-pin.json` |
| Pinned source line references | 227 unique line anchors checked; zero invalid ranges | `validation/source-anchors.json` |

The 49 tool tests comprise 29 HTTP capture/comparison tests, 15 durable-ledger tests and five source/graph-guard tests. They use synthetic/local data and a local HTTP server. They cover unexpected empty results, duplicate/skipped cases, request and provenance mismatches, altered evidence, transport errors, repeated multipart fields, XML mixed text/IDs/coordinates, exact JSON number semantics, unsafe ZIP members, actual competing task-claim processes, lease expiration, independent review identity, evidence hash rechecks, STOP handling, and atomic-write failure recovery.

The installer is tested separately with its embedded `--self-test` suite. Its seven cases cover read-only planning, installation/idempotence, conflict refusal without partial writes, a file in place of a required directory, symlinks, invalid/corrupt/duplicate payloads, and explicit installation outside a repository. A package round trip checks the actual embedded payload and archive against every distribution file hash and runs the structural validator on the installed copy.

## Independent review

A focused independent review reproduced one false pass in XML canonicalization: namespace bindings used only inside QName-valued attributes could disappear. The delivered comparator now retains namespace declarations with element positions in addition to canonical XML. New tests cover `xsi:type`, custom attributes, QName text, declaration ordering and binding scope. The reviewer reran the original reproduction and both added regression tests and confirmed the issue is closed. See `validation/independent-harness-review.md`.

A separate bounded review of the task controller and portions of the operating documentation found no confirmed actionable issue in those reviewed portions. It did not finish a substantive review of every task/feature row or rerun the controller tests; those limits are recorded in `validation/independent-kit-review.md`. The structural validator checks the task graph and matrix mechanically; that is not a claim of exhaustive independent semantic review.

## Reproduce the package checks

From the installed fork root:

```bash
python3 -B migration/tools/check_kit.py
python3 -B -m unittest discover -s migration/tools/tests -v
python3 -B migration/tools/verify_upstream.py --source /path/to/clean/pinned/oracle
```

The source verifier checks the eight recorded source files and the Git baseline. It intentionally reports runtime and model-asset validation as false. All source inventories are static; counts of upstream test declarations are not upstream execution results.

Run installer self-tests with:

```bash
python3 /path/to/install_grobid_rust_parity_kit.py --self-test
```

`DISTRIBUTION.json` records original kit-file hashes. It is a distribution integrity aid, not a runtime attestation, and becomes historical when agents intentionally edit the kit. The ledger also checks declared workflow consistency rather than cryptographically proving reviewer identities or claimed executions. Reviewers must inspect Git and rerun decisive commands.

## Validation deliberately left to the migration

No GROBID Java extraction or JUnit suite was run. Native model libraries and large weights were inventoried from the pinned Git tree rather than built or loaded. External evaluation corpora were not downloaded or scored. No Rust compiler/build, DeLFT inference, retraining, concurrency/load benchmark, PDF semantic comparison, or long-run soak was executed. The initial comparator does not yet implement the generated-ID graph and narrowly volatile timestamp policies required for full TEI comparisons.

All 60 implementation tasks and all 168 coverage rows remain pending or not verified. The starter HTTP cases are derived from source and must be characterized against the pinned oracle before they can become release evidence. Further work is explicitly assigned in the task graph rather than represented as already passing.
