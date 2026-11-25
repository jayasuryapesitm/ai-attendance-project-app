import copy
import unittest

from src.pipelines.exam_marking import (
    calculate_exam_result,
    subquestion_label,
    target_scores_from_result,
    validate_marking_scheme,
    validate_student_answers,
)


def _question(question_id, label, marks, or_group=None, compulsory=True, subs=None):
    return {
        "question_id": question_id,
        "label": label,
        "max_marks": marks,
        "compulsory": compulsory if or_group is None else False,
        "or_group_id": or_group,
        "subquestions": subs or [],
    }


def _three_module_scheme():
    module_one_group = "m1-choice"
    return {
        "alternative_policy": "highest_scoring",
        "modules": [
            {
                "module_id": "module-1",
                "name": "Module 1",
                "max_marks": 20,
                "or_groups": [{
                    "group_id": module_one_group,
                    "label": "A",
                    "allowed_attempts": 1,
                    "policy": "highest_scoring",
                }],
                "questions": [
                    _question(
                        "q1",
                        "Q1",
                        20,
                        module_one_group,
                        subs=[
                            {
                                "subquestion_id": "q1a",
                                "label": "Q1(a)",
                                "max_marks": 10,
                                "checkpoints": ["first concept"],
                            },
                            {
                                "subquestion_id": "q1b",
                                "label": "Q1(b)",
                                "max_marks": 10,
                                "checkpoints": ["second concept"],
                            },
                        ],
                    ),
                    _question(
                        "q2",
                        "Q2",
                        20,
                        module_one_group,
                        subs=[
                            {
                                "subquestion_id": "q2a",
                                "label": "Q2(a)",
                                "max_marks": 10,
                                "checkpoints": ["third concept"],
                            },
                            {
                                "subquestion_id": "q2b",
                                "label": "Q2(b)",
                                "max_marks": 10,
                                "checkpoints": ["fourth concept"],
                            },
                        ],
                    ),
                ],
            },
            {
                "module_id": "module-2",
                "name": "Module 2",
                "max_marks": 20,
                "or_groups": [],
                "questions": [_question("q3", "Q3", 20)],
            },
            {
                "module_id": "module-3",
                "name": "Module 3",
                "max_marks": 10,
                "or_groups": [],
                "questions": [_question("q4", "Q4", 10)],
            },
        ],
    }


def _or_only_scheme():
    scheme = _three_module_scheme()
    return {
        "alternative_policy": "highest_scoring",
        "modules": [scheme["modules"][0]],
    }


def _evaluate_or_attempt(answer_text, awarded_marks):
    scheme = _or_only_scheme()
    answers = validate_student_answers(
        scheme,
        {
            "answers": answer_text,
            "selected_alternatives": {},
        },
    )
    target_scores = {
        target_id: {
            "attempted": bool(answers["answers"].get(target_id, "").strip()),
            "awarded_marks": awarded_marks.get(target_id, 0),
        }
        for target_id in ("q1a", "q1b", "q2a", "q2b")
    }
    return calculate_exam_result(scheme, target_scores)


