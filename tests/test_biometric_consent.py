import base64
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.database.db import record_student_biometric_consent
from src.database.config import _validate_server_side_key


class BiometricConsentTests(unittest.TestCase):
    def test_rejects_anon_jwt_supabase_keys(self):
        payload = base64.urlsafe_b64encode(
            json.dumps({"role": "anon"}).encode("utf-8")
        ).decode("ascii").rstrip("=")

        with self.assertRaisesRegex(RuntimeError, "not a server-side key"):
            _validate_server_side_key(f"header.{payload}.signature")

    def test_accepts_service_role_jwt_supabase_keys(self):
        payload = base64.urlsafe_b64encode(
            json.dumps({"role": "service_role"}).encode("utf-8")
        ).decode("ascii").rstrip("=")

        _validate_server_side_key(f"header.{payload}.signature")

    def test_no_updated_student_row_returns_actionable_runtime_error(self):
        with patch("src.database.db.supabase") as supabase:
            query = supabase.table.return_value.update.return_value.eq.return_value.select.return_value
            query.execute.return_value = SimpleNamespace(data=[])
            with self.assertRaisesRegex(RuntimeError, "server-side"):
                record_student_biometric_consent(42, "face")
