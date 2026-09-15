#!/usr/bin/env python3
"""Structured local CLI for Apple Mail. Python standard library only."""
import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
import uuid
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
from email.utils import parseaddr
from pathlib import Path


class MailError(Exception):
    def __init__(self, code, message, details=None):
        self.code, self.message, self.details = code, message, details
        super().__init__(message)


def require(condition, code, message):
    if not condition:
        raise MailError(code, message)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_json(path):
    try:
        if str(path) == "-":
            raw = sys.stdin.read(2_000_001)
        else:
            with open(path, encoding="utf-8") as handle:
                raw = handle.read(2_000_001)
        require(len(raw) <= 2_000_000, "REQUEST_TOO_LARGE", "JSON request exceeds 2 MB.")
        obj = json.loads(raw)
        require(isinstance(obj, dict), "INVALID_JSON", "Expected a JSON object.")
        return obj
    except (OSError, ValueError) as exc:
        raise MailError("INVALID_JSON", str(exc)) from exc


def string(value, field, nonempty=True):
    require(isinstance(value, str) and "\x00" not in value,
            "INVALID_FIELD", f"{field} must be a string without NUL characters.")
    require(not nonempty or bool(value.strip()), "INVALID_FIELD", f"{field} must not be empty.")
    return value


def email_address(value):
    string(value, "email address")
    require(bool(re.fullmatch(r"[^\s@<>,;]+@[^\s@<>,;]+", value)),
            "INVALID_ADDRESS", "Use one bare email address per entry; display names are not accepted.")
    require(parseaddr(value)[1] == value, "INVALID_ADDRESS", f"Invalid email address: {value}")
    return value


def recipients(value, field):
    require(isinstance(value, list), "INVALID_FIELD", f"{field} must be an array of email addresses.")
    return [email_address(item) for item in value]


def mailbox_path(value):
    require(isinstance(value, list) and value, "INVALID_MAILBOX", "mailbox_path must be a nonempty array of exact folder names.")
    return [string(item, "mailbox_path entry") for item in value]


def message_id(value):
    require(isinstance(value, int) and not isinstance(value, bool) and value > 0,
            "INVALID_MESSAGE_ID", "message_id must be a positive Mail message ID.")
    return value


def file_info(path):
    candidate = Path(string(path, "attachment path")).expanduser()
    require(candidate.is_absolute(), "INVALID_ATTACHMENT", "Attachment paths must be absolute.")
    try:
        candidate = candidate.resolve(strict=True)
        require(candidate.is_file(), "INVALID_ATTACHMENT", f"Not a regular file: {candidate}")
        digest = hashlib.sha256()
        with candidate.open("rb") as handle:
            before = os.fstat(handle.fileno())
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
            after = os.fstat(handle.fileno())
        require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
                "ATTACHMENT_CHANGED", "An attachment changed while it was being read.")
        return {"path": str(candidate), "size": after.st_size, "sha256": digest.hexdigest()}
    except OSError as exc:
        raise MailError("INVALID_ATTACHMENT", str(exc)) from exc


def compose_request(obj, reply=False):
    allowed = {"account_id", "from", "body", "attachments"}
    allowed |= {"mailbox_path", "message_id"} if reply else {"to", "cc", "bcc", "subject"}
    require(not (set(obj) - allowed), "UNKNOWN_FIELD", f"Unknown fields: {sorted(set(obj) - allowed)}")
    result = {"account_id": string(obj.get("account_id"), "account_id"),
              "from": email_address(obj.get("from")), "body": string(obj.get("body"), "body", False)}
    if reply:
        result.update(mailbox_path=mailbox_path(obj.get("mailbox_path")),
                      message_id=message_id(obj.get("message_id")))
    else:
        result.update({key: recipients(obj.get(key, []), key) for key in ("to", "cc", "bcc")})
        require(any(result[key] for key in ("to", "cc", "bcc")), "NO_RECIPIENT", "At least one recipient is required.")
        combined = [addr.lower() for key in ("to", "cc", "bcc") for addr in result[key]]
        require(len(combined) == len(set(combined)), "DUPLICATE_RECIPIENT", "Duplicate recipient across To/Cc/Bcc.")
        result["subject"] = string(obj.get("subject"), "subject")
        require("\r" not in result["subject"] and "\n" not in result["subject"],
                "INVALID_SUBJECT", "Subject must be a single line.")
    paths = obj.get("attachments", [])
    require(isinstance(paths, list), "INVALID_ATTACHMENT", "attachments must be an array of absolute paths.")
    files = [file_info(item) for item in paths]
    require(len(files) == len({item["path"] for item in files}), "DUPLICATE_ATTACHMENT", "Duplicate attachment path.")
    result["attachments"] = [item["path"] for item in files]
    return result, files


