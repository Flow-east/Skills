---
name: feishu-doc-permission
description: Ensure every Feishu cloud document creation or edit has non-empty content and that newly created documents immediately grant collaborators edit access. Trigger this skill whenever you work with feishu_doc scripts, APIs, or CLIs that write documents or share them with teammates.
---

# Feishu Document Permission Guard

## Overview
- **Goal 1: Content guard.** Every `feishu_doc` creation/update must include non-empty text that meets the configured minimum length; invalid payloads should be rejected before the request runs.
- **Goal 2: Permission guard.** Once a document is created, the right collaborators (usually the human requester) should instantly receive `edit` access.
- **Resources:** `scripts/check_content.py`, `scripts/get_tenant_token.py`, `scripts/grant_edit_permission.py`.

## When to Use This Skill
Apply this skill when:
- You are creating or editing any Feishu doc (docx, doc, sheet, slides, mindnote) via automation.
- You want to ensure the document payload is non-empty and meets a minimum length before writing it to Feishu.
- You need to provision collaborators immediately after creation without manual sharing steps.
- You are writing scripts or skills that wrap `feishu_doc` calls and want to enforce safe defaults.

## Workflow
1. **Pre-flight validation (create/edit)**
   - Build the Markdown/HTML you plan to send to `feishu_doc` (create or update). Make sure the final text you passed to `check_content.py` is also the text you send in `feishu_doc(action="create")` (not just an empty title), or immediately follow the create call with a complete `append`/`update` payload.
   - Invoke `scripts/check_content.py` with either `--content` or `--file`. Example:
     ```bash
     ./scripts/check_content.py --file ./draft.md
     ```
     The script raises a `SystemExit` if the stripped text is shorter than `--min-length`, so you can abort before contacting Feishu. It does not judge factual accuracy, usefulness, or semantic quality.
   - Only call `feishu_doc` after `check_content.py` succeeds. Treat the script as a lint step for every doc mutation.

2. **Post-creation permission step**
   - After `feishu_doc(action="create", doc_token=...)` returns, capture the new doc token (the trailing ID in the share URL).
   - Ensure you have a fresh `tenant_access_token`. If you do not, run:
     ```bash
     ./scripts/get_tenant_token.py --app-id CLI_APP_ID --app-secret CLI_SECRET
     ```
     Optionally add `--cache ~/.cache/feishu-tenant.json` to write the token and expiry for your surrounding workflow. This helper does not read or refresh that cache automatically.
   - Grant edit rights for the intended collaborator:
     ```bash
     ./scripts/grant_edit_permission.py --doc-token NEW_TOKEN \
       --tenant-token $FEISHU_TENANT_TOKEN \
      --member-id ou_YOUR_MEMBER_ID
    ```
    That helper calls `drive/v1/permissions/<token>/members/batch_create` and prints the API response.

3. **Error handling**
   - If `grant_edit_permission.py` returns a 403/1063002, verify the application has been added via the document’s **··· → 更多 → 添加文档应用** menu and that the app scopes include `docs:permission.member:create`.
   - If the tenant token fetch fails, double-check the App ID/secret pair, network access, and Feishu console approvals. The script prints the Feishu error payload to help debugging.

## Best Practices
- Always treat `scripts/check_content.py` as part of your document pipeline safeguards (pre-commit for documents).
- If the surrounding automation reuses a `tenant_access_token`, use `--cache` to write the token and implement cache reading and expiry handling in that surrounding workflow.
- Ensure the payload you send to `feishu_doc(action="create")` already contains the textual blocks verified by `check_content.py`. If the API response only contains a title, immediately append the remaining sections before granting permissions.
- When working with multiple collaborators, repeat `--member` once per collaborator and pass one JSON object to each occurrence; do not pass a JSON array.
- Document the flow in your automation’s README so future teammates know to run these helpers.
