#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "live-selling-script" / "fixtures"
SCRIPT = ROOT / "live-selling-script" / "scripts" / "lint_script.py"
SPEC = importlib.util.spec_from_file_location("lint_script", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class LintScriptTests(unittest.TestCase):
    def test_risky_script_flags_core_risks_and_skips_banned_examples(self) -> None:
        text = (FIXTURES / "risky-script.md").read_text(encoding="utf-8")
        findings = MODULE.collect_findings(text)
        codes = {item.code for item in findings}

        self.assertIn("ABSOLUTE_PROMISE", codes)
        self.assertIn("RESULT_CLAIM", codes)
        self.assertIn("SCARCITY", codes)
        self.assertIn("NUMERIC_OUTCOME", codes)
        self.assertIn("PRICE_ANCHOR", codes)
        self.assertIn("PLACEHOLDER", codes)
        self.assertIn("COMMAND_HOOK", codes)
        self.assertTrue(any(item.match == "适合所有人" for item in findings))
        self.assertFalse(any(item.match == "一键爆款" for item in findings))
        self.assertFalse(any(item.match == "全网最低" for item in findings))

    def test_boundary_language_is_downgraded_to_review(self) -> None:
        text = (FIXTURES / "boundary-script.md").read_text(encoding="utf-8")
        findings = MODULE.collect_findings(text)

        self.assertTrue(findings)
        self.assertTrue(all(item.severity == "REVIEW" for item in findings))


if __name__ == "__main__":
    unittest.main()
