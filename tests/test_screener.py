"""Test per lo screener di certificati."""

from datetime import date, timedelta

from analyzer.screener import Screener
from models import Certificato


def _make_cert(**kwargs) -> Certificato:
    """Helper per creare un certificato con valori di default sensati."""
    defaults = {
        "isin": "IT0005412345",
        "nome": "Test Certificate",
        "cedola_annua_perc": 8.0,
        "barriera_perc": 60.0,
        "distanza_barriera_perc": 25.0,
        "scadenza": date.today() + timedelta(days=365),
        "prezzo_attuale": 98.0,
        "prezzo_iniziale": 100.0,
        "rendimento_annualizzato": 10.0,
    }
    defaults.update(kwargs)
    return Certificato(**defaults)


class TestScreener:
    def test_esclude_barriera_violata(self):
        certs = [
            _make_cert(isin="OK001", distanza_barriera_perc=20.0),
            _make_cert(isin="KO001", distanza_barriera_perc=-5.0),  # Barriera violata
        ]
        screener = Screener()
        result = screener.rank(certs, top_n=5)
        isins = [c.isin for c in result]
        assert "OK001" in isins
        assert "KO001" not in isins

    def test_top_n_limita_risultati(self):
        certs = [_make_cert(isin=f"CERT{i:08d}") for i in range(10)]
        screener = Screener()
        result = screener.rank(certs, top_n=3)
        assert len(result) == 3

    def test_ordine_per_score_decrescente(self):
        certs = [
            _make_cert(isin="LOW0000001", cedola_annua_perc=1.0, distanza_barriera_perc=5.0),
            _make_cert(isin="HIGH000001", cedola_annua_perc=12.0, distanza_barriera_perc=35.0),
        ]
        screener = Screener()
        result = screener.rank(certs, top_n=5)
        assert result[0].isin == "HIGH000001"
        assert result[0].opportunity_score > result[1].opportunity_score

    def test_score_alto_per_buon_certificato(self):
        cert = _make_cert(
            cedola_annua_perc=10.0,
            distanza_barriera_perc=25.0,
            scadenza=date.today() + timedelta(days=365),  # 12 mesi — ottimale
            rendimento_annualizzato=12.0,
        )
        screener = Screener()
        result = screener.rank([cert], top_n=1)
        assert result[0].opportunity_score > 60

    def test_score_basso_per_certificato_rischioso(self):
        cert = _make_cert(
            cedola_annua_perc=2.0,
            distanza_barriera_perc=3.0,
            scadenza=date.today() + timedelta(days=1500),  # >36 mesi
            rendimento_annualizzato=1.0,
        )
        screener = Screener()
        result = screener.rank([cert], top_n=1)
        assert result[0].opportunity_score < 30

    def test_lista_vuota(self):
        screener = Screener()
        result = screener.rank([], top_n=5)
        assert result == []

    def test_scadenza_nulla_non_causa_errore(self):
        cert = _make_cert(scadenza=None)
        screener = Screener()
        result = screener.rank([cert], top_n=1)
        assert len(result) == 1

    def test_mesi_alla_scadenza(self):
        screener = Screener()
        # 365 giorni ~ 12 mesi
        future = date.today() + timedelta(days=365)
        mesi = screener._mesi_alla_scadenza(future)
        assert mesi is not None
        assert 11.5 < mesi < 12.5

    def test_mesi_alla_scadenza_passata(self):
        screener = Screener()
        past = date.today() - timedelta(days=30)
        mesi = screener._mesi_alla_scadenza(past)
        assert mesi == 0  # Non negativo