class ExamMarkingTests(unittest.TestCase):
    def test_validates_three_dynamic_modules_and_subquestion_allocations(self):
        scheme = _three_module_scheme()

        validate_marking_scheme(scheme, 50)

        self.assertEqual(
            [module["max_marks"] for module in scheme["modules"]],
            [20, 20, 10],
        )

    def test_allows_a_different_five_module_scheme_without_shared_state(self):
        first = _three_module_scheme()
        second = {
            "modules": [
                {
                    "module_id": f"second-{index}",
                    "name": f"Section {index}",
                    "max_marks": marks,
                    "or_groups": [],
                    "questions": [
                        _question(f"second-q{index}", f"Q{index}", marks)
                    ],
                }
                for index, marks in enumerate([5, 10, 15, 20, 10], start=1)
            ],
        }

        validate_marking_scheme(second, 60)
        first_snapshot = copy.deepcopy(first)
        second["modules"][0]["max_marks"] = 6
        second["modules"][0]["questions"][0]["max_marks"] = 6

        self.assertEqual(first, first_snapshot)
        self.assertEqual(len(first["modules"]), 3)

    def test_caps_or_alternatives_to_configured_count_and_module_maximum(self):
        scheme = _three_module_scheme()
        scores = {
            "q1a": {"attempted": True, "awarded_marks": 10},
            "q1b": {"attempted": True, "awarded_marks": 10},
            "q2a": {"attempted": True, "awarded_marks": 9},
            "q2b": {"attempted": True, "awarded_marks": 10},
            "q3": {"attempted": True, "awarded_marks": 45},
            "q4": {"attempted": True, "awarded_marks": 10},
        }

        result = calculate_exam_result(scheme, scores)

        self.assertEqual(result["modules"][0]["awarded_marks"], 20)
        self.assertEqual(result["modules"][1]["awarded_marks"], 20)
        self.assertEqual(result["modules"][2]["awarded_marks"], 10)
        self.assertEqual(result["final_marks"], 50)
        self.assertLessEqual(result["modules"][0]["awarded_marks"], 20)
        self.assertEqual(
            [
                question["counted_for_score"]
                for question in result["modules"][0]["questions"]
            ],
            [True, False],
        )

    def test_rejects_subquestion_or_module_allocation_mismatches(self):
        scheme = _three_module_scheme()
        scheme["modules"][0]["questions"][0]["subquestions"][0]["max_marks"] = 9

        with self.assertRaisesRegex(ValueError, "sum of its sub-question marks"):
            validate_marking_scheme(scheme, 50)

        scheme = _three_module_scheme()
        scheme["modules"][0]["max_marks"] = 21
        with self.assertRaisesRegex(ValueError, "can award 20 marks"):
            validate_marking_scheme(scheme, 50)

    def test_or_alternatives_must_have_identical_question_marks(self):
        scheme = _three_module_scheme()
        alternative = scheme["modules"][0]["questions"][1]
        alternative["max_marks"] = 19
        alternative["subquestions"][0]["max_marks"] = 9

        with self.assertRaisesRegex(ValueError, "same maximum marks"):
            validate_marking_scheme(scheme, 50)

    def test_or_alternatives_must_have_identical_subquestion_distribution(self):
        scheme = _three_module_scheme()
        alternative = scheme["modules"][0]["questions"][1]
        alternative["subquestions"][0]["max_marks"] = 9
        alternative["subquestions"][1]["max_marks"] = 11

        with self.assertRaisesRegex(
            ValueError,
            "same sub-question count and marks distribution",
        ):
            validate_marking_scheme(scheme, 50)

    def test_student_validation_and_final_scoring_reject_inconsistent_or_marks(self):
        scheme = _three_module_scheme()
        scheme["modules"][0]["questions"][1]["subquestions"][0][
            "max_marks"
        ] = 9
        scheme["modules"][0]["questions"][1]["subquestions"][1][
            "max_marks"
        ] = 11

        with self.assertRaisesRegex(ValueError, "marks distribution"):
            validate_student_answers(
                scheme,
                {
                    "answers": {"q1a": "Answer", "q1b": "Answer"},
                    "selected_alternatives": {"m1-choice": ["q1"]},
                },
            )
        with self.assertRaisesRegex(ValueError, "marks distribution"):
            calculate_exam_result(scheme, {})

    def test_subquestion_labels_expand_past_single_letter_range(self):
        self.assertEqual(subquestion_label(0), "a")
        self.assertEqual(subquestion_label(25), "z")
        self.assertEqual(subquestion_label(26), "aa")

    def test_or_alternatives_are_scored_independently_for_partial_attempts(self):
        scenarios = [
            (
                "both main sub-questions",
                {"q1a": "answer", "q1b": "answer"},
                {"q1a": 8, "q1b": 9},
                17,
                "q1",
            ),
            (
                "both optional sub-questions",
                {"q2a": "answer", "q2b": "answer"},
                {"q2a": 10, "q2b": 6},
                16,
                "q2",
            ),
            (
                "only Q1(a)",
                {"q1a": "answer"},
                {"q1a": 8},
                8,
                "q1",
            ),
            (
                "only Q2(b)",
                {"q2b": "answer"},
                {"q2b": 9},
                9,
                "q2",
            ),
            (
                "mixed Q1(a) and Q2(b)",
                {"q1a": "answer", "q2b": "answer"},
                {"q1a": 8, "q2b": 9},
                9,
                "q2",
            ),
            (
                "all four sub-questions",
                {
                    "q1a": "answer",
                    "q1b": "answer",
                    "q2a": "answer",
                    "q2b": "answer",
                },
                {"q1a": 8, "q1b": 9, "q2a": 10, "q2b": 6},
                17,
                "q1",
            ),
            (
                "one sub-question from each alternative",
                {"q1b": "answer", "q2a": "answer"},
                {"q1b": 4, "q2a": 9},
                9,
                "q2",
            ),
            (
                "no answers",
                {},
                {},
                0,
                None,
            ),
        ]

        for name, answers, scores, expected, selected in scenarios:
            with self.subTest(name=name):
                result = _evaluate_or_attempt(answers, scores)
                module = result["modules"][0]
                self.assertEqual(result["final_marks"], expected)
                self.assertEqual(module["awarded_marks"], expected)
                self.assertLessEqual(module["awarded_marks"], 20)
                group = module["or_groups"][0]
                self.assertEqual(group["awarded_marks"], expected)
                selected_questions = group["selected_alternatives"]
                self.assertEqual(
                    [question["question_id"] for question in selected_questions],
                    [selected] if selected else [],
                )
                self.assertEqual(
                    {question["question_id"]: question["awarded_marks"]
                     for question in module["questions"]},
                    {
                        "q1": scores.get("q1a", 0) + scores.get("q1b", 0),
                        "q2": scores.get("q2a", 0) + scores.get("q2b", 0),
                    },
                )
                self.assertEqual(
                    {
                        subquestion["target_id"]: subquestion["attempted"]
                        for question in module["questions"]
                        for subquestion in question["subquestions"]
                    },
                    {
                        target_id: bool(answers.get(target_id))
                        for target_id in ("q1a", "q1b", "q2a", "q2b")
                    },
                )
                restored_scores = target_scores_from_result(result)
                self.assertEqual(
                    {
                        target_id: (
                            restored_scores[target_id]["attempted"],
                            restored_scores[target_id]["awarded_marks"],
                        )
                        for target_id in ("q1a", "q1b", "q2a", "q2b")
                    },
                    {
                        target_id: (
                            bool(answers.get(target_id)),
                            scores.get(target_id, 0),
                        )
                        for target_id in ("q1a", "q1b", "q2a", "q2b")
                    },
                )


if __name__ == "__main__":
    unittest.main()
