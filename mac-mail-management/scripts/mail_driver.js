/*
 * mac邮件管理: Apple Mail JXA transport.
 * Usage: osascript -l JavaScript mail_driver.js /absolute/request.json
 * No dynamic source evaluation; all user text arrives as JSON data.
 * The Python wrapper supplies authorization, durable state, and idempotency.
 * This transport must never be invoked directly by an autonomous workflow.
 */
"use strict";

function failure(code, message, details) {
    var error = new Error(message);
    error.mailCode = code;
    if (details !== undefined) error.mailDetails = details;
    throw error;
}

function requireString(value, label, allowEmpty) {
    if (typeof value !== "string" || (!allowEmpty && !value.trim()) || value.indexOf("\u0000") !== -1) {
        failure("INVALID_REQUEST", label + " must be a " + (allowEmpty ? "" : "non-empty ") + "string without NUL characters.");
    }
    return value;
}

function integer(value, label, min, max, defaultValue) {
    if (value === undefined && defaultValue !== undefined) return defaultValue;
    if (typeof value !== "number" || !isFinite(value) || Math.floor(value) !== value || value < min || value > max) {
        failure("INVALID_REQUEST", label + " must be an integer between " + min + " and " + max + ".");
    }
    return value;
}

function flag(value, label, defaultValue) {
    if (value === undefined) return defaultValue;
    if (typeof value !== "boolean") failure("INVALID_REQUEST", label + " must be boolean.");
    return value;
}

function normalizedAddress(value) {
    requireString(value, "email address", false);
    if (/[\r\n]/.test(value)) failure("INVALID_REQUEST", "Email addresses cannot contain line breaks.");
    var trimmed = value.trim();
    var angle = trimmed.match(/^[^<>]*<([^<>]+)>$/);
    var address = angle ? angle[1].trim() : trimmed;
    if (!/^[^\s<>,;@]+@[^\s<>,;@]+\.[^\s<>,;@]+$/.test(address)) {
        failure("INVALID_REQUEST", "Supply one explicit email address per recipient; groups and address lists are unsupported.");
    }
    return address.toLowerCase();
}

function recipientInputs(value, label) {
    if (value === undefined) return [];
    if (!Array.isArray(value) || value.length > 100) failure("INVALID_REQUEST", label + " must be an array of at most 100 recipients.");
    return value.map(function (item) {
        if (typeof item === "string") return {address: normalizedAddress(item)};
        if (!item || typeof item !== "object" || Array.isArray(item)) failure("INVALID_REQUEST", "Invalid " + label + " recipient.");
        var recipient = {address: normalizedAddress(item.address)};
        if (item.name !== undefined) recipient.name = requireString(item.name, "recipient name", true);
        return recipient;
    });
}

function attachmentInputs(value, environment) {
    if (value === undefined) return [];
    if (!Array.isArray(value) || value.length > 30) failure("INVALID_REQUEST", "attachments must contain at most 30 absolute file paths.");
    var seen = {};
    return value.map(function (path) {
        requireString(path, "attachment path", false);
        if (path.charAt(0) !== "/") failure("INVALID_REQUEST", "Attachment paths must be absolute.");
        if (seen[path]) failure("INVALID_REQUEST", "Duplicate attachment path.");
        seen[path] = true;
        if (environment && environment.assertAttachmentFile) environment.assertAttachmentFile(path);
        return path;
    });
}

function mailboxPath(value) {
    if (!Array.isArray(value) || value.length === 0 || value.length > 30) failure("INVALID_REQUEST", "mailbox_path must be an array of 1 to 30 exact mailbox names.");
    return value.map(function (part) { return requireString(part, "mailbox name", false); });
}

function dateText(value) {
    if (value === null || value === undefined) return null;
    var date = value instanceof Date ? value : new Date(value);
    return isNaN(date.getTime()) ? null : date.toISOString();
}

function textValue(value) {
    return value === null || value === undefined ? "" : String(value);
}

function accountInfo(account) {
    return {
        id: textValue(account.id()),
        name: textValue(account.name()),
        email_addresses: account.emailAddresses().map(textValue),
        enabled: Boolean(account.enabled())
    };
}

