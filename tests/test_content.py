"""Test per il generatore di contenuti della newsletter."""

from datetime import date

from content.generator import DIDACTIC_TOPICS, NewsletterGenerator


class TestNewsletterGenerator:
    def test_format_certificates(self):
        from models import Certificato

        certs = [
            Certificato(
                isin="XS1234567890",
                nome="Test Certificate",
                emittente="UniCredit",
                sottostante="ENI",
                tipo="Cash Collect",
                cedola_annua_perc=8.5,
                barriera_perc=60.0,
                distanza_barriera_perc=25.0,
                opportunity_score=78.5,
            )
        ]

        gen = NewsletterGenerator.__new__(NewsletterGenerator)
        text = gen._format_certificates(certs)
        assert "XS1234567890" in text
        assert "UniCredit" in text
        assert "ENI" in text
        assert "8.5%" in text

    def test_format_certificates_vuoto(self):
        gen = NewsletterGenerator.__new__(NewsletterGenerator)
        text = gen._format_certificates([])
        assert "Nessun certificato" in text

    def test_format_single_certificate(self):
        from models import Certificato

        cert = Certificato(
            isin="DE000ABC1234",
            nome="Bonus Cap FTSE MIB",
            sottostante="FTSE MIB",
            opportunity_score=85.0,
        )
        gen = NewsletterGenerator.__new__(NewsletterGenerator)
        text = gen._format_single_certificate(cert)
        assert "FTSE MIB" in text
        assert "85.0/100" in text

    def test_build_prompt_contiene_struttura(self):
        from models import Certificato

        certs = [Certificato(isin="IT0005412345", nome="Test")]
        gen = NewsletterGenerator.__new__(NewsletterGenerator)
        gen.newsletter_name = "Mondo Certificati"

        prompt = gen._build_prompt(certs)
        assert "INTRO" in prompt
        assert "CERTIFICATI DELLA SETTIMANA" in prompt
        assert "SPAZIO DIDATTICO" in prompt
        assert "OPPORTUNITA' IN EVIDENZA" in prompt
        assert "FOOTER" in prompt
        assert "disclaimer" in prompt.lower()

    def test_argomento_didattico_ruota(self):
        """L'argomento deve cambiare in base alla settimana ISO."""
        week_number = date.today().isocalendar()[1]
        expected_topic = DIDACTIC_TOPICS[week_number % len(DIDACTIC_TOPICS)]

        from models import Certificato

        gen = NewsletterGenerator.__new__(NewsletterGenerator)
        gen.newsletter_name = "Test"
        prompt = gen._build_prompt([Certificato(isin="IT0005412345", nome="Test")])
        assert expected_topic in prompt
