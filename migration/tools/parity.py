#!/usr/bin/env python3
"""Capture HTTP parity cases and compare immutable evidence, using Python 3.10+.

    python migration/tools/parity.py capture --suite cases.json \
      --base-url http://127.0.0.1:8070 --out evidence/java-001 --provenance java.json
    python migration/tools/parity.py compare --oracle evidence/java-001 \
      --candidate evidence/rust-001 --report evidence/comparison-001.json

This is an initial deterministic HTTP harness, not a complete GROBID parity proof.
It never retries, follows redirects, removes volatile fields, rounds coordinates,
normalizes PDF binaries, or calls a language-model CLI. See the kit's test strategy
for stage traces, corpus evaluation, training, load tests, and nondeterminism work.
"""

from __future__ import annotations

import argparse
import datetime as dt
import decimal
import hashlib
import http.client
import io
import ipaddress
import json
import math
import re
import socket
import ssl
import stat
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath


SCHEMA_VERSION = 1
MAX_BYTES = 256 * 1024 * 1024
MAX_ZIP_MEMBERS = 10000
ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}\Z")
HEADER_PATTERN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
COMPARATORS = {"bytes", "xml", "json", "zip"}
ENCODINGS = {"none", "form", "multipart", "raw"}
CASE_KEYS = {
    "id", "method", "path", "headers", "encoding", "fields", "files", "body_file",
    "comparator", "expected_status", "compare_headers", "allow_empty_body",
    "description", "tags", "covers",
}


