"""Raccoglie notizie di mercato reali da Borsa Italiana per il contesto della newsletter.

Usa Playwright per leggere i titoli delle notizie dalla sezione Radiocor
di Borsa Italiana, fornendo contesto reale e aggiornato alla newsletter.
"""

from __future__ import annotations

import logging
from datetime import datetime

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

# Pagine Radiocor di Borsa Italiana (struttura attuale)
NEWS_URLS = [
    "https://www.borsaitaliana.it/borsa/notizie/radiocor/prima-pagina/archivio.html",
    "https://www.borsaitaliana.it/borsa/notizie/radiocor/finanza/archivio.html",
]


def fetch_market_headlines(max_headlines: int = 15) -> str:
    """Scarica i titoli delle notizie recenti da Borsa Italiana Radiocor.

    Returns:
        Stringa con i titoli delle notizie formattati, oppure stringa vuota
        se lo scraping fallisce.
    """
    try:
        headlines = _scrape_headlines(max_headlines)
        if headlines:
            today = datetime.now().strftime("%d/%m/%Y")
            result = f"NOTIZIE DI MERCATO REALI (aggiornate al {today}):\n"
            for i, h in enumerate(headlines, 1):
                result += f"{i}. {h}\n"
            logger.info("Raccolte %d notizie di mercato", len(headlines))
            return result
        else:
            logger.warning("Nessuna notizia trovata")
            return ""
    except Exception:
        logger.warning("Impossibile scaricare notizie di mercato", exc_info=True)
        return ""


def _scrape_headlines(max_headlines: int) -> list[str]:
    """Scraping effettivo delle notizie da Radiocor."""
    all_headlines: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            locale="it-IT",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            for url in NEWS_URLS:
                try:
                    page.goto(url, timeout=15000, wait_until="domcontentloaded")
                    page.wait_for_timeout(2000)

                    # Accetta cookie se presente
                    try:
                        page.locator("button:has-text('Accetta')").first.click(timeout=3000)
                        page.wait_for_timeout(500)
                    except Exception:
                        pass

                    # Selettore principale: link dentro la lista archivio Radiocor
                    # Struttura: ul#itemListArchive > li > div > h3 > a.t-text.-black-warm-90
                    links = page.locator("ul#itemListArchive a")
                    count = links.count()

                    if count == 0:
                        # Fallback: prova con selettore alternativo
                        links = page.locator("ul.itemListArchive a")
                        count = links.count()

                    for i in range(min(count, max_headlines)):
                        text = links.nth(i).inner_text().strip()
                        # Filtra titoli troppo corti o duplicati
                        if text and len(text) > 10 and text not in all_headlines:
                            all_headlines.append(text)

                    logger.debug("Da %s: %d titoli trovati", url, count)

                except Exception:
                    logger.debug("Errore scraping notizie da %s", url, exc_info=True)
                    continue

                if len(all_headlines) >= max_headlines:
                    break

        finally:
            browser.close()

    return all_headlines[:max_headlines]
