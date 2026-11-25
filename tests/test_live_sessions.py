import unittest
from unittest.mock import MagicMock, patch

from postgrest.exceptions import APIError


class LiveCampusSessionCountTests(unittest.TestCase):
    def test_returns_count_from_supabase_exact_count(self):
        with patch("src.database.db.supabase") as mock_supabase:
            mock_query = MagicMock()
            mock_supabase.table.return_value.select.return_value.is_.return_value.gt.return_value = mock_query

            mock_response = MagicMock()
            mock_response.count = 7
            mock_response.data = [{"session_id": 1}]
            mock_query.execute.return_value = mock_response

            from src.database.db import get_live_campus_session_count

            count = get_live_campus_session_count()

            mock_supabase.table.assert_called_with("class_sessions")
            self.assertEqual(count, 7)

    def test_falls_back_to_data_length_when_count_is_none(self):
        with patch("src.database.db.supabase") as mock_supabase:
            mock_query = MagicMock()
            mock_supabase.table.return_value.select.return_value.is_.return_value.gt.return_value = mock_query

            mock_response = MagicMock()
            mock_response.count = None
            mock_response.data = [{"session_id": 1}, {"session_id": 2}]
            mock_query.execute.return_value = mock_response

            from src.database.db import get_live_campus_session_count

            count = get_live_campus_session_count()

            self.assertEqual(count, 2)

    def test_filters_by_teacher_id_when_provided(self):
        with patch("src.database.db.supabase") as mock_supabase:
            mock_base_query = MagicMock()
            mock_filtered_query = MagicMock()
            mock_supabase.table.return_value.select.return_value.is_.return_value.gt.return_value = mock_base_query
            mock_base_query.eq.return_value = mock_filtered_query

            mock_response = MagicMock()
            mock_response.count = 3
            mock_filtered_query.execute.return_value = mock_response

            from src.database.db import get_live_campus_session_count

            count = get_live_campus_session_count(teacher_id=42)

            mock_base_query.eq.assert_called_once_with("teacher_id", 42)
            self.assertEqual(count, 3)

    def test_returns_zero_on_database_error(self):
        with patch("src.database.db.supabase") as mock_supabase:
            mock_query = MagicMock()
            mock_supabase.table.return_value.select.return_value.is_.return_value.gt.return_value = mock_query
            mock_query.execute.side_effect = Exception("Database network error")

            from src.database.db import get_live_campus_session_count

            count = get_live_campus_session_count()

            self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
