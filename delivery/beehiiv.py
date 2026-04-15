"""Client Beehiiv API v2 per la pubblicazione della newsletter.

Crea un post in bozza, lo programma per martedi' 9:00 CET e logga il risultato.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

BEEHIIV_API_BASE = "https://api.beehiiv.com/v2"
CET = timezone(timedelta(hours=1))


class BeehiivClient:
    """Gestisce la pubblicazione su Beehiiv."""

    def __init__(self) -> None:
        s = get_settings()
        self.publication_id = s.beehiiv_publication_id
        self.headers = {
            "Authorization": f"Bearer {s.beehiiv_api_key}",
            "Content-Type": "application/json",
        }

    def publish_draft(
        self,
        html_content: str,
        subject: str | None = None,
        preview_text: str | None = None,
    ) -> dict[str, Any]:
        """Crea un post su Beehiiv programmato per martedi' 9:00 CET.

        Args:
            html_content: Corpo HTML della newsletter.
            subject: Oggetto dell'email (opzionale, usa il titolo se assente).
            preview_text: Testo di anteprima nell'inbox.

        Returns:
            Dizionario con 'post_id' e 'url' del post creato.
        """
        settings = get_settings()
        title = subject or f"{settings.newsletter_name} — Edizione settimanale"

        scheduled_at = self._next_tuesday_9am_cet()

        url = f"{BEEHIIV_API_BASE}/publications/{self.publication_id}/posts"

        payload: dict[str, Any] = {
            "post": {
                "title": title,
                "subtitle": preview_text or "",
                "content": [
                    {
                        "type": "html",
                        "html": html_content,
                    }
                ],
                "status": "scheduled",
                "publish_date": scheduled_at.isoformat(),
                "send_to": "all",
            }
        }

        # Rimuovi valori vuoti
        payload["post"] = {k: v for k, v in payload["post"].items() if v}

        logger.info(
            "Creazione post Beehiiv: '%s' programmato per %s",
            title,
            scheduled_at.strftime("%d/%m/%Y %H:%M CET"),
        )

        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()

        data = response.json().get("data", {})
        post_id = data.get("id", "")
        post_url = data.get("web_url", "")

        logger.info("Post Beehiiv creato: id=%s, url=%s", post_id, post_url)

        return {"post_id": post_id, "url": post_url}

    @staticmethod
    def _next_tuesday_9am_cet() -> datetime:
        """Calcola il prossimo martedi' alle 9:00 CET."""
        now = datetime.now(CET)
        days_until_tuesday = (1 - now.weekday()) % 7  # 1 = martedi'
        if days_until_tuesday == 0 and now.hour >= 9:
            days_until_tuesday = 7  # Gia' passato, prossima settimana
        target = now.replace(hour=9, minute=0, second=0, microsecond=0)
        target += timedelta(days=days_until_tuesday)
        return target
