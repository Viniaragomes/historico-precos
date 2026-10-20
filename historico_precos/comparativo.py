"""Compara o preço mais recente de um produto em cada loja e mostra onde está mais barato."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .modelo import PontoDePreco


@dataclass
class Oferta:
    loja: str
    preco: float
    preco_de: float | None
    data: str
    dias: int  # idade do preço
    fonte: str
    cidade: str | None
    evidencia: str
    diferenca_rs: float = 0.0  # em relação à mais barata
    diferenca_pct: float = 0.0

    @property
    def em_promocao(self) -> bool:
        return self.preco_de is not None and self.preco_de > self.preco

    @property
    def desatualizado(self) -> bool:
        return self.dias > 7


@dataclass
class Comparativo:
    ean: str
    ofertas: list[Oferta]  # da mais barata para a mais cara
    ignoradas: list[Oferta]  # preços antigos demais para comparar

    @property
    def mais_barata(self) -> Oferta | None:
        return self.ofertas[0] if self.ofertas else None

    @property
    def media(self) -> float | None:
        return sum(o.preco for o in self.ofertas) / len(self.ofertas) if self.ofertas else None

    @property
    def economia_maxima(self) -> float:
        """Quanto se economiza comprando na mais barata em vez da mais cara."""
        return self.ofertas[-1].preco - self.ofertas[0].preco if len(self.ofertas) > 1 else 0.0


def comparar(
    pontos: list[PontoDePreco], hoje: date | None = None, max_dias: int = 30, cidade: str | None = None
) -> Comparativo:
    """Usa o preço mais recente de cada loja. Preços com mais de `max_dias` ficam fora da comparação."""
    hoje = hoje or date.today()
    ultimo: dict[str, PontoDePreco] = {}
    for p in pontos:
        if cidade and p.cidade and p.cidade.lower() != cidade.lower():
            continue
        atual = ultimo.get(p.loja)
        # no mesmo dia, fica o menor preço (ex.: dois vendedores na mesma loja)
        if atual is None or p.data_observada > atual.data_observada or (
            p.data_observada == atual.data_observada and p.preco < atual.preco
        ):
            ultimo[p.loja] = p

    validas, ignoradas = [], []
    for p in ultimo.values():
        dias = (hoje - date.fromisoformat(p.data_observada)).days
        oferta = Oferta(p.loja, p.preco, p.preco_de, p.data_observada, dias, p.fonte, p.cidade, p.url_evidencia)
        (validas if dias <= max_dias else ignoradas).append(oferta)

    validas.sort(key=lambda o: (o.preco, o.dias))
    if validas:
        base = validas[0].preco
        for o in validas:
            o.diferenca_rs = o.preco - base
            o.diferenca_pct = (o.preco / base - 1) * 100
    return Comparativo(pontos[0].ean if pontos else "", validas, sorted(ignoradas, key=lambda o: o.preco))
