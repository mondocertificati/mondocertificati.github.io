"""Screener: calcola un opportunity_score (0-100) per ogni certificato.

Pesi:
- Cedola alta -> punteggio alto
- Distanza barriera > 20% -> bonus
- Scadenza 6-24 mesi -> ottimale
- Distanza barriera < 10% -> penalita' (rischioso)
- Scadenza > 36 mesi -> penalita'
- Barriera gia' violata (distanza < 0) -> escluso
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from models import Certificato

logger = logging.getLogger(__name__)


class Screener:
    """Classifica i certificati per opportunita' di investimento."""

    def rank(self, certificati: list[Certificato], top_n: int = 5) -> list[Certificato]:
        """Calcola lo score, filtra quelli con barriera violata, ritorna i migliori.

        Args:
            certificati: Lista di certificati dallo scraper.
            top_n: Quanti certificati restituire.

        Returns:
            Lista dei migliori certificati ordinati per opportunity_score decrescente.
        """
        scored: list[Certificato] = []

        for cert in certificati:
            # Escludi certificati con barriera gia' violata
            if cert.distanza_barriera_perc < 0:
                continue

            score = self._calculate_score(cert)
            cert.opportunity_score = round(score, 1)
            scored.append(cert)

        scored.sort(key=lambda c: c.opportunity_score, reverse=True)
        top = scored[:top_n]

        logger.info(
            "Screener: %d certificati analizzati, %d esclusi (barriera violata), top %d selezionati",
            len(certificati),
            len(certificati) - len(scored),
            len(top),
        )
        for c in top:
            logger.info("  %.1f pts — %s (%s)", c.opportunity_score, c.nome, c.isin)

        return top

    def _calculate_score(self, cert: Certificato) -> float:
        """Calcola il punteggio di opportunita' (0-100)."""
        score = 0.0

        # ── Cedola (max 35 punti) ──────────────────────────────────
        # Cedola 0% = 0 punti, 12%+ = 35 punti
        score += min(cert.cedola_annua_perc / 12.0, 1.0) * 35

        # ── Distanza barriera (max 30 punti) ───────────────────────
        dist = cert.distanza_barriera_perc
        if dist > 30:
            score += 30  # Molto sicuro
        elif dist > 20:
            score += 25  # Sicuro
        elif dist > 10:
            score += 15  # Discreto
        elif dist > 5:
            score += 5  # Rischioso
        else:
            score += 0  # Molto rischioso

        # ── Scadenza (max 25 punti) ────────────────────────────────
        mesi = self._mesi_alla_scadenza(cert.scadenza)
        if mesi is not None:
            if 6 <= mesi <= 24:
                score += 25  # Finestra ottimale
            elif 3 <= mesi < 6:
                score += 15  # Breve ma ok
            elif 24 < mesi <= 36:
                score += 15  # Medio-lungo
            elif mesi > 36:
                score += 5  # Troppo lungo, penalita'
            # mesi < 3: scadenza imminente, 0 punti

        # ── Rendimento annualizzato (max 10 punti) ─────────────────
        score += min(cert.rendimento_annualizzato / 15.0, 1.0) * 10

        return min(score, 100.0)

    @staticmethod
    def _mesi_alla_scadenza(scadenza: Optional[date]) -> Optional[float]:
        """Calcola i mesi rimanenti alla scadenza."""
        if scadenza is None:
            return None
        delta = scadenza - date.today()
        return max(delta.days / 30.44, 0)  # media giorni/mese