function findAccount(mail, id) {
    requireString(id, "account_id", false);
    var accounts = mail.accounts();
    var matches = accounts.filter(function (account) { return String(account.id()) === id; });
    if (matches.length !== 1) failure("ACCOUNT_NOT_FOUND", "No unique Mail account has the supplied account_id.");
    return matches[0];
}

function assertSender(account, from) {
    var requested = normalizedAddress(from);
    if (!account.enabled()) failure("ACCOUNT_DISABLED", "The selected Mail account is disabled.");
    var addresses = account.emailAddresses();
    var allowed = addresses.some(function (address) { return normalizedAddress(String(address)) === requested; });
    if (!allowed) failure("SENDER_ACCOUNT_MISMATCH", "from must be one of the selected account's configured email addresses.");
    return requested;
}

function findMailbox(account, requestedPath) {
    var path = mailboxPath(requestedPath);
    var parent = account;
    path.forEach(function (name) {
        var matches = parent.mailboxes().filter(function (mailbox) { return String(mailbox.name()) === name; });
        if (matches.length !== 1) failure("MAILBOX_NOT_FOUND", "No unique mailbox exists at the supplied exact mailbox_path.");
        parent = matches[0];
    });
    return parent;
}

function findMessage(mailbox, messageId) {
    var id = integer(messageId, "message_id", 1, 9007199254740991);
    var message = mailbox.messages.byId(id);
    try {
        if (Number(message.id()) !== id) failure("MESSAGE_NOT_FOUND", "The message is no longer present in this mailbox.");
    } catch (error) {
        if (error.mailCode) throw error;
        // Preserve permission/transport errors; only missing-object errors become not-found.
        if (Number(error.errorNumber) === -1728 || Number(error.number) === -1728) {
            failure("MESSAGE_NOT_FOUND", "The message is no longer present in this mailbox.");
        }
        throw error;
    }
    return message;
}

function messageInfo(message) {
    return {
        message_id: Number(message.id()),
        internet_message_id: textValue(message.messageId()),
        sender: textValue(message.sender()),
        subject: textValue(message.subject()),
        date_received: dateText(message.dateReceived()),
        date_sent: dateText(message.dateSent()),
        read_status: Boolean(message.readStatus()),
        flagged_status: Boolean(message.flaggedStatus()),
        message_size: Number(message.messageSize())
    };
}

function recipients(collection) {
    return collection().map(function (recipient) {
        return {name: textValue(recipient.name()), address: textValue(recipient.address())};
    });
}

function listMailboxes(account) {
    var result = [];
    function visit(parent, path) {
        var children = parent.mailboxes();
        if (path.length >= 30 && children.length) failure("MAILBOX_TREE_LIMIT", "Mailbox nesting exceeds the supported depth of 30.");
        children.forEach(function (mailbox) {
            if (result.length >= 2000) failure("MAILBOX_TREE_LIMIT", "Mailbox tree exceeds the supported maximum of 2000 folders.");
            var childPath = path.concat([String(mailbox.name())]);
            result.push({path: childPath, unread_count: Number(mailbox.unreadCount())});
            visit(mailbox, childPath);
        });
    }
    visit(account, []);
    return {account_id: String(account.id()), mailboxes: result};
}

