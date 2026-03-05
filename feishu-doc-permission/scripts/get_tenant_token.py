#!/usr/bin/env python3
"""Fetch a Feishu tenant_access_token and optionally cache it."""

import argparse
import json
import pathlib
import sys
import time
import urllib.request
import urllib.error

API_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"


def fetch_token(app_id: str, app_secret: str) -> dict:
    payload = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
    request = urllib.request.Request(API_URL, data=payload, headers={"Content-Type": "application/json;charset=utf-8"})
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        print(f"Failed to fetch token: {exc.code} {exc.reason}", file=sys.stderr)
        print(exc.read().decode(), file=sys.stderr)
        raise SystemExit(1)
    return json.loads(body)


def save_cache(path: pathlib.Path, token_data: dict) -> None:
    path.write_text(json.dumps({"token": token_data["tenant_access_token"], "expire": time.time() + token_data.get("expire", 0)}), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Get a Feishu tenant_access_token.")
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--app-secret", required=True)
    parser.add_argument("--cache", help="Path to write token cache (JSON).")
    parser.add_argument("--print-only", action="store_true", help="Only print the token string")
    args = parser.parse_args()

    data = fetch_token(args.app_id, args.app_secret)
    if data.get("code") != 0:
        print(f"Feishu returned error: {data.get('msg')}", file=sys.stderr)
        raise SystemExit(1)

    token = data["tenant_access_token"]
    print(token)
    if args.cache:
        save_cache(pathlib.Path(args.cache), data)
        print(f"Cached token to {args.cache}")

    if not args.print_only:
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
