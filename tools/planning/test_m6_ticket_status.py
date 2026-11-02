"""Pure lifecycle integrity checks for M6 ticket dependencies."""

import unittest

from tools.planning.validate_m6_tickets import (
    complete_stage_reasons,
    validate_status_dependencies,
)


class TicketStatusTest(unittest.TestCase):
    def test_completed_ticket_cannot_depend_on_unfinished_ticket(self):
        tickets = {
            "M6-T001": {"status": "in_progress", "depends_on": []},
            "M6-T002": {"status": "done", "depends_on": ["M6-T001"]},
        }
        self.assertEqual(
            ["M6-T002: completed_dependency_not_done"],
            validate_status_dependencies(tickets),
        )

    def test_in_progress_ticket_may_depend_on_unfinished_ticket(self):
        tickets = {
            "M6-T001": {"status": "in_progress", "depends_on": []},
            "M6-T002": {"status": "in_progress", "depends_on": ["M6-T001"]},
        }
        self.assertEqual([], validate_status_dependencies(tickets))

    def test_completed_ticket_with_completed_dependency_is_valid(self):
        tickets = {
            "M6-T001": {"status": "done", "depends_on": []},
            "M6-T002": {"status": "done", "depends_on": ["M6-T001"]},
        }
        self.assertEqual([], validate_status_dependencies(tickets))

    def test_complete_stage_is_data_driven_not_permanently_blocked(self):
        self.assertEqual(
            (),
            complete_stage_reasons(
                [
                    {"id": "M6-T001", "status": "done", "evidence": ["e1"]},
                    {"id": "M6-T002", "status": "done", "evidence": ["e2"]},
                ]
            ),
        )
        self.assertEqual(
            ("m6_tickets_not_complete",),
            complete_stage_reasons(
                [
                    {"id": "M6-T001", "status": "done", "evidence": ["e1"]},
                    {"id": "M6-T002", "status": "in_progress", "evidence": []},
                ]
            ),
        )
