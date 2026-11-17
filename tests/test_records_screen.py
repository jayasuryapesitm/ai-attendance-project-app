import unittest

from src.screens.records_screen import _record_row


class AttendanceRecordFormattingTests(unittest.TestCase):
    def test_legacy_record_does_not_invent_verification_details(self):
        row = _record_row(
            {
                "timestamp": "2026-10-12T09:30:00Z",
                "is_present": True,
                "subjects": {"name": "Algorithms", "subject_code": "CS 301"},
                "students": {"name": "A Student", "student_id": 42},
            }
        )

        self.assertEqual(row["Verification Mode"], "Attendance record")
        self.assertEqual(row["Confidence Score"], "—")
        self.assertEqual(row["Status"], "Present")

    def test_face_distance_is_not_displayed_as_a_confidence_percentage(self):
        row = _record_row(
            {
                "timestamp": "2026-10-12T09:30:00Z",
                "is_present": True,
                "verification_method": "face",
                "verification_score": 0.31,
            }
        )

        self.assertEqual(row["Confidence Score"], "0.310 distance")
        self.assertIsNone(row["Confidence Value"])

    def test_voice_similarity_is_rendered_as_a_percentage(self):
        row = _record_row(
            {
                "timestamp": "2026-10-12T09:30:00Z",
                "is_present": True,
                "verification_method": "voice",
                "verification_score": 0.92,
            }
        )

        self.assertEqual(row["Confidence Score"], "92.0%")
        self.assertEqual(row["Confidence Value"], 0.92)


if __name__ == "__main__":
    unittest.main()
