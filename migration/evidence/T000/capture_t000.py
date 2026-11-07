#!/usr/bin/env python3
"""T000: freeze pinned GROBID source and record the build/runtime environment.

Usage:
  python3 -I migration/evidence/T000/capture_t000.py \
      --oracle /path/to/grobid-oracle --kit-root /path/to/kit-checkout \
      --java-home /path/to/jdk21 --out migration/evidence/T000

Every external command is run with an argv list (no shell), logged to
<out>/logs/NN-<name>.log, and recorded with exit code, timestamps and the
log's sha256 in <out>/commands.json. Facts are written to three separate
sections: source_derived (bytes of the pinned Git checkout), runtime_observed
(tool output on this machine) and unresolved (not established by T000).
Nothing here edits the oracle checkout.
"""
import argparse, datetime, hashlib, json, os, pathlib, subprocess, sys

PIN = "f313f7010773fe8113cbb0f7a774960450a850d0"
PIN_TREE = "a59943da478e6d53e9a7833631768817a44960cb"


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Runner:
    def __init__(self, out):
        self.out = out
        self.logs = out / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.records = []

    def run(self, name, argv, cwd=None, env=None, timeout=900, ok_codes=(0,)):
        idx = len(self.records)
        log = self.logs / f"{idx:02d}-{name}.log"
        started = now()
        try:
            p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=timeout)
            code, stdout, stderr = p.returncode, p.stdout, p.stderr
        except FileNotFoundError as e:
            code, stdout, stderr = 127, b"", str(e).encode()
        except subprocess.TimeoutExpired as e:
            code, stdout, stderr = 124, e.stdout or b"", (e.stderr or b"") + b"\nTIMEOUT"
        finished = now()
        with open(log, "wb") as f:
            f.write(b"# argv: " + json.dumps(argv).encode() + b"\n")
            f.write(b"# cwd: " + str(cwd or os.getcwd()).encode() + b"\n")
            f.write(f"# exit: {code}\n# --- stdout\n".encode() + stdout + b"\n# --- stderr\n" + stderr)
        rec = {"name": name, "argv": argv, "cwd": str(cwd) if cwd else None, "exit_code": code,
               "expected_exit_codes": list(ok_codes), "started_at": started, "finished_at": finished,
               "log": str(log.relative_to(self.out)), "log_sha256": sha256_file(log)}
        self.records.append(rec)
        return code, stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oracle", required=True)
    ap.add_argument("--kit-root", required=True)
    ap.add_argument("--java-home", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lock-out", help="optional path for migration/contracts/host-environment-lock.json")
    a = ap.parse_args()
    oracle = pathlib.Path(a.oracle).resolve()
    kit = pathlib.Path(a.kit_root).resolve()
    out = pathlib.Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    r = Runner(out)
    failures = []

    lock = json.load(open(kit / "migration/contracts/upstream-lock.json"))
    index = json.load(open(kit / "migration/contracts/upstream-asset-index.json"))

    # ---------- source-derived: oracle checkout identity ----------
    git = ["git", "-C", str(oracle)]
    _, head, _ = r.run("git-head", git + ["rev-parse", "HEAD", "HEAD^{tree}"])
    head_sha, tree_sha = head.split()
    _, porcelain, _ = r.run("git-status", git + ["status", "--porcelain", "--ignored"])
    _, shallow, _ = r.run("git-shallow", git + ["rev-parse", "--is-shallow-repository"])
    _, remotes, _ = r.run("git-remotes", git + ["remote", "-v"])
    if head_sha != PIN: failures.append(f"oracle HEAD {head_sha} != pin {PIN}")
    if tree_sha != PIN_TREE: failures.append(f"oracle tree {tree_sha} != pinned tree {PIN_TREE}")
    if porcelain.strip(): failures.append("oracle checkout not clean (incl. ignored files)")

    # ---------- source-derived: eight critical source hashes ----------
    critical = []
    for rel, expected in lock["source_hashes"].items():
        actual = sha256_file(oracle / rel)
        critical.append({"path": rel, "expected_sha256": expected, "actual_sha256": actual,
                         "match": actual == expected})
        if actual != expected: failures.append(f"critical hash mismatch: {rel}")

    # ---------- source-derived: grobid-home file manifest vs asset index ----------
    _, lstree, _ = r.run("git-ls-tree-grobid-home", git + ["ls-tree", "-r", "-l", "HEAD", "grobid-home"])
    tree_entries = {}
    for line in lstree.splitlines():
        meta, path = line.split("\t", 1)
        mode, typ, obj, size = meta.split()
        tree_entries[path] = {"git_mode": mode, "git_type": typ, "git_object": obj, "size": int(size)}
    paths = sorted(tree_entries)
    # raw working-tree bytes hashed as git blobs (no filters) to detect eol conversion
    _, rawids, _ = r.run("git-hash-object-no-filters", git + ["hash-object", "--no-filters", "--"] + paths, timeout=1800)
    rawids = rawids.split()
    manifest = []
    for path, rawid in zip(paths, rawids):
        e = tree_entries[path]
        fp = oracle / path
        manifest.append({"path": path, **e, "worktree_bytes": fp.stat().st_size,
                         "worktree_sha256": sha256_file(fp),
                         "worktree_matches_blob": rawid == e["git_object"]})
    idx_map = {x["path"]: x for x in index["entries"]}
    missing_in_tree = sorted(set(idx_map) - set(tree_entries))
    extra_in_tree = sorted(set(tree_entries) - set(idx_map))
    obj_mismatch = sorted(p for p in idx_map if p in tree_entries and idx_map[p]["git_object"] != tree_entries[p]["git_object"])
    eol_changed = [m["path"] for m in manifest if not m["worktree_matches_blob"]]
    # The kit's asset index covers models/lexicons/native/detector assets; config,
    # schemas and scripts are outside it (config is covered by critical hashes).
    # Every index entry must exist with an identical blob; extras are reported.
    if missing_in_tree or obj_mismatch:
        failures.append("asset index entries missing or changed in oracle grobid-home tree")
    extra_outside_scope = [p for p in extra_in_tree
                           if not p.startswith(("grobid-home/config/", "grobid-home/schemas/", "grobid-home/scripts/"))]
    if extra_outside_scope:
        failures.append("grobid-home files outside index scope (not config/schemas/scripts): " + ", ".join(extra_outside_scope))
    with open(out / "grobid-home-manifest.json", "w") as f:
        json.dump({"commit": head_sha, "meaning": "bytes of the pinned Git checkout on this host; NOT runtime-loaded asset hashes (T003)",
                   "entries": manifest}, f, indent=1)

    # ---------- runtime-observed: host + toolchains ----------
    jh = a.java_home
    java_env = dict(os.environ, JAVA_HOME=jh, PATH=f"{jh}/bin:" + os.environ.get("PATH", ""))
    env_cmds = [
        ("uname", ["uname", "-a"]), ("sw_vers", ["sw_vers"]),
        ("cpu", ["sysctl", "-n", "machdep.cpu.brand_string", "hw.ncpu", "hw.memsize"]),
        ("java-version", [f"{jh}/bin/java", "-version"]),
        ("javac-version", [f"{jh}/bin/javac", "-version"]),
        ("rustc-version", ["rustc", "-vV"]), ("cargo-version", ["cargo", "-V"]),
        ("python-version", [sys.executable, "-VV"]),
        ("clang-version", ["cc", "--version"]), ("make-version", ["make", "--version"]),
        ("git-version", ["git", "--version"]),
        ("locale", ["locale"]), ("tz", ["date", "+%Z %z"]),
        ("gradlew-version", [str(oracle / "gradlew"), "--version", "--no-daemon"]),
    ]
    tool_out = {}
    for name, argv in env_cmds:
        code, so, se = r.run(name, argv, cwd=oracle if name.startswith("gradlew") else None,
                             env=java_env, timeout=1800)
        tool_out[name] = {"exit_code": code, "output": (so + se).strip()}
        if code != 0: failures.append(f"env command failed: {name} exit {code}")
    # gradlew must not have dirtied tracked files
    _, porcelain2, _ = r.run("git-status-after-gradle", git + ["status", "--porcelain"])
    if porcelain2.strip(): failures.append("tracked files changed after gradlew --version")

    # ---------- native dependency closure ----------
    native = []
    native_dirs = [p for p in paths if p.startswith(("grobid-home/lib/", "grobid-home/pdfalto/")) and not p.startswith("grobid-home/pdfalto/languages/")]
    for p in native_dirs:
        fp = str(oracle / p)
        _, fo, _ = r.run("file-" + p.replace("/", "_")[-60:], ["file", "-b", fp])
        rec = {"path": p, "sha256": sha256_file(fp), "file": fo.strip()}
        if "/mac_arm-64/" in p and "Mach-O" in fo:
            code, so, _ = r.run("otool-" + p.replace("/", "_")[-60:], ["otool", "-L", fp])
            rec["otool_L"] = so.strip().splitlines()[1:]
            code, so, se = r.run("codesign-" + p.replace("/", "_")[-60:], ["codesign", "-dv", fp], ok_codes=(0, 1))
            rec["codesign"] = (so + se).strip()
        if "/mac_arm-64/" in p and "shared library" in fo:
            _, syms, _ = r.run("nm-" + p.replace("/", "_")[-60:], ["nm", "-gU", fp])
            names = [l.split()[-1] for l in syms.splitlines() if l.strip()]
            rec["exported_symbols"] = {"total": len(names),
                                       "jni_Java_prefixed": sum(n.startswith("_Java_") for n in names),
                                       "sample_non_jni": [n for n in names if not n.startswith("_Java_")][:40]}
        native.append(rec)

    # host (non-system) dylib closure of the arm64 natives, followed recursively
    host_libs, queue, seen = [], [], set()
    for n in native:
        for l in n.get("otool_L", []):
            dep = l.strip().split(" (")[0]
            if not dep.startswith(("/usr/lib/", "/System/", "@rpath/")): queue.append((dep, n["path"]))
    while queue:
        dep, parent = queue.pop(0)
        real = os.path.realpath(dep)
        if real in seen: continue
        seen.add(real)
        entry = {"install_name": dep, "needed_by": parent, "resolved": real, "exists": os.path.exists(real)}
        if entry["exists"]:
            entry["sha256"] = sha256_file(real)
            _, so, _ = r.run("otool-host-" + os.path.basename(real), ["otool", "-L", real])
            _, lc, _ = r.run("otool-rpath-" + os.path.basename(real), ["otool", "-l", real])
            lines = lc.splitlines()
            rpaths = [lines[i + 2].split()[1] for i, l in enumerate(lines)
                      if l.strip() == "cmd LC_RPATH" and i + 2 < len(lines)]
            here = os.path.dirname(real)
            for l in so.strip().splitlines()[1:]:
                d = l.strip().split(" (")[0]
                if d.startswith(("/usr/lib/", "/System/")): continue
                if d.startswith("@loader_path/"):
                    queue.append((os.path.normpath(os.path.join(here, d[len("@loader_path/"):])), dep))
                elif d.startswith("@rpath/"):
                    cands = [os.path.normpath(os.path.join(rp.replace("@loader_path", here), d[len("@rpath/"):])) for rp in rpaths]
                    hit = next((c for c in cands if os.path.exists(c)), None)
                    if hit: queue.append((hit, dep))
                    else: failures.append(f"unresolved {d} needed by {dep} (rpaths {rpaths})")
                elif not d.startswith("@"):
                    queue.append((d, dep))
        else:
            failures.append(f"host library missing: {dep}")
        host_libs.append(entry)
    code, so, se = r.run("brew-host-lib-versions", ["brew", "list", "--versions", "fontconfig", "freetype", "libpng", "openjdk@21"], ok_codes=(0, 1))
    host_lib_versions = (so + se).strip().splitlines()

    # host-native pdfalto smoke (runtime-observed; does not process any PDF)
    pdfalto = oracle / "grobid-home/pdfalto/mac_arm-64/pdfalto"
    code, so, se = r.run("pdfalto-version", [str(pdfalto), "-v"], ok_codes=(0, 1, 99))
    pdfalto_obs = {"exit_code": code, "output": (so + se).strip()}

    # ---------- source-derived: model dependency closure from git tree ----------
    models = {}
    for p in paths:
        if p.startswith("grobid-home/models/"):
            parts = p.split("/")
            models.setdefault(parts[2], []).append({"file": "/".join(parts[3:]),
                                                    "sha256": next(m["worktree_sha256"] for m in manifest if m["path"] == p),
                                                    "bytes": tree_entries[p]["size"]})
    families = {}
    for p in paths:
        top = "/".join(p.split("/")[:2])
        families.setdefault(top, {"files": 0, "bytes": 0})
        families[top]["files"] += 1; families[top]["bytes"] += tree_entries[p]["size"]

    report = {
        "schema": "migration/evidence/T000/v1",
        "task_id": "T000",
        "pin": {"commit": PIN, "tree": PIN_TREE, "declared_version": lock["declared_version"]},
        "source_derived": {
            "oracle_checkout": {"path": str(oracle), "head": head_sha, "tree": tree_sha,
                                "clean_including_ignored": not porcelain.strip(),
                                "shallow": shallow.strip() == "true", "remotes": remotes.strip().splitlines()},
            "critical_source_hashes": critical,
            "grobid_home": {"tracked_files": len(paths), "by_top_level": families,
                             "asset_index_entries": len(idx_map), "missing_in_tree": missing_in_tree,
                             "outside_asset_index_scope": extra_in_tree, "git_object_mismatch": obj_mismatch,
                             "worktree_bytes_differ_from_blob_eol": eol_changed,
                             "manifest": "grobid-home-manifest.json",
                             "manifest_sha256": sha256_file(out / "grobid-home-manifest.json")},
            "model_directories": {k: v for k, v in sorted(models.items())},
            "native_binaries": native,
            "gradle_wrapper_distribution": (oracle / "gradle/wrapper/gradle-wrapper.properties").read_text().split("distributionUrl=")[1].split()[0],
        },
        "runtime_observed": {
            "observed_at": now(),
            "toolchains": tool_out,
            "pdfalto_mac_arm64_version_probe": pdfalto_obs,
            "host_dylib_closure_of_arm64_natives": host_libs,
            "host_package_versions": host_lib_versions,
        },
        "unresolved": [
            "Maven/Gradle runtime dependency closure and built jar hashes: T002 (build oracle).",
            "Runtime-loaded model/lexicon/pdfalto data hashes and effective per-getter config: T003.",
            "DeLFT/TensorFlow/Python/embeddings environment: out of S1 scope (CRF-first), deferred.",
            "Container digests: none; oracle is built natively on this host, not from an image.",
            "Corpus revision and item hashes: T004.",
            "Language/sentence detector runtime behavior: not exercised.",
        ],
        "failures": failures,
    }
    with open(out / "t000-report.json", "w") as f:
        json.dump(report, f, indent=1)
    with open(out / "commands.json", "w") as f:
        json.dump(r.records, f, indent=1)
    if a.lock_out:
        def first(name, n=1):
            return tool_out[name]["output"].splitlines()[:n]
        lock_doc = {
            "schema_version": 1,
            "meaning": "Runtime-observed oracle host environment at T000. Later tasks must re-check these before trusting oracle captures; drift requires a new lock, never an in-place edit.",
            "pin_commit": PIN, "pin_tree": PIN_TREE,
            "captured_by": "migration/evidence/T000/capture_t000.py",
            "report": "migration/evidence/T000/t000-report.json",
            "host": {"uname": first("uname")[0], "cpu": first("cpu", 3), "locale_LANG": first("locale")[0], "tz": first("tz")[0]},
            "jdk": {"java_home": jh, "java_version": first("java-version", 3)},
            "gradle": {"wrapper_distribution": report["source_derived"]["gradle_wrapper_distribution"],
                       "version_lines": [l for l in tool_out["gradlew-version"]["output"].splitlines() if l.startswith(("Gradle ", "Launcher JVM", "OS:"))]},
            "rust": first("rustc-version", 1),
            "pdfalto_mac_arm64": {"sha256": next(n["sha256"] for n in native if n["path"] == "grobid-home/pdfalto/mac_arm-64/pdfalto"),
                                   "version_probe": pdfalto_obs["output"]},
            "libwapiti_mac_arm64_sha256": next(n["sha256"] for n in native if n["path"] == "grobid-home/lib/mac_arm-64/libwapiti.dylib"),
            "host_dylib_closure": [{k: h[k] for k in ("install_name", "resolved", "sha256")} for h in host_libs],
            "host_package_versions": host_lib_versions,
        }
        with open(a.lock_out, "w") as f:
            json.dump(lock_doc, f, indent=1)
    bad = [c for c in r.records if c["exit_code"] not in c["expected_exit_codes"]]
    print(json.dumps({"failures": failures, "commands": len(r.records), "unexpected_exit": [c["name"] for c in bad],
                      "grobid_home_files": len(paths), "native": len(native), "model_dirs": len(models)}, indent=1))
    return 1 if failures or bad else 0


if __name__ == "__main__":
    sys.exit(main())
