import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import bcrypt

from src.database.mentor_db import (
    _get_current_accepted_mentor_email,
    accept_mentor_assignment_request,
    calculate_attendance,
    create_mentor,
    get_assigned_mentees,
    get_pending_assignment_requests,
    get_teacher_assignment_requests,
    end_mentor_assignment,
    reject_mentor_assignment_request,
    request_students_for_mentor,
)
from src.screens.mentor_screen import _format_acceptance_error, mentor_screen


class MentorAttendanceThresholdTests(unittest.TestCase):
    def attendance(self, present, held):
        logs = [
            {"is_present": index < present}
            for index in range(held)
        ]
        return calculate_attendance(logs)[2]

    def test_attendance_thresholds(self):
        cases = [
            (90, 100, 90),
            (80, 100, 80),
            (75, 100, 75),
            (7499, 10000, 74.99),
            (60, 100, 60),
            (0, 100, 0),
        ]
        for present, held, expected in cases:
            with self.subTest(present=present, held=held):
                if held == 10000:
                    actual = calculate_attendance(
                        [{"is_present": index < present} for index in range(held)]
                    )[2]
                else:
                    actual = self.attendance(present, held)
                self.assertAlmostEqual(actual, expected)

    def test_exact_75_is_not_below(self):
        _, _, percentage = calculate_attendance(
            [{"is_present": True}] * 3 + [{"is_present": False}]
        )
        self.assertEqual(percentage, 75)
        self.assertFalse(percentage < 75)

    def test_empty_attendance_is_zero(self):
        held, attended, percentage = calculate_attendance([])
        self.assertEqual((held, attended, percentage), (0, 0, 0))


class MentorAccountTests(unittest.TestCase):
    @patch("src.database.mentor_db.supabase")
    def test_create_mentor_normalizes_email_and_hashes_password(self, supabase):
        table = supabase.table.return_value
        table.select.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.execute.return_value = SimpleNamespace(data=[])
        insert = Mock()
        insert.execute.return_value = SimpleNamespace(data=[{"id": 7}])
        table.insert.return_value = insert

        result = create_mentor(
            "Vijay Kumar",
            "VIJAY@example.com",
            "",
            "Computer Science",
            "CSE",
            "",
            "secure-password",
        )

        payload = table.insert.call_args.args[0]
        self.assertEqual(result["id"], 7)
        self.assertEqual(payload["email"], "vijay@example.com")
        self.assertTrue(
            bcrypt.checkpw(
                b"secure-password",
                payload["password_hash"].encode(),
            )
        )

    @patch("src.database.mentor_db.supabase")
    def test_create_mentor_rejects_duplicate_email(self, supabase):
        table = supabase.table.return_value
        table.select.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.execute.return_value = SimpleNamespace(data=[{"id": 3}])

        with self.assertRaisesRegex(ValueError, "already exists"):
            create_mentor(
                "Vijay Kumar",
                "vijay@example.com",
                "",
                "Computer Science",
                "CSE",
                "",
                "secure-password",
            )
        table.insert.assert_not_called()


