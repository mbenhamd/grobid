#!/usr/bin/env python3
"""Local, locked migration ledger. Workflow validation is not identity authentication.

Paths beneath --root: migration/plans/tasks.json, migration/state/task-state.json,
migration/state/STOP. Evidence/log/artifact paths resolve within that root.
No commands from evidence are executed and no Git operations are performed.
"""
from __future__ import annotations

import argparse
import fcntl
import fnmatch
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import time


class TaskError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise TaskError(message)


def pairs_unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json(raw):
    def reject_constant(value):
        raise TaskError(f"Invalid JSON number: {value}")
    return json.loads(raw, object_pairs_hook=pairs_unique, parse_constant=reject_constant)


def text_value(value, name):
    require(isinstance(value, str) and bool(value.strip()) and "\x00" not in value,
            f"{name} must be nonempty text without NUL characters")
    return value


def identity(value, name):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value),
            f"{name} must be a stable identifier (letters, digits, dot, underscore, hyphen)")
    return value


def sha(value, name, lengths=(64,)):
    require(isinstance(value, str) and len(value) in lengths
            and re.fullmatch(r"[0-9a-fA-F]+", value) and len(set(value.lower())) > 1,
            f"{name} must be a non-placeholder {'/'.join(map(str, lengths))}-hex SHA")
    return value.lower()


def local_path(root, value):
    text_value(value, "path")
    path = (root / value).resolve()
    require(path.is_relative_to(root), f"Path escapes coordinator root: {value}")
    return path


