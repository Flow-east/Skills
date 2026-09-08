#!/usr/bin/env python3
"""Local, evidence-aware memory for prompt-assistant. Python 3.9+, stdlib only."""
import argparse
import contextlib
import datetime as dt
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import uuid

SCHEMA = 1
KINDS = {"case", "preference", "project", "method", "learning"}
SOURCES = {"user_statement", "user_report", "observation", "inference", "curated", "assistant_explanation"}
STATES = {"case": {"draft", "accepted", "effective", "mixed", "failed"},
          "preference": {"active", "tentative"}, "project": {"active", "tentative"},
          "method": {"candidate", "validated", "review", "revoked"},
          "learning": {"introduced", "understood", "applied"}}
SIGNALS = {"prompt_accepted": "accepted", "result_good": "effective",
           "result_mixed": "mixed", "result_bad": "failed"}
ENTRY_FIELDS = {"id", "kind", "key", "title", "body", "scope", "source", "data", "state", "revision", "created_at", "updated_at"}


class Problem(Exception):
    pass


def need(condition, message):
    if not condition:
        raise Problem(message)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def nonempty(value, name):
    need(isinstance(value, str) and bool(value.strip()), name + " must be a nonempty string")
    return value


def only(value, allowed, required=()):
    need(isinstance(value, dict), "expected a JSON object")
    need(set(value) <= set(allowed), "unknown fields: " + ", ".join(sorted(set(value) - set(allowed))))
    need(set(required) <= set(value), "missing fields: " + ", ".join(sorted(set(required) - set(value))))


def scope_of(value):
    only(value, {"project", "scenario", "tool"})
    return {key: nonempty(value.get(key, "*"), key) for key in ("project", "scenario", "tool")}


def read_json(path):
    if path == "-":
        return json.load(sys.stdin)
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def data_root(args):
    if args.data_dir:
        root = Path(args.data_dir).expanduser()
    elif os.environ.get("PROMPT_ASSISTANT_HOME"):
        root = Path(os.environ["PROMPT_ASSISTANT_HOME"]).expanduser()
    elif os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "prompt-assistant"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "prompt-assistant"
    root = root.resolve()
    skill = Path(__file__).resolve().parents[1]
    need(root != skill and skill not in root.parents, "personal data must be outside the installed Skill directory")
    return root


