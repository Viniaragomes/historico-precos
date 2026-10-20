"""Mudanças de imposto documentadas (eventos_tributarios.json) e seu efeito mecânico no preço."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ARQUIVO_PADRAO = Path(__file__).resolve().parents[2] / "eventos_tributarios.json"


@dataclass
class EventoTributario:
    id: str
    tributo: str
    uf: str  # "BR" para tributos federais
    vigencia: date
    aliquota_anterior: float  # em %
    aliquota_nova: float
    calculo: str  # "por_dentro" (ICMS) | "por_fora" | "sem_efeito"
    abrangencia: str  # descrição de quais produtos são atingidos
    categorias: list[str]  # categorias atingidas, ou ["*"] para alíquota geral/modal
    verificado: bool  # fonte oficial (lei/decreto) conferida por uma pessoa
    fontes: list[str]
    observacao: str = ""

    def efeito_pct(self) -> float:
        """Quanto o preço sobe se o imposto for repassado por inteiro."""
        a, b = self.aliquota_anterior / 100, self.aliquota_nova / 100
        if self.calculo == "por_dentro":  # imposto embutido na própria base, como o ICMS
            return ((1 - a) / (1 - b) - 1) * 100
        if self.calculo == "por_fora":
            return ((1 + b) / (1 + a) - 1) * 100
        return 0.0


def carregar(caminho: Path | str = ARQUIVO_PADRAO) -> list[EventoTributario]:
    dado = json.loads(Path(caminho).read_text(encoding="utf-8"))
    eventos = []
    for e in dado["eventos"]:
        e = dict(e)
        e["vigencia"] = date.fromisoformat(e["vigencia"])
        eventos.append(EventoTributario(**e))
    return eventos


def no_periodo(eventos: list[EventoTributario], uf: str, categoria: str | None, inicio: date, fim: date):
    for e in eventos:
        if e.uf not in (uf, "BR") or not (inicio < e.vigencia <= fim):
            continue
        if "*" in e.categorias or (categoria and categoria in e.categorias):
            yield e