function listMessages(account, request) {
    var mailbox = findMailbox(account, request.mailbox_path);
    var limit = integer(request.limit, "limit", 1, 100, 25);
    var offset = integer(request.offset, "offset", 0, 9007199254740991, 0);
    var unreadOnly = flag(request.unread_only, "unread_only", false);
    var query = request.query === undefined ? "" : requireString(request.query, "query", true).toLowerCase();
    if (query.length > 500) failure("INVALID_REQUEST", "query must not exceed 500 characters.");
    // length sends a count event; indexing accesses only the bounded native-order window.
    var total = Number(mailbox.messages.length);
    var end = Math.min(total, offset + limit);
    var result = [];
    for (var index = offset; index < end; index += 1) {
        var metadata = messageInfo(mailbox.messages[index]);
        if (unreadOnly && metadata.read_status) continue;
        if (query && (metadata.subject + "\n" + metadata.sender).toLowerCase().indexOf(query) === -1) continue;
        result.push(metadata);
    }
    return {
        account_id: String(account.id()), mailbox_path: request.mailbox_path.slice(),
        messages: result, total_count: total, scanned_count: Math.max(0, end - offset),
        offset: offset, next_offset: end < total ? end : null, has_more: end < total,
        scan_start_inclusive: offset, scan_end_exclusive: Math.max(offset, end),
        scan_limit: limit, order: "mail_native", query_fields: ["subject", "sender"],
        filters_apply_within_scan_window: true,
        snapshot_is_atomic: false
    };
}

function readMessage(account, request) {
    var message = findMessage(findMailbox(account, request.mailbox_path), request.message_id);
    return {
        account_id: String(account.id()), mailbox_path: request.mailbox_path.slice(),
        metadata: messageInfo(message), body: textValue(message.content()),
        to: recipients(message.toRecipients), cc: recipients(message.ccRecipients),
        reply_to: textValue(message.replyTo()),
        attachments: message.mailAttachments().map(function (attachment) {
            return {
                id: textValue(attachment.id()), name: textValue(attachment.name()),
                mime_type: textValue(attachment.mimeType()),
                approximate_size_bytes: Number(attachment.fileSize()),
                downloaded: Boolean(attachment.downloaded())
            };
        })
    };
}

function findDraft(mail, draftId, expectedSnapshot) {
    var id = integer(draftId, "draft_id", 0, 9007199254740991);
    var matches = mail.outgoingMessages().filter(function (message) { return Number(message.id()) === id; });
    if (matches.length > 1 && expectedSnapshot) {
        matches = matches.filter(function (message) {
            return sameComposeFields(inspectOutgoing(message).snapshot, expectedSnapshot, false);
        });
    }
    if (matches.length > 1) failure("DRAFT_AMBIGUOUS", "Several outgoing drafts share this ID and cannot be uniquely matched to the prepared snapshot. No draft was selected.");
    if (matches.length !== 1) failure("DRAFT_NOT_FOUND", "The outgoing draft is not available or cannot be uniquely matched. Its identifier can expire when Mail closes the compose session or restarts.");
    return matches[0];
}

function inspectOutgoing(draft) {
    var inspection = {
        draft_id: Number(draft.id()), from: textValue(draft.sender()),
        to: recipients(draft.toRecipients), cc: recipients(draft.ccRecipients), bcc: recipients(draft.bccRecipients),
        subject: textValue(draft.subject()), body: textValue(draft.content()),
        visible: Boolean(draft.visible()), attachments: null,
        attachment_verification: "unavailable",
        attachment_verification_details: {
            enumeration_supported: false, content_hash_verified: false,
            note: "Verified means attachment paths were completely enumerated. Mail does not expose a verified MIME payload; content has not been re-hashed inside Mail."
        }
    };
    try {
        inspection.attachments = draft.content.attachments().map(function (attachment) {
            var path = String(attachment.fileName());
            if (!path || path.charAt(0) !== "/") failure("ATTACHMENTS_UNVERIFIED", "Mail returned an attachment without an absolute file path.");
            return path;
        });
        inspection.attachment_verification = "verified";
        inspection.attachment_verification_details.enumeration_supported = true;
    } catch (error) {
        // Capability probing is the sole optional property read. Never label an unavailable read successful.
        inspection.attachments = null;
        inspection.attachment_verification_details.error = textValue(error.message || error);
    }
    inspection.snapshot = {
        from: normalizedAddress(inspection.from),
        to: inspection.to.map(function (recipient) { return normalizedAddress(recipient.address); }),
        cc: inspection.cc.map(function (recipient) { return normalizedAddress(recipient.address); }),
        bcc: inspection.bcc.map(function (recipient) { return normalizedAddress(recipient.address); }),
        subject: inspection.subject.replace(/\r\n?/g, "\n"),
        body: inspection.body.replace(/\r\n?/g, "\n"),
        attachments: inspection.attachments
    };
    return inspection;
}

