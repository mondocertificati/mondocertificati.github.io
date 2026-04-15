"""Test per il client Beehiiv."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from delivery.beehiiv import BeehiivClient, CET


class TestBeehiivClient:
    @patch("delivery.beehiiv.get_settings")
    def test_headers_contengono_auth(self, mock_settings):
        mock_settings.return_value = MagicMock(
            beehiiv_api_key="test-key-123",
            beehiiv_publication_id="pub-123",
        )
        client = BeehiivClient()
        assert "Bearer test-key-123" in client.headers["Authorization"]

    @patch("delivery.beehiiv.httpx.Client")
    @patch("delivery.beehiiv.get_settings")
    def test_publish_draft_crea_post(self, mock_settings, mock_httpx_class):
        mock_settings.return_value = MagicMock(
            beehiiv_api_key="key",
            beehiiv_publication_id="pub-123",
            newsletter_name="Mondo Certificati",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"id": "post-abc", "web_url": "https://beehiiv.com/p/abc"}
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_httpx_class.return_value = mock_client

        client = BeehiivClient()
        result = client.publish_draft(html_content="<p>Test</p>", subject="Test Subject")

        assert result["post_id"] == "post-abc"
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["post"]["title"] == "Test Subject"
        assert payload["post"]["status"] == "scheduled"

    def test_next_tuesday_9am_cet(self):
        result = BeehiivClient._next_tuesday_9am_cet()
        # Deve essere un martedi'
        assert result.weekday() == 1  # 0=lunedi, 1=martedi
        assert result.hour == 9
        assert result.minute == 0
        # Deve essere nel futuro o oggi
        now = datetime.now(CET)
        assert result >= now.replace(hour=0, minute=0, second=0, microsecond=0)
