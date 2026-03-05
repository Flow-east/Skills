#!/usr/bin/env python3
"""Validate that the Feishu doc payload contains meaningful content."""

import argparse
import pathlib
import sys


def read_file(path: str) -> str:
    return pathlib.Path(path).read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ensure Feishu document text is not empty.")
    parser.add_argument("--content", help="Inline content to validate.")
    parser.add_argument("--file", help="Path to a file that contains document content.")
    parser.add_argument("--min-length", type=int, default=1, help="Minimum number of characters after stripping whitespace.")
    args = parser.parse_args()

    if not args.content and not args.file:
        parser.error("either --content or --file must be provided")

    raw = args.content or read_file(args.file)
    text = raw.strip()

    if len(text) < args.min_length:
        print("ERROR: document content is empty or below min-length", file=sys.stderr)
        raise SystemExit(1)

    print("Content validation passed (length={} after strip).".format(len(text)))


if __name__ == "__main__":
    main()
