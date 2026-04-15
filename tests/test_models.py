"""Test per il modello dati Certificato."""

from datetime import date

from models import Certificato


class TestCertificato:
    def test_crea_certificato_minimo(self):
        c = Certificato(isin="IT0005412345", nome="Test Certificate")
        assert c.isin == "IT0005412345"
        assert c.cedola_annua_perc == 0.0
        assert c.opportunity_score == 0.0

    def test_crea_certificato_completo(self):
        c = Certificato(
            isin="XS1234567890",
            nome="Autocall su ENI - Barriera 60%",
            emittente="Societe Generale",
            sottostante="ENI",
            tipo="Autocall",
            cedola_annua_perc=8.5,
            barriera_perc=60.0,
            distanza_barriera_perc=25.3,
            scadenza=date(2025, 12, 15),
            prezzo_attuale=98.5,
            prezzo_iniziale=100.0,
            rendimento_annualizzato=10.2,
            url_scheda="https://www.borsaitaliana.it/certificati/test",
        )
        assert c.emittente == "Societe Generale"
        assert c.sottostante == "ENI"
        assert c.cedola_annua_perc == 8.5

    def test_to_db_row(self):
        c = Certificato(
            isin="DE000ABC1234",
            nome="Test",
            opportunity_score=75.0,
            distanza_barriera_perc=20.0,
            prezzo_attuale=95.0,
        )
        row = c.to_db_row()
        assert row["isin"] == "DE000ABC1234"
        assert row["opportunity_score"] == 75.0
        assert row["prezzo_attuale"] == 95.0

    def test_model_dump_json(self):
        c = Certificato(
            isin="IT0005412345",
            nome="Test",
            scadenza=date(2025, 6, 30),
        )
        data = c.model_dump(mode="json")
        assert data["scadenza"] == "2025-06-30"
        assert isinstance(data["isin"], str)