function canonicalSnapshot(snapshot, allowUnknownAttachments) {
    if (!snapshot || typeof snapshot !== "object" || Array.isArray(snapshot)) failure("INVALID_REQUEST", "expected_snapshot must be an object.");
    var normalized = {from: normalizedAddress(snapshot.from)};
    ["to", "cc", "bcc"].forEach(function (type) {
        if (!Array.isArray(snapshot[type])) failure("INVALID_REQUEST", "expected_snapshot." + type + " must be an array of email address strings.");
        normalized[type] = snapshot[type].map(normalizedAddress);
    });
    normalized.subject = requireString(snapshot.subject, "expected_snapshot.subject", true).replace(/\r\n?/g, "\n");
    normalized.body = requireString(snapshot.body, "expected_snapshot.body", true).replace(/\r\n?/g, "\n");
    if (snapshot.attachments === null && allowUnknownAttachments) {
        normalized.attachments = null;
        return normalized;
    }
    if (!Array.isArray(snapshot.attachments)) failure("ATTACHMENTS_UNVERIFIED", "Attachment paths could not be enumerated when this snapshot was prepared.");
    normalized.attachments = snapshot.attachments.map(function (path) {
        requireString(path, "snapshot attachment path", false);
        if (path.charAt(0) !== "/") failure("ATTACHMENTS_UNVERIFIED", "Snapshot attachment paths must be absolute.");
        return path;
    });
    return normalized;
}

function sameComposeFields(left, right, savedRepresentation) {
    var first = canonicalSnapshot(left, true);
    var second = canonicalSnapshot(right, true);
    delete first.attachments;
    delete second.attachments;
    // Recipient order is not semantically meaningful and may differ in the stored copy.
    ["to", "cc", "bcc"].forEach(function (key) {
        first[key].sort();
        second[key].sort();
    });
    if (savedRepresentation) {
        // NSTextStorage includes attachment placeholder characters in some Mail versions.
        first.body = first.body.replace(/\ufffc/g, "").trim();
        second.body = second.body.replace(/\ufffc/g, "").trim();
    }
    return JSON.stringify(first) === JSON.stringify(second);
}

function internetId(value) {
    return textValue(value).trim().replace(/^<|>$/g, "");
}

function savedDraftMessages(mail, accountId, subject) {
    var mailbox = mail.draftsMailbox();
    var messages = mailbox.messages();
    if (messages.length > 5000) failure("DRAFT_SCAN_LIMIT", "The aggregate Drafts mailbox exceeds the bounded limit of 5000 drafts.");
    return messages.filter(function (message) {
        if (subject !== undefined && String(message.subject()) !== subject) return false;
        return String(message.mailbox().account().id()) === accountId;
    });
}

function savedBaseline(mail, accountId, subject) {
    return savedDraftMessages(mail, accountId, subject).map(function (message) { return Number(message.id()); });
}

function savedMessageSnapshot(message) {
    return {
        from: normalizedAddress(textValue(message.sender())),
        to: recipients(message.toRecipients).map(function (recipient) { return normalizedAddress(recipient.address); }),
        cc: recipients(message.ccRecipients).map(function (recipient) { return normalizedAddress(recipient.address); }),
        bcc: recipients(message.bccRecipients).map(function (recipient) { return normalizedAddress(recipient.address); }),
        subject: textValue(message.subject()).replace(/\r\n?/g, "\n"),
        body: textValue(message.content()).replace(/\r\n?/g, "\n"), attachments: null
    };
}

function savedCandidates(mail, accountId, snapshot, locator) {
    return savedDraftMessages(mail, accountId, snapshot.subject).filter(function (message) {
        var id = Number(message.id());
        if (locator.baseline_ids) return locator.baseline_ids.indexOf(id) === -1;
        return id === locator.saved_message_id && internetId(message.messageId()) === internetId(locator.internet_message_id);
    }).filter(function (message) { return sameComposeFields(savedMessageSnapshot(message), snapshot, true); });
}

