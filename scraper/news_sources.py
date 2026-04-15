"""Scraper per nuovi certificati da siti italiani specializzati.

Fonti:
1. investire-certificati.it — Nuove emissioni (tabelle strutturate con ISIN, cedola, barriera)
2. investire.biz — Notizie certificati (articoli e analisi)

Questi dati arricchiscono la newsletter con:
- Nuovi prodotti appena emessi
- Contesto editoriale sulle ultime novita'
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

# URL delle fonti
INVESTIRE_CERT_URL = "https://www.investire-certificati.it/category/notizie/nuove-emissioni/"
INVESTIRE_BIZ_URL = "https://www.investire.biz/news/certificati"

# Pattern ISIN: 2 lettere + 10 alfanumerici
ISIN_PATTERN = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b")


@dataclass
class NuovoCertificato:
    """Dati di un nuovo certificato trovato negli articoli."""

    isin: str = ""
    sottostante: str = ""
    emittente: str = ""
    cedola: str = ""
    barriera: str = ""
    scadenza: str = ""
    fonte_url: str = ""
    fonte_titolo: str = ""


@dataclass
class NewsArticle:
    """Articolo di notizie sui certificati."""

    titolo: str
    url: str
    data: str = ""
    categoria: str = ""
    fonte: str = ""


@dataclass
class ExternalSourcesData:
    """Dati raccolti dalle fonti esterne."""

    nuovi_certificati: list[NuovoCertificato] = field(default_factory=list)
    articoli: list[NewsArticle] = field(default_factory=list)

    def format_for_prompt(self) -> str:
        """Formatta i dati per il prompt della newsletter."""
        parts = []

        if self.nuovi_certificati:
            parts.append("NUOVI CERTIFICATI SUL MERCATO (da fonti specializzate):")
            for i, cert in enumerate(self.nuovi_certificati[:8], 1):
                line = f"{i}. "
                if cert.isin:
                    line += f"ISIN {cert.isin}"
                if cert.sottostante:
                    line += f" — Sottostante: {cert.sottostante}"
                if cert.emittente:
                    line += f" — Emittente: {cert.emittente}"
                if cert.cedola:
                    line += f" — Cedola: {cert.cedola}"
                if cert.barriera:
                    line += f" — Barriera: {cert.barriera}"
                if cert.fonte_titolo:
                    line += f"\n   (Fonte: {cert.fonte_titolo})"
                parts.append(line)

        if self.articoli:
            parts.append("\nNOTIZIE RECENTI SUI CERTIFICATI:")
            for i, art in enumerate(self.articoli[:10], 1):
                line = f"{i}. {art.titolo}"
                if art.data:
                    line += f" ({art.data})"
                if art.fonte:
                    line += f" — {art.fonte}"
                parts.append(line)

        return "\n".join(parts) if parts else ""


def fetch_external_sources() -> ExternalSourcesData:
    """Raccoglie dati da tutte le fonti esterne.

    Returns:
        ExternalSourcesData con nuovi certificati e articoli recenti.
    """
    data = ExternalSourcesData()

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
            # 1. investire-certificati.it — Nuove emissioni
            _scrape_investire_certificati(page, data)

            # 2. investire.biz — Notizie certificati
            _scrape_investire_biz(page, data)

        except Exception:
            logger.warning("Errore generale scraping fonti esterne", exc_info=True)
        finally:
            browser.close()

    logger.info(
        "Fonti esterne: %d nuovi certificati, %d articoli",
        len(data.nuovi_certificati),
        len(data.articoli),
    )
    return data


def _accept_cookies(page) -> None:
    """Tenta di accettare cookie banner."""
    for selector in [
        "button:has-text('Accetta')",
        "button:has-text('Accetto')",
        "button:has-text('Accept')",
        "a:has-text('Accetta')",
        "#cookie-law-info-bar .cli-plugin-button",
    ]:
        try:
            page.locator(selector).first.click(timeout=2000)
            page.wait_for_timeout(500)
            return
        except Exception:
            continue


def _scrape_investire_certificati(page, data: ExternalSourcesData) -> None:
    """Scrape investire-certificati.it per nuove emissioni."""
    try:
        page.goto(INVESTIRE_CERT_URL, timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        _accept_cookies(page)

        # Raccogli articoli dalla lista
        articles = page.locator("h3.entry-title a")
        count = articles.count()
        logger.info("investire-certificati.it: %d articoli trovati", count)

        article_links: list[tuple[str, str]] = []
        for i in range(min(count, 6)):
            try:
                title = articles.nth(i).inner_text().strip()
                href = articles.nth(i).get_attribute("href") or ""
                if title and href:
                    article_links.append((title, href))
                    data.articoli.append(
                        NewsArticle(
                            titolo=title,
                            url=href,
                            fonte="investire-certificati.it",
                        )
                    )
            except Exception:
                continue

        # Visita i primi 3 articoli per estrarre tabelle con dati certificati
        for title, href in article_links[:3]:
            try:
                _extract_certificates_from_article(page, title, href, data)
            except Exception:
                logger.debug("Errore estrazione da %s", href, exc_info=True)
                continue

    except Exception:
        logger.warning("Errore scraping investire-certificati.it", exc_info=True)


def _extract_certificates_from_article(
    page, article_title: str, url: str, data: ExternalSourcesData
) -> None:
    """Visita un articolo ed estrae dati certificati dalle tabelle HTML."""
    page.goto(url, timeout=15000, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)

    # Cerca tabelle nel contenuto dell'articolo
    tables = page.locator(".td-post-content table")
    table_count = tables.count()

    if table_count == 0:
        # Nessuna tabella — prova a estrarre ISIN dal testo
        content_text = page.locator(".td-post-content").first.inner_text()
        isins = ISIN_PATTERN.findall(content_text)
        for isin in isins[:3]:
            data.nuovi_certificati.append(
                NuovoCertificato(
                    isin=isin,
                    fonte_url=url,
                    fonte_titolo=article_title,
                )
            )
        return

    for t in range(min(table_count, 2)):
        try:
            table = tables.nth(t)
            rows = table.locator("tr")
            row_count = rows.count()

            if row_count < 2:
                continue

            # Leggi header
            header_cells = rows.nth(0).locator("td, th")
            headers = []
            for h in range(header_cells.count()):
                headers.append(header_cells.nth(h).inner_text().strip().lower())

            # Mappa colonne
            col_map = _map_columns(headers)

            # Leggi righe dati
            for r in range(1, min(row_count, 8)):
                cells = rows.nth(r).locator("td, th")
                cell_count = cells.count()
                if cell_count < 2:
                    continue

                cell_values = []
                for c in range(cell_count):
                    cell_values.append(cells.nth(c).inner_text().strip())

                cert = _row_to_certificate(cell_values, col_map, url, article_title)
                if cert and (cert.isin or cert.sottostante):
                    data.nuovi_certificati.append(cert)

        except Exception:
            logger.debug("Errore parsing tabella %d in %s", t, url, exc_info=True)
            continue


def _map_columns(headers: list[str]) -> dict[str, int]:
    """Mappa i nomi delle colonne agli indici."""
    col_map: dict[str, int] = {}

    for i, h in enumerate(headers):
        h_lower = h.lower()
        if "isin" in h_lower or "codice" in h_lower:
            col_map["isin"] = i
        elif "sottostant" in h_lower or "azioni" in h_lower or "basket" in h_lower:
            col_map["sottostante"] = i
        elif "emittent" in h_lower:
            col_map["emittente"] = i
        elif "cedola" in h_lower or "premio" in h_lower or "coupon" in h_lower:
            col_map["cedola"] = i
        elif "barriera" in h_lower:
            col_map["barriera"] = i
        elif "scadenz" in h_lower:
            col_map["scadenza"] = i
        elif "strike" in h_lower:
            col_map.setdefault("sottostante_extra", i)

    return col_map


def _row_to_certificate(
    cells: list[str],
    col_map: dict[str, int],
    url: str,
    article_title: str,
) -> Optional[NuovoCertificato]:
    """Converte una riga di tabella in un NuovoCertificato."""
    cert = NuovoCertificato(fonte_url=url, fonte_titolo=article_title)

    def safe_get(idx: int) -> str:
        return cells[idx] if idx < len(cells) else ""

    if "isin" in col_map:
        raw = safe_get(col_map["isin"])
        # Estrai ISIN con pattern
        match = ISIN_PATTERN.search(raw)
        cert.isin = match.group() if match else raw.strip()

    if "sottostante" in col_map:
        cert.sottostante = safe_get(col_map["sottostante"])

    if "emittente" in col_map:
        cert.emittente = safe_get(col_map["emittente"])

    if "cedola" in col_map:
        cert.cedola = safe_get(col_map["cedola"])

    if "barriera" in col_map:
        cert.barriera = safe_get(col_map["barriera"])

    if "scadenza" in col_map:
        cert.scadenza = safe_get(col_map["scadenza"])

    return cert


def _scrape_investire_biz(page, data: ExternalSourcesData) -> None:
    """Scrape investire.biz per notizie sui certificati."""
    try:
        page.goto(INVESTIRE_BIZ_URL, timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        _accept_cookies(page)

        # Articoli dalla pagina notizie certificati
        cards = page.locator("a.card.shadowLink.linkCard, a.card")
        count = cards.count()
        logger.info("investire.biz: %d articoli trovati", count)

        for i in range(min(count, 8)):
            try:
                card = cards.nth(i)
                title_el = card.locator("h2.card-title")
                if title_el.count() == 0:
                    continue

                title = title_el.first.inner_text().strip()
                href = card.get_attribute("href") or ""

                if not href.startswith("http"):
                    href = f"https://www.investire.biz{href}"

                if title:
                    data.articoli.append(
                        NewsArticle(
                            titolo=title,
                            url=href,
                            fonte="investire.biz",
                        )
                    )
            except Exception:
                continue

    except Exception:
        logger.warning("Errore scraping investire.biz", exc_info=True)
