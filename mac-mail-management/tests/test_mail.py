"""Offline safety and workflow tests. Never calls or creates objects in Apple Mail."""
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from email import policy
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mail.py"
SPEC = importlib.util.spec_from_file_location("mac_mail_cli_under_test", SCRIPT)
mail = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mail)


def saved_mime(snapshot, attachments, message_id=101, internet_message_id="<fixture-101@example.test>"):
    """Use Python's independent MIME encoder, including RFC encoded Chinese filenames."""
    message = EmailMessage(policy=policy.SMTP)
    message["From"] = snapshot["from"]
    for field in ("to", "cc", "bcc"):
        if snapshot[field]:
            message[field.title()] = ", ".join(snapshot[field])
    message["Subject"] = snapshot["subject"]
    message["Message-ID"] = internet_message_id
    message.set_content(snapshot["body"], charset="utf-8", cte="quoted-printable")
    for name, content in attachments:
        message.add_attachment(content, maintype="application", subtype="pdf", filename=name, cte="base64")
    return {"message_id": message_id, "internet_message_id": internet_message_id,
            "source": message.as_bytes().decode("ascii")}


class FakeBridge:
    """Models draft snapshots and submission outcomes, not Apple Mail's implementation."""

    def __init__(self):
        self.calls = []
        self.drafts = {}
        self.next_id = 1
        self.submissions = 0
        self.send_error = None
        self.send_result = {"submitted_to_mail": True}
        self.verification = "verified"
        self.before_send = None
        self.draft_transform = None
        self.mime_mode = False
        self.saved = {}
        self.previous_saved = {}

    def call(self, payload):
        self.calls.append(copy.deepcopy(payload))
        op = payload["op"]
        if op in ("draft", "reply-draft"):
            draft_id = self.next_id
            self.next_id += 1
            snapshot = {key: copy.deepcopy(payload.get(key, []))
                        for key in ("to", "cc", "bcc", "attachments")}
            snapshot.update({key: payload.get(key, "") for key in ("from", "subject", "body")})
            if op == "reply-draft":
                snapshot.update(to=["recruiter@example.com"], subject="Re: Interview")
            if self.draft_transform:
                self.draft_transform(snapshot)
            if self.mime_mode:
                snapshot["attachments"] = None
                self.saved[draft_id] = saved_mime(
                    snapshot, [(Path(path).name, Path(path).read_bytes()) for path in payload.get("attachments", [])],
                    message_id=draft_id + 100, internet_message_id="<fixture-%s@example.test>" % draft_id)
                self.previous_saved[draft_id] = {
                    "message_id": self.saved[draft_id]["message_id"],
                    "internet_message_id": self.saved[draft_id]["internet_message_id"],
                }
            self.drafts[draft_id] = snapshot
            result = {"draft_id": draft_id, "snapshot": copy.deepcopy(snapshot),
                      "attachment_verification": "unavailable" if self.mime_mode else self.verification}
            if self.mime_mode:
                result["saved_draft"] = copy.deepcopy(self.saved[draft_id])
            return result
        if op == "inspect-draft":
            return {"snapshot": copy.deepcopy(self.drafts[payload["draft_id"]]),
                    "attachment_verification": self.verification}
        if op == "verify-draft":
            result = {"snapshot": copy.deepcopy(self.drafts[payload["draft_id"]]),
                      "attachment_verification": "unavailable",
                      "saved_draft": copy.deepcopy(self.saved[payload["draft_id"]])}
            previous = self.previous_saved.get(payload["draft_id"])
            if previous is not None:
                result["previous_saved_draft"] = copy.deepcopy(previous)
            return result
        if op == "send-draft":
            self.submissions += 1
            if self.before_send:
                self.before_send(payload)
            if self.send_error:
                raise self.send_error
            return copy.deepcopy(self.send_result)
        raise AssertionError("Unexpected Mail operation: " + op)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.store = mail.Store(self.state)
        self.bridge = FakeBridge()
        self.attachment = self.root / "简历 '引用' $样本.pdf"
        self.attachment.write_bytes(b"%PDF-1.4\nfictional resume fixture\n")
        self.request = {
            "account_id": "explicit-qq-account-id", "from": "candidate@qq.com",
            "to": ["hr@example.com"], "cc": [], "bcc": [],
            "subject": "应聘 · 数据分析师", "body": "您好，附件是我的简历。\n谢谢！",
            "attachments": [str(self.attachment)],
        }

    def assert_mail_error(self, code, callback):
        with self.assertRaises(mail.MailError) as caught:
            callback()
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def draft(self, request=None):
        return mail.make_draft(request or self.request, False, self.bridge, self.store)

    def send(self, ticket, key="job:example:analyst", authorized=True, store=None):
        return mail.send_ticket(ticket, authorized, key, self.bridge, store or self.store)

    def test_preview_preserves_arbitrary_content_without_contacting_mail_or_creating_state(self):
        body = '您好 "朋友"\n\\ `touch /tmp/DO_NOT_CREATE` $(whoami)\n\'; Application("Mail").quit(); //'
        request = dict(self.request, body=body)
        path = self.root / "request.json"
        path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        args = mail.parser().parse_args(["--state-dir", str(self.state), "preview", "--request", str(path)])
        result = mail.dispatch(args, bridge=self.bridge)
        self.assertTrue(result["preview_only"])
        self.assertFalse(result["mail_contacted"])
        self.assertEqual(result["request"]["body"], body)
        self.assertEqual(self.bridge.calls, [])
        self.assertFalse(self.state.exists())

    def test_invalid_recipient_fails_before_mail_call(self):
        for value in ("hr@example.com\r\nBcc: leak@example.com", "HR <hr@example.com>",
                      "one@example.com,two@example.com", "not-an-address"):
            with self.subTest(address=value):
                self.assert_mail_error("INVALID_ADDRESS", lambda: self.draft(dict(self.request, to=[value])))
        self.assertEqual(self.bridge.calls, [])

    def test_missing_attachment_fails_before_mail_call(self):
        request = dict(self.request, attachments=[str(self.root / "absent.pdf")])
        self.assert_mail_error("INVALID_ATTACHMENT", lambda: self.draft(request))
        self.assertEqual(self.bridge.calls, [])

    def test_sender_and_account_are_required_before_mail_call(self):
        for field in ("account_id", "from"):
            with self.subTest(field=field):
                request = dict(self.request)
                request.pop(field)
                self.assert_mail_error("INVALID_FIELD", lambda: self.draft(request))
        self.assertEqual(self.bridge.calls, [])

    def test_draft_creates_ticket_but_does_not_submit_and_requires_authorization(self):
        prepared = self.draft()
        self.assertEqual(prepared["status"], "draft_ready")
        self.assertEqual(self.bridge.submissions, 0)
        self.assertEqual(self.store.get(prepared["ticket"])["snapshot"]["body"], self.request["body"])
        before = copy.deepcopy(self.bridge.calls)
        self.assert_mail_error("AUTHORIZATION_REQUIRED", lambda: self.send(prepared["ticket"], authorized=False))
        self.assertEqual(self.bridge.calls, before)
        self.assertEqual(self.store.get(prepared["ticket"])["status"], "draft_ready")

    def test_authorized_send_uses_selected_account_and_sender(self):
        prepared = self.draft()
        result = self.send(prepared["ticket"])
        sent_payload = [item for item in self.bridge.calls if item["op"] == "send-draft"][0]
        self.assertEqual(sent_payload["account_id"], self.request["account_id"])
        self.assertEqual(sent_payload["from"], self.request["from"])
        self.assertEqual(result["status"], "submitted_to_mail")
        self.assertFalse(result["already_submitted"])

    def test_repeat_send_after_reopening_store_submits_once(self):
        prepared = self.draft()
        self.send(prepared["ticket"])
        before = len(self.bridge.calls)
        result = self.send(prepared["ticket"], store=mail.Store(self.state))
        self.assertTrue(result["already_submitted"])
        self.assertEqual(len(self.bridge.calls), before)
        self.assertEqual(self.bridge.submissions, 1)

    def test_same_job_key_cannot_send_another_ticket(self):
        first = self.draft()
        second = self.draft(dict(self.request, subject="另一个草稿"))
        self.send(first["ticket"])
        self.assert_mail_error("IDEMPOTENCY_KEY_REUSED", lambda: self.send(second["ticket"]))
        self.assertEqual(self.bridge.submissions, 1)
        self.assertEqual(self.store.get(second["ticket"])["status"], "draft_ready")

    def test_timeout_blocks_retries_even_with_a_new_key_and_reopened_store(self):
        prepared = self.draft()
        self.bridge.send_error = mail.MailError("BRIDGE_TIMEOUT", "simulated unknown outcome")
        self.assert_mail_error("BRIDGE_TIMEOUT", lambda: self.send(prepared["ticket"]))
        self.assertEqual(self.store.get(prepared["ticket"])["status"], "uncertain")
        self.bridge.send_error = None
        for key in ("job:example:analyst", "a-new-key-must-not-bypass-uncertainty"):
            with self.subTest(key=key):
                self.assert_mail_error("SEND_OUTCOME_UNCERTAIN", lambda: self.send(
                    prepared["ticket"], key=key, store=mail.Store(self.state)))
        self.assertEqual(self.bridge.submissions, 1)

    def test_unconfirmed_submission_blocks_retries(self):
        prepared = self.draft()
        self.bridge.send_result = {"submitted_to_mail": False}
        self.assert_mail_error("SEND_NOT_CONFIRMED", lambda: self.send(prepared["ticket"]))
        self.assert_mail_error("SEND_OUTCOME_UNCERTAIN", lambda: self.send(prepared["ticket"]))
        self.assertEqual(self.bridge.submissions, 1)

    def test_keyboard_interrupt_during_send_is_persisted_as_uncertain(self):
        prepared = self.draft()
        self.bridge.send_error = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.send(prepared["ticket"])
        self.assertEqual(self.store.get(prepared["ticket"])["status"], "uncertain")
        self.assert_mail_error("SEND_OUTCOME_UNCERTAIN", lambda: self.send(prepared["ticket"]))
        self.assertEqual(self.bridge.submissions, 1)

    def test_live_draft_changes_block_submission(self):
        changes = {"to": ["other@example.com"], "cc": ["extra@example.com"],
                   "bcc": ["hidden@example.com"], "from": "wrong@qq.com",
                   "subject": "Changed subject", "body": "被改过的正文",
                   "attachments": []}
        for field, value in changes.items():
            with self.subTest(field=field):
                prepared = self.draft()
                self.bridge.drafts[prepared["draft_id"]][field] = value
                self.assert_mail_error("DRAFT_CHANGED", lambda: self.send(prepared["ticket"], key="job:" + field))
        self.assertEqual(self.bridge.submissions, 0)

    def test_source_attachment_change_blocks_before_live_draft_inspection(self):
        prepared = self.draft()
        self.attachment.write_bytes(b"different resume bytes")
        calls_before = len(self.bridge.calls)
        self.assert_mail_error("ATTACHMENT_CHANGED", lambda: self.send(prepared["ticket"]))
        self.assertEqual(len(self.bridge.calls), calls_before)
        self.assertEqual(self.bridge.submissions, 0)

    def test_unverified_attachments_at_creation_or_send_block_submission(self):
        self.bridge.verification = "unavailable"
        unverified = self.draft()
        self.bridge.verification = "verified"
        self.assert_mail_error("ATTACHMENTS_UNVERIFIED", lambda: self.send(unverified["ticket"]))
        verified = self.draft()
        self.bridge.verification = "unavailable"
        self.assert_mail_error("ATTACHMENTS_UNVERIFIED", lambda: self.send(verified["ticket"]))
        self.assertEqual(self.bridge.submissions, 0)

    def test_null_attachment_snapshot_preserves_reviewable_ticket_but_cannot_send(self):
        self.bridge.verification = "unavailable"
        self.bridge.draft_transform = lambda snapshot: snapshot.update(attachments=None)
        prepared = self.draft()
        self.assertEqual(prepared["status"], "draft_ready")
        self.assertEqual(prepared["attachment_verification"], "unavailable")
        self.assertIsNone(prepared["snapshot"]["attachments"])
        self.assertIsNone(self.store.get(prepared["ticket"])["snapshot"]["attachments"])
        calls_before = len(self.bridge.calls)
        self.assert_mail_error("ATTACHMENTS_UNVERIFIED", lambda: self.send(prepared["ticket"]))
        self.assertEqual(len(self.bridge.calls), calls_before)
        self.assertEqual(self.bridge.submissions, 0)

    def test_verified_attachments_must_match_requested_files(self):
        for attachments in ([], [str(self.attachment), str(self.root / "unexpected.pdf")],
                            [str(self.root / "different.pdf")]):
            with self.subTest(attachments=attachments):
                self.bridge.draft_transform = lambda snapshot: snapshot.update(attachments=attachments)
                self.assert_mail_error("ATTACHMENT_MISMATCH", self.draft)
        self.assertEqual(self.bridge.submissions, 0)

    def test_new_draft_body_cannot_silently_change(self):
        for body in ("", "改写了全文", self.request["body"] + "\n新增一句用户未要求的内容",
                     self.request["body"].replace("简历", "合同")):
            with self.subTest(body=body):
                self.bridge.draft_transform = lambda snapshot: snapshot.update(body=body)
                self.assert_mail_error("BODY_MISMATCH", self.draft)
        self.assertEqual(self.bridge.submissions, 0)

    def test_new_draft_allows_trailing_newline_difference_and_keeps_actual_snapshot(self):
        actual_body = self.request["body"] + "\n\n"
        self.bridge.draft_transform = lambda snapshot: snapshot.update(body=actual_body)
        prepared = self.draft()
        self.assertEqual(prepared["snapshot"]["body"], actual_body)
        self.assertEqual(self.store.get(prepared["ticket"])["snapshot"]["body"], actual_body)
        result = self.send(prepared["ticket"])
        self.assertEqual(result["status"], "submitted_to_mail")

    def test_new_draft_allows_mail_trailing_whitespace_and_attachment_marker(self):
        actual_body = self.request["body"] + " \t\n\ufffc \n"
        self.bridge.draft_transform = lambda snapshot: snapshot.update(body=actual_body)
        prepared = self.draft()
        self.assertEqual(prepared["snapshot"]["body"], actual_body)
        self.assertEqual(self.send(prepared["ticket"])["status"], "submitted_to_mail")

    def test_new_draft_body_validation_failure_identifies_partial_draft(self):
        self.bridge.draft_transform = lambda snapshot: snapshot.update(body="未获授权的其他内容")
        error = self.assert_mail_error("BODY_MISMATCH", self.draft)
        self.assertIn(error.details["partial_draft_id"], self.bridge.drafts)
        self.assertTrue(error.details["recovery"])
        self.assertEqual(self.bridge.submissions, 0)

    def test_mime_bytes_verify_with_chinese_filename_and_binary_content(self):
        content = bytes(range(256)) + "中文二进制简历".encode("utf-8")
        self.attachment.write_bytes(content)
        snapshot = {key: self.request[key] for key in ("from", "to", "cc", "bcc", "subject", "body", "attachments")}
        saved = saved_mime(snapshot, [(self.attachment.name, content)])
        files = [mail.file_info(str(self.attachment))]
        proof = mail.verify_saved_mime(saved, snapshot, files)
        self.assertEqual(proof["attachments"], [{"name": self.attachment.name, "size": len(content),
                                                "sha256": hashlib.sha256(content).hexdigest()}])
        self.assertEqual(proof["message_id"], saved["message_id"])
        self.assertEqual(proof["internet_message_id"], saved["internet_message_id"])
        self.assertNotIn("source", proof)
        self.assertNotIn(content.decode("utf-8", errors="replace"), json.dumps(proof))

    def test_mime_missing_extra_changed_and_renamed_attachments_fail(self):
        snapshot = {key: self.request[key] for key in ("from", "to", "cc", "bcc", "subject", "body", "attachments")}
        content = self.attachment.read_bytes()
        files = [mail.file_info(str(self.attachment))]
        cases = {
            "missing": [],
            "extra": [(self.attachment.name, content), ("额外附件.pdf", b"extra")],
            "changed_same_size": [(self.attachment.name, b"X" + content[1:])],
            "truncated": [(self.attachment.name, content[:-1])],
            "renamed": [("其他简历.pdf", content)],
            "duplicated": [(self.attachment.name, content), (self.attachment.name, content)],
        }
        for label, attachments in cases.items():
            with self.subTest(case=label):
                self.assert_mail_error("ATTACHMENT_MISMATCH", lambda: mail.verify_saved_mime(
                    saved_mime(snapshot, attachments), snapshot, files))

    def test_mime_header_changes_fail(self):
        snapshot = {key: self.request[key] for key in ("from", "to", "cc", "bcc", "subject", "body", "attachments")}
        files = [mail.file_info(str(self.attachment))]
        changes = {"from": "wrong@qq.com", "to": ["wrong@example.com"], "cc": ["extra@example.com"],
                   "bcc": ["hidden@example.com"], "subject": "被改写的主题"}
        for field, value in changes.items():
            with self.subTest(field=field):
                changed = dict(snapshot, **{field: value})
                saved = saved_mime(changed, [(self.attachment.name, self.attachment.read_bytes())])
                self.assert_mail_error("MIME_HEADER_MISMATCH", lambda: mail.verify_saved_mime(saved, snapshot, files))

    def test_mime_mode_null_compose_attachments_can_send_verified_bytes(self):
        self.bridge.mime_mode = True
        prepared = self.draft()
        self.assertIsNone(prepared["snapshot"]["attachments"])
        self.assertEqual(prepared["attachment_verification"], "mime_source")
        record = self.store.get(prepared["ticket"])
        self.assertNotIn("source", record["saved_draft_proof"])
        result = self.send(prepared["ticket"])
        self.assertEqual(result["status"], "submitted_to_mail")
        self.assertEqual([item["op"] for item in self.bridge.calls], ["draft", "verify-draft", "send-draft"])
        send_payload = self.bridge.calls[-1]
        self.assertEqual(send_payload["expected_saved_source"], self.bridge.saved[prepared["draft_id"]]["source"])
        self.assertEqual(send_payload["internet_message_id"], record["saved_draft_proof"]["internet_message_id"])
        self.assertEqual(self.bridge.submissions, 1)
        self.assertTrue(self.send(prepared["ticket"])["already_submitted"])
        self.assertEqual(self.bridge.submissions, 1)

    def test_mime_preflight_changed_attachment_bytes_block_send(self):
        self.bridge.mime_mode = True
        prepared = self.draft()
        saved = self.bridge.saved[prepared["draft_id"]]
        self.bridge.saved[prepared["draft_id"]] = saved_mime(
            prepared["snapshot"], [(self.attachment.name, b"different bytes in Mail")],
            saved["message_id"], saved["internet_message_id"])
        self.assert_mail_error("ATTACHMENT_MISMATCH", lambda: self.send(prepared["ticket"]))
        self.assertEqual(self.bridge.submissions, 0)
        self.assertEqual(self.store.get(prepared["ticket"])["status"], "draft_ready")
        self.assertEqual(self.store.ledger(), {})

    def test_mime_preflight_changed_headers_block_send(self):
        self.bridge.mime_mode = True
        prepared = self.draft()
        saved = self.bridge.saved[prepared["draft_id"]]
        changed = dict(prepared["snapshot"], bcc=["unexpected@example.com"])
        self.bridge.saved[prepared["draft_id"]] = saved_mime(
            changed, [(self.attachment.name, self.attachment.read_bytes())],
            saved["message_id"], saved["internet_message_id"])
        self.assert_mail_error("MIME_HEADER_MISMATCH", lambda: self.send(prepared["ticket"]))
        self.assertEqual(self.bridge.submissions, 0)

    def test_mime_preflight_rebuilt_identity_with_valid_lineage_can_send(self):
        self.bridge.mime_mode = True
        prepared = self.draft()
        saved = self.bridge.saved[prepared["draft_id"]]
        previous = {key: saved[key] for key in ("message_id", "internet_message_id")}
        self.bridge.saved[prepared["draft_id"]] = saved_mime(
            prepared["snapshot"], [(self.attachment.name, self.attachment.read_bytes())],
            saved["message_id"] + 500, "<rebuilt-draft@example.test>")
        refreshed = self.bridge.saved[prepared["draft_id"]]
        result = self.send(prepared["ticket"])
        self.assertEqual(result["status"], "submitted_to_mail")
        verify_payload = self.bridge.calls[-2]
        self.assertEqual(verify_payload["saved_message_id"], previous["message_id"])
        self.assertEqual(verify_payload["internet_message_id"], previous["internet_message_id"])
        send_payload = self.bridge.calls[-1]
        self.assertEqual(send_payload["saved_message_id"], refreshed["message_id"])
        self.assertEqual(send_payload["internet_message_id"], refreshed["internet_message_id"])
        self.assertEqual(send_payload["expected_saved_source"], refreshed["source"])
        proof = self.store.get(prepared["ticket"])["saved_draft_proof"]
        self.assertEqual(proof["message_id"], refreshed["message_id"])
        self.assertEqual(proof["internet_message_id"], refreshed["internet_message_id"])
        self.assertEqual(self.bridge.submissions, 1)

    def test_mime_preflight_missing_or_wrong_previous_anchor_blocks_send(self):
        self.bridge.mime_mode = True
        for changed_field in (None, "message_id", "internet_message_id"):
            with self.subTest(changed_field=changed_field):
                prepared = self.draft()
                draft_id = prepared["draft_id"]
                if changed_field is None:
                    self.bridge.previous_saved.pop(draft_id)
                elif changed_field == "message_id":
                    self.bridge.previous_saved[draft_id][changed_field] += 1000
                else:
                    self.bridge.previous_saved[draft_id][changed_field] = "<unrelated-draft@example.test>"
                self.assert_mail_error("DRAFT_CHANGED", lambda: self.send(
                    prepared["ticket"], key="lineage:" + str(changed_field)))
                self.assertEqual(self.store.get(prepared["ticket"])["status"], "draft_ready")
        self.assertEqual(self.bridge.submissions, 0)

    def test_mime_send_unknown_outcome_is_not_retried(self):
        self.bridge.mime_mode = True
        prepared = self.draft()
        self.bridge.send_error = mail.MailError("BRIDGE_TIMEOUT", "MIME send outcome unknown")
        self.assert_mail_error("BRIDGE_TIMEOUT", lambda: self.send(prepared["ticket"]))
        self.assertEqual(self.store.get(prepared["ticket"])["status"], "uncertain")
        calls_before = len(self.bridge.calls)
        self.bridge.send_error = None
        self.assert_mail_error("SEND_OUTCOME_UNCERTAIN", lambda: self.send(
            prepared["ticket"], key="different-key", store=mail.Store(self.state)))
        self.assertEqual(len(self.bridge.calls), calls_before)
        self.assertEqual(self.bridge.submissions, 1)

    def test_mime_creation_validation_failure_keeps_partial_draft_id(self):
        self.bridge.mime_mode = True
        original_call = self.bridge.call

        def mismatched_saved_draft(payload):
            result = original_call(payload)
            if payload["op"] == "draft":
                result["saved_draft"] = saved_mime(result["snapshot"], [])
            return result

        self.bridge.call = mismatched_saved_draft
        error = self.assert_mail_error("ATTACHMENT_MISMATCH", self.draft)
        self.assertIn(error.details["partial_draft_id"], self.bridge.drafts)
        self.assertTrue(error.details["recovery"])
        self.assertEqual(self.bridge.submissions, 0)

    def test_send_intent_is_durable_before_bridge_submission(self):
        prepared = self.draft()
        observed = []

        def observe(_):
            reopened = mail.Store(self.state)
            ticket = reopened.get(prepared["ticket"])
            ledger = reopened.ledger()
            observed.append((ticket["status"], ledger[ticket["idempotency_key_hash"]]["status"]))

        self.bridge.before_send = observe
        self.send(prepared["ticket"])
        self.assertEqual(observed, [("sending", "sending")])

    def test_interrupted_state_persistence_blocks_retry_without_submitting(self):
        prepared = self.draft()
        with patch.object(self.store, "put_ledger", side_effect=OSError("simulated disk failure")):
            with self.assertRaises(OSError):
                self.send(prepared["ticket"])
        self.assertEqual(self.bridge.submissions, 0)
        self.assert_mail_error("SEND_OUTCOME_UNCERTAIN", lambda: self.send(
            prepared["ticket"], store=mail.Store(self.state)))
        self.assertEqual(self.bridge.submissions, 0)

    def test_concurrent_same_ticket_submits_once(self):
        prepared = self.draft()
        start = threading.Barrier(2)

        def submit():
            start.wait(timeout=5)
            return self.send(prepared["ticket"], store=mail.Store(self.state))

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _: submit(), range(2)))
        self.assertEqual(self.bridge.submissions, 1)
        self.assertEqual(sorted(result["already_submitted"] for result in results), [False, True])

    def test_path_traversal_ticket_is_rejected(self):
        self.assert_mail_error("INVALID_TICKET", lambda: self.send("../../outside"))
        self.assertEqual(self.bridge.calls, [])


