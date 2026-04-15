"""Orchestratore principale della newsletter Mondo Certificati.

Flusso:
    1. scraper.run()                -> List[Certificato]
    2. fetch_market_headlines()     -> str (notizie Radiocor)
    3. fetch_external_sources()     -> ExternalSourcesData (nuovi certificati)
    4. screener.rank()              -> List[Certificato] (top 5)
    5. generator.create_issue()     -> html_content: str
    6. beehiiv.publish_draft()      -> post_id: str
    7. db.log_issue()               -> None

Uso:
    python main.py              # Pipeline completa
    python main.py --dry-run    # Genera senza inviare
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("newsletter")


def run_pipeline(*, dry_run: bool = False) -> None:
    """Esegue la pipeline completa della newsletter."""

    from analyzer.screener import Screener
    from content.generator import NewsletterGenerator
    from content.market_news import fetch_market_headlines
    from delivery.beehiiv import BeehiivClient
    from scraper.borsaitaliana import BorsaItalianaScraper
    from scraper.news_sources import fetch_external_sources
    from storage.db import Database

    db = Database()

    # ── 1. Scraping Borsa Italiana ──────────────────────────────────
    logger.info("=" * 60)
    logger.info("PASSO 1/7 — Raccolta dati da Borsa Italiana")
    logger.info("=" * 60)

    scraper = BorsaItalianaScraper()
    certificati = scraper.run()

    if not certificati:
        logger.warning("Scraping fallito e nessuna cache. Provo dal database.")
        cached = db.get_cached_certificates()
        if not cached:
            logger.error("Nessun dato disponibile. Impossibile continuare.")
            sys.exit(1)
        logger.info("Recuperati %d certificati dal database", len(cached))

    # ── 2. Notizie di mercato (Radiocor) ────────────────────────────
    logger.info("=" * 60)
    logger.info("PASSO 2/7 — Raccolta notizie di mercato (Radiocor)")
    logger.info("=" * 60)

    market_context = fetch_market_headlines()
    if market_context:
        logger.info("Notizie di mercato raccolte con successo")
    else:
        logger.warning("Notizie Radiocor non disponibili")

    # ── 3. Fonti esterne (investire-certificati.it, investire.biz) ──
    logger.info("=" * 60)
    logger.info("PASSO 3/7 — Raccolta da fonti esterne")
    logger.info("=" * 60)

    try:
        external_data = fetch_external_sources()
        external_text = external_data.format_for_prompt()
        if external_text:
            logger.info("Fonti esterne raccolte con successo")
        else:
            logger.warning("Nessun dato dalle fonti esterne")
    except Exception:
        logger.warning("Errore fonti esterne", exc_info=True)
        external_text = ""

    # ── 4. Screener ─────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("PASSO 4/7 — Selezione dei migliori certificati")
    logger.info("=" * 60)

    screener = Screener()
    top_5 = screener.rank(certificati, top_n=5)

    if not top_5:
        logger.error("Nessun certificato valido trovato dallo screener.")
        sys.exit(1)

    # Salva lo storico dei certificati analizzati
    try:
        db.save_certificates_history(certificati)
    except Exception:
        logger.warning("Impossibile salvare lo storico certificati", exc_info=True)

    # ── 5. Generazione contenuto ────────────────────────────────────
    logger.info("=" * 60)
    logger.info("PASSO 5/7 — Generazione newsletter con Claude")
    logger.info("=" * 60)

    generator = NewsletterGenerator()
    try:
        html_content = generator.create_issue(
            top_5,
            market_context=market_context,
            external_sources=external_text,
        )
    except RuntimeError:
        logger.error("Impossibile generare la newsletter (Claude API non disponibile)")
        _save_fallback_html("", top_5)
        sys.exit(1)

    # ── 6. Pubblicazione ────────────────────────────────────────────
    if dry_run:
        logger.info("=" * 60)
        logger.info("MODALITA' DRY-RUN — Newsletter non inviata")
        logger.info("=" * 60)
        _save_fallback_html(html_content, top_5)
        return

    logger.info("=" * 60)
    logger.info("PASSO 6/7 — Pubblicazione su Beehiiv")
    logger.info("=" * 60)

    try:
        beehiiv = BeehiivClient()
        result = beehiiv.publish_draft(html_content=html_content)
        post_id = result["post_id"]
        post_url = result.get("url", "")
    except Exception:
        logger.error("Pubblicazione Beehiiv fallita. Salvo l'HTML locale.", exc_info=True)
        _save_fallback_html(html_content, top_5)
        post_id = ""
        post_url = ""

    # ── 7. Registrazione nel database ───────────────────────────────
    logger.info("=" * 60)
    logger.info("PASSO 7/7 — Registrazione nel database")
    logger.info("=" * 60)

    try:
        db.log_issue(post_id=post_id, certificates=top_5)
    except Exception:
        logger.warning("Impossibile registrare l'edizione nel database", exc_info=True)

    # ── Riepilogo ───────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("COMPLETATO!")
    logger.info("  Post ID: %s", post_id or "(non inviato)")
    logger.info("  URL: %s", post_url or "(non disponibile)")
    logger.info("  Certificati: %s", ", ".join(c.isin for c in top_5))
    logger.info("=" * 60)


def _save_fallback_html(html_content: str, certificates: list) -> None:
    """Salva l'HTML in un file locale come fallback."""
    from datetime import date

    filename = f"newsletter_{date.today().isoformat()}.html"
    Path(filename).write_text(html_content or "<p>Contenuto non generato</p>", encoding="utf-8")
    logger.info("HTML salvato in: %s", filename)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mondo Certificati — Newsletter Pipeline")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Genera la newsletter senza inviarla (salva solo il file HTML)",
    )
    args = parser.parse_args()

    try:
        run_pipeline(dry_run=args.dry_run)
    except Exception:
        logger.exception("Pipeline fallita")
        sys.exit(1)


if __name__ == "__main__":
    main()
