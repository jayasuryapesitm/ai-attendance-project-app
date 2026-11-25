import unittest
from unittest.mock import patch

import numpy as np

from src.pipelines import face_pipeline
from src.pipelines.face_pipeline import get_trained_model
from src.pipelines.face_matching import match_face_embeddings


class MatchFaceEmbeddingsTests(unittest.TestCase):
    def setUp(self):
        self.model_data = {
            'embeddings': np.array([
                [0.0, 0.0],
                [1.0, 1.0],
                [2.0, 2.0],
            ]),
            'student_ids': [10, 20, 30],
        }

    def test_matches_only_students_enrolled_in_the_selected_subject(self):
        detected, matched_count = match_face_embeddings(
            [np.array([0.0, 0.0]), np.array([1.0, 1.0])],
            self.model_data,
            candidate_student_ids=[20],
        )

        self.assertEqual(detected, {20: True})
        self.assertEqual(matched_count, 1)

    def test_matches_multiple_faces_and_counts_each_observation(self):
        detected, matched_count = match_face_embeddings(
            [np.array([0.0, 0.0]), np.array([1.0, 1.0])],
            self.model_data,
            candidate_student_ids=[10, 20],
        )

        self.assertEqual(detected, {10: True, 20: True})
        self.assertEqual(matched_count, 2)

    def test_leaves_faces_unmatched_when_no_enrolled_profile_matches(self):
        detected, matched_count = match_face_embeddings(
            [np.array([8.0, 8.0])],
            self.model_data,
            candidate_student_ids=[10, 20],
        )

        self.assertEqual(detected, {})
        self.assertEqual(matched_count, 0)

    def test_rejects_the_nearest_profile_when_its_distance_exceeds_strict_limit(self):
        detected, matched_count = match_face_embeddings(
            [np.array([0.46, 0.0])],
            {
                'embeddings': np.array([[0.0, 0.0]]),
                'student_ids': [10],
            },
        )

        self.assertEqual(detected, {})
        self.assertEqual(matched_count, 0)

    def test_rejects_ambiguous_nearest_and_second_best_profiles(self):
        with self.assertLogs('src.pipelines.face_matching', level='INFO') as logs:
            detected, matched_count = match_face_embeddings(
                [np.array([0.03, 0.0])],
                {
                    'embeddings': np.array([[0.0, 0.0], [0.06, 0.0]]),
                    'student_ids': [10, 20],
                },
            )

        self.assertEqual(detected, {})
        self.assertEqual(matched_count, 0)
        self.assertIn('best_student_id=10', logs.output[0])
        self.assertIn('second_student_id=20', logs.output[0])
        self.assertIn('best_distance=0.030000', logs.output[0])
        self.assertIn('ambiguous_best_and_second_match', logs.output[0])

    def test_accepts_a_confident_match_with_a_clear_margin(self):
        detected, matched_count = match_face_embeddings(
            [np.array([0.02, 0.0])],
            {
                'embeddings': np.array([[0.0, 0.0], [0.2, 0.0]]),
                'student_ids': [10, 20],
            },
        )

        self.assertEqual(detected, {10: True})
        self.assertEqual(matched_count, 1)

    def test_accepts_a_single_profile_at_the_inclusive_distance_limit(self):
        detected, matched_count = match_face_embeddings(
            [np.array([0.45, 0.0])],
            {
                'embeddings': np.array([[0.0, 0.0]]),
                'student_ids': [10],
            },
        )

        self.assertEqual(detected, {10: True})
        self.assertEqual(matched_count, 1)

    def test_identifies_the_student_associated_with_the_matched_profile(self):
        student_b = {'student_id': 20, 'name': 'Student B'}
        model_data = {
            'embeddings': np.array([[0.0, 0.0], [0.4, 0.0]]),
            'student_ids': [10, 20],
            'students_by_id': {
                10: {'student_id': 10, 'name': 'Student A'},
                20: student_b,
            },
        }

        with (
            patch.object(
                face_pipeline,
                'get_face_embeddings',
                return_value=[np.array([0.4, 0.0])],
            ),
            patch.object(face_pipeline, 'get_trained_model', return_value=model_data),
        ):
            student, face_count = face_pipeline.identify_student(np.zeros((1, 1, 3)))

        self.assertEqual(face_count, 1)
        self.assertEqual(student, student_b)

    def test_unknown_face_is_unmatched_for_attendance(self):
        model_data = {
            'embeddings': np.array([[0.0, 0.0]]),
            'student_ids': [20],
        }

        with (
            patch.object(
                face_pipeline,
                'get_face_embeddings',
                return_value=[np.array([0.46, 0.0])],
            ),
            patch.object(face_pipeline, 'get_trained_model', return_value=model_data),
        ):
            detected, face_count, unmatched = face_pipeline.predict_attendance(
                np.zeros((1, 1, 3)),
                candidate_student_ids=[20],
            )

        self.assertEqual(detected, {})
        self.assertEqual(face_count, 1)
        self.assertEqual(unmatched, 1)

    def test_unknown_face_does_not_receive_a_student_identity(self):
        model_data = {
            'embeddings': np.array([[0.0, 0.0]]),
            'student_ids': [20],
            'students_by_id': {
                20: {'student_id': 20, 'name': 'Student B'},
            },
        }

        with (
            patch.object(
                face_pipeline,
                'get_face_embeddings',
                return_value=[np.array([0.46, 0.0])],
            ),
            patch.object(face_pipeline, 'get_trained_model', return_value=model_data),
        ):
            student, face_count = face_pipeline.identify_student(np.zeros((1, 1, 3)))

        self.assertEqual(face_count, 1)
        self.assertIsNone(student)

    def test_skips_invalid_profiles_without_breaking_student_id_mapping(self):
        valid_embedding = np.zeros(128, dtype=np.float64).tolist()
        students = [
            {
                'student_id': 20,
                'name': 'Student B',
                'face_embedding': valid_embedding,
            },
            {
                'student_id': 30,
                'name': 'Invalid shape',
                'face_embedding': [0.0, 1.0],
            },
            {
                'student_id': 40,
                'name': 'Non-finite',
                'face_embedding': [float('nan')] * 128,
            },
        ]

        get_trained_model.clear()
        try:
            with patch.object(face_pipeline, 'get_all_students', return_value=students):
                model_data = get_trained_model()
        finally:
            get_trained_model.clear()

        self.assertEqual(model_data['student_ids'], [20])
        self.assertEqual(model_data['students_by_id'][20]['name'], 'Student B')
