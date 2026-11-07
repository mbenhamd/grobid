"""Meaningful self-tests of the harness; no upstream Java/Rust runtime is tested.

Run: python -m unittest discover -s migration/tools/tests -v
Only in-process loopback HTTP fixtures are contacted.
"""

from __future__ import annotations

import contextlib
import hashlib
import http.server
import importlib.util
import io
import json
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
import warnings
import zipfile
from pathlib import Path


TOOL = Path(__file__).resolve().parents[1] / "parity.py"
SPEC = importlib.util.spec_from_file_location("parity", TOOL)
parity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parity)


class FixtureHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def respond(self, status, data, content_type="application/json", extra=()):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        for name, value in extra:
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def do_GET(self):
        self.server.paths.append(self.path)
        if self.path == "/json":
            self.respond(200, b'{"integer":9007199254740993,"values":[1,2],"flag":true}')
        elif self.path == "/binary":
            self.respond(200, b"%PDF-fixture\x00\xff\xfe\x00", "application/pdf")
        elif self.path == "/empty":
            self.respond(204, b"", "application/xml")
        elif self.path == "/empty200":
            self.respond(200, b"", "text/plain")
        elif self.path == "/redirect":
            self.respond(302, b"move", "text/plain", [("Location", "/target")])
        elif self.path == "/close":
            self.respond(200, b"close-after-body", "text/plain", [("Connection", "close")])
            self.close_connection = True
        elif self.path == "/truncated":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", "100")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(b"short")
            self.close_connection = True
        elif self.path == "/slow":
            time.sleep(0.12)
            try:
                self.respond(200, b"slow", "text/plain")
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.respond(404, b'{"error":"unknown"}')

    def do_POST(self):
        self.server.paths.append(self.path)
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if self.path == "/form":
            result = {"fields": urllib.parse.parse_qsl(raw.decode("ascii"), keep_blank_values=True),
                      "accept": self.headers.get("Accept"),
                      "content_type": self.headers.get("Content-Type")}
            self.respond(200, json.dumps(result, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/multipart":
            self.respond(200, raw, "application/octet-stream")
        elif self.path == "/error":
            self.respond(400, b'{"error":"bad request"}')
        else:
            self.respond(404, b'{"error":"unknown"}')


@contextlib.contextmanager
def fixture_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    server.paths = []
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


def make_zip(entries, year=2020):
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(output, "w") as archive:
            for name, data in entries:
                info = zipfile.ZipInfo(name, (year, 1, 1, 0, 0, 0))
                archive.writestr(info, data)
    return output.getvalue()


class ComparatorTests(unittest.TestCase):
    def test_bytes_does_not_canonicalize_pdf_or_other_binary(self):
        self.assertTrue(parity.compare_bodies(b"%PDF\x00\xff", b"%PDF\x00\xff", "bytes"))
        self.assertFalse(parity.compare_bodies(b"%PDF\x00\xff", b"%PDF\x00\xfe", "bytes"))

    def test_xml_allows_attribute_order_and_empty_element_syntax(self):
        self.assertTrue(parity.compare_bodies(b'<r b="2" a="1"><s/></r>',
                                              b'<r a="1" b="2"><s></s></r>', "xml"))

    def test_xml_preserves_mixed_whitespace_order_ids_coordinates_comments(self):
        baseline = b'<r xml:id="p1" coords="1,2.10,3"><p>A <hi>B</hi> C</p><!--x--></r>'
        variants = [baseline.replace(b"A ", b"A"), baseline.replace(b"> C", b">C"),
                    baseline.replace(b"p1", b"p2"), baseline.replace(b"2.10", b"2.1"),
                    baseline.replace(b"<!--x-->", b"<!--y-->"),
                    baseline.replace(b"<hi>B</hi> C", b"C <hi>B</hi>")]
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertFalse(parity.compare_bodies(baseline, variant, "xml"))

    def test_xml_preserves_namespace_bindings_used_only_in_qname_values(self):
        examples = [
            b'<r xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            b'xmlns:t="urn:one" xsi:type="t:Example"/>',
            b'<r xmlns:t="urn:one" custom="t:Example"/>',
            b'<r xmlns:t="urn:one">t:Example</r>',
        ]
        for baseline in examples:
            with self.subTest(baseline=baseline):
                self.assertTrue(parity.compare_bodies(baseline, baseline, "xml"))
                self.assertFalse(parity.compare_bodies(
                    baseline, baseline.replace(b"urn:one", b"urn:two"), "xml"))

    def test_xml_namespace_order_is_syntax_but_binding_scope_is_preserved(self):
        a = b'<r xmlns:a="urn:a" xmlns:b="urn:b"><s kind="a:T"/></r>'
        b = b'<r xmlns:b="urn:b" xmlns:a="urn:a"><s kind="a:T"></s></r>'
        self.assertTrue(parity.compare_bodies(a, b, "xml"))
        a = b'<r><s xmlns:t="urn:a" kind="t:T"/><s kind="t:T"/></r>'
        b = b'<r><s kind="t:T"/><s xmlns:t="urn:a" kind="t:T"/></r>'
        self.assertFalse(parity.compare_bodies(a, b, "xml"))

    def test_xml_rejects_dtd_even_when_utf16_encoded(self):
        text = '<!DOCTYPE r [<!ENTITY x "secret">]><r>&x;</r>'
        for data in (text.encode("utf-8"), text.encode("utf-16")):
            with self.subTest(encoding=data[:4]), self.assertRaises(parity.ParityError):
                parity.compare_bodies(data, data, "xml")

    def test_xml_invalid_input_never_passes_itself(self):
        with self.assertRaises(parity.ParityError):
            parity.compare_bodies(b"<r>", b"<r>", "xml")

    def test_json_object_order_is_ignored_but_array_order_is_not(self):
        self.assertTrue(parity.compare_bodies(b'{"x":1,"y":[2,3]}', b'{"y":[2,3],"x":1.0}', "json"))
        self.assertFalse(parity.compare_bodies(b'{"x":[1,2]}', b'{"x":[2,1]}', "json"))

    def test_json_numbers_are_exact_and_distinct_from_boolean(self):
        self.assertFalse(parity.compare_bodies(b'{"x":9007199254740992}', b'{"x":9007199254740993}', "json"))
        self.assertFalse(parity.compare_bodies(b'{"x":true}', b'{"x":1}', "json"))
        self.assertFalse(parity.compare_bodies(b'{"x":1e-500}', b'{"x":0}', "json"))
        self.assertTrue(parity.compare_bodies(b'{"x":1e500}', b'{"x":10e499}', "json"))

    def test_json_rejects_duplicate_keys_and_nonstandard_numbers(self):
        for body in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}'):
            with self.subTest(body=body), self.assertRaises(parity.ParityError):
                parity.compare_bodies(body, body, "json")

    def test_zip_ignores_container_order_and_timestamps_only(self):
        a = make_zip([("paper.tei.xml", b"<r/>"), ("assets/a.bin", b"\x00\xff")])
        b = make_zip([("assets/a.bin", b"\x00\xff"), ("paper.tei.xml", b"<r/>")], year=2024)
        self.assertNotEqual(a, b)
        self.assertTrue(parity.compare_bodies(a, b, "zip"))
        self.assertFalse(parity.compare_bodies(a, make_zip([("paper.tei.xml", b"<r/>")]), "zip"))
        self.assertFalse(parity.compare_bodies(a, make_zip([("paper.tei.xml", b"<r></r>"),
                                                          ("assets/a.bin", b"\x00\xff")]), "zip"))

    def test_zip_rejects_unsafe_duplicate_and_ambiguous_paths(self):
        invalid = [[("../escape", b"x")], [("/root", b"x")], [("a\\b", b"x")],
                   [("C:/a", b"x")], [("a//b", b"x")], [("./a", b"x")],
                   [("a", b"x"), ("a", b"y")], [("a", b"x"), ("a/", b"")],
                   [("a", b"x"), ("a/b", b"y")]]
        for entries in invalid:
            data = make_zip(entries)
            with self.subTest(entries=entries), self.assertRaises(parity.ParityError):
                parity.compare_bodies(data, data, "zip")

    def test_zip_rejects_symlinks_and_bounded_expansion(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            info = zipfile.ZipInfo("link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, "../../outside")
        with self.assertRaises(parity.ParityError):
            parity.logical_zip(stream.getvalue())
        with self.assertRaises(parity.ParityError):
            parity.logical_zip(make_zip([("large", b"x" * 100)]), max_bytes=50)
        with self.assertRaises(parity.ParityError):
            parity.logical_zip(b"not-a-zip")


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.suite_path = self.root / "cases.json"
        self.provenance_path = self.root / "provenance.json"
        self.provenance = {"implementation": "local-http-test", "source_revision": "self-test-only",
                           "compatibility": {"test_fixture": "local-test"}}
        self.provenance_path.write_text(json.dumps(self.provenance))

    def tearDown(self):
        self.temp.cleanup()

    def suite(self, cases):
        value = {"schema_version": 1, "suite_id": "self-test", "profile": "fixture-only", "cases": cases}
        self.suite_path.write_text(json.dumps(value, ensure_ascii=False))
        return value

    def capture(self, name, base_url, **kwargs):
        out = self.root / name
        manifest = parity.capture(self.suite_path, base_url, out, self.provenance_path, **kwargs)
        return out, manifest

    def rewrite_manifest(self, directory, transform):
        path = directory / "manifest.json"
        manifest = json.loads(path.read_text())
        transform(manifest)
        path.write_text(json.dumps(manifest))

    def test_capture_and_compare_form_repeated_fields_binary_and_errors(self):
        self.suite([
            {"id": "get", "path": "/json", "comparator": "json"},
            {"id": "form", "method": "POST", "path": "/form", "encoding": "form",
             "headers": [["Accept", "application/json"]],
             "fields": [["citation", "Élément + one"], ["citation", "second"], ["empty", ""]],
             "comparator": "json"},
            {"id": "binary", "path": "/binary"},
            {"id": "error", "method": "POST", "path": "/error", "expected_status": 400, "comparator": "json"},
        ])
        with fixture_server() as (server, url):
            a, first = self.capture("java", url)
            self.provenance["implementation"] = "other-local-build"
            self.provenance_path.write_text(json.dumps(self.provenance))
            b, second = self.capture("rust", url)
        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(len(server.paths), 8)
        report = parity.compare_captures(a, b)
        self.assertTrue(report["ok"], report)
        form = json.loads((a / "responses/form.bin").read_bytes())
        self.assertEqual(form["fields"], [["citation", "Élément + one"], ["citation", "second"], ["empty", ""]])
        self.assertEqual(form["accept"], "application/json")
        self.assertEqual((a / "responses/binary.bin").read_bytes(), b"%PDF-fixture\x00\xff\xfe\x00")
        self.assertGreaterEqual(first["cases"][0]["elapsed_seconds"], 0)
        self.assertEqual(len(first["cases"][0]["request_sha256"]), 64)

    def test_multipart_preserves_repeated_fields_and_binary_file_exactly(self):
        data = b"PDF\x00\xff\r\nEOF"
        (self.root / "input.pdf").write_bytes(data)
        self.suite([{"id": "upload", "method": "POST", "path": "/multipart", "encoding": "multipart",
                     "fields": [["teiCoordinates", "ref"], ["teiCoordinates", "figure"]],
                     "files": [{"field": "input", "path": "input.pdf", "filename": "source.pdf",
                                "content_type": "application/pdf"}]}])
        with fixture_server() as (_, url):
            a, manifest = self.capture("a", url)
            b, _ = self.capture("b", url)
        self.assertTrue(manifest["ok"])
        request = (a / "requests/upload.bin").read_bytes()
        self.assertIn(b'name="teiCoordinates"\r\n\r\nref\r\n', request)
        self.assertIn(b'name="teiCoordinates"\r\n\r\nfigure\r\n', request)
        self.assertIn(b'filename="source.pdf"', request)
        self.assertIn(data, request)
        self.assertEqual(request, (a / "responses/upload.bin").read_bytes())
        self.assertTrue(parity.compare_captures(a, b)["ok"])

    def test_remote_targets_and_path_traversal_ids_are_rejected_before_io(self):
        with self.assertRaises(parity.ParityError):
            parity.validate_base_url("https://example.com")
        self.assertEqual(parity.validate_base_url("https://example.com", True).hostname, "example.com")
        for url in ("http://user:pass@127.0.0.1", "http://127.0.0.1/api", "http://127.0.0.1#fragment"):
            with self.subTest(url=url), self.assertRaises(parity.ParityError):
                parity.validate_base_url(url)
        for ident in ("../escape", "/root", "a/b", ".."):
            with self.subTest(ident=ident), self.assertRaises(parity.ParityError):
                parity.validate_suite(self.suite([{"id": ident, "path": "/json"}]))

    def test_empty_duplicate_skipped_and_misspelled_case_sets_fail(self):
        invalid = [[], [{"id": "a", "path": "/json"}, {"id": "a", "path": "/json"}],
                   [{"id": "a", "path": "/json", "skip": True}],
                   [{"id": "a", "path": "/json", "comparater": "json"}],
                   [{"id": "a", "path": "//example.com/"}]]
        for cases in invalid:
            with self.subTest(cases=cases), self.assertRaises(parity.ParityError):
                parity.validate_suite(self.suite(cases))

    def test_redirect_is_captured_without_following(self):
        self.suite([{"id": "move", "path": "/redirect", "expected_status": 302,
                     "compare_headers": ["Location"]}])
        with fixture_server() as (server, url):
            directory, manifest = self.capture("redirect", url)
        self.assertTrue(manifest["ok"])
        self.assertEqual(server.paths, ["/redirect"])
        self.assertEqual(manifest["cases"][0]["response"]["status"], 302)
        self.assertTrue(parity.compare_captures(directory, directory)["ok"])

    def test_valid_connection_close_response_is_captured(self):
        self.suite([{"id": "close", "path": "/close"}])
        with fixture_server() as (_, url):
            directory, manifest = self.capture("close", url)
        self.assertTrue(manifest["ok"], manifest)
        self.assertEqual((directory / "responses/close.bin").read_bytes(), b"close-after-body")

    def test_unexpected_status_or_empty_response_never_passes(self):
        for path in ("/missing", "/empty200"):
            self.suite([{"id": "bad", "path": path}])
            with fixture_server() as (_, url):
                directory, manifest = self.capture(path[1:], url)
            self.assertFalse(manifest["ok"])
            self.assertFalse(parity.compare_captures(directory, directory)["ok"])

    def test_intentionally_empty_204_requires_explicit_allowance(self):
        self.suite([{"id": "none", "path": "/empty", "expected_status": 204,
                     "allow_empty_body": True, "comparator": "xml"}])
        with fixture_server() as (_, url):
            directory, manifest = self.capture("empty", url)
        self.assertTrue(manifest["ok"])
        self.assertTrue(parity.compare_captures(directory, directory)["ok"])

    def test_truncated_and_oversized_responses_fail_without_retries(self):
        for name, path, limit in (("truncated", "/truncated", 1024), ("large", "/binary", 5)):
            self.suite([{"id": "bounded", "path": path}])
            with fixture_server() as (server, url):
                directory, manifest = self.capture(name, url, max_bytes=limit)
            self.assertFalse(manifest["ok"])
            self.assertEqual(server.paths, [path])
            self.assertIsNotNone(manifest["cases"][0]["error"])

    def test_timeout_is_failed_evidence(self):
        self.suite([{"id": "slow", "path": "/slow"}])
        with fixture_server() as (server, url):
            directory, manifest = self.capture("timeout", url, timeout=0.025)
        self.assertFalse(manifest["ok"])
        self.assertEqual(server.paths, ["/slow"])
        self.assertFalse(parity.compare_captures(directory, directory)["ok"])

    def test_existing_capture_is_never_overwritten(self):
        self.suite([{"id": "a", "path": "/json"}])
        with fixture_server() as (_, url):
            directory, _ = self.capture("fixed", url)
            before = (directory / "manifest.json").read_bytes()
            with self.assertRaises(FileExistsError):
                self.capture("fixed", url)
        self.assertEqual(before, (directory / "manifest.json").read_bytes())

    def test_tampered_body_missing_case_or_incomplete_capture_fails(self):
        self.suite([{"id": "a", "path": "/json", "comparator": "json"}])
        with fixture_server() as (_, url):
            good, _ = self.capture("good", url)
            body, _ = self.capture("body", url)
            missing, _ = self.capture("missing", url)
            incomplete, _ = self.capture("incomplete", url)
        (body / "responses/a.bin").write_bytes(b"{}")
        self.rewrite_manifest(missing, lambda m: m.update(cases=[]))
        self.rewrite_manifest(incomplete, lambda m: m.update(capture_complete=False))
        for bad in (body, missing, incomplete):
            with self.subTest(bad=bad):
                report = parity.compare_captures(good, bad)
                self.assertFalse(report["ok"])
                self.assertTrue(report["errors"])

    def test_request_content_changes_are_detected_even_with_identical_echo_output(self):
        (self.root / "raw.bin").write_bytes(b"one")
        self.suite([{"id": "request", "method": "POST", "path": "/error", "encoding": "raw",
                     "body_file": "raw.bin", "expected_status": 400, "comparator": "json"}])
        with fixture_server() as (_, url):
            a, _ = self.capture("one", url)
            (self.root / "raw.bin").write_bytes(b"two")
            b, _ = self.capture("two", url)
        report = parity.compare_captures(a, b)
        self.assertFalse(report["ok"])
        self.assertIn("Request fingerprints differ", report["cases"][0]["errors"][0])

    def test_shared_compatibility_must_match_while_implementation_may_differ(self):
        self.suite([{"id": "a", "path": "/json", "comparator": "json"}])
        with fixture_server() as (_, url):
            a, _ = self.capture("first", url)
            self.provenance["compatibility"]["test_fixture"] = "different-models"
            self.provenance_path.write_text(json.dumps(self.provenance))
            b, _ = self.capture("second", url)
        report = parity.compare_captures(a, b)
        self.assertFalse(report["ok"])
        self.assertIn("Provenance compatibility differs", report["errors"])

    def test_provenance_is_required_and_evidence_paths_cannot_escape(self):
        self.suite([{"id": "a", "path": "/json"}])
        self.provenance_path.write_text('{"implementation":"unverifiable"}')
        with self.assertRaises(parity.ParityError):
            self.capture("bad", "http://127.0.0.1:1")
        self.provenance_path.write_text(json.dumps(self.provenance))
        with fixture_server() as (_, url):
            directory, _ = self.capture("capture", url)
        self.rewrite_manifest(directory, lambda m: m["cases"][0].update(response_file="../raw.bin"))
        self.assertFalse(parity.compare_captures(directory, directory)["ok"])

    def test_cli_capture_and_compare_return_meaningful_exit_codes(self):
        self.suite([{"id": "cli", "path": "/json", "comparator": "json"}])
        directory = self.root / "cli"
        with fixture_server() as (_, url):
            captured = subprocess.run([sys.executable, str(TOOL), "capture", "--suite", str(self.suite_path),
                                       "--base-url", url, "--out", str(directory),
                                       "--provenance", str(self.provenance_path)], capture_output=True, text=True)
        self.assertEqual(captured.returncode, 0, captured.stderr)
        report_path = self.root / "report.json"
        compared = subprocess.run([sys.executable, str(TOOL), "compare", "--oracle", str(directory),
                                   "--candidate", str(directory), "--report", str(report_path)],
                                  capture_output=True, text=True)
        self.assertEqual(compared.returncode, 0, compared.stderr)
        self.assertTrue(json.loads(report_path.read_text())["ok"])
        (directory / "responses/cli.bin").write_bytes(b"tampered")
        failed = subprocess.run([sys.executable, str(TOOL), "compare", "--oracle", str(directory),
                                 "--candidate", str(directory), "--report", str(self.root / "failed.json")],
                                capture_output=True, text=True)
        self.assertEqual(failed.returncode, 1, failed.stderr)


if __name__ == "__main__":
    unittest.main()