def file_hash(path):
    require(path.is_file(), f"Required file missing or not regular: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checked_file(root, record, path_key, hash_key):
    require(isinstance(record, dict), "File evidence entry must be an object")
    expected = sha(record.get(hash_key), hash_key)
    path = local_path(root, record.get(path_key))
    require(file_hash(path) == expected, f"Hash mismatch: {path}")
    return path


def string_list(value, name):
    require(isinstance(value, list), f"{name} must be an array")
    for item in value:
        text_value(item, name)
    return value


def execution_evidence(root, data):
    commands, artifacts = data.get("commands"), data.get("artifacts")
    require(isinstance(commands, list) and commands, "commands must be a nonempty array")
    require(isinstance(artifacts, list) and artifacts, "artifacts must be a nonempty array")
    for command in commands:
        require(isinstance(command, dict), "Command entry must be an object")
        argv = command.get("argv")
        require(isinstance(argv, list) and argv and all(isinstance(x, str) for x in argv)
                and argv[0].strip(), "Command argv must be a nonempty string array")
        require(type(command.get("exit_code")) is int and command["exit_code"] == 0,
                "Every evidence command must have integer exit_code 0")
        checked_file(root, command, "log", "log_sha256")
    for artifact in artifacts:
        checked_file(root, artifact, "path", "sha256")


def case_counts(data):
    counts = data.get("case_counts")
    require(isinstance(counts, dict), "case_counts must be an object")
    for key in ("executed", "failed", "skipped"):
        require(type(counts.get(key)) is int and counts[key] >= 0, f"Invalid case_counts.{key}")
    require(counts["executed"] > 0 and counts["failed"] == 0,
            "Evidence must execute at least one case and have zero failed cases")
    if counts["skipped"]:
        require(string_list(data.get("skip_justifications"), "skip_justifications"),
                "Skipped cases require nonempty skip_justifications")


def packet(root, filename):
    path = local_path(root, filename)
    raw = path.read_bytes()
    data = parse_json(raw)
    require(isinstance(data, dict), "Evidence/review must be a JSON object")
    return data, {"path": path.relative_to(root).as_posix(),
                  "sha256": hashlib.sha256(raw).hexdigest()}


def validate_submission(root, task, data, worker):
    require(data.get("task_id") == task["id"], "Evidence task_id does not match task")
    require(data.get("worker") == worker, "Evidence worker does not match lease owner")
    sha(data.get("base_commit"), "base_commit", (40, 64))
    result = sha(data.get("result_commit"), "result_commit", (40, 64))
    execution_evidence(root, data)
    case_counts(data)
    string_list(data.get("limitations"), "limitations")
    string_list(data.get("source_refs"), "source_refs")
    for changed in string_list(data.get("changed_paths"), "changed_paths"):
        path = PurePosixPath(changed)
        require(path.parts and not path.is_absolute() and ".." not in path.parts and "\\" not in changed,
                f"changed_paths must be repository-relative: {changed}")
        require(any(fnmatch.fnmatchcase(changed, owned) or changed.startswith(owned.rstrip("/") + "/")
                    for owned in task.get("owned_paths", [])), f"Changed path outside task ownership: {changed}")
    return result


def load_ledger(root):
    plan = parse_json(local_path(root, "migration/plans/tasks.json").read_bytes())
    state = parse_json(local_path(root, "migration/state/task-state.json").read_bytes())
    require(isinstance(plan, dict) and type(plan.get("schema_version")) is int and plan["schema_version"] == 1
            and isinstance(plan.get("tasks"), list) and plan["tasks"], "Invalid task plan schema")
    tasks = {}
    for task in plan["tasks"]:
        require(isinstance(task, dict), "Task definition must be an object")
        key = identity(task.get("id"), "task id")
        require(key not in tasks, f"Duplicate task id: {key}")
        text_value(task.get("title"), "task title")
        string_list(task.get("depends_on"), "depends_on")
        string_list(task.get("owned_paths"), "owned_paths")
        tasks[key] = task
    visited, active = set(), set()
    def visit(key):
        require(key in tasks, f"Unknown dependency: {key}")
        require(key not in active, f"Dependency cycle includes {key}")
        if key not in visited:
            active.add(key)
            for dependency in tasks[key]["depends_on"]:
                visit(dependency)
            active.remove(key)
            visited.add(key)
    for key in tasks:
        visit(key)
    require(isinstance(state, dict) and type(state.get("schema_version")) is int and state["schema_version"] == 1
            and isinstance(state.get("tasks"), dict) and set(state["tasks"]) == set(tasks)
            and isinstance(state.get("events"), list) and all(isinstance(e, dict) for e in state["events"]),
            "Invalid state schema or plan/state task mismatch")
    for record in state["tasks"].values():
        require(isinstance(record, dict) and record.get("status") in
                ("pending", "running", "submitted", "done", "blocked", "failed"), "Invalid task status")
        require(type(record.get("attempts")) is int and record["attempts"] >= 0, "Invalid attempts count")
        if record["status"] in ("running", "submitted"):
            identity(record.get("worker"), "lease worker")
            expiry = record.get("lease_expires_at")
            require(type(expiry) in (int, float) and math.isfinite(expiry), "Invalid lease expiry")
    return tasks, state


def atomic_save(path, state):
    fd, temporary = tempfile.mkstemp(prefix=".task-state-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(state, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def operate(args):
    root = Path(args.root).resolve()
    folder = local_path(root, "migration/state")
    require(folder.is_dir(), "Missing migration/state directory; install the kit first")
    with local_path(root, "migration/state/.task-state.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        stop = folder / "STOP"
        stopped = stop.exists() or stop.is_symlink()
        mutating = args.action not in ("list", "next")
        require(not (mutating and stopped), "STOP exists; checkpoint and stop")
        tasks, ledger = load_ledger(root)
        states, now = ledger["tasks"], time.time()
        def ready(key):
            return all(states[d]["status"] == "done" for d in tasks[key]["depends_on"])
        def view(key):
            record = states[key]
            return {**tasks[key], **record, "dependency_ready": ready(key),
                    "stale": record["status"] in ("running", "submitted")
                    and now >= record["lease_expires_at"]}
        if args.action == "list":
            return {"ok": True, "stopped": stopped, "tasks": [view(k) for k in tasks]}
        if args.action == "next":
            keys = [k for k in tasks if states[k]["status"] == "pending" and ready(k)]
            return {"ok": True, "stopped": stopped, "task": view(keys[0]) if keys and not stopped else None}
        require(args.task in tasks, f"Unknown task: {args.task}")
        key, record = args.task, states[args.task]
        before = record["status"]
        worker = identity(args.worker, "worker") if hasattr(args, "worker") else None
        event = {"at": now, "action": args.action, "task_id": key, "worker": worker, "before": before}
        if hasattr(args, "reason"):
            event["reason"] = text_value(args.reason, "reason")
        if args.action in ("claim", "heartbeat", "reclaim"):
            require(1 <= args.lease_seconds <= 86400, "lease-seconds must be between 1 and 86400")
        if args.action in ("heartbeat", "block", "submit"):
            require(before in ("running", "submitted"), "Task must have an active running/submitted lease")
            require(record["worker"] == worker, "Worker does not own task lease")
            require(now < record["lease_expires_at"], "Lease expired; inspect owner and explicitly reclaim")
        if args.action in ("claim", "reclaim"):
            require(ready(key), "Dependencies are not done")
            if args.action == "claim":
                require(before == "pending", "Only pending tasks can be claimed; unblock/reclaim explicitly")
            else:
                require(before in ("running", "submitted") and now >= record["lease_expires_at"],
                        "Only expired running/submitted leases can be reclaimed")
                event["previous_submission"] = record.pop("submission", None)
            record.update(status="running", worker=worker, attempts=record["attempts"] + 1, claimed_at=now)
        if args.action in ("claim", "reclaim", "heartbeat"):
            record.update(heartbeat_at=now, lease_expires_at=now + args.lease_seconds)
        elif args.action == "block":
            event["previous_submission"] = record.pop("submission", None)
            record.update(status="blocked", blocked_reason=args.reason)
            record.pop("lease_expires_at", None)
        elif args.action == "unblock":
            require(before in ("blocked", "failed"), "Only blocked/failed tasks can be unblocked")
            require(record.get("worker", worker) == worker, "Only the last owner may unblock this task")
            record.update(status="pending", resolution=args.reason)
        elif args.action == "submit":
            require(before == "running", "Submitted evidence is immutable; block/reclaim before resubmitting")
            data, evidence = packet(root, args.evidence)
            result = validate_submission(root, tasks[key], data, worker)
            evidence.update(result_commit=result, worker=worker, submitted_at=now)
            record.update(status="submitted", submission=evidence)
            event["submission"] = evidence.copy()
        elif args.action == "approve":
            require(before == "submitted", "Only submitted tasks can be approved")
            submission = record.get("submission")
            require(isinstance(submission, dict), "Missing submission record")
            data, snapshot = packet(root, submission.get("path"))
            require(snapshot["sha256"] == sha(submission.get("sha256"), "submission sha256"),
                    "Submitted evidence file hash changed")
            result = validate_submission(root, tasks[key], data, record["worker"])
            require(result == submission.get("result_commit"), "Submitted result commit changed")
            review, evidence = packet(root, args.review_file)
            reviewer = identity(review.get("reviewer"), "reviewer")
            require(review.get("task_id") == key and review.get("decision") == "approve", "Invalid approval task/decision")
            require(reviewer != record["worker"], "Independent reviewer required; self-review is forbidden")
            require(sha(review.get("result_commit"), "review result_commit", (40, 64)) == result,
                    "Review must target the submitted result commit")
            execution_evidence(root, review)
            if "case_counts" in review:
                case_counts(review)
            evidence.update(reviewer=reviewer, result_commit=result)
            record.update(status="done", review=evidence, completed_at=now)
            record.pop("lease_expires_at", None)
            event.update(worker=reviewer, review=evidence.copy())
        record["updated_at"] = now
        event["after"] = record["status"]
        ledger["events"].append(event)
        require(not (stop.exists() or stop.is_symlink()), "STOP appeared; ledger mutation cancelled")
        atomic_save(folder / "task-state.json", ledger)
        return {"ok": True, "action": args.action, "task": view(key)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Coordinator repository checkout (not worker worktree)")
    commands = parser.add_subparsers(dest="action", required=True)
    for action in ("list", "next", "claim", "heartbeat", "block", "unblock", "submit", "approve", "reclaim"):
        command = commands.add_parser(action)
        if action not in ("list", "next"):
            command.add_argument("--task", required=True)
        if action not in ("list", "next", "approve"):
            command.add_argument("--worker", required=True)
        if action in ("claim", "heartbeat", "reclaim"):
            command.add_argument("--lease-seconds", type=int, default=1800)
        if action in ("block", "unblock", "reclaim"):
            command.add_argument("--reason", required=True)
        if action == "submit":
            command.add_argument("--evidence", required=True)
        if action == "approve":
            command.add_argument("--review-file", required=True)
    try:
        result = operate(parser.parse_args(argv))
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (TaskError, OSError, ValueError, TypeError, RecursionError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
