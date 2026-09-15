#!/usr/bin/env node
/*
 * Offline driver tests. Run: node tests/test_driver.js
 * Only injected in-memory objects are used: no Application(), osascript,
 * real Mail account, filesystem attachment, draft, or send operation.
 */
"use strict";

const assert = require("node:assert/strict");
const driver = require("../scripts/mail_driver.js");

function properties(values) {
    const object = {};
    for (const [key, initial] of Object.entries(values)) {
        let value = initial;
        Object.defineProperty(object, key, {
            configurable: true,
            get() { return () => value; },
            set(next) { value = next; }
        });
    }
    return object;
}

function collection(items) {
    const callable = () => items;
    Object.defineProperty(callable, "length", {get: () => items.length});
    return new Proxy(callable, {
        get(object, key) {
            if (key === "byId") return id => items.find(item => item.id() === id);
            if (key === "push") return item => items.push(item);
            if (/^\d+$/.test(String(key))) return items[Number(key)];
            return Reflect.get(object, key);
        }
    });
}

function recipient(value) {
    return properties({address: value.address, name: value.name || ""});
}

function fixtures() {
    let nextDraftId = 100;
    let nextSavedId = 10000;
    let clockMs = 0;
    const stored = [];
    const savedByOutgoing = new Map();
    const events = {saves: 0, sends: 0, checks: [], replies: [], sourceSuffix: "", freezeSave: false};
    function outgoing(input) {
        const object = properties({id: nextDraftId++, sender: input.sender, subject: input.subject, visible: input.visible || false});
        let body = input.content;
        const content = () => body;
        content.attachments = collection([]);
        object._attachments = content.attachments;
        Object.defineProperty(object, "content", {get: () => content, set: value => { body = value; }});
        for (const type of ["to", "cc", "bcc"]) object[type + "Recipients"] = collection([]);
        return object;
    }
    function incoming(id, read, subject) {
        const object = properties({
            id, messageId: "internet-" + id, sender: "hr@example.com", subject,
            dateReceived: new Date("2026-09-15T00:00:00Z"), dateSent: new Date("2026-09-15T00:00:00Z"),
            readStatus: read, flaggedStatus: false, messageSize: 20,
            content: "inbound " + id, replyTo: "reply@example.com"
        });
        object.toRecipients = collection([recipient({address: "me@example.com"})]);
        object.ccRecipients = collection([]);
        object.mailAttachments = collection([properties({id: "attachment-" + id, name: "position.pdf", mimeType: "application/pdf", fileSize: 2048, downloaded: false})]);
        return object;
    }
    const messages = [incoming(1, false, "Role"), incoming(2, true, "Other"), incoming(3, false, "Role two")];
    const child = properties({name: "Child", unreadCount: 0});
    child.mailboxes = collection([]);
    child.messages = collection([]);
    const inbox = properties({name: "收件箱", unreadCount: 2});
    inbox.mailboxes = collection([child]);
    inbox.messages = collection(messages);
    const account = properties({id: "a", name: "QQ", enabled: true, emailAddresses: ["me@example.com"]});
    account.mailboxes = collection([inbox]);
    const draftsMailbox = {messages: collection(stored), account: () => account};
    const mail = {
        accounts: collection([account]), outgoingMessages: collection([]),
        draftsMailbox: () => draftsMailbox,
        OutgoingMessage: outgoing, ToRecipient: recipient, CcRecipient: recipient, BccRecipient: recipient,
        Attachment: value => properties(value),
        save(outgoing) {
            events.saves += 1;
            if (events.freezeSave) return;
            const old = savedByOutgoing.get(outgoing);
            if (old) stored.splice(stored.indexOf(old), 1);
            const id = nextSavedId++;
            const saved = properties({id, messageId: "saved-" + id + "@example.com", sender: "", subject: "", content: "", source: "", mailbox: draftsMailbox});
            savedByOutgoing.set(outgoing, saved);
            stored.push(saved);
            saved.sender = outgoing.sender();
            saved.subject = outgoing.subject();
            saved.content = outgoing.content();
            for (const type of ["to", "cc", "bcc"]) saved[type + "Recipients"] = collection(outgoing[type + "Recipients"]().map(value => recipient({address: value.address(), name: value.name()})));
            saved.source = "Message-ID: " + saved.messageId() + "\nSubject: " + saved.subject() + "\n\n" + saved.content() + events.sourceSuffix;
        },
        send() { events.sends += 1; return true; },
        checkForNewMail(parameters) { events.checks.push(parameters.for); },
        reply(original, options) {
            events.replies.push({original, options});
            const draft = outgoing({sender: "me@example.com", subject: "Re: " + original.subject(), content: "quoted original"});
            draft.toRecipients.push(recipient({address: original.replyTo()}));
            mail.outgoingMessages.push(draft);
            return draft;
        }
    };
    const environment = {
        path: path => path,
        now: () => clockMs,
        pause: seconds => { clockMs += seconds * 1000; },
        assertAttachmentFile(path) { if (path === "/missing") throw new Error("Simulated missing file"); }
    };
    return {mail, environment, events, messages, account, stored, savedByOutgoing};
}

