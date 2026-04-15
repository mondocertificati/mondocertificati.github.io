"""Scraper per certificati dal mercato SeDex di Borsa Italiana via Playwright.

Flusso:
1. Apre la pagina di ricerca avanzata SeDex
2. Clicca CERCA senza filtri per ottenere tutti i certificati
3. Parsa la tabella risultante
4. Gestisce paginazione, retry con backoff esponenziale e cache locale JSON
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page, sync_playwright

from config import get_settings
from models import Certificato

logger = logging.getLogger(__name__)

# URL della ricerca avanzata SeDex
SEARCH_URL = "https://www.borsaitaliana.it/borsa/cw-e-certificates/ricerca-avanzata.html?search=1"
RESULTS_URL = "https://www.borsaitaliana.it/borsa/cw-e-certificates/cerca-strumento.html"
BASE_URL = "https://www.borsaitaliana.it"

MAX_RETRIES = 3
BASE_DELAY_S = 2.0


class BorsaItalianaScraper:
    """Estrae i certificati dal SeDex di Borsa Italiana."""

    def run(self) -> list[Certificato]:
        """Esegue lo scraping completo. Usa la cache se lo scraping fallisce."""
        settings = get_settings()

        try:
            certificati = self._scrape_all_pages()
            if certificati:
                self._save_cache(certificati, settings.scrape_cache_path)
            return certificati
        except Exception:
            logger.exception("Scraping fallito, tento di usare la cache locale")
            return self._load_cache(settings.scrape_cache_path)

    def _scrape_all_pages(self) -> list[Certificato]:
        """Lancia Playwright, cerca tutti i certificati e raccoglie i risultati."""
        settings = get_settings()
        all_certs: list[Certificato] = []

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
                # Passo 1: apri la pagina di ricerca e clicca CERCA
                self._open_search_and_submit(page)

                # Passo 2: parsa la prima pagina di risultati
                certs = self._parse_results_table(page)
                all_certs.extend(certs)
                logger.info("Pagina 1: %d certificati", len(certs))

                # Passo 3: segui le pagine successive (se esistono)
                for page_num in range(2, settings.scrape_max_pages + 1):
                    next_certs = self._go_to_next_page(page, page_num)
                    if not next_certs:
                        logger.info("Fine paginazione alla pagina %d", page_num - 1)
                        break
                    all_certs.extend(next_certs)
                    logger.info(
                        "Pagina %d: %d certificati (totale: %d)",
                        page_num, len(next_certs), len(all_certs),
                    )
            finally:
                browser.close()

        logger.info("Scraping completato: %d certificati totali", len(all_certs))
        return all_certs

    def _open_search_and_submit(self, page: Page) -> None:
        """Apre la ricerca avanzata SeDex e clicca CERCA."""
        settings = get_settings()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                page.goto(SEARCH_URL, timeout=settings.scrape_timeout_ms, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                # Accetta cookie se presente
                try:
                    page.locator("text=Accetta tutti").first.click(timeout=3000)
                    page.wait_for_timeout(1000)
                except Exception:
                    pass

                # Clicca il bottone CERCA
                page.locator("button.m-btn").click()
                page.wait_for_timeout(5000)

                # Verifica che i risultati siano caricati
                page.wait_for_selector("table.m-table", timeout=settings.scrape_timeout_ms)
                logger.info("Risultati ricerca caricati correttamente")
                return

            except Exception:
                delay = BASE_DELAY_S * (2 ** (attempt - 1))
                logger.warning(
                    "Tentativo %d/%d fallito per apertura ricerca, attendo %.1fs",
                    attempt, MAX_RETRIES, delay, exc_info=True,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(delay)

        raise RuntimeError("Impossibile caricare i risultati di ricerca dopo %d tentativi" % MAX_RETRIES)

    def _parse_results_table(self, page: Page) -> list[Certificato]:
        """Parsa la tabella dei risultati nella pagina corrente.

        Colonne della tabella:
        [0] ISIN  [1] SOTTOSTANTE  [2] EMITTENTE  [3] FACOLTA'  [4] STRIKE  [5] SCADENZA  [6] RIF  [7] (vuoto)
        """
        rows = page.locator("table.m-table tbody tr")
        count = rows.count()
        certificati: list[Certificato] = []

        for i in range(count):
            try:
                cert = self._parse_row(rows.nth(i))
                if cert:
                    certificati.append(cert)
            except Exception:
                logger.debug("Riga %d non parsabile", i, exc_info=True)
                continue

        return certificati

    def _parse_row(self, row) -> Optional[Certificato]:
        """Converte una riga HTML in un oggetto Certificato."""
        cells = row.locator("td")
        cell_count = cells.count()
        if cell_count < 6:
            return None  # Riga header o vuota

        def text(idx: int) -> str:
            if idx < cell_count:
                return cells.nth(idx).inner_text().strip()
            return ""

        def num(val: str) -> float:
            if not val:
                return 0.0
            cleaned = val.replace("%", "").replace(",", ".").replace("€", "").replace(".", "", val.count(".") - 1) if val.count(".") > 1 else val.replace(",", ".").replace("€", "").replace("%", "")
            cleaned = cleaned.strip()
            try:
                return float(cleaned)
            except ValueError:
                return 0.0

        def parse_date(val: str):
            if not val:
                return None
            for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y"):
                try:
                    return datetime.strptime(val.strip(), fmt).date()
                except ValueError:
                    continue
            return None

        isin = text(0)
        if not isin or not re.match(r"^[A-Z]{2}[A-Z0-9]{10}$", isin):
            return None

        # Estrai URL scheda prodotto dal link nell'ISIN
        url_scheda = ""
        link = cells.nth(0).locator("a")
        if link.count() > 0:
            href = link.first.get_attribute("href") or ""
            if href:
                url_scheda = f"{BASE_URL}{href}" if href.startswith("/") else href

        sottostante = text(1)
        emittente = text(2)
        tipo = text(3)  # "Bull", "Bear", "Call", "Put", etc.
        strike = num(text(4))
        scadenza = parse_date(text(5))
        prezzo_rif = num(text(6))

        # Costruisci un nome leggibile
        nome = f"{tipo} su {sottostante} - {emittente} ({isin})"

        return Certificato(
            isin=isin,
            nome=nome,
            emittente=emittente,
            sottostante=sottostante,
            tipo=tipo,
            prezzo_attuale=prezzo_rif,
            prezzo_iniziale=strike,
            scadenza=scadenza,
            url_scheda=url_scheda,
            # barriera e cedola non disponibili nella tabella lista — servono le schede dettaglio
            barriera_perc=0.0,
            cedola_annua_perc=0.0,
        )

    def _go_to_next_page(self, page: Page, target_page: int) -> list[Certificato]:
        """Tenta di navigare alla pagina successiva dei risultati."""
        try:
            # Borsa Italiana usa link di paginazione nella tabella
            next_link = page.locator(f"a:has-text('{target_page}')")
            if next_link.count() == 0:
                return []

            next_link.first.click()
            page.wait_for_timeout(5000)
            page.wait_for_selector("table.m-table", timeout=get_settings().scrape_timeout_ms)
            return self._parse_results_table(page)

        except Exception:
            logger.debug("Paginazione fallita per pagina %d", target_page, exc_info=True)
            return []

    @staticmethod
    def _extract_isin(text: str) -> Optional[str]:
        """Estrae un codice ISIN (12 caratteri) dal testo."""
        match = re.search(r"\b[A-Z]{2}[A-Z0-9]{10}\b", text.upper())
        return match.group(0) if match else None

    # ── Cache locale ────────────────────────────────────────────────

    def _save_cache(self, certificati: list[Certificato], path: str) -> None:
        """Salva i certificati in un file JSON locale."""
        cache_path = Path(path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = [c.model_dump(mode="json") for c in certificati]
        cache_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Cache salvata: %d certificati in %s", len(data), path)

    def _load_cache(self, path: str) -> list[Certificato]:
        """Carica i certificati dalla cache locale, se disponibile."""
        cache_path = Path(path)
        if not cache_path.exists():
            logger.warning("Nessuna cache trovata in %s", path)
            return []

        data = json.loads(cache_path.read_text(encoding="utf-8"))
        certificati = [Certificato.model_validate(item) for item in data]
        logger.info("Cache caricata: %d certificati da %s", len(certificati), path)
        return certificati
