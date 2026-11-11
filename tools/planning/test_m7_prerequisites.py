"""Pure completion rules for choosing a real first-provider implementation."""

import unittest

from tools.planning.validate_m7_tickets import prerequisite_errors


class M7PrerequisiteTests(unittest.TestCase):
    def test_storage_cannot_close_before_any_provider_is_done(self):
        tickets = {
            "storage": {
                "status": "done",
                "depends_on": [],
                "depends_on_any": [["a", "b"]],
            },
            "a": {"status": "planned"},
            "b": {"status": "in_progress"},
        }
        self.assertIn(
            "storage: provider_prerequisite_unfinished",
            prerequisite_errors("storage", tickets["storage"], tickets),
        )

    def test_one_completed_provider_suffices_without_waiting_for_all(self):
        tickets = {
            "storage": {
                "status": "done",
                "depends_on": [],
                "depends_on_any": [["a", "b"]],
            },
            "a": {"status": "blocked"},
            "b": {"status": "done"},
        }
        self.assertEqual(
            [], prerequisite_errors("storage", tickets["storage"], tickets)
        )

    def test_unknown_alternative_cannot_hide_in_a_satisfied_group(self):
        tickets = {
            "storage": {
                "status": "done",
                "depends_on": [],
                "depends_on_any": [["a", "unknown"]],
            },
            "a": {"status": "done"},
        }
        self.assertIn(
            "storage: invalid_alternative_dependency",
            prerequisite_errors("storage", tickets["storage"], tickets),
        )

    def test_planned_work_can_retain_unfinished_prerequisites(self):
        tickets = {
            "storage": {
                "status": "planned",
                "depends_on": ["core"],
                "depends_on_any": [["a"]],
            },
            "core": {"status": "planned"},
            "a": {"status": "blocked"},
        }
        self.assertEqual(
            [], prerequisite_errors("storage", tickets["storage"], tickets)
        )
