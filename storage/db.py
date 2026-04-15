"""Persistenza su Supabase — newsletter_issues e certificates_history.

Per creare le tabelle, esegui il file storage/schema.sql nell'SQL Editor di Supabase.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from supabase import Client, create_client

from config import get_settings
from models import Certificato

logger = logging.getLogger(__name__)


class Database:
    """Client per il database Supabase."""

    def __init__(self) -> None:
        s = get_settings()
        self.client: Client = create_client(s.supabase_url, s.supabase_key)

    # ── Newsletter issues ───────────────────────────────────────────

    def log_issue(
        self,
        post_id: str,
        certificates: list[Certificato],
        status: str = "scheduled",
    ) -> dict[str, Any]:
        """Registra una nuova edizione della newsletter.

        Args:
            post_id: ID del post su Beehiiv.
            certificates: Certificati inclusi nell'edizione.
            status: Stato del post (draft, scheduled, sent).

        Returns:
            La riga inserita.
        """
        today = date.today()
        isins = [c.isin for c in certificates]

        row = {
            "week_number": today.isocalendar()[1],
            "year": today.year,
            "beehiiv_post_id": post_id,
            "status": status,
            "certificates_featured": isins,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        result = self.client.table("newsletter_issues").insert(row).execute()
        logger.info(
            "Edizione registrata: settimana %d/%d, post_id=%s, %d certificati",
            today.isocalendar()[1],
            today.year,
            post_id,
            len(isins),
        )
        return result.data[0] if result.data else row

    def get_latest_issue(self) -> dict[str, Any] | None:
        """Restituisce l'ultima edizione registrata."""
        result = (
            self.client.table("newsletter_issues")
            .select("*")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    # ── Certificates history ────────────────────────────────────────

    def save_certificates_history(self, certificates: list[Certificato]) -> int:
        """Salva lo snapshot dei certificati per tracciamento storico.

        Args:
            certificates: Lista di certificati da salvare.

        Returns:
            Numero di righe inserite.
        """
        if not certificates:
            return 0

        rows = [
            {
                "isin": c.isin,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "opportunity_score": c.opportunity_score,
                "distanza_barriera_perc": c.distanza_barriera_perc,
                "prezzo_attuale": c.prezzo_attuale,
            }
            for c in certificates
        ]

        result = self.client.table("certificates_history").insert(rows).execute()
        count = len(result.data) if result.data else 0
        logger.info("Storico certificati salvato: %d righe", count)
        return count

    def get_cached_certificates(self) -> list[dict[str, Any]]:
        """Recupera i certificati piu' recenti dal database (fallback se lo scraping fallisce)."""
        result = (
            self.client.table("certificates_history")
            .select("*")
            .order("scraped_at", desc=True)
            .limit(50)
            .execute()
        )
        return result.data or []
