# Mondo Certificati

Newsletter settimanale automatica sui certificati di investimento, pensata per
investitori italiani che vogliono capire come funzionano questi strumenti e
scoprire le opportunita' piu' interessanti del mercato.

Ogni martedi' il sistema raccoglie i dati da Borsa Italiana, seleziona i
certificati piu' interessanti, scrive la newsletter con l'intelligenza
artificiale e la invia tramite Beehiiv.

---

## Come funziona (in parole semplici)

1. **Raccolta dati** — Un programma visita il sito di Borsa Italiana e legge
   tutti i certificati disponibili sul mercato SeDex.
2. **Selezione** — Un algoritmo assegna un punteggio (da 0 a 100) a ogni
   certificato, basandosi su cedola, distanza dalla barriera e scadenza.
   Sceglie i 5 migliori.
3. **Scrittura** — L'intelligenza artificiale (Claude di Anthropic) scrive la
   newsletter in italiano: introduce i certificati scelti, spiega un concetto
   didattico e analizza in dettaglio il certificato migliore.
4. **Invio** — La newsletter viene pubblicata su Beehiiv e programmata per
   l'invio il martedi' mattina alle 9:00.
5. **Archiviazione** — Tutti i dati vengono salvati in un database (Supabase)
   per tenere uno storico.

---

## Setup in 5 passi

### 1. Creare un account Beehiiv

Vai su [beehiiv.com](https://www.beehiiv.com), registrati e crea una nuova
pubblicazione. Poi vai su **Settings > Integrations > API** e copia:
- La **API Key**
- Il **Publication ID**

### 2. Creare un account Supabase

Vai su [supabase.com](https://supabase.com), registrati e crea un nuovo
progetto. Poi vai su **Settings > API** e copia:
- La **URL** del progetto
- La **anon key**

Infine, vai nell'**SQL Editor** e incolla il contenuto del file
`storage/schema.sql` per creare le tabelle.

### 3. Ottenere la API key di Anthropic

Vai su [console.anthropic.com](https://console.anthropic.com), registrati,
vai su **Settings > API Keys** e crea una nuova chiave.

### 4. Compilare il file .env

Copia il file `.env.example` e rinominalo in `.env`:

```
cp .env.example .env
```

Apri `.env` con un editor di testo e incolla le chiavi che hai copiato nei
passi precedenti.

### 5. Pubblicare su GitHub e attivare Actions

Crea un nuovo repository su GitHub, carica tutti i file e vai su
**Settings > Secrets and variables > Actions**. Aggiungi questi segreti:

- `ANTHROPIC_API_KEY`
- `BEEHIIV_API_KEY`
- `BEEHIIV_PUBLICATION_ID`
- `SUPABASE_URL`
- `SUPABASE_KEY`

La newsletter partira' automaticamente ogni martedi' alle 8:00 (ora italiana).

---

## Come testare manualmente

```bash
python main.py --dry-run
```

Questo comando esegue tutto il processo ma senza inviare la newsletter.
Salva il risultato in un file HTML che puoi aprire nel browser per controllare
come appare.

---

## Disclaimer

Questo progetto ha scopo puramente educativo e informativo. Non fornisce
consulenza finanziaria. I certificati di investimento sono strumenti
finanziari complessi che comportano rischi, inclusa la possibile perdita
del capitale investito.