function missingObjectError(error) {
    return Number(error.errorNumber !== undefined ? error.errorNumber : error.number) === -1728;
}

function savedSource(message) {
    var source = textValue(message.source());
    var mid = internetId(message.messageId());
    if (!source || !mid) failure("SAVED_DRAFT_UNVERIFIED", "The saved draft has no complete MIME source or Internet Message-ID.");
    return {message_id: Number(message.id()), internet_message_id: mid, source: source};
}

function readSavedAnchor(mail, accountId, snapshot, locator) {
    var candidates = savedCandidates(mail, accountId, snapshot, locator);
    if (candidates.length > 1) failure("SAVED_DRAFT_AMBIGUOUS", "The saved draft anchor is not unique; no save or send was attempted.");
    if (candidates.length !== 1) failure("SAVED_DRAFT_UNVERIFIED", "The saved draft anchor is missing or its compose fields changed. Do not replace the anchor by guessing.");
    return savedSource(candidates[0]);
}

function awaitSavedDraft(mail, accountId, snapshot, locator, environment) {
    var clock = environment && environment.now ? environment.now : function () { return Date.now(); };
    var pause = environment && environment.pause ? environment.pause : function (seconds) { delay(seconds); };
    var started = clock();
    var result = null;
    var lastCount = 0;
    // Only a newly appearing saved ID can establish completion of this save attempt.
    // An unchanged older copy is never treated as successful persistence.
    for (var attempt = 0; attempt < 21; attempt += 1) {
        result = null;
        try {
            var candidates = savedCandidates(mail, accountId, snapshot, locator);
            lastCount = candidates.length;
            if (candidates.length === 1) {
                var message = candidates[0];
                var source = textValue(message.source());
                var mid = internetId(message.messageId());
                if (source && mid && sameComposeFields(savedMessageSnapshot(message), snapshot, true)) {
                    result = {message_id: Number(message.id()), internet_message_id: mid, source: source};
                }
            }
        } catch (error) {
            // Mail may replace a stored draft while an Apple Event references its previous object.
            // Only that exact missing-object error is transient; permission and transport errors propagate.
            if (!missingObjectError(error)) throw error;
            lastCount = 0;
        }
        if (clock() - started >= 5000 || attempt === 20) break;
        pause(0.25);
    }
    if (!result) {
        if (lastCount > 1) failure("SAVED_DRAFT_AMBIGUOUS", "Multiple saved drafts match the requested account, identity, and compose fields. No unique MIME source can be verified.");
        failure("SAVED_DRAFT_UNVERIFIED", "No unique complete saved draft matched within the bounded save window. Mail saving is asynchronous; no send command was called.");
    }
    return result;
}

function attachSavedVerification(inspection, saved) {
    inspection.saved_draft = saved;
    inspection.saved_draft_verification = {
        method: "saved_message_mime_source", asynchronous_save: true,
        maximum_wait_ms: 5000, content_hash_verified_by_driver: false,
        note: "Mail provides no save-completion token. The saved draft was uniquely matched after a bounded observation window; the Python wrapper must verify MIME bytes. This does not confirm recipient delivery."
    };
    return inspection;
}

function verifyDraft(mail, account, request, environment) {
    var expected = canonicalSnapshot(request.expected_snapshot, true);
    var locator = {
        saved_message_id: integer(request.saved_message_id, "saved_message_id", 1, 9007199254740991),
        internet_message_id: internetId(requireString(request.internet_message_id, "internet_message_id", false))
    };
    var draft = findDraft(mail, request.draft_id, expected);
    if (!sameComposeFields(inspectOutgoing(draft).snapshot, expected, false)) failure("DRAFT_CHANGED", "The current compose fields differ from the prepared snapshot; no save or send was attempted.");
    assertSender(account, expected.from);
    var previous = readSavedAnchor(mail, String(account.id()), expected, locator);
    var baseline = savedBaseline(mail, String(account.id()), expected.subject);
    mail.save(draft);
    var saved = awaitSavedDraft(mail, String(account.id()), expected, {baseline_ids: baseline}, environment);
    var current = inspectOutgoing(draft);
    if (!sameComposeFields(current.snapshot, expected, false)) failure("DRAFT_CHANGED", "The compose fields changed while the saved draft was being verified; no send was attempted.");
    current.previous_saved_draft = {message_id: previous.message_id, internet_message_id: previous.internet_message_id};
    return attachSavedVerification(current, saved);
}

