"""Generatore di contenuti per la newsletter usando l'API Claude di Anthropic.

Sezioni della newsletter:
1. Intro (~100 parole) — contesto di mercato REALE, tono conversazionale
2. Certificati della settimana (top 5) — spiegazione semplice per ciascuno
3. Spazio didattico (~200 parole) — argomento a rotazione settimanale
4. Opportunita' in evidenza (~300 parole) — analisi dettagliata del #1
5. Footer — disclaimer e link unsubscribe
"""

from __future__ import annotations

import logging
import time
from datetime import date

import anthropic

from config import get_settings
from models import Certificato

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Sei un esperto di certificati di investimento che scrive per investitori retail italiani. "
    "Il tuo tono e' chiaro, educativo e mai promozionale. Non fornisci mai consulenza finanziaria. "
    "Usi un linguaggio semplice ma preciso. Sei entusiasta dei certificati ma sempre equilibrato "
    "sui rischi.\n\n"
    "REGOLE FONDAMENTALI:\n"
    "1. NON inventare MAI eventi di mercato, notizie o fatti specifici. Usa SOLO le informazioni "
    "fornite nella sezione 'CONTESTO DI MERCATO' del prompt.\n"
    "2. Se non hai notizie di mercato reali, scrivi un'intro generica sull'importanza di "
    "seguire i mercati e valutare le opportunita' con attenzione.\n"
    "3. Per ogni certificato, usa SOLO i dati numerici forniti. Se un dato e' 0.0 o mancante, "
    "NON inventare un valore: dillo esplicitamente o ometti quel dettaglio.\n"
    "4. NON inventare livelli di prezzo, target, variazioni percentuali o previsioni.\n"
    "5. Se la cedola e' 0.0%, NON scrivere che paga cedole — potrebbe non essere un certificato "
    "a cedola (ad esempio i Bull/Bear sono certificati a leva).\n"
    "6. Se la barriera e' 0.0%, non scrivere nulla sulla barriera — il dato non e' disponibile."
)

DIDACTIC_TOPICS = [
    "Come funziona la barriera",
    "Cosa sono le cedole condizionate",
    "Differenza tra Autocall e Cash Collect",
    "Come leggere il KID",
    "Rischio emittente",
    "Fiscalita' dei certificati in Italia",
    "Come si calcola il rendimento annualizzato",
]

MAX_RETRIES = 3
RETRY_DELAY_S = 5


