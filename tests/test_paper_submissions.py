import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch


class PaperSubmissionTests(unittest.TestCase):
    def test_insert_rejects_a_second_submission_for_the_same_exam(self):
        subject_table = Mock()
        subject_query = subject_table.select.return_value
        subject_query.eq.return_value = subject_query
        subject_query.execute.return_value = SimpleNamespace(
            data=[{"student_id": 17}]
        )

        submissions_table = Mock()
        submissions_query = submissions_table.select.return_value
        submissions_query.eq.return_value = submissions_query
        submissions_query.execute.return_value = SimpleNamespace(
            data=[{"submission_id": 301}]
        )

        with (
            patch(
                "src.database.db._get_owned_exam",
                return_value={"subject_id": 8},
            ),
            patch("src.database.db.supabase") as supabase,
        ):
            supabase.table.side_effect = [subject_table, submissions_table]

            from src.database.db import insert_paper_submission

            with self.assertRaisesRegex(
                ValueError,
                "already has a submission",
            ):
                insert_paper_submission(4, 2, 17, "[]")

        submissions_table.insert.assert_not_called()

    def test_insert_allows_a_students_first_submission(self):
        subject_table = Mock()
        subject_query = subject_table.select.return_value
        subject_query.eq.return_value = subject_query
        subject_query.execute.return_value = SimpleNamespace(
            data=[{"student_id": 17}]
        )

        submissions_table = Mock()
        submissions_query = submissions_table.select.return_value
        submissions_query.eq.return_value = submissions_query
        submissions_query.execute.return_value = SimpleNamespace(data=[])
        inserted = {"submission_id": 301, "student_id": 17}
        submissions_table.insert.return_value.select.return_value.execute.return_value = (
            SimpleNamespace(data=[inserted])
        )

        with (
            patch(
                "src.database.db._get_owned_exam",
                return_value={"subject_id": 8},
            ),
            patch("src.database.db.supabase") as supabase,
        ):
            supabase.table.side_effect = [
                subject_table,
                submissions_table,
                submissions_table,
            ]

            from src.database.db import insert_paper_submission

            result = insert_paper_submission(4, 2, 17, "[]")

        self.assertEqual(result, inserted)
        submissions_table.insert.assert_called_once()


if __name__ == "__main__":
    unittest.main()
