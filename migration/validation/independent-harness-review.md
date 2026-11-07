> Final status: the finding below is fixed in the delivered kit and independently retested. See the resolution at the end.

# Focused parity harness review

Reviewer: independent subagent `final_harness_review`.

Scope: `migration/tools/parity.py` and `migration/tools/tests/test_parity.py` in `/workspace/scratch/426a1dce0cf4/grobid-rust-parity-kit`. Applied the kit's `AGENTS.md` and `.agents/skills/grobid-review-parity/SKILL.md` guidance. No implementation files were edited. This is a bounded local comparator/capture review, not a claim of live GROBID parity or authenticated CI evidence.

## Confirmed finding

### P2 — XML comparison drops namespace context needed by QName-valued attributes

**Location:** `migration/tools/parity.py`, `canonical_xml`, approximately lines 419–430; also affects `compare_bodies(..., "xml")`.

`canonical_xml` uses `ElementTree.C14NWriterTarget` without QName-aware attributes or tags. Namespace declarations used only by a QName-valued attribute are removed from canonical output. Changing such a namespace binding can therefore change the XML's meaning while producing identical canonical bytes. In particular, XML Schema Instance's `xsi:type` attribute contains a QName: the two inputs below designate different expanded type names, `{urn:one}Example` and `{urn:two}Example`.

**Exact reproduction**, run from the kit root:

```bash
python - <<'PY'
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "parity", Path("migration/tools/parity.py")
)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

a = b'<root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:t="urn:one" xsi:type="t:Example"/>'
b = b'<root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:t="urn:two" xsi:type="t:Example"/>'
print(p.canonical_xml(a))
print(p.canonical_xml(b))
print(p.compare_bodies(a, b, "xml"))
PY
```

**Observed output:**

```text
b'<root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="t:Example"></root>'
b'<root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="t:Example"></root>'
True
```

**Impact:** The XML comparator can report a pass for semantically different accepted XML responses. This is a generic comparator finding; this review did not establish that a current GROBID endpoint emits this specific attribute. Existing XML regression tests cover element/attribute syntax, comments, mixed whitespace, IDs, coordinates, malformed XML, and DTD rejection, but do not cover QName namespace context.

**Suggested fix:** Preserve namespace context for QName-valued content. At minimum, configure the canonicalizer's QName-aware attributes with `{http://www.w3.org/2001/XMLSchema-instance}type` and add a regression showing that the two bodies above compare unequal. If arbitrary XML is accepted, preserve all namespace declarations conservatively or fail closed on unsupported QName content; a fixed list cannot infer every vocabulary's QName-valued field. Retain positive tests for permitted syntax-only canonicalization.

## Review coverage and limits

- Inspected suite validation, compatibility comparison, expected-case cardinality/order checks, saved request/response hashes, XML/JSON/ZIP comparison, and freezing request bodies before network capture.
- No additional confirmed false passes were established in the inspected compatibility, cardinality, capture integrity, JSON, ZIP, or suite-freezing paths.
- The focused reproduction above was executed successfully. The full unit suite was not rerun during this bounded review; inspection of existing tests is not reported as execution.
- No live oracle/candidate capture, corpus parity run, broad repository audit, or metadata-authenticity assessment was performed.
- Caller metadata authenticity is explicitly outside this review's scope. No unconfirmed concurrency or timeout hypothesis is presented as a finding.
- Review applies to the source inspected during this turn; no commit-specific attestation or complete security certification is claimed.

**Decision:** Fix the confirmed XML false-pass case before relying on this harness for generic XML semantic parity. Other inspected safeguards did not produce a confirmed finding in the allotted review window.

## Resolution verification

The implementation now returns canonical XML bytes together with sorted namespace-declaration bindings and their element start indices. This conservatively retains namespace context even when canonical XML serialization drops a declaration used only inside an attribute or text value. The implementation explicitly documents that namespace relocation or redundant declarations can produce conservative mismatches.

Reran the exact original reproduction against the updated source. Observed:

```text
Canonical equality: False
XML comparison: False
```

Executed only the two new targeted regression methods; both passed:

```text
test_xml_namespace_order_is_syntax_but_binding_scope_is_preserved ... ok
test_xml_preserves_namespace_bindings_used_only_in_qname_values ... ok
Ran 2 tests in 0.001s
OK
```

These regressions cover namespace binding changes in `xsi:type`, a custom attribute, and text, plus declaration order equivalence and changed binding scope. The follow-up did not rerun the full suite or expand the review scope. No implementation changes were made by this reviewer.

**Updated decision:** The confirmed XML QName false pass is resolved by the inspected fix and focused execution. The prior finding is closed; the original bounded-review limitations remain.