function addRecipients(mail, draft, type, values) {
    var constructorName = type.charAt(0).toUpperCase() + type.slice(1) + "Recipient";
    var collection = draft[type + "Recipients"];
    values.forEach(function (value) { collection.push(mail[constructorName](value)); });
}

function addAttachments(mail, draft, paths, environment) {
    paths.forEach(function (path) {
        draft.content.attachments.push(mail.Attachment({fileName: environment.path(path)}));
    });
}

function checkedComposeInputs(account, request, environment, reply) {
    var from = assertSender(account, request.from);
    var body = requireString(request.body, "body", true);
    var attachments = attachmentInputs(request.attachments, environment);
    var inputs = {from: from, body: body, attachments: attachments};
    if (!reply) {
        inputs.subject = requireString(request.subject, "subject", true);
        if (/[\r\n]/.test(inputs.subject)) failure("INVALID_REQUEST", "subject cannot contain line breaks.");
        inputs.to = recipientInputs(request.to, "to");
        inputs.cc = recipientInputs(request.cc, "cc");
        inputs.bcc = recipientInputs(request.bcc, "bcc");
        if (inputs.to.length + inputs.cc.length + inputs.bcc.length === 0) failure("INVALID_REQUEST", "At least one explicit recipient is required.");
    }
    return inputs;
}

function createDraft(mail, account, request, environment, reply) {
    var inputs = checkedComposeInputs(account, request, environment, reply);
    // Native reply subjects are locale-dependent, so replies take an ID-only account baseline first.
    var baseline = savedBaseline(mail, String(account.id()), reply ? undefined : inputs.subject);
    var draft;
    var createdId = null;
    try {
        if (reply) {
            var original = findMessage(findMailbox(account, request.mailbox_path), request.message_id);
            draft = mail.reply(original, {openingWindow: false, replyToAll: false});
            createdId = Number(draft.id());
            draft.sender = inputs.from;
            // Changing content on Mail's native reply retains Mail's threading metadata.
            var quotedContent = textValue(draft.content());
            draft.content = inputs.body + (quotedContent ? "\n\n" + quotedContent : "");
        } else {
            draft = mail.OutgoingMessage({sender: inputs.from, subject: inputs.subject, content: inputs.body, visible: false});
            mail.outgoingMessages.push(draft);
            createdId = Number(draft.id());
            addRecipients(mail, draft, "to", inputs.to);
            addRecipients(mail, draft, "cc", inputs.cc);
            addRecipients(mail, draft, "bcc", inputs.bcc);
        }
        addAttachments(mail, draft, inputs.attachments, environment);
        mail.save(draft);
        var inspection = inspectOutgoing(draft);
        if (normalizedAddress(inspection.from) !== inputs.from) {
            failure("SENDER_NOT_APPLIED", "Mail did not preserve the requested sender. The draft was not sent.");
        }
        inspection.account_id = String(account.id());
        inspection.saved = true;
        inspection.submitted_to_mail = false;
        inspection.requested_attachment_paths = inputs.attachments.slice();
        if (reply) inspection.reply_to_message_id = request.message_id;
        if (inspection.attachment_verification !== "verified") {
            attachSavedVerification(inspection, awaitSavedDraft(mail, String(account.id()), inspection.snapshot, {baseline_ids: baseline}, environment));
            if (!sameComposeFields(inspectOutgoing(draft).snapshot, inspection.snapshot, false)) failure("DRAFT_CHANGED", "The compose fields changed during saved-draft verification; no send was attempted.");
        }
        return inspection;
    } catch (error) {
        // A failed mutation may have left a partial draft; expose its ID and do not delete it or retry creation.
        if (createdId !== null) {
            error.mailDetails = {
                partial_draft_id: createdId,
                recovery: "Inspect this outgoing draft before retrying. Creation may have partially completed; no send command was called."
            };
        }
        throw error;
    }
}

