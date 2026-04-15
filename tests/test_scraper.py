"""Test per lo scraper di Borsa Italiana."""

import json
import tempfile
from pathlib import Path

from models import Certificato
from scraper.borsaitaliana import BorsaItalianaScraper


class TestExtractIsin:
    def test_estrae_isin_valido(self):
        assert BorsaItalianaScraper._extract_isin("Prodotto XS1234567890 dettagli") == "XS1234567890"

    def test_estrae_isin_italiano(self):
        assert BorsaItalianaScraper._extract_isin("IT0005412345") == "IT0005412345"

    def test_estrae_isin_tedesco(self):
        assert BorsaItalianaScraper._extract_isin("Codice: DE000ABC1234") == "DE000ABC1234"

    def test_nessun_isin(self):
        assert BorsaItalianaScraper._extract_isin("nessun codice qui 12345") is None

    def test_isin_da_multilinea(self):
        text = "Nome prodotto\nISIN: FR0012345678\nAltro"
        assert BorsaItalianaScraper._extract_isin(text) == "FR0012345678"


class TestCache:
    def test_salva_e_carica_cache(self):
        scraper = BorsaItalianaScraper()
        certs = [
            Certificato(
                isin="IT0005412345",
                nome="Test Certificate",
                cedola_annua_perc=8.5,
                prezzo_attuale=98.0,
            )
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = str(Path(tmpdir) / "test_cache.json")
            scraper._save_cache(certs, cache_path)

            # Verifica che il file esiste e contiene JSON valido
            data = json.loads(Path(cache_path).read_text())
            assert len(data) == 1
            assert data[0]["isin"] == "IT0005412345"

            # Ricarica dalla cache
            loaded = scraper._load_cache(cache_path)
            assert len(loaded) == 1
            assert loaded[0].isin == "IT0005412345"
            assert loaded[0].cedola_annua_perc == 8.5

    def test_cache_inesistente(self):
        scraper = BorsaItalianaScraper()
        result = scraper._load_cache("/percorso/inesistente/cache.json")
        assert result == []
