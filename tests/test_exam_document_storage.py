import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.database import db
from src.pipelines.exam_marking import calculate_exam_result


class TableQuery:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *_columns):
        return self

    def range(self, *_bounds):
        return self

    def eq(self, *_filters):
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows)


class UpdateQuery:
    def __init__(self):
        self.filters = []
        self.updates = None

    def update(self, updates):
        self.updates = updates
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def select(self, *_columns):
        return self

    def execute(self):
        return SimpleNamespace(data=[{"exam_id": 102, **self.updates}])


class ExamDocumentStorageTests(unittest.TestCase):
    def test_removal_preserves_files_referenced_by_other_exams(self):
        fake_supabase = SimpleNamespace(
            table=lambda name: TableQuery(
                [
                    {
                        "blueprint_path": json.dumps(["shared.jpg"]),
                        "question_paper_path": None,
                    }
                ]
                if name == "exam_papers"
                else [{"sheet_path": json.dumps(["other-submission.jpg"])}]
            )
        )
        with (
            patch.object(db, "supabase", fake_supabase),
            patch(
                "src.pipelines.paper_pipeline.remove_stored_pages"
            ) as remove_files,
        ):
            db.remove_unreferenced_exam_files([
                "shared.jpg",
                "other-submission.jpg",
                "exam-only.jpg",
            ])

        remove_files.assert_called_once_with(["exam-only.jpg"])

    def test_removal_does_not_call_storage_for_shared_files(self):
        fake_supabase = SimpleNamespace(
            table=lambda _name: TableQuery([
                {
                    "blueprint_path": json.dumps(["still-used.jpg"]),
                    "question_paper_path": None,
                }
            ])
        )
        with (
            patch.object(db, "supabase", fake_supabase),
            patch(
                "src.pipelines.paper_pipeline.remove_stored_pages"
            ) as remove_files,
        ):
            db.remove_unreferenced_exam_files(["still-used.jpg"])

        remove_files.assert_not_called()

    def test_document_update_targets_only_the_selected_exam(self):
        query = UpdateQuery()
        fake_supabase = SimpleNamespace(table=lambda _name: query)
        with (
            patch.object(db, "supabase", fake_supabase),
            patch.object(
                db,
                "_get_owned_exam",
                return_value={
                    "exam_id": 102,
                    "blueprint_path": '["exam-102-blueprint.jpg"]',
                    "question_paper_path": '["exam-102-question.jpg"]',
                },
            ) as get_owned_exam,
        ):
            updated = db.update_exam_documents(
                102,
                7,
                question_paper_path='["replacement.jpg"]',
            )

        get_owned_exam.assert_called_once_with(102, 7)
        self.assertEqual(query.filters, [("exam_id", 102), ("teacher_id", 7)])
        self.assertEqual(
            query.updates,
            {"question_paper_path": '["replacement.jpg"]'},
        )
        self.assertEqual(updated["exam_id"], 102)

    def test_marking_scheme_update_targets_only_the_selected_exam(self):
        query = UpdateQuery()
        marking_scheme = {
            "modules": [{"module_id": "module-1"}],
        }
        fake_supabase = SimpleNamespace(
            table=lambda name: (
                TableQuery([]) if name == "paper_submissions" else query
            )
        )
        with (
            patch.object(db, "supabase", fake_supabase),
            patch.object(
                db,
                "_get_owned_exam",
                return_value={"exam_id": 102},
            ) as get_owned_exam,
            patch(
                "src.pipelines.exam_marking.validate_marking_scheme"
            ) as validate_scheme,
        ):
            updated = db.update_exam_marking_scheme(
                102,
                7,
                marking_scheme,
                50,
                {"questions": []},
            )

        get_owned_exam.assert_called_once_with(102, 7)
        validate_scheme.assert_called_once_with(marking_scheme, 50)
        self.assertEqual(query.filters, [("exam_id", 102), ("teacher_id", 7)])
        self.assertEqual(
            query.updates,
            {
                "marking_scheme": marking_scheme,
                "blueprint_rubric": {"questions": []},
                "max_marks": 50,
            },
        )
        self.assertEqual(updated["exam_id"], 102)

    def test_verified_exam_storage_keeps_every_or_subquestion_and_selected_score(self):
        marking_scheme = {
            "modules": [
                {
                    "module_id": "module-1",
                    "name": "Module 1",
                    "max_marks": 20,
                    "or_groups": [{
                        "group_id": "choice",
                        "label": "A",
                        "allowed_attempts": 1,
                    }],
                    "questions": [
                        {
                            "question_id": "q1",
                            "label": "Q1",
                            "max_marks": 20,
                            "or_group_id": "choice",
                            "subquestions": [
                                {
                                    "subquestion_id": "q1a",
                                    "label": "Q1(a)",
                                    "max_marks": 10,
                                },
                                {
                                    "subquestion_id": "q1b",
                                    "label": "Q1(b)",
                                    "max_marks": 10,
                                },
                            ],
                        },
                        {
                            "question_id": "q2",
                            "label": "Q2",
                            "max_marks": 20,
                            "or_group_id": "choice",
                            "subquestions": [
                                {
                                    "subquestion_id": "q2a",
                                    "label": "Q2(a)",
                                    "max_marks": 10,
                                },
                                {
                                    "subquestion_id": "q2b",
                                    "label": "Q2(b)",
                                    "max_marks": 10,
                                },
                            ],
                        },
                    ],
                }
            ]
        }
        evaluated = calculate_exam_result(
            marking_scheme,
            {
                "q1a": {"attempted": True, "awarded_marks": 8},
                "q1b": {"attempted": False, "awarded_marks": 0},
                "q2a": {"attempted": False, "awarded_marks": 0},
                "q2b": {"attempted": True, "awarded_marks": 9},
            },
        )
        query = UpdateQuery()
        fake_supabase = SimpleNamespace(table=lambda _name: query)
        with (
            patch.object(db, "supabase", fake_supabase),
            patch.object(
                db,
                "_get_owned_exam",
                return_value={
                    "exam_id": 102,
                    "max_marks": 20,
                    "marking_scheme": marking_scheme,
                },
            ),
        ):
            db.save_teacher_verified_marks(
                501,
                102,
                7,
                9,
                evaluated,
            )

        stored_details = query.updates["evaluation_details"]
        stored_module = stored_details["modules"][0]
        self.assertEqual(query.updates["final_marks"], 9)
        self.assertEqual(
            stored_module["or_groups"][0]["selected_alternatives"][0][
                "question_id"
            ],
            "q2",
        )
        self.assertEqual(
            {
                subquestion["target_id"]: (
                    subquestion["attempted"],
                    subquestion["awarded_marks"],
                )
                for question in stored_module["questions"]
                for subquestion in question["subquestions"]
            },
            {
                "q1a": (True, 8),
                "q1b": (False, 0),
                "q2a": (False, 0),
                "q2b": (True, 9),
            },
        )


if __name__ == "__main__":
    unittest.main()
