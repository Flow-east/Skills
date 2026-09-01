# Feishu Document Permission Guard

**English** | [简体中文](README.zh-CN.md) · [← All Skills](../README.md)

Current release: [v0.1.0](https://github.com/Flow-east/Skills/blob/feishu-doc-permission-v0.1.0/feishu-doc-permission/README.md) · Released: 2026-09-01

`feishu-doc-permission` adds two safeguards to automated Feishu document workflows: validate the intended content before a write, then grant the intended collaborators access after a document is created.

The skill provides an agent workflow and three lightweight Python helpers. Your Feishu tool, API client, or automation still performs the actual document creation or update.

## When to use it

- An automation creates or updates Feishu documents and should reject empty payloads before sending them.
- Newly created documents should be editable by specific teammates without a separate manual sharing step.
- A wrapper around Feishu document APIs needs consistent content and permission checks.

It is not intended for manual sharing in the Feishu UI, non-Feishu files, application setup, collaborator discovery, or full permission lifecycle management such as listing and revoking access.

## Capabilities and boundaries

- **Content preflight:** checks inline text or a UTF-8 file after trimming surrounding whitespace. It can enforce a minimum length, but it does not judge factual accuracy, usefulness, or semantic quality.
- **Tenant token retrieval:** exchanges an internal Feishu app ID and secret for a `tenant_access_token`. It can write the response to a cache file, but it does not read or refresh that cache automatically.
- **Permission grant:** grants `view`, `edit`, or `full_access` to supplied collaborators; `edit` is the default. Supported token types are `docx`, `doc`, `sheet`, `folder`, `mindnote`, `slides`, and `wiki`.
- **Feishu prerequisites:** the caller must already know the document token and collaborator ID. The Feishu app must have the required permission scope and access to the target document.
- **Pipeline responsibility:** validate the same payload that will be written. The helpers cannot verify that another tool later sent unchanged content.

App credentials and tenant tokens are secrets. The token helper prints the token to standard output, so avoid shared terminal logs and protect any cache file it creates.

## Install

From a compatible Skills CLI:

```bash
npx skills add Flow-east/Skills --skill feishu-doc-permission
```

Or copy the entire `feishu-doc-permission` directory into your agent's skills directory, preserving `SKILL.md` and `scripts/` together. For a personal Codex installation:

```bash
cp -R feishu-doc-permission "${CODEX_HOME:-$HOME/.codex}/skills/feishu-doc-permission"
```

## Quick invocation

```text
Use $feishu-doc-permission to validate this Feishu document before writing it, then grant edit access to the collaborator with OpenID ou_xxxx after creation.
```

Provide the final content or its file path, the document type, and the collaborator identifier. The workflow will also need authorized Feishu app credentials or an existing tenant token at the permission step.

## Scripts and inputs

Run the helpers with Python 3; they use only the Python standard library.

| Script | Main inputs | Purpose |
| --- | --- | --- |
| [`scripts/check_content.py`](scripts/check_content.py) | One of `--content` or `--file`; optional `--min-length` | Stops the workflow when trimmed content is shorter than the required length. |
| [`scripts/get_tenant_token.py`](scripts/get_tenant_token.py) | `--app-id`, `--app-secret`; optional `--cache`, `--print-only` | Requests a Feishu tenant token and optionally writes it to JSON for the surrounding workflow. |
| [`scripts/grant_edit_permission.py`](scripts/grant_edit_permission.py) | `--doc-token`, `--tenant-token`, plus `--member-id` or one or more `--member` JSON objects | Calls Feishu's batch member API to grant the requested permission. |

The intended order is:

```text
validate content → create or update with your Feishu tool → capture document token
                 → obtain tenant token → grant collaborator permission
```

If Feishu returns `403` or `1063002`, first confirm that the app is attached to the document and has the `docs:permission.member:create` scope.