class NewsletterGenerator:
    """Genera il contenuto HTML della newsletter tramite Claude API."""

    def __init__(self) -> None:
        s = get_settings()
        self.client = anthropic.Anthropic(api_key=s.anthropic_api_key)
        self.model = s.anthropic_model
        self.newsletter_name = s.newsletter_name

    def create_issue(
        self,
        top_certificates: list[Certificato],
        market_context: str = "",
    ) -> str:
        """Genera l'HTML completo della newsletter.

        Args:
            top_certificates: I migliori certificati (gia' ordinati dallo screener).
            market_context: Notizie di mercato reali (opzionale).

        Returns:
            Stringa HTML della newsletter pronta per l'invio.
        """
        prompt = self._build_prompt(top_certificates, market_context)
        html = self._call_claude(prompt)
        logger.info("Newsletter generata: %d caratteri HTML", len(html))
        return html

    def _build_prompt(
        self,
        certificates: list[Certificato],
        market_context: str = "",
    ) -> str:
        """Costruisce il prompt completo per Claude."""
        # Argomento didattico basato sul numero della settimana ISO
        week_number = date.today().isocalendar()[1]
        topic_index = week_number % len(DIDACTIC_TOPICS)
        topic = DIDACTIC_TOPICS[topic_index]

        # Formatta i dati dei certificati
        certs_text = self._format_certificates(certificates)

        # Certificato #1 per la sezione approfondita
        top_cert = certificates[0] if certificates else None
        top_cert_text = self._format_single_certificate(top_cert) if top_cert else "N/A"

        # Contesto di mercato
        if market_context:
            market_section = (
                f"## CONTESTO DI MERCATO (NOTIZIE REALI)\n"
                f"Usa SOLO queste notizie per l'intro. Non aggiungere fatti non presenti qui.\n\n"
                f"{market_context}"
            )
        else:
            market_section = (
                "## CONTESTO DI MERCATO\n"
                "Non sono disponibili notizie di mercato aggiornate. Scrivi un'intro generica "
                "che parli dell'importanza di monitorare i certificati e diversificare. "
                "NON inventare notizie, eventi o dati di mercato specifici."
            )

        today_str = date.today().strftime("%d/%m/%Y")

        return f"""\
Genera una newsletter completa in HTML per "{self.newsletter_name}" del {today_str}.
La newsletter e' rivolta a investitori retail italiani interessati ai certificati di investimento.

IMPORTANTE: Genera SOLO codice HTML valido (senza tag <html>, <head>, <body>). Usa stili inline
per compatibilita' email. Font: Arial, sans-serif. Max-width: 600px. Background: bianco.

{market_section}

## STRUTTURA OBBLIGATORIA

### 1. INTRO (~100 parole)
Scrivi un'apertura calorosa e conversazionale.
- Se hai notizie di mercato reali sopra, fai riferimento a 2-3 di quelle notizie.
- Se NON hai notizie, scrivi un'intro generica e accogliente.
- NON inventare MAI notizie, dati di borsa, variazioni di indici o eventi specifici.
- Firma come "Il team di {self.newsletter_name}".

### 2. CERTIFICATI DELLA SETTIMANA
Per ciascuno dei seguenti 5 certificati, scrivi 3-4 frasi in italiano semplice:
- Spiega brevemente che tipo di certificato e' (Bull, Bear, Call, Put, ecc.)
- Se il tipo e' "Bull" o "Call", spiega che guadagna se il sottostante sale
- Se il tipo e' "Bear" o "Put", spiega che guadagna se il sottostante scende
- Se cedola_annua_perc e' 0.0, NON menzionare cedole — potrebbe essere un certificato a leva
- Se barriera_perc e' 0.0, NON menzionare la barriera — il dato non e' disponibile
- Usa SOLO i dati numerici forniti. Non inventare mai cifre
- NON dire mai "ti consiglio di comprare"
- Aggiungi sempre: "Questo non e' un consiglio di investimento."

Dati certificati:
{certs_text}

### 3. SPAZIO DIDATTICO (~200 parole)
Argomento di questa settimana: "{topic}"
Spiega questo concetto in modo chiaro e accessibile, con un esempio concreto.

### 4. OPPORTUNITA' IN EVIDENZA (~300 parole)
Analisi approfondita del certificato numero 1:
{top_cert_text}

Includi:
- Breve presentazione del sottostante (settore, contesto generale — senza inventare dati)
- Se disponibili (non 0.0), analizza barriera e margine di sicurezza
- Pro e contro basati SOLO sui dati forniti
- Se molti dati sono 0.0, dillo: "Alcuni dati tecnici non sono disponibili dalla fonte"
- Termina con un disclaimer chiaro

### 5. FOOTER
Includi:
- Placeholder per link di disiscrizione: [UNSUBSCRIBE_LINK]
- Disclaimer legale standard italiano sugli strumenti finanziari complessi
- "I certificati sono strumenti finanziari complessi che comportano il rischio di perdita
  del capitale investito. Questo contenuto ha scopo puramente informativo e non costituisce
  consulenza finanziaria, raccomandazione o sollecitazione all'investimento."

## STILE HTML
- Header: background #1a365d, testo bianco, border-radius 8px
- Intestazioni <h2> con color: #1a365d; font-size: 22px
- Testo: font-size: 16px; line-height: 1.6; color: #333333
- Certificati: background #f7fafc, border-left 4px solid #2563eb, padding 16px
- Separatori: <hr style="border: 1px solid #e2e8f0; margin: 30px 0;">
- Link: color: #2563eb
- Disclaimer footer: font-size: 12px; color: #666666
- Padding generale: 20px
- NON usare JavaScript
- NON includere immagini esterne

Genera SOLO il codice HTML."""

    def _format_certificates(self, certificates: list[Certificato]) -> str:
        """Formatta la lista di certificati per il prompt."""
        if not certificates:
            return "Nessun certificato disponibile."

        lines = []
        for i, c in enumerate(certificates, 1):
            parts = [
                f"{i}. {c.nome}",
                f"   ISIN: {c.isin}",
                f"   Emittente: {c.emittente}",
                f"   Sottostante: {c.sottostante}",
                f"   Tipo: {c.tipo}",
                f"   Scadenza: {c.scadenza}",
                f"   Prezzo attuale: {c.prezzo_attuale}",
            ]

            # Includi solo dati disponibili (non 0.0)
            if c.cedola_annua_perc > 0:
                parts.append(f"   Cedola annua: {c.cedola_annua_perc}%")
            else:
                parts.append("   Cedola annua: dato non disponibile")

            if c.barriera_perc > 0:
                parts.append(f"   Barriera: {c.barriera_perc}%")
            else:
                parts.append("   Barriera: dato non disponibile")

            if c.distanza_barriera_perc > 0:
                parts.append(f"   Distanza barriera: {c.distanza_barriera_perc}%")

            if c.prezzo_iniziale > 0:
                parts.append(f"   Prezzo iniziale (strike): {c.prezzo_iniziale}")

            if c.rendimento_annualizzato > 0:
                parts.append(f"   Rendimento annualizzato: {c.rendimento_annualizzato}%")

            parts.append(f"   Score: {c.opportunity_score}/100")

            lines.append("\n".join(parts))
        return "\n\n".join(lines)

    def _format_single_certificate(self, c: Certificato) -> str:
        """Formatta un singolo certificato per la sezione approfondita."""
        parts = [
            f"Nome: {c.nome}",
            f"ISIN: {c.isin}",
            f"Emittente: {c.emittente}",
            f"Sottostante: {c.sottostante}",
            f"Tipo: {c.tipo}",
            f"Scadenza: {c.scadenza}",
            f"Prezzo attuale: {c.prezzo_attuale}",
        ]

        if c.prezzo_iniziale > 0:
            parts.append(f"Prezzo iniziale (strike): {c.prezzo_iniziale}")

        if c.cedola_annua_perc > 0:
            parts.append(f"Cedola annua: {c.cedola_annua_perc}%")
        else:
            parts.append("Cedola annua: DATO NON DISPONIBILE — non menzionare cedole")

        if c.barriera_perc > 0:
            parts.append(f"Barriera: {c.barriera_perc}% (distanza: {c.distanza_barriera_perc}%)")
        else:
            parts.append("Barriera: DATO NON DISPONIBILE — non menzionare la barriera")

        if c.rendimento_annualizzato > 0:
            parts.append(f"Rendimento annualizzato: {c.rendimento_annualizzato}%")

        parts.append(f"Score: {c.opportunity_score}/100")

        if c.url_scheda:
            parts.append(f"Scheda: {c.url_scheda}")

        return "\n".join(parts)

    def _call_claude(self, prompt: str) -> str:
        """Chiama l'API Claude con retry automatico."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )

                html = message.content[0].text

                # Rimuovi eventuali code fence markdown
                if html.startswith("```"):
                    lines = html.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    html = "\n".join(lines)

                return html

            except Exception:
                logger.warning(
                    "Chiamata Claude fallita (tentativo %d/%d)",
                    attempt,
                    MAX_RETRIES,
                    exc_info=True,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_S)

        raise RuntimeError("Impossibile generare la newsletter dopo %d tentativi" % MAX_RETRIES)
