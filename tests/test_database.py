"""Test per il modulo di persistenza su Supabase."""

from unittest.mock import MagicMock, patch

from models import Certificato


class TestDatabase:
    @patch("storage.db.create_client")
    @patch("storage.db.get_settings")
    def test_log_issue(self, mock_settings, mock_create):
        mock_settings.return_value = MagicMock(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
        )
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        mock_result = MagicMock()
        mock_result.data = [{"id": 1, "week_number": 15}]
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_result

        from storage.db import Database

        db = Database()
        certs = [Certificato(isin="IT0005412345", nome="Test")]
        result = db.log_issue(post_id="post-123", certificates=certs)

        assert result["id"] == 1
        call_args = mock_client.table.return_value.insert.call_args[0][0]
        assert call_args["beehiiv_post_id"] == "post-123"
        assert "IT0005412345" in call_args["certificates_featured"]

    @patch("storage.db.create_client")
    @patch("storage.db.get_settings")
    def test_save_certificates_history_vuoto(self, mock_settings, mock_create):
        mock_settings.return_value = MagicMock(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
        )
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        from storage.db import Database

        db = Database()
        assert db.save_certificates_history([]) == 0

    @patch("storage.db.create_client")
    @patch("storage.db.get_settings")
    def test_save_certificates_history(self, mock_settings, mock_create):
        mock_settings.return_value = MagicMock(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
        )
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        mock_result = MagicMock()
        mock_result.data = [{"id": 1}, {"id": 2}]
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_result

        from storage.db import Database

        db = Database()
        certs = [
            Certificato(isin="CERT00000001", nome="A", prezzo_attuale=95.0),
            Certificato(isin="CERT00000002", nome="B", prezzo_attuale=101.0),
        ]
        count = db.save_certificates_history(certs)
        assert count == 2

    @patch("storage.db.create_client")
    @patch("storage.db.get_settings")
    def test_get_latest_issue_vuoto(self, mock_settings, mock_create):
        mock_settings.return_value = MagicMock(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
        )
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        mock_result = MagicMock()
        mock_result.data = []
        mock_client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        from storage.db import Database

        db = Database()
        assert db.get_latest_issue() is None