function fails(action, expectedCode) {
    assert.throws(action, error => error.mailCode === expectedCode);
}

function run() {
    const {mail, environment, events, messages, account} = fixtures();
    const execute = request => driver.executeRequest(request, mail, environment);
    const location = {account_id: "a", mailbox_path: ["收件箱"]};
    const compose = {
        op: "draft", account_id: "a", from: "ME@example.com", to: ["hr@example.com"],
        subject: "Application", body: "Hello\r\nTeam", attachments: ["/private/tmp/resume.pdf"]
    };

    assert.deepEqual(execute({op: "accounts"}).accounts, [{id: "a", name: "QQ", email_addresses: ["me@example.com"], enabled: true}]);
    assert.deepEqual(execute({op: "mailboxes", account_id: "a"}).mailboxes.map(item => item.path), [["收件箱"], ["收件箱", "Child"]]);
    let page = execute({op: "list", ...location, limit: 2, unread_only: true, query: "role"});
    assert.equal(page.messages.length, 1);
    assert.equal(page.scanned_count, 2);
    assert.equal(page.next_offset, 2);
    assert.equal(page.has_more, true);
    assert.equal(page.messages[0].body, undefined);
    page = execute({op: "list", ...location, offset: 10});
    assert.equal(page.scanned_count, 0);
    assert.equal(page.has_more, false);
    page = execute({op: "list", ...location, limit: 1, query: "no-match"});
    assert.deepEqual(page.messages, []);
    assert.equal(page.has_more, true);
    const read = execute({op: "read", ...location, message_id: 1});
    assert.equal(read.body, "inbound 1");
    assert.equal(read.attachments[0].mime_type, "application/pdf");
    assert.equal(read.attachments[0].downloaded, false);
    assert.equal(messages[0].readStatus(), false);
    execute({op: "check", account_id: "a"});
    assert.equal(events.checks[0], account);

    fails(() => execute({...compose, from: "other@example.com"}), "SENDER_ACCOUNT_MISMATCH");
    assert.equal(mail.outgoingMessages.length, 0);
    const prepared = execute(compose);
    assert.equal(events.saves, 1);
    assert.equal(events.sends, 0);
    assert.equal(prepared.attachment_verification, "verified");
    assert.deepEqual(prepared.snapshot.attachments, ["/private/tmp/resume.pdf"]);
    assert.equal(prepared.snapshot.body, "Hello\nTeam");
    assert.deepEqual(execute({op: "inspect-draft", draft_id: prepared.draft_id}).snapshot, prepared.snapshot);

    const send = {op: "send-draft", account_id: "a", from: "me@example.com", draft_id: prepared.draft_id, expected_snapshot: prepared.snapshot};
    const live = mail.outgoingMessages()[0];
    live.content = "Changed";
    fails(() => execute(send), "DRAFT_CHANGED");
    assert.equal(events.sends, 0);
    live.content = "Hello\nTeam";
    const savedAttachments = live.content.attachments;
    live.content.attachments = () => { throw new Error("Simulated unsupported enumeration"); };
    const unavailable = execute({op: "inspect-draft", draft_id: prepared.draft_id});
    assert.equal(unavailable.attachment_verification, "unavailable");
    assert.equal(unavailable.snapshot.attachments, null);
    fails(() => execute(send), "ATTACHMENTS_UNVERIFIED");
    assert.equal(events.sends, 0);
    live.content.attachments = savedAttachments;
    live.bccRecipients.push(recipient({address: "unexpected@example.com"}));
    fails(() => execute(send), "DRAFT_CHANGED");
    assert.equal(events.sends, 0);
    live.bccRecipients().pop();
    assert.equal(execute(send).submitted_to_mail, true);
    assert.equal(events.sends, 1);

    // Mail versions whose compose attachment collection is unavailable use a unique saved MIME copy.
    const fallbackFixture = fixtures();
    const originalConstructor = fallbackFixture.mail.OutgoingMessage;
    fallbackFixture.mail.OutgoingMessage = input => {
        const draft = originalConstructor(input);
        draft.id = 0;
        const attach = draft.content.attachments;
        const unreadable = () => null;
        unreadable.push = value => attach.push(value);
        draft.content.attachments = unreadable;
        return draft;
    };
    const fallbackExecute = request => driver.executeRequest(request, fallbackFixture.mail, fallbackFixture.environment);
    const fallback = fallbackExecute(compose);
    assert.equal(fallback.draft_id, 0);
    assert.equal(fallback.attachment_verification, "unavailable");
    assert.equal(fallback.snapshot.attachments, null);
    assert.equal(fallback.saved_draft.message_id, 10000);
    assert.match(fallback.saved_draft.source, /Message-ID:/);
    assert.equal(fallback.saved_draft_verification.asynchronous_save, true);
    const verify = {
        op: "verify-draft", account_id: "a", draft_id: fallback.draft_id,
        expected_snapshot: fallback.snapshot, saved_message_id: fallback.saved_draft.message_id,
        internet_message_id: fallback.saved_draft.internet_message_id
    };
    const verified = fallbackExecute(verify);
    assert.equal(verified.previous_saved_draft.message_id, fallback.saved_draft.message_id);
    assert.notEqual(verified.saved_draft.message_id, fallback.saved_draft.message_id);
    assert.notEqual(verified.saved_draft.internet_message_id, fallback.saved_draft.internet_message_id);
    const verifyCurrent = {...verify, saved_message_id: verified.saved_draft.message_id, internet_message_id: verified.saved_draft.internet_message_id};
    const fallbackSend = {...verifyCurrent, op: "send-draft", from: "me@example.com", expected_saved_source: verified.saved_draft.source};
    const currentStored = fallbackFixture.stored.find(message => message.id() === verified.saved_draft.message_id);
    currentStored.source = currentStored.source() + "\nChanged actual MIME bytes";
    const saveCountBeforeSend = fallbackFixture.events.saves;
    fails(() => fallbackExecute(fallbackSend), "SAVED_DRAFT_CHANGED");
    assert.equal(fallbackFixture.events.sends, 0);
    currentStored.source = verified.saved_draft.source;
    assert.equal(fallbackExecute(fallbackSend).submitted_to_mail, true);
    assert.equal(fallbackFixture.events.sends, 1);
    assert.equal(fallbackFixture.events.saves, saveCountBeforeSend);
    fallbackFixture.events.freezeSave = true;
    fails(() => fallbackExecute(verifyCurrent), "SAVED_DRAFT_UNVERIFIED");
    fallbackFixture.events.freezeSave = false;

    // A second id=0 draft cannot be selected accidentally. The snapshot disambiguates differing drafts.
    const second = fallbackExecute({...compose, subject: "Another role"});
    fails(() => fallbackExecute({op: "inspect-draft", draft_id: 0}), "DRAFT_AMBIGUOUS");
    assert.equal(fallbackExecute({op: "inspect-draft", draft_id: 0, expected_snapshot: second.snapshot}).subject, "Another role");
    const cloned = fallbackFixture.stored[0];
    fallbackFixture.stored.push(cloned);
    fails(() => fallbackExecute(verifyCurrent), "SAVED_DRAFT_AMBIGUOUS");
    assert.equal(fallbackFixture.events.sends, 1);
    fails(() => execute({...send, from: "other@example.com"}), "SENDER_ACCOUNT_MISMATCH");
    assert.equal(events.sends, 1);

    const reply = execute({op: "reply-draft", ...location, message_id: 1, from: "me@example.com", body: "Thanks"});
    assert.equal(events.replies[0].options.replyToAll, false);
    assert.equal(events.replies[0].original, messages[0]);
    assert.deepEqual(reply.snapshot.to, ["reply@example.com"]);
    assert.equal(reply.reply_to_message_id, 1);
    assert.equal(reply.snapshot.body, "Thanks\n\nquoted original");
    assert.equal(events.sends, 1);
    assert.equal(execute({op: "mark-read", ...location, message_id: 1, read_status: true}).read_status, true);
    fails(() => execute({op: "list", ...location, limit: 101}), "INVALID_REQUEST");
    fails(() => execute({...compose, attachments: ["relative.pdf"]}), "INVALID_REQUEST");
    fails(() => execute({...compose, to: ["a@example.com,b@example.com"]}), "INVALID_REQUEST");
    fails(() => execute({op: "list", account_id: "a", mailbox_path: ["Missing"]}), "MAILBOX_NOT_FOUND");
    fails(() => execute({op: "accounts-and-delete"}), "UNSUPPORTED_OPERATION");

    // An attachment failure after Mail creates a draft exposes its ID; it does not send or silently retry.
    const before = mail.outgoingMessages.length;
    assert.throws(() => driver.executeRequest(compose, mail, {
        assertAttachmentFile() {}, path() { throw new Error("Simulated attach failure"); }
    }), error => Number.isInteger(error.mailDetails.partial_draft_id));
    assert.equal(mail.outgoingMessages.length, before + 1);
    assert.equal(events.sends, 1);
    console.log("PASS: all 11 driver operations, pagination, sender/snapshot checks, saved-MIME fallback, changed MIME refusal, id=0 ambiguity, unexpected Bcc, and partial-draft errors. No real Mail operations executed.");
}

run();