class MentorAssignmentTests(unittest.TestCase):
    @patch("src.database.mentor_db.supabase")
    def test_teacher_assignment_creates_unique_requests_with_teacher_id(self, supabase):
        response = Mock()
        response.execute.return_value = SimpleNamespace(data=2)
        supabase.rpc.return_value = response

        created = request_students_for_mentor([10, 11, 10], 4, 8)

        self.assertEqual(created, 2)
        supabase.rpc.assert_called_once_with(
            "create_mentor_assignment_requests",
            {"p_student_ids": [10, 11], "p_mentor_id": 4, "p_teacher_id": 8},
        )

    @patch("src.database.mentor_db.supabase")
    def test_assignment_request_requires_students_and_teacher(self, supabase):
        with self.assertRaisesRegex(ValueError, "at least one student"):
            request_students_for_mentor([], 4, 8)
        with self.assertRaisesRegex(ValueError, "teacher"):
            request_students_for_mentor([10], 4, None)
        supabase.rpc.assert_not_called()

    @patch("src.database.mentor_db.supabase")
    def test_accept_request_sends_request_id_and_logged_in_mentor_id(self, supabase):
        response = Mock()
        response.execute.return_value = SimpleNamespace(data=1)
        supabase.rpc.return_value = response

        accepted = accept_mentor_assignment_request(4, 21)

        self.assertEqual(accepted, 1)
        supabase.rpc.assert_called_once_with(
            "accept_mentor_assignment_request",
            {"p_mentor_id": 4, "p_request_id": 21},
        )

    @patch("src.database.mentor_db.supabase")
    def test_reject_request_sends_request_id_and_reason(self, supabase):
        response = Mock()
        response.execute.return_value = SimpleNamespace(data=1)
        supabase.rpc.return_value = response

        rejected = reject_mentor_assignment_request(4, 21, "Not my department")

        self.assertEqual(rejected, 1)
        supabase.rpc.assert_called_once_with(
            "reject_mentor_assignment_request",
            {
                "p_mentor_id": 4,
                "p_request_id": 21,
                "p_rejection_reason": "Not my department",
            },
        )

    @patch("src.database.mentor_db.supabase")
    def test_pending_requests_are_scoped_to_mentor_and_pending_status(self, supabase):
        table = supabase.table.return_value
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.execute.return_value = SimpleNamespace(data=[{
            "id": 21,
            "status": "pending",
            "students": {"student_id": 10, "name": "Student A"},
            "teachers": {"name": "Teacher A"},
        }])

        requests = get_pending_assignment_requests(4)

        self.assertEqual(requests[0]["student"]["name"], "Student A")
        self.assertEqual(requests[0]["teacher"]["name"], "Teacher A")
        self.assertEqual(table.eq.call_args_list, [
            unittest.mock.call("mentor_id", 4),
            unittest.mock.call("status", "pending"),
        ])
        supabase.rpc.assert_not_called()

    @patch("src.database.mentor_db.supabase")
    def test_teacher_history_is_scoped_to_initiating_teacher(self, supabase):
        table = supabase.table.return_value
        table.select.return_value = table
        table.eq.return_value = table
        table.order.return_value = table
        table.execute.return_value = SimpleNamespace(data=[{
            "id": 21,
            "status": "rejected",
            "students": {"name": "Student A"},
            "mentors": {"full_name": "Mentor A"},
        }])

        requests = get_teacher_assignment_requests(8)

        self.assertEqual(requests[0]["status"], "rejected")
        self.assertEqual(requests[0]["student"]["name"], "Student A")
        self.assertEqual(requests[0]["mentor"]["full_name"], "Mentor A")
        table.eq.assert_called_once_with("assigned_by_teacher_id", 8)

    @patch("src.database.mentor_db.supabase")
    def test_ending_assignment_is_scoped_to_teacher_student_and_mentor(self, supabase):
        response = Mock()
        response.execute.return_value = SimpleNamespace(data=1)
        supabase.rpc.return_value = response

        ended = end_mentor_assignment(8, 10, 4)

        self.assertEqual(ended, 1)
        supabase.rpc.assert_called_once_with(
            "end_mentor_assignment",
            {"p_teacher_id": 8, "p_student_id": 10, "p_mentor_id": 4},
        )

    @patch("src.database.mentor_db.supabase")
    def test_my_mentees_query_includes_only_accepted_relationships(self, supabase):
        table = supabase.table.return_value
        table.select.return_value = table
        table.eq.return_value = table
        table.execute.side_effect = [
            SimpleNamespace(data=[{
                "student_id": 10,
                "accepted_at": "2026-11-25T10:00:00Z",
                "students": {"student_id": 10, "name": "Student A"},
            }]),
            SimpleNamespace(data=[{"is_present": True}]),
        ]

        mentees = get_assigned_mentees(4)

        self.assertEqual(mentees[0]["name"], "Student A")
        self.assertEqual(mentees[0]["_accepted_at"], "2026-11-25T10:00:00Z")
        self.assertIn(unittest.mock.call("status", "accepted"), table.eq.call_args_list)
        self.assertIn(unittest.mock.call("is_active", True), table.eq.call_args_list)

    @patch("src.database.mentor_db.supabase")
    def test_email_recipient_requires_current_accepted_assignment(self, supabase):
        table = supabase.table.return_value
        table.select.return_value = table
        table.eq.return_value = table
        table.limit.return_value = table
        table.execute.side_effect = [
            SimpleNamespace(data=[{"mentors": {"email": "mentor@example.com"}}]),
            SimpleNamespace(data=[]),
        ]

        self.assertEqual(
            _get_current_accepted_mentor_email(10, 4),
            "mentor@example.com",
        )
        self.assertIsNone(_get_current_accepted_mentor_email(10, 4))
        self.assertIn(unittest.mock.call("status", "accepted"), table.eq.call_args_list)


class MentorPortalRoutingTests(unittest.TestCase):
    def test_duplicate_acceptance_error_explains_required_migration(self):
        message = _format_acceptance_error(
            "duplicate key value violates unique constraint "
            '"mentor_mentees_assignment_request_idx"'
        )

        self.assertIn("latest sql/mentor_mentee.sql", message)
        self.assertIn("still pending", message)

    @patch("src.screens.mentor_screen.st")
    @patch("src.screens.mentor_screen.mentor_dashboard")
    @patch("src.screens.mentor_screen.mentor_login_view")
    def test_teacher_session_does_not_open_assignment_page_in_mentor_portal(
        self,
        mentor_login,
        mentor_dashboard,
        streamlit,
    ):
        streamlit.session_state = {"teacher_data": {"name": "Teacher"}}

        mentor_screen()

        mentor_dashboard.assert_not_called()
        mentor_login.assert_called_once_with()

    @patch("src.screens.mentor_screen.st")
    @patch("src.screens.mentor_screen.mentor_dashboard")
    @patch("src.screens.mentor_screen.mentor_login_view")
    def test_mentor_session_opens_acceptance_dashboard(
        self,
        mentor_login,
        mentor_dashboard,
        streamlit,
    ):
        streamlit.session_state = {"mentor_data": {"full_name": "Mentor"}}

        mentor_screen()

        mentor_dashboard.assert_called_once_with()
        mentor_login.assert_not_called()


if __name__ == "__main__":
    unittest.main()