function executeRequest(request, mail, environment) {
    if (!request || typeof request !== "object" || Array.isArray(request)) failure("INVALID_REQUEST", "The request must be a JSON object.");
    requireString(request.op, "op", false);
    var operation = request.op;
    if (operation === "accounts") return {accounts: mail.accounts().map(accountInfo)};
    if (operation === "inspect-draft") return inspectOutgoing(findDraft(mail, request.draft_id, request.expected_snapshot));
    if (operation === "verify-draft") return verifyDraft(mail, findAccount(mail, request.account_id), request, environment);
    if (operation === "send-draft") {
        var draft = findDraft(mail, request.draft_id, request.expected_snapshot);
        // The wrapper always supplies these fields; requiring them closes the default-account fallback.
        var sendAccount = findAccount(mail, request.account_id);
        var from = assertSender(sendAccount, request.from);
        if (normalizedAddress(textValue(draft.sender())) !== from) failure("SENDER_ACCOUNT_MISMATCH", "The draft sender changed; no send command was called.");
        var expected = canonicalSnapshot(request.expected_snapshot, true);
        var current = inspectOutgoing(draft);
        if (!sameComposeFields(current.snapshot, expected, false)) failure("DRAFT_CHANGED", "The current draft differs from its prepared snapshot; no send command was called.");
        if (request.expected_saved_source !== undefined) {
            var source = requireString(request.expected_saved_source, "expected_saved_source", false);
            var anchor = {
                saved_message_id: integer(request.saved_message_id, "saved_message_id", 1, 9007199254740991),
                internet_message_id: internetId(requireString(request.internet_message_id, "internet_message_id", false))
            };
            // verify-draft already saved and returned the exact MIME bytes for Python to inspect.
            // A second save would regenerate Message-ID/Date, invalidating that proof.
            var saved = readSavedAnchor(mail, String(sendAccount.id()), expected, anchor);
            if (saved.source !== source) failure("SAVED_DRAFT_CHANGED", "The current saved MIME source differs from the verified source; no send command was called.");
            if (!sameComposeFields(inspectOutgoing(draft).snapshot, expected, false)) failure("DRAFT_CHANGED", "Compose fields changed during the final saved-source check; no send command was called.");
        } else {
            if (current.attachment_verification !== "verified") failure("ATTACHMENTS_UNVERIFIED", "Mail cannot enumerate current attachments and no verified saved MIME source was supplied; no send command was called.");
            if (JSON.stringify(canonicalSnapshot(current.snapshot)) !== JSON.stringify(canonicalSnapshot(expected))) failure("DRAFT_CHANGED", "The current draft differs from its prepared snapshot; no send command was called.");
        }
        var sent = mail.send(draft);
        if (typeof sent !== "boolean") failure("SEND_RESULT_UNKNOWN", "Mail returned an unexpected send result. Do not retry automatically.");
        return {
            draft_id: request.draft_id, account_id: request.account_id,
            submitted_to_mail: sent, delivery_confirmed: false,
            status: sent ? "submitted_to_mail" : "mail_reported_send_failure",
            note: "This result concerns submission to the Mail client. It does not prove delivery to the recipient."
        };
    }
    var supported = ["mailboxes", "list", "read", "check", "draft", "reply-draft", "mark-read"];
    if (supported.indexOf(operation) === -1) failure("UNSUPPORTED_OPERATION", "Unsupported operation: " + operation);
    var account = findAccount(mail, request.account_id);
    if (operation === "mailboxes") return listMailboxes(account);
    if (operation === "list") return listMessages(account, request);
    if (operation === "read") return readMessage(account, request);
    if (operation === "check") {
        if (!account.enabled()) failure("ACCOUNT_DISABLED", "The selected Mail account is disabled.");
        mail.checkForNewMail({for: account});
        return {account_id: request.account_id, check_requested: true, synchronization_complete: false};
    }
    if (operation === "draft" || operation === "reply-draft") return createDraft(mail, account, request, environment, operation === "reply-draft");
    if (operation === "mark-read") {
        var readStatus = flag(request.read_status, "read_status", undefined);
        if (readStatus === undefined) failure("INVALID_REQUEST", "read_status is required.");
        var message = findMessage(findMailbox(account, request.mailbox_path), request.message_id);
        message.readStatus = readStatus;
        var actual = Boolean(message.readStatus());
        if (actual !== readStatus) failure("WRITE_NOT_APPLIED", "Mail did not apply the requested read status.");
        return {account_id: request.account_id, mailbox_path: request.mailbox_path.slice(), message_id: request.message_id, read_status: actual};
    }
}

