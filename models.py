"""Modelli dati Pydantic v2 per i certificati di investimento."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field


class Certificato(BaseModel):
    """Modello di un certificato di investimento quotato su SeDex."""

    isin: str = Field(description="Codice ISIN a 12 caratteri")
    nome: str = Field(description="Nome descrittivo del certificato")
    emittente: str = Field(default="", description="Es. Societe Generale, UniCredit")
    sottostante: str = Field(default="", description="Es. ENI, FTSE MIB, Tesla")
    tipo: str = Field(default="", description="Es. Cash Collect, Autocall, Bonus Cap")
    cedola_annua_perc: float = Field(default=0.0, description="Cedola annua in percentuale")
    barriera_perc: float = Field(
        default=0.0, description="Livello barriera come % del prezzo iniziale (es. 60.0)"
    )
    distanza_barriera_perc: float = Field(
        default=0.0, description="Distanza attuale dalla barriera in %. Positivo = sopra"
    )
    scadenza: Optional[date] = Field(default=None, description="Data di scadenza")
    prezzo_attuale: float = Field(default=0.0, description="Ultimo prezzo negoziato")
    prezzo_iniziale: float = Field(default=0.0, description="Prezzo iniziale / strike")
    rendimento_annualizzato: float = Field(default=0.0, description="Rendimento annualizzato %")
    url_scheda: str = Field(default="", description="URL alla scheda prodotto su Borsa Italiana")

    # Calcolato dallo screener
    opportunity_score: float = Field(
        default=0.0, description="Punteggio opportunita' 0-100 calcolato dallo screener"
    )

    def to_db_row(self) -> dict[str, Any]:
        """Converte in dizionario per l'inserimento in Supabase."""
        return {
            "isin": self.isin,
            "scraped_at": "now()",
            "opportunity_score": self.opportunity_score,
            "distanza_barriera_perc": self.distanza_barriera_perc,
            "prezzo_attuale": self.prezzo_attuale,
        }
