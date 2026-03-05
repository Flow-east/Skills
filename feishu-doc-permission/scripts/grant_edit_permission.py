#!/usr/bin/env python3
"""Grant edit permission to a Feishu document collaborator."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://open.feishu.cn/open-apis/drive/v1/permissions/{token}/members/batch_create"


def call_api(doc_token: str, tenant_token: str, doc_type: str, members: list[dict]) -> dict:
    params = urllib.parse.urlencode({"type": doc_type})
    url = BASE_URL.format(token=urllib.parse.quote(doc_token, safe="")) + "?" + params
    payload = json.dumps({"members": members}).encode("utf-8")
    headers = {
        "Content-Type": "application/json;charset=utf-8",
        "Authorization": f"Bearer {tenant_token}"
    }
    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="ignore")
        print(f"Permission grant failed ({exc.code}):", file=sys.stderr)
        print(body, file=sys.stderr)
        raise


def parse_member(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"member must be valid JSON: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Grant Feishu doc edit permissions for one or more collaborators.")
    parser.add_argument("--doc-token", required=True, help="Feishu document token (the part after /docx/).")
    parser.add_argument("--tenant-token", required=True, help="tenant_access_token with docs:permission.member:create scope.")
    parser.add_argument("--doc-type", default="docx", choices=["docx", "doc", "sheet", "folder", "mindnote", "slides", "wiki"], help="Document type for the token.")
    parser.add_argument("--member", type=parse_member, action="append", help="JSON definition of one collaborator, e.g. '{\"member_type\":\"openid\",\"member_id\":\"ou_xxxx\",\"perm\":\"edit\"}'")
    parser.add_argument("--member-id", help="Shortcut for a single collaborator using OpenID + edit.")
    parser.add_argument("--member-type", default="openid")
    parser.add_argument("--perm", default="edit", choices=["view", "edit", "full_access"])
    parser.add_argument("--perm-type", default="container", choices=["container", "single_page"])
    args = parser.parse_args()

    members = args.member or []
    if args.member_id:
        members.append({
            "member_type": args.member_type,
            "member_id": args.member_id,
            "perm": args.perm,
            "perm_type": args.perm_type,
            "type": "user",
        })

    if not members:
        parser.error("At least one collaborator must be provided via --member or --member-id.")

    result = call_api(args.doc_token, args.tenant_token, args.doc_type, members)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