class Bridge:
    def __init__(self, timeout=45):
        self.timeout = timeout
        self.driver = Path(__file__).with_name("mail_driver.js")

    def call(self, payload):
        require(sys.platform == "darwin", "MACOS_REQUIRED", "This tool requires macOS Apple Mail.")
        require(self.driver.is_file(), "DRIVER_MISSING", "mail_driver.js is missing.")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", encoding="utf-8") as request_file:
            json.dump(payload, request_file, ensure_ascii=False)
            request_file.flush()
            try:
                completed = subprocess.run(
                    ["/usr/bin/osascript", "-l", "JavaScript", str(self.driver), request_file.name],
                    stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8",
                    timeout=self.timeout, check=False)
            except subprocess.TimeoutExpired as exc:
                raise MailError("BRIDGE_TIMEOUT", "Mail control timed out. If sending was attempted, do not retry; inspect Sent and Outbox first.") from exc
        raw = completed.stdout.strip()
        try:
            response = json.loads(raw)
        except ValueError as exc:
            detail = completed.stderr.strip()[:1500] or "Mail driver returned no valid JSON."
            raise MailError("BRIDGE_FAILURE", detail) from exc
        require(isinstance(response, dict), "BRIDGE_FAILURE", "Unexpected driver response.")
        if completed.returncode or not response.get("ok"):
            error = response.get("error", {})
            raise MailError(str(error.get("code", "MAIL_ERROR")), str(error.get("message", completed.stderr.strip())),
                            error.get("details"))
        return response.get("result", {})


def canonical_snapshot(snapshot):
    require(isinstance(snapshot, dict), "INVALID_SNAPSHOT", "Missing draft snapshot.")
    result = {}
    for key in ("from", "subject", "body"):
        result[key] = string(snapshot.get(key), key, False).replace("\r\n", "\n").replace("\r", "\n")
    for key in ("to", "cc", "bcc", "attachments"):
        value = snapshot.get(key)
        if key == "attachments" and value is None:
            result[key] = None  # Preserve an unknown snapshot for review, never treat it as zero attachments.
            continue
        require(isinstance(value, list) and all(isinstance(item, str) for item in value),
                "INVALID_SNAPSHOT", f"Draft {key} must be an array of strings.")
        result[key] = value
    return result


