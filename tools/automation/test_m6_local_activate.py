"""Pure policy checks for the constrained M6 dashboard transition."""

import unittest
from pathlib import Path

from tools.automation.implementations.auto_m6_local_activate import (
    build_override,
    clean_status,
    inactive_start_permitted,
    rollback_permitted,
    safe_cgroup,
    same_identity,
)


class LocalActivationPolicyTest(unittest.TestCase):
    def test_override_targets_only_selected_checkout(self):
        self.assertEqual(
            "[Service]\nWorkingDirectory=/work/agentmonitor\n"
            "Environment=PYTHONPATH=/work/agentmonitor/backend/src\n",
            build_override(Path("/work/agentmonitor")),
        )

    def test_override_rejects_unit_injection(self):
        with self.assertRaises(ValueError):
            build_override(Path("/work/bad\nunit"))

    def test_cgroup_rejects_any_unclassified_child(self):
        self.assertTrue(safe_cgroup(123, frozenset({123})))
        self.assertFalse(safe_cgroup(123, frozenset({123, 456})))
        self.assertFalse(safe_cgroup(123, frozenset()))
        self.assertFalse(safe_cgroup(1, frozenset({1})))

    def test_only_explicit_tool_symlinks_may_be_untracked(self):
        self.assertTrue(clean_status(("?? backend/.venv", "?? frontend/node_modules")))
        self.assertFalse(clean_status((" M backend/src/file.py",)))
        self.assertFalse(clean_status(("?? unrelated",)))

    def test_rollback_never_unlinks_a_different_file(self):
        self.assertTrue(same_identity((10, 20), (10, 20)))
        self.assertFalse(same_identity((10, 20), (10, 21)))
        self.assertFalse(same_identity(None, (10, 20)))

    def test_rollback_restart_rejects_busy_changed_or_unknown_candidate(self):
        identity = (123, "start", "/unit")
        self.assertTrue(rollback_permitted(identity, identity, frozenset({123}), False))
        self.assertFalse(
            rollback_permitted(identity, identity, frozenset({123, 456}), False)
        )
        self.assertFalse(
            rollback_permitted(
                identity, (124, "other", "/unit"), frozenset({124}), False
            )
        )
        self.assertFalse(rollback_permitted(None, identity, frozenset({123}), False))
        self.assertFalse(rollback_permitted(identity, identity, frozenset({123}), True))

    def test_inactive_rollback_start_requires_terminal_empty_unit(self):
        self.assertTrue(inactive_start_permitted("failed", 0, frozenset(), False))
        self.assertTrue(inactive_start_permitted("inactive", 0, frozenset(), False))
        self.assertFalse(inactive_start_permitted("activating", 0, frozenset(), False))
        self.assertFalse(inactive_start_permitted("failed", 9, frozenset(), False))
        self.assertFalse(inactive_start_permitted("failed", 0, frozenset({9}), False))
        self.assertFalse(inactive_start_permitted("failed", 0, frozenset(), True))