function errorEnvelope(error) {
    var number = Number(error.errorNumber !== undefined ? error.errorNumber : error.number);
    var code = error.mailCode || (number === -1743 ? "AUTOMATION_PERMISSION_DENIED" : (number === -1712 ? "MAIL_TIMEOUT" : "MAIL_ERROR"));
    var value = {code: code, message: textValue(error.message || error)};
    if (isFinite(number)) value.apple_event_error_number = number;
    if (error.mailDetails !== undefined) value.details = error.mailDetails;
    return {ok: false, error: value};
}

function jxaEnvironment() {
    ObjC.import("Foundation");
    return {
        path: function (path) { return Path(path); },
        now: function () { return Date.now(); },
        pause: function (seconds) { delay(seconds); },
        assertAttachmentFile: function (path) {
            var manager = $.NSFileManager.defaultManager;
            var directory = Ref();
            if (!manager.fileExistsAtPathIsDirectory($(path), directory) || directory[0]) failure("ATTACHMENT_NOT_FOUND", "Attachment must be an existing regular file: " + path);
            var attributes = manager.attributesOfItemAtPathError($(path), null);
            if (!attributes || ObjC.unwrap(attributes.objectForKey($.NSFileType)) !== "NSFileTypeRegular") failure("INVALID_ATTACHMENT", "Attachment must be a regular file: " + path);
            if (!manager.isReadableFileAtPath($(path))) failure("ATTACHMENT_UNREADABLE", "Attachment is not readable: " + path);
        },
        readJSON: function (path) {
            requireString(path, "request path", false);
            if (path.charAt(0) !== "/") failure("INVALID_REQUEST", "Request file path must be absolute.");
            var data = $.NSData.dataWithContentsOfFile($(path));
            if (!data) failure("REQUEST_FILE_UNREADABLE", "Cannot read the JSON request file.");
            if (Number(data.length) > 100 * 1024 * 1024) failure("INVALID_REQUEST", "Bridge request file exceeds 100 MiB.");
            var value = $.NSString.alloc.initWithDataEncoding(data, $.NSUTF8StringEncoding);
            if (!value) failure("INVALID_REQUEST", "Request file must be valid UTF-8.");
            try { return JSON.parse(ObjC.unwrap(value)); }
            catch (error) { failure("INVALID_REQUEST", "Request file does not contain valid JSON."); }
        }
    };
}

function run(argv) {
    try {
        if (!argv || argv.length !== 1) failure("INVALID_REQUEST", "Pass exactly one absolute JSON request file path.");
        var environment = jxaEnvironment();
        var request = environment.readJSON(argv[0]);
        return JSON.stringify({ok: true, result: executeRequest(request, Application("com.apple.mail"), environment)});
    } catch (error) {
        return JSON.stringify(errorEnvelope(error));
    }
}

// Enables tests with injected in-memory Mail objects; importing this module never opens Mail.
if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        executeRequest: executeRequest, errorEnvelope: errorEnvelope,
        normalizedAddress: normalizedAddress, recipientInputs: recipientInputs,
        mailboxPath: mailboxPath, attachmentInputs: attachmentInputs,
        inspectOutgoing: inspectOutgoing, canonicalSnapshot: canonicalSnapshot,
        sameComposeFields: sameComposeFields
    };
}