class ParityError(ValueError):
    """Invalid input or incomplete/invalid evidence. Never a passing comparison."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ParityError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ParityError(f"Nonstandard JSON number: {value}")


def read_json(data: bytes, *, numbers_as_decimal=False):
    try:
        kwargs = {"object_pairs_hook": _unique_object, "parse_constant": _reject_constant}
        if numbers_as_decimal:
            kwargs.update(parse_int=decimal.Decimal, parse_float=decimal.Decimal)
        return json.loads(data.decode("utf-8"), **kwargs)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ParityError(f"Invalid JSON: {exc}") from exc


def _pairs(value, what):
    if not isinstance(value, list):
        raise ParityError(f"{what} must be an ordered list of [name, value] string pairs")
    for pair in value:
        if (not isinstance(pair, list) or len(pair) != 2
                or not all(isinstance(v, str) for v in pair)):
            raise ParityError(f"{what} must preserve string pairs, including repeated names")
    return value


def _header(name, value):
    if not HEADER_PATTERN.fullmatch(name):
        raise ParityError(f"Invalid header name: {name!r}")
    if any(ord(c) < 32 and c != "\t" or ord(c) == 127 for c in value):
        raise ParityError(f"Invalid control character in header {name}")
    try:
        value.encode("latin-1")
    except UnicodeEncodeError as exc:
        raise ParityError(f"Header {name} is not representable in HTTP/1.1 Latin-1") from exc


def policy(case):
    names = case.get("compare_headers", [])
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        raise ParityError("compare_headers must be a list of header names")
    for name in names:
        _header(name, "")
    expected = case.get("expected_status", 200)
    if type(expected) is not int or not 100 <= expected <= 599:
        raise ParityError("expected_status must be an integer HTTP status")
    empty = case.get("allow_empty_body", False)
    if type(empty) is not bool:
        raise ParityError("allow_empty_body must be a boolean")
    comparator = case.get("comparator", "bytes")
    if comparator not in COMPARATORS:
        raise ParityError(f"Unknown comparator: {comparator!r}")
    return {"comparator": comparator, "expected_status": expected,
            "allow_empty_body": empty,
            "compare_headers": sorted({"content-type", *(n.lower() for n in names)})}


def validate_suite(suite):
    if (not isinstance(suite, dict) or type(suite.get("schema_version")) is not int
            or suite["schema_version"] != SCHEMA_VERSION):
        raise ParityError("Suite must be an object with schema_version: 1")
    unknown = set(suite) - {"schema_version", "suite_id", "profile", "cases", "description"}
    if unknown:
        raise ParityError(f"Unknown suite keys: {sorted(unknown)}")
    for key in ("suite_id", "profile"):
        if not isinstance(suite.get(key), str) or not suite[key].strip():
            raise ParityError(f"Suite requires nonempty {key}")
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ParityError("Empty or missing case set; this cannot establish parity")
    seen = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ParityError("Each case must be an object")
        unknown = set(case) - CASE_KEYS
        if unknown:
            raise ParityError(f"Unknown case keys (skips are unsupported): {sorted(unknown)}")
        ident = case.get("id")
        if not isinstance(ident, str) or not ID_PATTERN.fullmatch(ident) or ident in seen:
            raise ParityError(f"Invalid or duplicate case id: {ident!r}")
        seen.add(ident)
        method = case.get("method", "GET")
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
            raise ParityError(f"Unsupported method: {method!r}")
        path = case.get("path")
        if (not isinstance(path, str) or not path.startswith("/") or path.startswith("//")
                or "\\" in path or "#" in path or any(ord(c) <= 32 for c in path)):
            raise ParityError(f"Case {ident}: path must be an origin-relative, encoded HTTP path")
        try:
            path.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ParityError("Percent-encode non-ASCII request paths") from exc
        encoding = case.get("encoding", "none")
        if encoding not in ENCODINGS:
            raise ParityError(f"Unknown encoding: {encoding!r}")
        for name, value in _pairs(case.get("headers", []), "headers"):
            _header(name, value)
            if name.lower() in {"host", "content-length", "transfer-encoding", "connection"}:
                raise ParityError(f"Transport-owned header cannot be overridden: {name}")
            if encoding in {"form", "multipart"} and name.lower() == "content-type":
                raise ParityError("Use raw encoding to test an explicitly supplied Content-Type")
        fields = _pairs(case.get("fields", []), "fields")
        files = case.get("files", [])
        if not isinstance(files, list):
            raise ParityError("files must be a list")
        if encoding not in {"form", "multipart"} and fields:
            raise ParityError("fields require form or multipart encoding")
        if encoding != "multipart" and files:
            raise ParityError("files require multipart encoding")
        if encoding != "raw" and "body_file" in case:
            raise ParityError("body_file requires raw encoding")
        if encoding == "raw" and not isinstance(case.get("body_file"), str):
            raise ParityError("raw encoding requires body_file")
        if method in {"GET", "HEAD"} and encoding != "none":
            raise ParityError("GET/HEAD bodies are unsupported in this initial harness")
        for item in files:
            if not isinstance(item, dict) or set(item) - {"field", "path", "filename", "content_type"}:
                raise ParityError("Invalid multipart file declaration")
            if not all(isinstance(item.get(k), str) and item[k] for k in ("field", "path")):
                raise ParityError("Multipart file requires field and path strings")
            for key in ("filename", "content_type"):
                if key in item and not isinstance(item[key], str):
                    raise ParityError(f"Multipart {key} must be a string")
        policy(case)
    return suite


def validate_base_url(url, allow_remote=False):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        raise ParityError("base-url must be an HTTP(S) origin without credentials, path or query")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ParityError(f"Invalid port: {exc}") from exc
    if port is not None and not 1 <= port <= 65535:
        raise ParityError("Port must be between 1 and 65535")
    if not allow_remote:
        host = parsed.hostname.lower()
        if host == "localhost":
            addresses = socket.getaddrinfo(host, port or 80, type=socket.SOCK_STREAM)
            if not addresses or not all(ipaddress.ip_address(a[4][0]).is_loopback for a in addresses):
                raise ParityError("localhost does not resolve exclusively to loopback")
        else:
            try:
                local = ipaddress.ip_address(host).is_loopback
            except ValueError:
                local = False
            if not local:
                raise ParityError("Remote target denied; use --allow-remote only for an authorized server")
    return parsed


def _input_file(suite_dir, name, max_bytes):
    path = (suite_dir / name).resolve()
    if not path.is_file():
        raise ParityError(f"Input is not a file: {name}")
    if path.stat().st_size > max_bytes:
        raise ParityError(f"Input exceeds byte limit: {name}")
    body = path.read_bytes()
    if len(body) > max_bytes:
        raise ParityError(f"Input changed beyond byte limit: {name}")
    return body


def _quoted_disposition(value):
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ParityError("Control character in multipart field/filename")
    return value.replace("\\", "\\\\").replace('"', '\\"')


def prepare_request(case, suite_dir, max_bytes=MAX_BYTES):
    """Build deterministic payload; preserve field order, repeated names and file bytes."""
    encoding = case.get("encoding", "none")
    headers = [[name.lower(), value] for name, value in case.get("headers", [])]
    fields = case.get("fields", [])
    body = b""
    if encoding == "form":
        body = urllib.parse.urlencode([tuple(pair) for pair in fields], encoding="utf-8").encode("ascii")
        headers.append(["content-type", "application/x-www-form-urlencoded"])
    elif encoding == "raw":
        body = _input_file(suite_dir, case["body_file"], max_bytes)
    elif encoding == "multipart":
        parts = []
        for name, value in fields:
            head = f'Content-Disposition: form-data; name="{_quoted_disposition(name)}"\r\n\r\n'
            parts.append((head.encode("utf-8"), value.encode("utf-8")))
        for item in case.get("files", []):
            data = _input_file(suite_dir, item["path"], max_bytes)
            filename = item.get("filename", Path(item["path"]).name)
            content_type = item.get("content_type", "application/octet-stream")
            _header("content-type", content_type)
            head = (f'Content-Disposition: form-data; name="{_quoted_disposition(item["field"])}"; '
                    f'filename="{_quoted_disposition(filename)}"\r\nContent-Type: {content_type}\r\n\r\n')
            parts.append((head.encode("utf-8"), data))
        seed = json_bytes([[digest(head), digest(data)] for head, data in parts])
        boundary = ("grobid-parity-" + digest(seed)[:48]).encode("ascii")
        if any(boundary in head or boundary in data for head, data in parts):
            raise ParityError("Multipart boundary collision; refuse ambiguous request")
        if sum(len(h) + len(d) + len(boundary) + 8 for h, d in parts) + len(boundary) + 6 > max_bytes:
            raise ParityError("Multipart request exceeds byte limit")
        body = b"".join(b"--" + boundary + b"\r\n" + h + d + b"\r\n" for h, d in parts)
        body += b"--" + boundary + b"--\r\n"
        headers.append(["content-type", "multipart/form-data; boundary=" + boundary.decode("ascii")])
    if len(body) > max_bytes:
        raise ParityError("Request exceeds byte limit")
    method = case.get("method", "GET")
    if not any(name == "accept-encoding" for name, _ in headers):
        headers.append(["accept-encoding", "identity"])
    if encoding != "none" or method in {"POST", "PUT", "PATCH"}:
        headers.append(["content-length", str(len(body))])
    descriptor = {"method": method, "path": case["path"], "headers": headers,
                  "body_sha256": digest(body), "body_size": len(body)}
    return descriptor, body


def send_request(origin, request, body, timeout, max_bytes):
    """One HTTP request, no redirects, proxy discovery, decompression, or retries."""
    if origin.scheme == "https":
        connection = http.client.HTTPSConnection(origin.hostname, origin.port, timeout=timeout,
                                                  context=ssl.create_default_context())
    else:
        connection = http.client.HTTPConnection(origin.hostname, origin.port, timeout=timeout)
    started = time.monotonic()
    try:
        connection.putrequest(request["method"], request["path"], skip_host=True, skip_accept_encoding=True)
        connection.putheader("Host", origin.netloc)
        for name, value in request["headers"]:
            connection.putheader(name, value)
        connection.endheaders(body if body else None)
        network_socket = connection.sock
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise ParityError("Request exceeded wall-time limit while sending")
        if network_socket is not None:
            network_socket.settimeout(remaining)
        response = connection.getresponse()
        parts = []
        size = 0
        while True:
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise ParityError("Request exceeded wall-time limit")
            # A Connection: close response can close its backing socket as soon as
            # read1 consumes the last bytes; the following read1 then returns EOF.
            if network_socket is not None and network_socket.fileno() >= 0:
                network_socket.settimeout(remaining)
            chunk = response.read1(min(65536, max_bytes - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise ParityError("Response exceeds byte limit")
            parts.append(chunk)
        payload = b"".join(parts)
        # read1 does not necessarily raise IncompleteRead: check the HTTP body's length.
        if request["method"] != "HEAD" and response.status not in {204, 304}:
            declared = response.getheader("Content-Length")
            if declared is not None:
                try:
                    expected_length = int(declared)
                except ValueError as exc:
                    raise ParityError("Invalid response Content-Length") from exc
                if expected_length != len(payload):
                    raise ParityError("Truncated or inconsistent Content-Length response")
        envelope = {"status": response.status, "reason": response.reason,
                    "headers": [[name, value] for name, value in response.getheaders()],
                    "body_sha256": digest(payload), "body_size": len(payload)}
        return envelope, payload, time.monotonic() - started
    finally:
        connection.close()


def _save_manifest(directory, manifest):
    temporary = directory / "manifest.json.tmp"
    temporary.write_bytes(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8") + b"\n")
    temporary.replace(directory / "manifest.json")


def capture(suite_path, base_url, output_dir, provenance_path, *, allow_remote=False,
            timeout=120.0, max_bytes=MAX_BYTES):
    if not math.isfinite(timeout) or timeout <= 0 or type(max_bytes) is not int or max_bytes < 1:
        raise ParityError("Timeout and byte limit must be positive")
    suite_path, output_dir, provenance_path = map(Path, (suite_path, output_dir, provenance_path))
    suite_raw = suite_path.read_bytes()
    suite = validate_suite(read_json(suite_raw))
    provenance_raw = provenance_path.read_bytes()
    provenance = read_json(provenance_raw)
    if not isinstance(provenance, dict) or not provenance:
        raise ParityError("Provenance must be a nonempty JSON object describing the actual runtime")
    if not isinstance(provenance.get("compatibility"), dict) or not provenance["compatibility"]:
        raise ParityError("Provenance requires a nonempty compatibility object of pinned shared conditions")
    origin = validate_base_url(base_url, allow_remote)
    # Validate all inputs before sending anything. The user-authored suite may contain stateful APIs.
    prepared = [(case, *prepare_request(case, suite_path.resolve().parent, max_bytes)) for case in suite["cases"]]
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "requests").mkdir()
    (output_dir / "responses").mkdir()
    (output_dir / "suite.json").write_bytes(suite_raw)
    (output_dir / "provenance.json").write_bytes(provenance_raw)
    manifest = {"schema_version": SCHEMA_VERSION, "capture_complete": False,
                "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "base_url": base_url, "remote_opt_in": allow_remote,
                "suite_id": suite["suite_id"], "profile": suite["profile"],
                "suite_sha256": digest(suite_raw), "provenance_sha256": digest(provenance_raw),
                "provenance": provenance, "harness_sha256": digest(Path(__file__).read_bytes()),
                "timeout_seconds": timeout, "max_bytes": max_bytes,
                "expected_case_ids": [case["id"] for case in suite["cases"]], "cases": []}
    _save_manifest(output_dir, manifest)
    for case, request, body in prepared:
        ident = case["id"]
        request_file = f"requests/{ident}.bin"
        (output_dir / request_file).write_bytes(body)
        row = {"id": ident, "policy": policy(case), "request": request,
               "request_file": request_file, "request_sha256": digest(json_bytes(request)),
               "response": None, "response_file": None, "response_sha256": None,
               "elapsed_seconds": None, "error": None, "checks": []}
        started = time.monotonic()
        try:
            response, payload, elapsed = send_request(origin, request, body, timeout, max_bytes)
            response_file = f"responses/{ident}.bin"
            (output_dir / response_file).write_bytes(payload)
            row.update(response=response, response_file=response_file,
                       response_sha256=digest(json_bytes(response)), elapsed_seconds=elapsed)
            if response["status"] != row["policy"]["expected_status"]:
                row["checks"].append(f"Expected status {row['policy']['expected_status']}, got {response['status']}")
            if not payload and not row["policy"]["allow_empty_body"]:
                row["checks"].append("Unexpected empty response body")
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            row["elapsed_seconds"] = time.monotonic() - started
        manifest["cases"].append(row)
        _save_manifest(output_dir, manifest)
    manifest["capture_complete"] = True
    manifest["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest["ok"] = all(not row["error"] and not row["checks"] for row in manifest["cases"])
    _save_manifest(output_dir, manifest)
    return manifest


class _NoDoctypeCanonicalTarget(ET.C14NWriterTarget):
    def __init__(self, write, **options):
        super().__init__(write, **options)
        self.namespace_declarations = []
        self._pending_declarations = []
        self._element_index = 0

    def start_ns(self, prefix, uri):
        self._pending_declarations.append((prefix or "", uri))
        return super().start_ns(prefix, uri)

    def start(self, tag, attrs):
        # C14N alone can discard a namespace used only inside a QName-valued
        # attribute or text node, changing its meaning without changing bytes.
        # Preserve all declaration bindings and their element positions. This
        # deliberately rejects some equivalent namespace relocation/redundancy;
        # a generic comparator cannot infer every vocabulary's QName fields.
        if self._pending_declarations:
            self.namespace_declarations.append(
                (self._element_index, tuple(sorted(self._pending_declarations))))
            self._pending_declarations.clear()
        self._element_index += 1
        return super().start(tag, attrs)

    def doctype(self, name, pubid, system):
        raise ParityError("DOCTYPE/entity declarations are unsupported by the conservative XML comparator")


def canonical_xml(data):
    """Return canonical bytes plus conservative namespace-declaration evidence."""
    output = io.StringIO()
    target = _NoDoctypeCanonicalTarget(output.write, with_comments=True, strip_text=False,
                                       rewrite_prefixes=False)
    parser = ET.XMLParser(target=target)
    try:
        parser.feed(data)
        parser.close()
    except (ET.ParseError, ValueError) as exc:
        raise ParityError(f"Invalid/unsupported XML: {exc}") from exc
    return output.getvalue().encode("utf-8"), tuple(target.namespace_declarations)


def _json_structure(value):
    # Tagged leaves prevent Python's True == 1 from silently accepting a type change.
    if value is None:
        return ("null",)
    if type(value) is bool:
        return ("bool", value)
    if isinstance(value, decimal.Decimal):
        return ("number", value)
    if isinstance(value, str):
        return ("string", value)
    if isinstance(value, list):
        return ("array", tuple(_json_structure(v) for v in value))
    if isinstance(value, dict):
        return ("object", tuple((k, _json_structure(v)) for k, v in sorted(value.items())))
    raise ParityError(f"Unexpected JSON value type: {type(value).__name__}")


def logical_zip(data, max_bytes=MAX_BYTES):
    members = {}
    logical_names = set()
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ZIP_MEMBERS:
                raise ParityError("ZIP member count exceeds limit")
            for info in entries:
                name = info.filename
                parts = name[:-1].split("/") if name.endswith("/") else name.split("/")
                if (not name or info.orig_filename != name or "\\" in name or ":" in name
                        or name.startswith("/") or any(p in {"", ".", ".."} for p in parts)):
                    raise ParityError(f"Unsafe/ambiguous ZIP member: {name!r}")
                if name in members:
                    raise ParityError(f"Duplicate ZIP member: {name!r}")
                logical_name = name.rstrip("/")
                if logical_name in logical_names:
                    raise ParityError(f"Conflicting ZIP file/directory member: {name!r}")
                logical_names.add(logical_name)
                mode = info.external_attr >> 16
                if stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}:
                    raise ParityError(f"Unsupported ZIP member type: {name!r}")
                if info.flag_bits & 1:
                    raise ParityError("Encrypted ZIP entries are unsupported")
                total += info.file_size
                if total > max_bytes:
                    raise ParityError("ZIP uncompressed bytes exceed limit")
                with archive.open(info) as member:
                    payload = member.read(info.file_size + 1)
                if len(payload) != info.file_size:
                    raise ParityError(f"Inconsistent ZIP member size: {name!r}")
                if info.is_dir() and payload:
                    raise ParityError(f"ZIP directory contains bytes: {name!r}")
                members[name] = ("directory" if info.is_dir() else "file", payload)
            files = {name for name, (kind, _) in members.items() if kind == "file"}
            for name in members:
                parts = name.rstrip("/").split("/")
                if any("/".join(parts[:n]) in files for n in range(1, len(parts))):
                    raise ParityError(f"ZIP file is also used as a directory: {name!r}")
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise ParityError(f"Invalid/unsupported ZIP: {exc}") from exc
    return members


def compare_bodies(left, right, comparator, max_bytes=MAX_BYTES):
    if comparator == "bytes":
        return left == right
    if comparator == "xml":
        return canonical_xml(left) == canonical_xml(right)
    if comparator == "json":
        return (_json_structure(read_json(left, numbers_as_decimal=True))
                == _json_structure(read_json(right, numbers_as_decimal=True)))
    if comparator == "zip":
        return logical_zip(left, max_bytes) == logical_zip(right, max_bytes)
    raise ParityError(f"Unknown comparator: {comparator!r}")


def _evidence_file(directory, relative, max_bytes=MAX_BYTES):
    if not isinstance(relative, str) or "\\" in relative:
        raise ParityError("Invalid evidence path")
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in {"..", "."} for part in path.parts):
        raise ParityError("Evidence path escapes its capture directory")
    resolved = (directory / relative).resolve()
    if not resolved.is_relative_to(directory.resolve()) or not resolved.is_file():
        raise ParityError(f"Missing or escaping evidence file: {relative!r}")
    if resolved.stat().st_size > max_bytes:
        raise ParityError("Evidence file exceeds configured byte limit")
    data = resolved.read_bytes()
    if len(data) > max_bytes:
        raise ParityError("Evidence file changed beyond configured byte limit")
    return data


def _headers(envelope, names):
    pairs = _pairs(envelope.get("headers"), "response headers")
    result = {name: [] for name in names}
    for name, value in pairs:
        _header(name, value)
        if name.lower() in result:
            result[name.lower()].append(value)
    return result


def load_capture(directory, max_bytes=MAX_BYTES):
    directory = Path(directory)
    manifest = read_json(_evidence_file(directory, "manifest.json", max_bytes))
    if (not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int
            or manifest["schema_version"] != SCHEMA_VERSION):
        raise ParityError("Unknown capture schema")
    if manifest.get("capture_complete") is not True or manifest.get("ok") is not True:
        raise ParityError("Capture is incomplete or contains failed requests")
    suite_raw = _evidence_file(directory, "suite.json", max_bytes)
    if digest(suite_raw) != manifest.get("suite_sha256"):
        raise ParityError("Suite evidence hash mismatch")
    suite = validate_suite(read_json(suite_raw))
    provenance_raw = _evidence_file(directory, "provenance.json", max_bytes)
    if digest(provenance_raw) != manifest.get("provenance_sha256"):
        raise ParityError("Provenance evidence hash mismatch")
    provenance = read_json(provenance_raw)
    if not isinstance(provenance, dict) or not provenance or provenance != manifest.get("provenance"):
        raise ParityError("Missing/inconsistent provenance")
    if not isinstance(provenance.get("compatibility"), dict) or not provenance["compatibility"]:
        raise ParityError("Missing shared compatibility provenance")
    if any(manifest.get(key) != suite[key] for key in ("suite_id", "profile")):
        raise ParityError("Suite identity/profile differs from its evidence")
    expected = [case["id"] for case in suite["cases"]]
    rows = manifest.get("cases")
    if (not isinstance(rows, list) or not rows or manifest.get("expected_case_ids") != expected
            or any(not isinstance(row, dict) for row in rows)
            or [row.get("id") for row in rows] != expected):
        raise ParityError("Missing, duplicate, skipped, reordered, or empty captured case set")
    for case, row in zip(suite["cases"], rows):
        if row.get("error") is not None or row.get("checks") != []:
            raise ParityError(f"Case {row['id']}: failed or skipped capture")
        if row.get("policy") != policy(case):
            raise ParityError(f"Case {row['id']}: comparison policy differs from suite")
        request = row.get("request")
        response = row.get("response")
        if not isinstance(request, dict) or not isinstance(response, dict):
            raise ParityError(f"Case {row['id']}: missing request/response")
        if request.get("method") != case.get("method", "GET") or request.get("path") != case["path"]:
            raise ParityError(f"Case {row['id']}: request differs from suite")
        for kind, envelope in (("request", request), ("response", response)):
            payload = _evidence_file(directory, row.get(kind + "_file"), max_bytes)
            if envelope.get("body_size") != len(payload) or envelope.get("body_sha256") != digest(payload):
                raise ParityError(f"Case {row['id']}: {kind} payload hash/size mismatch")
            if row.get(kind + "_sha256") != digest(json_bytes(envelope)):
                raise ParityError(f"Case {row['id']}: {kind} envelope hash mismatch")
        if response.get("status") != row["policy"]["expected_status"]:
            raise ParityError(f"Case {row['id']}: unexpected HTTP status")
        if response.get("body_size") == 0 and not row["policy"]["allow_empty_body"]:
            raise ParityError(f"Case {row['id']}: unexpectedly empty response")
        _headers(response, row["policy"]["compare_headers"])
    return manifest


def compare_captures(oracle_dir, candidate_dir, *, max_bytes=MAX_BYTES):
    report = {"schema_version": SCHEMA_VERSION, "ok": False,
              "oracle": str(oracle_dir), "candidate": str(candidate_dir), "errors": [], "cases": []}
    captures = []
    for role, directory in (("oracle", oracle_dir), ("candidate", candidate_dir)):
        try:
            captures.append(load_capture(directory, max_bytes))
        except (OSError, ValueError, TypeError, KeyError) as exc:
            report["errors"].append(f"{role}: {exc}")
    if report["errors"]:
        return report
    left, right = captures
    for key in ("suite_id", "profile", "suite_sha256", "expected_case_ids", "harness_sha256"):
        if left.get(key) != right.get(key):
            report["errors"].append(f"Captures disagree on {key}")
    # These are caller-declared equivalence conditions, e.g. immutable model/native asset
    # manifests. Revisions of the Java and Rust implementation themselves may differ.
    if json_bytes(left["provenance"]["compatibility"]) != json_bytes(right["provenance"]["compatibility"]):
        report["errors"].append("Provenance compatibility differs")
    if left["expected_case_ids"] != right["expected_case_ids"]:
        return report
    for a, b in zip(left["cases"], right["cases"]):
        result = {"id": a["id"], "ok": False, "errors": [],
                  "oracle_response_sha256": a["response_sha256"],
                  "candidate_response_sha256": b["response_sha256"]}
        if a["request_sha256"] != b["request_sha256"]:
            result["errors"].append("Request fingerprints differ; outputs are not comparable")
        if a["policy"] != b["policy"]:
            result["errors"].append("Comparison policies differ")
        if a["response"]["status"] != b["response"]["status"]:
            result["errors"].append("HTTP statuses differ")
        selected = a["policy"]["compare_headers"]
        if _headers(a["response"], selected) != _headers(b["response"], selected):
            result["errors"].append("Selected response headers (including Content-Type) differ")
        if not result["errors"]:
            try:
                body_a = _evidence_file(Path(oracle_dir), a["response_file"], max_bytes)
                body_b = _evidence_file(Path(candidate_dir), b["response_file"], max_bytes)
                # Empty bodies are valid only with an explicit per-case allowance. There is
                # no XML/JSON document to parse for e.g. an expected 204 response.
                equal = (not body_a and not body_b and a["policy"]["allow_empty_body"])
                if not equal:
                    equal = compare_bodies(body_a, body_b, a["policy"]["comparator"], max_bytes)
                if not equal:
                    result["errors"].append(f"Response bodies differ under {a['policy']['comparator']} comparator")
            except (OSError, ValueError, TypeError, RecursionError) as exc:
                result["errors"].append(f"Comparator rejected evidence: {exc}")
        result["ok"] = not result["errors"]
        report["cases"].append(result)
    report["ok"] = bool(report["cases"]) and not report["errors"] and all(c["ok"] for c in report["cases"])
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    cap = commands.add_parser("capture", help="capture one explicitly chosen local server")
    cap.add_argument("--suite", required=True, type=Path)
    cap.add_argument("--base-url", required=True)
    cap.add_argument("--out", required=True, type=Path)
    cap.add_argument("--provenance", required=True, type=Path)
    cap.add_argument("--allow-remote", action="store_true", help="explicitly permit the supplied non-loopback origin")
    cap.add_argument("--timeout", type=float, default=120.0)
    cap.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    comp = commands.add_parser("compare", help="compare complete captures, failing closed")
    comp.add_argument("--oracle", required=True, type=Path)
    comp.add_argument("--candidate", required=True, type=Path)
    comp.add_argument("--report", required=True, type=Path)
    comp.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            result = capture(args.suite, args.base_url, args.out, args.provenance,
                             allow_remote=args.allow_remote, timeout=args.timeout, max_bytes=args.max_bytes)
            print(json.dumps({"ok": result["ok"], "manifest": str(args.out / "manifest.json"),
                              "cases": len(result["cases"])}))
        else:
            result = compare_captures(args.oracle, args.candidate, max_bytes=args.max_bytes)
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open("x", encoding="utf-8") as output:
                json.dump(result, output, indent=2, ensure_ascii=False, allow_nan=False)
                output.write("\n")
            print(json.dumps({"ok": result["ok"], "report": str(args.report),
                              "cases": len(result["cases"]), "errors": result["errors"]}))
        return 0 if result["ok"] else 1
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"parity: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