class BoundaryTests(unittest.TestCase):
    def test_bridge_preserves_partial_draft_details_from_driver_error(self):
        details = {"partial_draft_id": 987,
                   "recovery": "Inspect this draft before retrying; creation may have partially completed."}
        response = {"ok": False, "error": {"code": "MAIL_ERROR", "message": "attachment insertion failed",
                                           "details": details}}
        completed = subprocess.CompletedProcess([], 0, json.dumps(response), "")
        with patch.object(mail.sys, "platform", "darwin"), patch.object(mail.subprocess, "run", return_value=completed):
            with self.assertRaises(mail.MailError) as caught:
                mail.Bridge().call({"op": "draft"})
        self.assertEqual(caught.exception.code, "MAIL_ERROR")
        self.assertEqual(caught.exception.details, details)

    def test_bridge_passes_untrusted_text_as_json_file_not_executable_arguments(self):
        text = "中文 ' \" `touch /tmp/not-real` $(whoami)\n); Application('Mail').quit(); //"
        payload = {"op": "draft", "body": text, "subject": text, "to": ["hr@example.com"]}
        seen = []

        def fake_run(argv, **kwargs):
            self.assertEqual(argv[:3], ["/usr/bin/osascript", "-l", "JavaScript"])
            self.assertEqual(Path(argv[3]), SCRIPT.with_name("mail_driver.js"))
            self.assertEqual(len(argv), 5)
            self.assertNotIn(text, argv)
            self.assertFalse(kwargs.get("shell", False))
            self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
            data_file = Path(argv[4])
            self.assertEqual(json.loads(data_file.read_text(encoding="utf-8")), payload)
            self.assertEqual(data_file.stat().st_mode & 0o077, 0)
            seen.append(data_file)
            return subprocess.CompletedProcess(argv, 0, '{"ok": true, "result": {"mock": true}}', "")

        with patch.object(mail.sys, "platform", "darwin"), patch.object(mail.subprocess, "run", side_effect=fake_run):
            self.assertEqual(mail.Bridge().call(payload), {"mock": True})
        self.assertEqual(len(seen), 1)
        self.assertFalse(seen[0].exists(), "Temporary payload must be removed after bridge completion")

    def test_cli_help_and_static_doctor_are_executable(self):
        for argv in (["--help"], ["doctor"]):
            with self.subTest(argv=argv):
                result = subprocess.run([sys.executable, str(SCRIPT), *argv],
                                        capture_output=True, text=True, timeout=15, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                if argv == ["doctor"]:
                    payload = json.loads(result.stdout)
                    self.assertTrue(payload["ok"])
                    self.assertFalse(payload["result"]["mail_control_tested"])
                    self.assertTrue(payload["result"]["driver_present"])
                else:
                    self.assertIn("preview", result.stdout)
                    self.assertIn("send", result.stdout)

    def test_static_doctor_does_not_probe_bridge(self):
        fake = FakeBridge()
        result = mail.dispatch(mail.parser().parse_args(["doctor"]), bridge=fake)
        self.assertFalse(result["mail_control_tested"])
        self.assertEqual(fake.calls, [])


if __name__ == "__main__":
    unittest.main()
