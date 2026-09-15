# Mac Mail Management

**English** | [简体中文](README.zh-CN.md) · [← All Skills](../README.md)

Current release: [v0.1.0](https://github.com/Flow-east/Skills/blob/mac-mail-management-v0.1.0/mac-mail-management/README.md)

Manage accounts already configured in macOS Mail, including QQ Mail and Gmail. The skill's display name is **mac邮件管理**; its directory and invocation name are `mac-mail-management`.

## What it does

- Discover accounts and mailboxes, request a mail check, and browse message metadata with bounded pagination.
- Read messages and attachment metadata; mark messages read or unread when requested.
- Preview locally, save new drafts or native replies, and attach local files such as a résumé.
- Submit authorized drafts through Mail after checking the sender, recipients, contents, and attachments.
- Keep persistent send records to prevent duplicate submissions and stop automatic retries when the outcome is uncertain.
- Guide an agent in configuring scheduled checks and authorized application workflows using its available scheduler.

## Requirements

- A Mac with Apple Mail, Python 3, and the system `osascript` command. No pip or npm dependencies are needed at runtime.
- The intended mailbox must already be configured in Mail and able to synchronize. Mail continues to manage account credentials; the skill does not read passwords or QQ authorization codes.
- The process running the script needs the normal macOS permission to control Mail. The agent's execution sandbox may also require approval for native application access.

The package follows the Agent Skills folder format. Other compatible agents can load it on macOS; `agents/openai.yaml` supplies optional Codex UI metadata. Node.js is only needed for the mocked driver tests.

## Install

Ask a compatible agent:

```text
Install this skill:
https://github.com/Flow-east/Skills/tree/main/mac-mail-management
```

Or, from a local copy of this repository, copy the complete directory into a personal Codex skill directory:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R mac-mail-management "${CODEX_HOME:-$HOME/.codex}/skills/mac-mail-management"
```

## Use

```text
Use $mac-mail-management to summarize unread hiring emails in my QQ inbox.
```

```text
Use mac邮件管理 to draft an application for the recipient I provided and attach my selected résumé.
```

The agent discovers the real account IDs and mailbox paths before operating on messages. Command examples and JSON request formats are in the [operations guide](references/operations.md).

## Sending and scheduled work

Sending requires a user instruction or an applicable previously authorized rule. Existing authorization can cover a batch; it does not require a new confirmation for every email. Installing this skill does not enable automatic sending or create a scheduled task.

The CLI verifies a saved draft before submission and stores its state in `~/Library/Application Support/mac-mail-management`. These private records include recipients and draft contents and must stay outside public repositories. Reuse the same state directory and job key across retries and scheduled runs.

`submitted_to_mail` means Mail accepted the request; it is not proof of delivery. An uncertain result stops automatic retries. Local scheduled work depends on the Mac, Mail, and the scheduler being available; it cannot guarantee execution while the Mac is asleep or shut down.

## Limits and verification

- Incoming attachment downloads, deletion, forwarding, and mailbox moves are not built-in commands in this version.
- Message lists use Mail's native order, which is not guaranteed to be newest first. Filters apply to each scanned page; partial scans must be reported as partial.
- Mail may change saved-draft IDs or expose incomplete attachment information. The script verifies the available attachment paths or the decoded bytes of a uniquely matched saved draft and stops when verification fails. Do not edit the same draft concurrently with sending.
- Live checks covered account/mailbox access and a disposable draft with an attachment. No real email was sent in testing.

From the repository root, run the offline tests:

```bash
python3 -m unittest discover -s mac-mail-management/tests -v
node mac-mail-management/tests/test_driver.js
```

The Python suite covers request validation, draft changes, attachment verification, authorization flags, concurrency, duplicate prevention, and uncertain send outcomes. The Node suite mocks the Mail driver operations; neither suite sends email.

## Detailed guides

- [Agent instructions](SKILL.md)
- [Commands, requests, and troubleshooting](references/operations.md)
- [Scheduled checks and application workflows](references/automation.md)

## License

[MIT](../LICENSE), following the repository license.
