"""Focused safety checks for the local inventory command."""

import re
import subprocess
import sys
import unittest
from pathlib import Path

from tools.discovery.m6_local_inventory import NoRedirect, read_json


class LocalInventoryPolicyTest(unittest.TestCase):
    def test_unapproved_source_is_rejected_before_io(self):
        with self.assertRaisesRegex(ValueError, "source_not_allowed"):
            read_json("/api/generate")

    def test_redirect_does_not_authorize_another_target(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.com"))


class LocalInventoryLiveTest(unittest.TestCase):
    def test_canonical_inventory_matches_real_stable_local_source(self):
        before = (len(read_json("/api/tags")["models"]), len(read_json("/api/ps")["models"]))
        root = Path(__file__).resolve().parents[2]
        run = subprocess.run(
            [sys.executable, "tools/automation/run.py", "AUTO-M6-LOCAL-INVENTORY"],
            cwd=root, capture_output=True, text=True, timeout=15, check=False,
        )
        after = (len(read_json("/api/tags")["models"]), len(read_json("/api/ps")["models"]))
        self.assertEqual(before, after, "local_model_state_changed_during_test")
        self.assertEqual(0, run.returncode, "local_inventory_command_failed")
        match = re.search(r"daemon ([0-9]+\.[0-9]+\.[0-9]+); installed ([0-9]+); loaded ([0-9]+)", run.stdout)
        self.assertIsNotNone(match, "local_inventory_output_invalid")
        self.assertEqual(before, (int(match.group(2)), int(match.group(3))))
        self.assertIn("Not a capability-admission or milestone-completion result.", run.stdout)
