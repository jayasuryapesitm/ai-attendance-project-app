import unittest
from io import BytesIO
from unittest.mock import Mock, patch

import pymupdf
from PIL import Image

from src.pipelines.paper_pipeline import (
    MAX_IMAGE_WIDTH,
    _call_vision_json,
    compress_uploaded_pages,
    create_blueprint_rubric,
    evaluate_answer_sheet,
    evaluate_configured_exam,
    evaluate_exam_pages,
    extract_exam_rubric,
    exam_storage_prefix,
    upload_page_images,
)


class UploadedFile:
    def __init__(self, name, content_type, content):
        self.name = name
        self.type = content_type
        self._content = content

    def getvalue(self):
        return self._content


class PaperPipelineTests(unittest.TestCase):
    def test_evaluate_exam_pages_uses_configured_scheme_aggregation(self):
        exam = {"marking_scheme": {"modules": [{"module_id": "module-1"}]}}
        scores = {"target-1": {"awarded_marks": 4.0}}
        expected_result = {"final_marks": 4.0, "modules": []}
        with (
            patch(
                "src.pipelines.paper_pipeline.evaluate_configured_exam",
                return_value=scores,
            ) as evaluate,
            patch(
                "src.pipelines.paper_pipeline.calculate_exam_result",
                return_value=expected_result,
            ) as aggregate,
        ):
            result = evaluate_exam_pages(exam, [b"page"])

        self.assertEqual(result, (4.0, expected_result))
        evaluate.assert_called_once_with(
            exam["marking_scheme"],
            page_images=[b"page"],
        )
        aggregate.assert_called_once_with(exam["marking_scheme"], scores)

    def test_evaluate_exam_pages_sums_legacy_rubric_scores(self):
        exam = {"blueprint_rubric": {"questions": []}}
        question_scores = [
            {"awarded_marks": 2.5},
            {"awarded_marks": 3.0},
        ]
        with patch(
            "src.pipelines.paper_pipeline.evaluate_answer_sheet",
            return_value=question_scores,
        ):
            result = evaluate_exam_pages(exam, [b"page"])

        self.assertEqual(result, (5.5, question_scores))

    def test_retired_configured_model_falls_back_to_supported_gemini_model(self):
        client = Mock()
        client.models.generate_content.side_effect = [
            RuntimeError(
                "404 NOT_FOUND: gemini-2.5-flash-lite is no longer available"
            ),
            Mock(text='{"evaluated": true}'),
        ]
        with (
            patch(
                "src.pipelines.paper_pipeline.get_vision_api_key",
                return_value="test-key",
            ),
            patch(
                "src.pipelines.paper_pipeline.get_vision_model",
                return_value="gemini-2.5-flash-lite",
            ),
            patch("google.genai.Client", return_value=client),
        ):
            result = _call_vision_json("Evaluate this answer.", [])

        self.assertEqual(result, {"evaluated": True})
        self.assertEqual(
            [
                call.kwargs["model"]
                for call in client.models.generate_content.call_args_list
            ],
            ["gemini-2.5-flash-lite", "gemini-3.5-flash-lite"],
        )

    def test_invalid_credentials_do_not_get_hidden_by_model_fallback(self):
        client = Mock()
        client.models.generate_content.side_effect = RuntimeError(
            "401 UNAUTHENTICATED: invalid API key"
        )
        with (
            patch(
                "src.pipelines.paper_pipeline.get_vision_api_key",
                return_value="invalid-key",
            ),
            patch(
                "src.pipelines.paper_pipeline.get_vision_model",
                return_value="gemini-2.5-flash-lite",
            ),
            patch("google.genai.Client", return_value=client),
        ):
            with self.assertRaisesRegex(RuntimeError, "invalid API key"):
                _call_vision_json("Evaluate this answer.", [])

        client.models.generate_content.assert_called_once()

    def test_create_blueprint_rubric_accepts_a_top_level_questions_list(self):
        response = [
            {
                "question_no": "1",
                "max_marks": 50,
                "checkpoints": ["correct concept"],
            }
        ]
        with patch(
            "src.pipelines.paper_pipeline._call_vision_json",
            return_value=response,
        ):
            rubric = create_blueprint_rubric([b"page"], 50)

        self.assertEqual(rubric["questions"][0]["question_no"], "1")
        self.assertEqual(rubric["questions"][0]["max_marks"], 50)

    def test_extract_exam_rubric_compares_documents_and_keeps_manual_rubric(self):
        scheme = {
            "modules": [
                {
                    "module_id": "module-1",
                    "name": "Module 1",
                    "max_marks": 5,
                    "or_groups": [],
                    "questions": [
                        {
                            "question_id": "question-1",
                            "label": "Q1",
                            "max_marks": 5,
                            "compulsory": True,
                            "or_group_id": None,
                            "rubric_notes": "",
                            "subquestions": [
                                {
                                    "subquestion_id": "question-1a",
                                    "label": "Q1(a)",
                                    "max_marks": 5,
                                    "rubric_notes": "Manual checkpoint",
                                    "checkpoints": [],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        response = {
            "items": [
                {
                    "id": "question-1a",
                    "checkpoints": [],
                    "blueprint_marks": 5,
                    "question_paper_marks": 4,
                }
            ],
            "modules": [
                {
                    "id": "module-1",
                    "blueprint_marks": 5,
                    "question_paper_marks": 5,
                }
            ],
            "unconfigured_questions": [],
            "unconfigured_modules": [],
        }
        with patch(
            "src.pipelines.paper_pipeline._call_vision_json",
            return_value=response,
        ):
            updated_scheme, report = extract_exam_rubric(
                [b"blueprint"],
                [b"question paper"],
                scheme,
            )

        self.assertEqual(
            updated_scheme["modules"][0]["questions"][0]["subquestions"][0][
                "checkpoints"
            ],
            ["Manual checkpoint"],
        )
        self.assertEqual(len(report["mark_mismatches"]), 1)
        self.assertEqual(report["mark_mismatches"][0]["question_no"], "Q1(a)")

    def test_configured_exam_evaluates_mixed_or_subquestions_independently(self):
        scheme = {
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
                                    "checkpoints": ["main concept"],
                                },
                                {
                                    "subquestion_id": "q1b",
                                    "label": "Q1(b)",
                                    "max_marks": 10,
                                    "checkpoints": ["second concept"],
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
                                    "checkpoints": ["third concept"],
                                },
                                {
                                    "subquestion_id": "q2b",
                                    "label": "Q2(b)",
                                    "max_marks": 10,
                                    "checkpoints": ["fourth concept"],
                                },
                            ],
                        },
                    ],
                }
            ]
        }
        response = {
            "items": [
                {
                    "id": "q1a",
                    "attempted": False,
                    "semantic_match_pct": 80,
                    "feedback": "Good main answer.",
                },
                {
                    "id": "q2b",
                    "attempted": False,
                    "semantic_match_pct": 90,
                    "feedback": "Good alternative answer.",
                },
            ]
        }
        with patch(
            "src.pipelines.paper_pipeline._call_vision_json",
            return_value=response,
        ) as evaluate:
            scores = evaluate_configured_exam(
                scheme,
                text_answers={
                    "q1a": "Main answer",
                    "q1b": "",
                    "q2a": "",
                    "q2b": "Alternative answer",
                },
            )

        prompt = evaluate.call_args.args[0]
        self.assertIn('"id": "q1a"', prompt)
        self.assertIn('"id": "q2b"', prompt)
        self.assertNotIn('"id": "q1b"', prompt)
        self.assertNotIn('"id": "q2a"', prompt)
        self.assertEqual(
            [scores[target]["attempted"] for target in ("q1a", "q1b", "q2a", "q2b")],
            [True, False, False, True],
        )
        self.assertEqual(scores["q1a"]["awarded_marks"], 8)
        self.assertEqual(scores["q2b"]["awarded_marks"], 9)

    def test_exam_document_paths_are_scoped_by_exam_and_type(self):
        exam_a_blueprint = exam_storage_prefix(101, "blueprints")
        exam_b_blueprint = exam_storage_prefix(102, "blueprints")
        exam_a_question_paper = exam_storage_prefix(101, "question-papers")

        self.assertNotEqual(exam_a_blueprint, exam_b_blueprint)
        self.assertNotEqual(exam_a_blueprint, exam_a_question_paper)
        with self.assertRaises(ValueError):
            exam_storage_prefix(101, "shared")

    def test_uploads_have_unique_names_and_never_overwrite(self):
        storage = Mock()
        with (
            patch(
                "src.pipelines.paper_pipeline.supabase.storage.from_",
                return_value=storage,
            ),
            patch(
                "src.pipelines.paper_pipeline.uuid.uuid4",
                side_effect=[
                    Mock(hex="first"),
                    Mock(hex="second"),
                ],
            ),
        ):
            paths = upload_page_images(
                [b"page one", b"page two"],
                exam_storage_prefix(101, "blueprints"),
            )

        self.assertEqual(len(set(paths)), 2)
        self.assertTrue(all(path.startswith("exams/101/blueprints/") for path in paths))
        self.assertTrue(
            all(
                call.kwargs["file_options"]["upsert"] == "false"
                for call in storage.upload.call_args_list
            )
        )

    def test_partial_upload_failure_removes_already_uploaded_pages(self):
        storage = Mock()
        storage.upload.side_effect = [None, RuntimeError("storage unavailable")]
        with (
            patch(
                "src.pipelines.paper_pipeline.supabase.storage.from_",
                return_value=storage,
            ),
            patch(
                "src.pipelines.paper_pipeline.uuid.uuid4",
                side_effect=[
                    Mock(hex="first"),
                    Mock(hex="second"),
                ],
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "storage unavailable"):
                upload_page_images(
                    [b"page one", b"page two"],
                    exam_storage_prefix(101, "blueprints"),
                )

        storage.remove.assert_called_once_with([
            "exams/101/blueprints/first-page-001.jpg"
        ])

    def test_compresses_images_to_jpeg_at_or_below_max_width(self):
        source = BytesIO()
        Image.new("RGB", (1600, 900), "white").save(source, format="PNG")

        pages = compress_uploaded_pages(
            UploadedFile("answers.png", "image/png", source.getvalue())
        )

        self.assertEqual(len(pages), 1)
        with Image.open(BytesIO(pages[0])) as compressed:
            self.assertEqual(compressed.format, "JPEG")
            self.assertLessEqual(compressed.width, MAX_IMAGE_WIDTH)

    def test_converts_each_pdf_page_to_a_separate_jpeg(self):
        document = pymupdf.open()
        document.new_page().insert_text((72, 72), "First page")
        document.new_page().insert_text((72, 72), "Second page")
        pdf_bytes = document.tobytes()
        document.close()

        pages = compress_uploaded_pages(
            UploadedFile("answers.pdf", "application/pdf", pdf_bytes)
        )

        self.assertEqual(len(pages), 2)
        self.assertTrue(all(page.startswith(b"\xff\xd8") for page in pages))

    def test_awards_full_marks_at_conceptual_threshold_and_proportional_below(self):
        rubric = {
            "questions": [
                {"question_no": "1", "max_marks": 10, "checkpoints": ["concept"]},
                {"question_no": "2", "max_marks": 20, "checkpoints": ["concept"]},
            ]
        }
        response = {
            "questions": [
                {
                    "question_no": "1",
                    "semantic_match_pct": 85,
                    "awarded_marks": 0,
                    "feedback": "Concept conveyed in different words.",
                },
                {
                    "question_no": "2",
                    "semantic_match_pct": 60,
                    "awarded_marks": 20,
                    "feedback": "One key concept was missed.",
                },
            ]
        }
        with patch(
            "src.pipelines.paper_pipeline._call_vision_json",
            return_value=response,
        ):
            scores = evaluate_answer_sheet([b"page"], rubric)

        self.assertEqual([score["awarded_marks"] for score in scores], [10, 12])
        self.assertEqual(scores[0]["feedback"], "Concept conveyed in different words.")


if __name__ == "__main__":
    unittest.main()