def connect(root, create=False):
    path = root / "memory.sqlite3"
    if not path.exists() and not create:
        raise Problem("memory is not initialized; run init, or continue without persistent memory")
    if create:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(str(path), timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA secure_delete=ON")
    version = db.execute("PRAGMA user_version").fetchone()[0]
    need(version in (0, SCHEMA), "unsupported database schema; use a compatible Skill version")
    if version == 0:
        need(create, "database has no recognized schema")
        db.executescript("""
            BEGIN IMMEDIATE;
            CREATE TABLE IF NOT EXISTS entries(id TEXT PRIMARY KEY, kind TEXT NOT NULL, key TEXT NOT NULL,
                scope TEXT NOT NULL, doc TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS entry_lookup ON entries(kind,key,scope);
            CREATE TABLE IF NOT EXISTS history(entry_id TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
                revision INTEGER NOT NULL, doc TEXT NOT NULL, PRIMARY KEY(entry_id,revision));
            CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, entry_id TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
                kind TEXT NOT NULL, doc TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS links(source_id TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
                derived_id TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
                PRIMARY KEY(source_id,derived_id));
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            INSERT OR IGNORE INTO settings VALUES('memory','on'),('teaching','on');
            PRAGMA user_version=1;
            COMMIT;
        """)
        db.commit()
    if create and os.name != "nt":
        path.chmod(0o600)
    return db


@contextlib.contextmanager
def transaction(db):
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise


def settings(db):
    return dict(db.execute("SELECT key,value FROM settings"))


def write_enabled(db):
    need(settings(db)["memory"] == "on", "memory is off; no learning data was written")


def get(db, entry_id):
    row = db.execute("SELECT doc FROM entries WHERE id=?", (entry_id,)).fetchone()
    need(row is not None, "entry not found")
    return json.loads(row[0])


def all_entries(db):
    return [json.loads(row[0]) for row in db.execute("SELECT doc FROM entries")]


def save(db, entry):
    doc = encode(entry)
    db.execute("INSERT INTO entries(id,kind,key,scope,doc) VALUES(?,?,?,?,?)",
               (entry["id"], entry["kind"], entry["key"], encode(entry["scope"]), doc))
    # UPDATE, not REPLACE, is used for revisions below: REPLACE would cascade-delete history.
    db.execute("INSERT INTO history VALUES(?,?,?)", (entry["id"], entry["revision"], doc))


def revise(db, entry):
    entry["revision"] += 1
    entry["updated_at"] = now()
    doc = encode(entry)
    db.execute("UPDATE entries SET doc=?,scope=? WHERE id=?", (doc, encode(entry["scope"]), entry["id"]))
    db.execute("INSERT INTO history VALUES(?,?,?)", (entry["id"], entry["revision"], doc))


def event(db, entry_id, kind, data):
    value = {"id": uuid.uuid4().hex, "entry_id": entry_id, "kind": kind, "at": now(), "data": data}
    db.execute("INSERT INTO events VALUES(?,?,?,?)", (value["id"], entry_id, kind, encode(value)))


def relate(db, source_id, derived_id):
    get(db, source_id)
    need(source_id != derived_id, "an entry cannot derive from itself")
    # A method may help a later case which then supplies new method evidence.
    # Such cycles are valid; descendants uses a visited set when removing/reviewing.
    db.execute("INSERT OR IGNORE INTO links VALUES(?,?)", (source_id, derived_id))


def descendants(db, entry_id):
    found, todo = {entry_id}, [entry_id]
    while todo:
        for row in db.execute("SELECT derived_id FROM links WHERE source_id=?", (todo.pop(),)):
            if row[0] not in found:
                found.add(row[0])
                todo.append(row[0])
    return found


def validate_content(kind, data, source):
    need(isinstance(data, dict), "data must be an object")
    if kind in {"preference", "project"}:
        need(source in {"user_statement", "user_report", "observation", "inference"}, "personal facts require user/observed evidence or an explicit inference")
        nonempty(data.get("evidence"), "data.evidence")
    if kind == "case":
        for key in ("task_id", "request", "prompt"):
            nonempty(data.get(key), "data." + key)
        need(not ({"last_feedback", "validation"} & set(data)), "feedback must use its dedicated command")
    if kind == "method":
        for key in ("rationale", "when_not"):
            nonempty(data.get(key), "data." + key)
        need("validation" not in data, "method validation must use validate")
    if kind == "learning":
        need(data.get("stage") in STATES["learning"], "learning requires stage introduced, understood, or applied")
        nonempty(data.get("evidence"), "data.evidence")
        if data["stage"] != "introduced":
            need(source in {"user_statement", "user_report", "observation"}, "understanding/application requires user or observed evidence")


def record(db, payload):
    only(payload, {"kind", "key", "title", "body", "scope", "source", "data", "related_ids"},
         {"kind", "key", "title", "body", "scope", "source", "data"})
    kind, source = payload["kind"], payload["source"]
    need(isinstance(kind, str) and kind in KINDS, "unknown entry kind")
    need(isinstance(source, str) and source in SOURCES, "unknown source")
    for key in ("key", "title", "body"):
        nonempty(payload[key], key)
    scope = scope_of(payload["scope"])
    data = payload["data"]
    validate_content(kind, data, source)
    related = payload.get("related_ids", [])
    need(isinstance(related, list) and all(isinstance(x, str) for x in related), "related_ids must be a list of IDs")
    if kind == "case" and data.get("parent_id"):
        parent = get(db, data["parent_id"])
        need(parent["kind"] == "case" and parent["data"]["task_id"] == data["task_id"], "a case revision must share its parent's task_id")
        related = related + [parent["id"]]
    for linked_id in related:
        get(db, linked_id)
    state = ("draft" if kind == "case" else "candidate" if kind == "method" else
             data["stage"] if kind == "learning" else "tentative" if source == "inference" else "active")
    entry = {key: payload[key] for key in ("kind", "key", "title", "body", "source", "data")}
    entry.update(scope=scope, state=state)
    old = None
    if kind != "case":
        row = db.execute("SELECT doc FROM entries WHERE kind=? AND key=? AND scope=?",
                         (kind, payload["key"], encode(scope))).fetchone()
        old = json.loads(row[0]) if row else None
    if old:
        need(not (source == "inference" and old["source"] != "inference"), "an inference cannot overwrite an explicit record; use a separate tentative key")
        entry.update(id=old["id"], revision=old["revision"], created_at=old["created_at"])
        revise(db, entry)
    else:
        entry.update(id=uuid.uuid4().hex, revision=1, created_at=now(), updated_at=now())
        save(db, entry)
    for linked_id in related:
        relate(db, linked_id, entry["id"])
    return brief(entry)


def brief(entry):
    return {key: entry[key] for key in ("id", "kind", "title", "state", "scope", "revision")}


def feedback(db, entry_id, value):
    only(value, {"signal", "source", "evidence", "output"}, {"signal", "source", "evidence"})
    need(isinstance(value["signal"], str) and value["signal"] in SIGNALS, "unknown feedback signal")
    need(value["source"] in {"user_report", "observation"}, "feedback source must be user_report or observation")
    nonempty(value["evidence"], "evidence")
    entry = get(db, entry_id)
    need(entry["kind"] == "case", "feedback requires a case ID")
    signal = value["signal"]
    event(db, entry_id, "feedback", value)
    if signal != "prompt_accepted" or entry["state"] in {"draft", "accepted"}:
        entry["state"] = SIGNALS[signal]
        entry["data"]["last_feedback"] = dict(value, at=now())
        revise(db, entry)
    invalidated = []
    if signal in {"result_mixed", "result_bad"}:
        for derived_id in descendants(db, entry_id) - {entry_id}:
            method = get(db, derived_id)
            if method["kind"] == "method" and method["state"] == "validated":
                method["state"] = "review"
                revise(db, method)
                event(db, derived_id, "counterexample", {"case_id": entry_id})
                invalidated.append(derived_id)
    return {"entry": brief(entry), "methods_needing_review": invalidated}


def matches(scope, current):
    return all(value == "*" or (current.get(key) not in (None, "", "*") and current[key] == value)
               for key, value in scope.items())


def validate_method(db, entry_id, value):
    only(value, {"trials", "conclusion", "counterexamples"}, {"trials", "conclusion"})
    nonempty(value["conclusion"], "conclusion")
    method = get(db, entry_id)
    need(method["kind"] == "method", "validate requires a method ID")
    need(isinstance(value["trials"], list) and len(value["trials"]) >= 2, "at least two independent task trials are required")
    tasks, support = set(), set()
    for trial in value["trials"]:
        only(trial, {"case_id", "verdict", "source", "baseline_result", "candidate_result", "controls", "evidence"},
             {"case_id", "verdict", "source", "baseline_result", "candidate_result", "controls", "evidence"})
        need(trial["verdict"] == "helpful", "all promotion trials must be helpful; keep a mixed method as candidate/review")
        need(trial["source"] in {"user_report", "observation"}, "trial evidence must be reported or observed")
        for key in ("baseline_result", "candidate_result", "controls", "evidence"):
            nonempty(trial[key], key)
        case = get(db, trial["case_id"])
        need(case["kind"] == "case" and case["state"] == "effective", "each trial must reference an effective case")
        need(matches(method["scope"], case["scope"]), "trial is outside this method's scope")
        tasks.add(case["data"]["task_id"])
        support.add(case["id"])
    need(len(tasks) >= 2, "versions of one task do not count as independent trials")
    resolutions = value.get("counterexamples", [])
    need(isinstance(resolutions, list), "counterexamples must be a list")
    resolved = set()
    for resolution in resolutions:
        only(resolution, {"case_id", "resolution", "source", "evidence"}, {"case_id", "resolution", "source", "evidence"})
        case = get(db, resolution["case_id"])
        need(case["kind"] == "case", "counterexample must reference a case")
        need(resolution["source"] in {"user_report", "observation"}, "counterexample resolution requires reported or observed evidence")
        nonempty(resolution["resolution"], "resolution")
        nonempty(resolution["evidence"], "evidence")
        resolved.add(case["id"])
    neighbors = {row[0] for row in db.execute("SELECT source_id FROM links WHERE derived_id=? UNION SELECT derived_id FROM links WHERE source_id=?", (entry_id, entry_id))}
    negatives = {i for i in neighbors if get(db, i)["kind"] == "case" and get(db, i)["state"] in {"mixed", "failed"}}
    need(negatives <= resolved, "linked counterexamples need explicit evidence-based resolution before revalidation")
    method["state"] = "validated"
    method["data"]["validation"] = dict(value, at=now())
    revise(db, method)
    for case_id in support:
        relate(db, case_id, entry_id)
    for case_id in resolved:
        relate(db, case_id, entry_id)
    event(db, entry_id, "validation", value)
    return brief(method)


def tokens(text):
    value = text.lower()
    result = set(re.findall(r"[a-z0-9_]+", value))
    for run in re.findall(r"[\u3400-\u9fff]+", value):
        result.update(run[i:i+2] for i in range(max(1, len(run)-1)))
    return result


def retrieve(db, args):
    if settings(db)["memory"] == "off":
        return {"settings": settings(db), "entries": [], "reason": "memory_off"}
    current = {key: getattr(args, key) for key in ("project", "scenario", "tool")}
    query = tokens(args.query)
    eligible = []
    for entry in all_entries(db):
        if not matches(entry["scope"], current):
            continue
        if entry["state"] in {"tentative", "candidate", "review", "revoked", "draft"}:
            continue
        searchable = " ".join([entry["title"], entry["body"], entry["key"], encode(entry["scope"])])
        overlap = len(query & tokens(searchable))
        if query and entry["kind"] in {"case", "method", "learning"} and not overlap:
            continue
        # Resolve same-key preferences by project > scenario > tool > recency.
        specificity = tuple(int(entry["scope"][k] != "*") for k in ("project", "scenario", "tool"))
        eligible.append((entry, specificity, overlap))
    eligible.sort(key=lambda item: (item[1], item[0]["updated_at"]), reverse=True)
    seen, selected = set(), []
    for entry, specificity, overlap in eligible:
        identity = (entry["kind"], entry["key"])
        if entry["kind"] in {"preference", "project", "learning"}:
            if identity in seen:
                continue
            seen.add(identity)
        selected.append((entry, specificity, overlap))
    priority = {"preference": 5, "project": 4, "method": 3, "case": 2, "learning": 1}
    selected.sort(key=lambda item: (priority[item[0]["kind"]], item[2], item[1], item[0]["updated_at"]), reverse=True)
    entries, used, omitted = [], 0, 0
    roles = {"accepted": "accepted_prompt_only", "effective": "example", "mixed": "pitfall", "failed": "pitfall"}
    for entry, _, _ in selected:
        summary = brief(entry)
        summary.update(key=entry["key"], body=entry["body"], source=entry["source"], updated_at=entry["updated_at"],
                       use_as=roles.get(entry["state"], entry["kind"]))
        if entry["kind"] == "case":
            fb = entry["data"].get("last_feedback")
            if fb:
                summary["feedback"] = {k: fb[k] for k in ("signal", "source", "evidence")}
        if entry["kind"] == "method":
            summary["when_not"] = entry["data"]["when_not"]
        size = len(encode(summary))
        if used + size > args.budget or len(entries) >= args.limit:
            omitted += 1
            continue
        entries.append(summary)
        used += size
    return {"settings": settings(db), "entries": entries, "summary_characters": used, "omitted": omitted,
            "note": "Scope-filtered lexical recall, not semantic search. Use get for original prompts and full evidence; broaden the query if needed."}


def export_data(db):
    return {"schema_version": SCHEMA, "exported_at": now(), "settings": settings(db),
            "entries": all_entries(db),
            "history": [json.loads(row[0]) for row in db.execute("SELECT doc FROM history ORDER BY entry_id,revision")],
            "events": [json.loads(row[0]) for row in db.execute("SELECT doc FROM events ORDER BY id")],
            "links": [list(row) for row in db.execute("SELECT source_id,derived_id FROM links ORDER BY source_id,derived_id")]}


def validate_snapshot(entry):
    only(entry, ENTRY_FIELDS, ENTRY_FIELDS)
    need(isinstance(entry["kind"], str) and entry["kind"] in KINDS, "invalid entry kind")
    need(isinstance(entry["state"], str) and entry["state"] in STATES[entry["kind"]], "invalid entry state")
    need(isinstance(entry["source"], str) and entry["source"] in SOURCES, "invalid entry source")
    need(type(entry["revision"]) is int and entry["revision"] > 0, "invalid revision")
    for key in ("id", "key", "title", "body", "created_at", "updated_at"):
        nonempty(entry[key], key)
    need(scope_of(entry["scope"]) == entry["scope"], "export scope must be complete")
    need(isinstance(entry["data"], dict), "invalid entry data")
    # Dedicated commands normally populate these evidence fields; validate basic shape on import.
    clean = {k: v for k, v in entry["data"].items() if k not in {"last_feedback", "validation"}}
    validate_content(entry["kind"], clean, entry["source"])
    if entry["kind"] == "case" and entry["state"] != "draft":
        fb = entry["data"].get("last_feedback", {})
        need(fb.get("signal") in SIGNALS and fb.get("source") in {"user_report", "observation"}, "case is missing feedback evidence")
        nonempty(fb.get("evidence"), "feedback.evidence")
        need(SIGNALS[fb["signal"]] == entry["state"], "case state and feedback disagree")


def import_data(db, value):
    only(value, {"schema_version", "exported_at", "settings", "entries", "history", "events", "links"},
         {"schema_version", "settings", "entries", "history", "events", "links"})
    need(value["schema_version"] == SCHEMA, "unsupported export schema")
    need(not all_entries(db), "import requires an empty database; choose a new data directory")
    only(value["settings"], {"memory", "teaching"}, {"memory", "teaching"})
    need(all(v in ("on", "off") for v in value["settings"].values()), "invalid settings")
    for key in ("entries", "history", "events", "links"):
        need(isinstance(value[key], list), key + " must be a list")
    by_id = {}
    for entry in value["entries"]:
        validate_snapshot(entry)
        need(entry["id"] not in by_id, "duplicate entry ID")
        by_id[entry["id"]] = entry
        db.execute("INSERT INTO entries VALUES(?,?,?,?,?)", (entry["id"], entry["kind"], entry["key"], encode(entry["scope"]), encode(entry)))
    unique_keys = set()
    for entry in by_id.values():
        if entry["kind"] != "case":
            key = (entry["kind"], entry["key"], encode(entry["scope"]))
            need(key not in unique_keys, "duplicate semantic key and scope")
            unique_keys.add(key)
    versions = {}
    for snapshot in value["history"]:
        validate_snapshot(snapshot)
        parent = by_id.get(snapshot["id"])
        need(parent is not None and snapshot["kind"] == parent["kind"] and snapshot["key"] == parent["key"], "history identity mismatch")
        need(snapshot["revision"] <= parent["revision"], "history is newer than entry")
        versions.setdefault(snapshot["id"], {})[snapshot["revision"]] = snapshot
        db.execute("INSERT INTO history VALUES(?,?,?)", (snapshot["id"], snapshot["revision"], encode(snapshot)))
    for entry in by_id.values():
        history = versions.get(entry["id"], {})
        need(set(history) == set(range(1, entry["revision"] + 1)), "history has missing revisions")
        need(history[entry["revision"]] == entry, "latest history snapshot differs from entry")
    for ev in value["events"]:
        only(ev, {"id", "entry_id", "kind", "at", "data"}, {"id", "entry_id", "kind", "at", "data"})
        need(ev["entry_id"] in by_id and isinstance(ev["data"], dict), "invalid event reference/data")
        for key in ("id", "kind", "at"):
            nonempty(ev[key], key)
        db.execute("INSERT INTO events VALUES(?,?,?,?)", (ev["id"], ev["entry_id"], ev["kind"], encode(ev)))
    for pair in value["links"]:
        need(isinstance(pair, list) and len(pair) == 2 and all(isinstance(x, str) for x in pair), "invalid provenance link")
        get(db, pair[1])
        relate(db, pair[0], pair[1])
    # Imported success labels retain their stated provenance, never become new local observations.
    # Procedures need revalidation in their new environment; revoked methods stay revoked.
    reset = []
    for entry in by_id.values():
        if entry["kind"] == "method" and entry["state"] != "revoked":
            entry["state"] = "candidate"
            entry["data"].pop("validation", None)
            revise(db, entry)
            event(db, entry["id"], "import_revalidation", {"reason": "new environment"})
            reset.append(entry["id"])
    for key, val in value["settings"].items():
        db.execute("UPDATE settings SET value=? WHERE key=?", (val, key))
    return {"imported": len(by_id), "methods_requiring_validation": reset}


def write_export(path, value):
    path = Path(path).expanduser()
    need(not path.exists(), "export destination already exists; choose a new filename")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".prompt-assistant-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Hard link provides atomic, no-clobber publication on local filesystems.
        os.link(temp, str(path))
    finally:
        os.unlink(temp)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--data-dir", help="override private storage directory (outside Skill)")
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("status", "init", "review"):
        commands.add_parser(name)
    cfg = commands.add_parser("config")
    cfg.add_argument("--memory", choices=("on", "off"))
    cfg.add_argument("--teaching", choices=("on", "off"))
    rec = commands.add_parser("record")
    rec.add_argument("--input", required=True, help="JSON filename or - for stdin")
    for name in ("feedback", "validate", "rescope"):
        sub = commands.add_parser(name)
        sub.add_argument("id")
        sub.add_argument("--input", required=True)
    for name in ("get", "history", "impact", "forget", "revoke", "rollback"):
        sub = commands.add_parser(name)
        sub.add_argument("id")
        if name == "revoke":
            sub.add_argument("--reason", required=True)
        if name == "rollback":
            sub.add_argument("--revision", type=int, required=True)
    sub = commands.add_parser("list")
    sub.add_argument("--kind", choices=sorted(KINDS))
    sub.add_argument("--state")
    sub.add_argument("--limit", type=int, default=50)
    sub = commands.add_parser("context")
    sub.add_argument("--query", default="")
    for name in ("project", "scenario", "tool"):
        sub.add_argument("--" + name)
    sub.add_argument("--budget", type=int, default=9000, help="maximum characters in returned entry summaries")
    sub.add_argument("--limit", type=int, default=12)
    sub = commands.add_parser("export")
    sub.add_argument("--output", required=True)
    sub = commands.add_parser("import")
    sub.add_argument("--input", required=True)
    return result


def execute(db, args):
    cmd = args.command
    if cmd in {"record", "feedback", "validate", "revoke", "rollback", "rescope"}:
        write_enabled(db)
    if cmd in {"status", "init"}:
        return {"initialized": True, "schema_version": SCHEMA, "settings": settings(db), "entries": db.execute("SELECT count(*) FROM entries").fetchone()[0]}
    if cmd == "config":
        for key in ("memory", "teaching"):
            if getattr(args, key) is not None:
                db.execute("UPDATE settings SET value=? WHERE key=?", (getattr(args, key), key))
        return {"settings": settings(db)}
    if cmd == "record":
        values = read_json(args.input)
        if not isinstance(values, list):
            values = [values]
        need(0 < len(values) <= 100, "record requires 1–100 entries")
        return {"entries": [record(db, value) for value in values]}
    if cmd == "feedback":
        return feedback(db, args.id, read_json(args.input))
    if cmd == "validate":
        return validate_method(db, args.id, read_json(args.input))
    if cmd == "rescope":
        entry = get(db, args.id)
        need(entry["kind"] != "case", "preserve the original case scope; record a new case for a new task")
        scope = scope_of(read_json(args.input))
        conflict = db.execute("SELECT id FROM entries WHERE kind=? AND key=? AND scope=? AND id<>?",
                              (entry["kind"], entry["key"], encode(scope), args.id)).fetchone()
        need(conflict is None, "this key already exists in the target scope; reconcile the two records first")
        entry["scope"] = scope
        if entry["kind"] == "method":
            entry["state"] = "candidate"
            entry["data"].pop("validation", None)
        revise(db, entry)
        event(db, args.id, "rescope", {"scope": scope})
        return brief(entry)
    if cmd == "get":
        entry = get(db, args.id)
        return {"entry": entry, "events": [json.loads(r[0]) for r in db.execute("SELECT doc FROM events WHERE entry_id=? ORDER BY rowid", (args.id,))],
                "derived_from": [r[0] for r in db.execute("SELECT source_id FROM links WHERE derived_id=?", (args.id,))]}
    if cmd == "history":
        get(db, args.id)
        return {"history": [json.loads(r[0]) for r in db.execute("SELECT doc FROM history WHERE entry_id=? ORDER BY revision", (args.id,))]}
    if cmd in {"list", "review"}:
        entries = all_entries(db)
        if cmd == "review":
            entries = [e for e in entries if e["state"] in {"tentative", "candidate", "review", "mixed", "failed"}]
        else:
            entries = [e for e in entries if (not args.kind or e["kind"] == args.kind) and (not args.state or e["state"] == args.state)]
            need(args.limit > 0, "limit must be positive")
        entries.sort(key=lambda e: e["updated_at"], reverse=True)
        limit = getattr(args, "limit", 50)
        return {"entries": [brief(e) for e in entries[:limit]], "total": len(entries)}
    if cmd == "context":
        need(args.budget >= 0 and args.limit > 0, "budget must be nonnegative and limit positive")
        return retrieve(db, args)
    if cmd in {"impact", "forget"}:
        get(db, args.id)
        ids = sorted(descendants(db, args.id))
        if cmd == "impact":
            return {"entries_to_forget": [brief(get(db, i)) for i in ids]}
        for entry_id in ids:
            db.execute("DELETE FROM entries WHERE id=?", (entry_id,))
        return {"forgotten_ids": ids, "note": "Removed linked local records, revisions, and events. External artifacts and prior exports/backups are not modified."}
    if cmd == "revoke":
        entry = get(db, args.id)
        need(entry["kind"] == "method", "revoke requires a method ID")
        nonempty(args.reason, "reason")
        entry["state"] = "revoked"
        revise(db, entry)
        event(db, args.id, "revoked", {"reason": args.reason})
        return brief(entry)
    if cmd == "rollback":
        entry = get(db, args.id)
        need(entry["kind"] != "case", "case prompts are separate versions; select the older case instead")
        row = db.execute("SELECT doc FROM history WHERE entry_id=? AND revision=?", (args.id, args.revision)).fetchone()
        need(row is not None, "revision not found")
        restored = json.loads(row[0])
        conflict = db.execute("SELECT id FROM entries WHERE kind=? AND key=? AND scope=? AND id<>?",
                              (restored["kind"], restored["key"], encode(restored["scope"]), args.id)).fetchone()
        need(conflict is None, "restoring this scope would conflict with another record")
        restored["revision"] = entry["revision"]
        if restored["kind"] == "method":
            restored["state"] = "candidate"
            restored["data"].pop("validation", None)
        revise(db, restored)
        event(db, args.id, "rollback", {"from_revision": args.revision})
        return brief(restored)
    if cmd == "export":
        write_export(args.output, export_data(db))
        return {"exported_to": str(Path(args.output).expanduser().resolve())}
    if cmd == "import":
        return import_data(db, read_json(args.input))
    raise Problem("unknown command")


def main(argv=None):
    args = parser().parse_args(argv)
    db = None
    try:
        root = data_root(args)
        if args.command == "status" and not (root / "memory.sqlite3").exists():
            result = {"initialized": False, "data_dir": str(root), "defaults": {"memory": "on", "teaching": "on"}}
        else:
            db = connect(root, create=args.command in {"init", "import", "config"})
            with transaction(db):
                result = execute(db, args)
            if args.command in {"status", "init"}:
                result["data_dir"] = str(root)
        print(encode({"ok": True, **result}))
        return 0
    except (Problem, ValueError, TypeError, KeyError, OSError, sqlite3.Error) as exc:
        message = str(exc) if isinstance(exc, Problem) else "invalid input or local storage operation failed (" + type(exc).__name__ + ")"
        print(encode({"ok": False, "error": message}), file=sys.stderr)
        return 2
    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    sys.exit(main())