def snapshot_digest(snapshot):
    raw = json.dumps(canonical_snapshot(snapshot), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def verify_saved_mime(saved, snapshot, files):
    """Verify actual saved MIME attachments, without saving the MIME source in the ticket."""
    require(isinstance(saved, dict), "ATTACHMENTS_UNVERIFIED", "No uniquely associated saved draft is available.")
    source = string(saved.get("source"), "saved draft source")
    require(len(source) <= 100 * 1024 * 1024, "MIME_TOO_LARGE", "Saved draft MIME exceeds the 100 MiB bridge limit.")
    message = BytesParser(policy=policy.default).parsebytes(source.encode("utf-8"))
    require(not message.defects, "MIME_INVALID", "Saved draft MIME has parsing defects.")
    for field in ("from", "to", "cc", "bcc"):
        expected = [snapshot[field]] if field == "from" else snapshot[field]
        actual = sorted(address.lower() for _, address in getaddresses([str(x) for x in message.get_all(field, [])]))
        require(actual == sorted(parseaddr(x)[1].lower() for x in expected),
                "MIME_HEADER_MISMATCH", f"Saved draft {field} does not match the compose snapshot.")
    require(str(message.get("Subject", "")) == snapshot["subject"], "MIME_HEADER_MISMATCH", "Saved draft subject differs from the compose snapshot.")
    actual_files = []
    for part in message.walk():
        if part.get_filename() is None and part.get_content_disposition() != "attachment":
            continue
        payload = part.get_payload(decode=True)
        require(isinstance(payload, bytes) and not part.defects, "MIME_INVALID", "An attachment could not be fully decoded.")
        actual_files.append({"name": unicodedata.normalize("NFC", part.get_filename() or ""),
                             "size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    expected_files = [{"name": unicodedata.normalize("NFC", Path(x["path"]).name),
                       "size": x["size"], "sha256": x["sha256"]} for x in files]
    ordering = lambda item: (item["name"], item["size"], item["sha256"])
    require(sorted(actual_files, key=ordering) == sorted(expected_files, key=ordering),
            "ATTACHMENT_MISMATCH", "The saved MIME contains missing, extra or changed attachment bytes.")
    return {"message_id": saved.get("message_id"), "internet_message_id": saved.get("internet_message_id"),
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(), "attachments": actual_files}


class Store:
    def __init__(self, path):
        self.root = Path(path).expanduser().resolve()

    @contextlib.contextmanager
    def lock(self):
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.root.joinpath("tickets").mkdir(mode=0o700, exist_ok=True)
        fd = os.open(str(self.root / ".lock"), os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, "a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield

    def ticket_path(self, ticket):
        require(isinstance(ticket, str) and re.fullmatch(r"[0-9a-f]{32}", ticket), "INVALID_TICKET", "Invalid local ticket ID.")
        return self.root / "tickets" / (ticket + ".json")

    def write(self, path, obj):
        fd, temporary = tempfile.mkstemp(prefix=".write-", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(obj, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def get(self, ticket):
        return read_json(self.ticket_path(ticket))

    def put(self, record):
        self.write(self.ticket_path(record["ticket"]), record)

    def ledger(self):
        path = self.root / "submissions.json"
        return read_json(path) if path.exists() else {}

    def put_ledger(self, ledger):
        self.write(self.root / "submissions.json", ledger)


def ticket_summary(record):
    return {key: record.get(key) for key in
            ("ticket", "status", "draft_id", "account_id", "created_at", "updated_at", "attachment_verification")}


def make_draft(request, reply, bridge, store):
    payload, files = compose_request(request, reply)
    # Test filesystem access before asking Mail to create anything.
    with store.lock():
        pass
    result = bridge.call(dict(payload, op="reply-draft" if reply else "draft"))
    require(isinstance(result, dict) and result.get("draft_id") is not None,
            "DRAFT_RESULT_INVALID", "Mail did not return a draft ID. Do not assume no draft was created.")
    try:
        snapshot = canonical_snapshot(result.get("snapshot"))
        actual_sender = parseaddr(snapshot["from"])[1].lower()
        require(actual_sender == payload["from"].lower(), "SENDER_MISMATCH", "Mail draft sender differs from requested sender; not eligible for sending.")
        if not reply:
            for key in ("to", "cc", "bcc"):
                require(sorted(parseaddr(x)[1].lower() for x in snapshot[key]) == sorted(x.lower() for x in payload[key]),
                        "RECIPIENT_MISMATCH", f"Mail draft {key} differs from request; not eligible for sending.")
            require(snapshot["subject"] == payload["subject"], "SUBJECT_MISMATCH", "Mail changed the requested subject.")
            expected_body = payload["body"].replace("\r\n", "\n").replace("\r", "\n")
            # Mail can append whitespace or a text attachment placeholder. Preserve its actual snapshot.
            require(snapshot["body"].replace("\ufffc", "").rstrip() == expected_body.replace("\ufffc", "").rstrip(),
                    "BODY_MISMATCH", "Mail changed the requested body; inspect the draft before sending.")
        require(any(snapshot[key] for key in ("to", "cc", "bcc")), "NO_RECIPIENT", "Mail produced a draft without recipients.")
        verification = result.get("attachment_verification", "unavailable")
        proof = None
        if verification == "verified":
            require(isinstance(snapshot["attachments"], list) and sorted(snapshot["attachments"]) == sorted(payload["attachments"]),
                    "ATTACHMENT_MISMATCH", "Mail draft attachments differ from the requested paths; no send will be attempted.")
        if result.get("saved_draft"):
            proof = verify_saved_mime(result["saved_draft"], snapshot, files)
            verification = "mime_source"
    except MailError as exc:
        exc.details = {"partial_draft_id": result["draft_id"], "recovery": "Inspect this draft; it was not sent. Do not blindly repeat draft creation."}
        raise
    record = {"version": 1, "ticket": uuid.uuid4().hex, "status": "draft_ready",
              "draft_id": result["draft_id"], "account_id": payload["account_id"], "from": payload["from"],
              "snapshot": snapshot, "files": files, "created_at": now(),
              "attachment_verification": verification, "saved_draft_proof": proof}
    with store.lock():
        store.put(record)
    return dict(ticket_summary(record), snapshot=snapshot, files=files,
                note="Draft saved; no send requested. Review the actual recipients, body and attachments.")


def send_ticket(ticket, authorized, key, bridge, store):
    require(authorized, "AUTHORIZATION_REQUIRED", "Sending requires the user's explicit instruction or an applicable pre-authorized workflow; then pass --authorized.")
    string(key, "idempotency key")
    require(len(key) <= 256, "INVALID_KEY", "Idempotency key must be at most 256 characters.")
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    # A process-wide lock serializes every send, including across scheduled runs.
    with store.lock():
        record = store.get(ticket)
        ledger = store.ledger()
        previous = ledger.get(key_hash)
        require(not previous or previous.get("ticket") == ticket,
                "IDEMPOTENCY_KEY_REUSED", "This job key already refers to another draft. Inspect its status; do not send a replacement automatically.")
        if record["status"] == "submitted_to_mail":
            return dict(ticket_summary(record), already_submitted=True,
                        note="Already submitted to Mail. No additional send was attempted; recipient delivery is not verified.")
        require(record["status"] == "draft_ready" and not previous,
                "SEND_OUTCOME_UNCERTAIN", "This draft/job has a previous or interrupted send attempt. Inspect Sent/Outbox and local status; do not automatically resend.")
        require(record.get("attachment_verification") in ("verified", "mime_source"), "ATTACHMENTS_UNVERIFIED",
                "Mail could not verify the draft's attachments. Automatic sending is blocked; inspect the draft in Mail.")
        for old in record["files"]:
            require(file_info(old["path"]) == old, "ATTACHMENT_CHANGED", "An attachment changed since draft preparation. Prepare a new reviewed draft.")
        mime_mode = record.get("attachment_verification") == "mime_source"
        inspect_payload = {"op": "verify-draft" if mime_mode else "inspect-draft", "draft_id": record["draft_id"],
                           "account_id": record["account_id"], "expected_snapshot": record["snapshot"]}
        proof = record.get("saved_draft_proof")
        if mime_mode:
            inspect_payload.update(saved_message_id=proof["message_id"], internet_message_id=proof["internet_message_id"])
        live = bridge.call(inspect_payload)
        if not mime_mode:
            require(live.get("attachment_verification") == "verified", "ATTACHMENTS_UNVERIFIED", "Cannot inspect current draft attachments.")
        require(snapshot_digest(live.get("snapshot")) == snapshot_digest(record["snapshot"]),
                "DRAFT_CHANGED", "The draft changed after preparation. Review it and prepare a new ticket.")
        send_payload = {"op": "send-draft", "account_id": record["account_id"], "from": record["from"],
                        "draft_id": record["draft_id"], "expected_snapshot": record["snapshot"]}
        if mime_mode:
            updated_proof = verify_saved_mime(live.get("saved_draft"), record["snapshot"], record["files"])
            require(live.get("previous_saved_draft") == {"message_id": proof["message_id"],
                                                         "internet_message_id": proof["internet_message_id"]},
                    "DRAFT_CHANGED", "The refreshed saved draft is not linked to the verified previous draft.")
            record["saved_draft_proof"] = updated_proof
            send_payload.update(saved_message_id=updated_proof["message_id"], internet_message_id=updated_proof["internet_message_id"],
                                expected_saved_source=live["saved_draft"]["source"])
        record.update(status="sending", updated_at=now(), idempotency_key_hash=key_hash)
        store.put(record)  # Persist before attempting send, including before possible crashes.
        ledger[key_hash] = {"ticket": ticket, "status": "sending", "updated_at": now()}
        store.put_ledger(ledger)
        try:
            result = bridge.call(send_payload)
            require(result.get("submitted_to_mail") is True, "SEND_NOT_CONFIRMED", "Mail did not confirm submission. Inspect Outbox/Sent before any further action.")
        except BaseException as exc:
            record.update(status="uncertain", updated_at=now(),
                          last_error=getattr(exc, "code", type(exc).__name__))
            store.put(record)
            ledger[key_hash].update(status="uncertain", updated_at=now())
            store.put_ledger(ledger)
            raise
        record.update(status="submitted_to_mail", updated_at=now())
        store.put(record)
        ledger[key_hash].update(status="submitted_to_mail", updated_at=now())
        store.put_ledger(ledger)
        return dict(ticket_summary(record), already_submitted=False,
                    note="Submitted to Apple Mail for sending. Final delivery to the recipient has not been verified.")


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state-dir", default=str(Path.home() / "Library/Application Support/mac-mail-management"))
    p.add_argument("--timeout", type=int, default=45, help="Mail bridge timeout in seconds (5–120).")
    commands = p.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Check runtime files; --probe also asks Mail for account metadata.")
    doctor.add_argument("--probe", action="store_true")
    commands.add_parser("accounts")
    for name in ("mailboxes", "check", "list", "read", "mark-read"):
        sub = commands.add_parser(name)
        sub.add_argument("--account-id", required=True)
        if name in ("list", "read", "mark-read"):
            sub.add_argument("--mailbox-path", required=True, help='Exact path as JSON, e.g. ["INBOX"]. Discover with mailboxes first.')
        if name in ("read", "mark-read"):
            sub.add_argument("--message-id", required=True, type=int)
        if name == "list":
            sub.add_argument("--limit", type=int, default=30)
            sub.add_argument("--offset", type=int, default=0)
            sub.add_argument("--unread-only", action="store_true")
            sub.add_argument("--query", default="", help="Subject/sender filter within each scan window; not full-text search.")
        if name == "mark-read":
            sub.add_argument("--value", choices=("true", "false"), required=True)
    for name in ("preview", "draft", "reply-draft"):
        sub = commands.add_parser(name)
        sub.add_argument("--request", required=True, help="UTF-8 JSON path or - for stdin.")
        if name == "preview":
            sub.add_argument("--reply", action="store_true")
    send = commands.add_parser("send", help="Send an unchanged prepared draft; requires prior user authorization.")
    send.add_argument("--ticket", required=True)
    send.add_argument("--authorized", action="store_true")
    send.add_argument("--idempotency-key", required=True, help="Stable job identifier; reuse it after an uncertain outcome.")
    status = commands.add_parser("status")
    status.add_argument("--ticket", required=True)
    return p


def dispatch(args, bridge=None):
    require(5 <= args.timeout <= 120, "INVALID_TIMEOUT", "timeout must be between 5 and 120 seconds.")
    bridge = bridge or Bridge(args.timeout)
    store = Store(args.state_dir)
    op = args.command
    if op == "doctor":
        result = {"platform": sys.platform, "python": sys.version.split()[0],
                  "mail_installed": Path("/System/Applications/Mail.app").is_dir(),
                  "osascript_available": Path("/usr/bin/osascript").is_file(),
                  "driver_present": Path(__file__).with_name("mail_driver.js").is_file(),
                  "mail_control_tested": False, "state_dir": str(store.root)}
        if args.probe:
            result["accounts"] = bridge.call({"op": "accounts"})
            result["mail_control_tested"] = True
        return result
    if op == "preview":
        payload, files = compose_request(read_json(args.request), args.reply)
        return {"preview_only": True, "mail_contacted": False, "request": payload, "files": files}
    if op in ("draft", "reply-draft"):
        return make_draft(read_json(args.request), op == "reply-draft", bridge, store)
    if op == "send":
        return send_ticket(args.ticket, args.authorized, args.idempotency_key, bridge, store)
    if op == "status":
        with store.lock():
            return ticket_summary(store.get(args.ticket))
    payload = {"op": op}
    if hasattr(args, "account_id"):
        payload["account_id"] = string(args.account_id, "account_id")
    if hasattr(args, "mailbox_path"):
        try:
            payload["mailbox_path"] = mailbox_path(json.loads(args.mailbox_path))
        except ValueError as exc:
            raise MailError("INVALID_MAILBOX", "mailbox-path must be valid JSON.") from exc
    if hasattr(args, "message_id"):
        payload["message_id"] = message_id(args.message_id)
    if op == "list":
        require(1 <= args.limit <= 100 and args.offset >= 0, "INVALID_PAGE", "limit must be 1–100; offset must be nonnegative.")
        payload.update(limit=args.limit, offset=args.offset, unread_only=args.unread_only, query=args.query)
    if op == "mark-read":
        payload["read_status"] = args.value == "true"
    return bridge.call(payload)


def main():
    args = parser().parse_args()
    try:
        result = dispatch(args)
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
        return 0
    except (MailError, OSError) as exc:
        error = {"code": getattr(exc, "code", "LOCAL_IO_ERROR"), "message": str(exc)}
        if getattr(exc, "details", None) is not None:
            error["details"] = exc.details
        print(json.dumps({"ok": False, "error": error}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
