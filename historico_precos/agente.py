"""Orquestra a varredura: identifica o produto, busca em cada fonte, guarda tudo e aponta as mudanças."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from itertools import groupby

from .armazenamento import Banco
from .fontes import openfoodfacts, openprices, pagina_produto, vtex, wayback
from .modelo import PontoDePreco, Produto
from .rede import Navegador

log = logging.getLogger(__name__)


@dataclass
class Mudanca:
    loja: str
    data_anterior: str
    data_nova: str
    preco_anterior: float
    preco_novo: float
    evidencia_anterior: str
    evidencia_nova: str

    @property
    def variacao_pct(self) -> float:
        return (self.preco_novo / self.preco_anterior - 1) * 100


@dataclass
class Relatorio:
    produto: Produto
    pontos: list[PontoDePreco]
    novos: int
    mudancas: list[Mudanca] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def detectar_mudancas(pontos: list[PontoDePreco], tolerancia_pct: float = 0.5) -> list[Mudanca]:
    """Compara preços consecutivos da mesma loja e registra cada alta ou queda acima da tolerância."""
    mudancas = []
    por_loja = sorted(pontos, key=lambda p: (p.loja, p.data_observada))
    for loja, grupo in groupby(por_loja, key=lambda p: p.loja):
        anterior = None
        for ponto in grupo:
            if anterior and abs(ponto.preco / anterior.preco - 1) * 100 > tolerancia_pct:
                mudancas.append(
                    Mudanca(
                        loja=loja,
                        data_anterior=anterior.data_observada,
                        data_nova=ponto.data_observada,
                        preco_anterior=anterior.preco,
                        preco_novo=ponto.preco,
                        evidencia_anterior=anterior.url_evidencia,
                        evidencia_nova=ponto.url_evidencia,
                    )
                )
            anterior = ponto
    return sorted(mudancas, key=lambda m: m.data_nova)


class AgenteHistorico:
    def __init__(self, nav: Navegador, banco: Banco, lojas: list[dict]):
        self.nav = nav
        self.banco = banco
        self.lojas = lojas

    def executar(
        self,
        ean: str,
        usar_wayback: bool = True,
        max_capturas: int = 40,
        urls_extras: list[tuple[str, str]] | None = None,
    ) -> Relatorio:
        """`urls_extras`: [(nome_da_loja, url_da_pagina)] para páginas que você já conhece."""
        avisos = []
        produto = openfoodfacts.identificar(self.nav, ean)
        if produto.nome is None and (conhecido := self.banco.produto(ean)):
            produto = conhecido
        self.banco.salvar_produto(produto)

        coletados: list[PontoDePreco] = []
        paginas: list[tuple[str, str]] = list(urls_extras or [])

        for loja in self.lojas:
            if loja.get("tipo", "vtex") != "vtex":
                continue
            log.info("VTEX: %s", loja["nome"])
            pontos, links = vtex.buscar_por_ean(self.nav, loja, ean)
            coletados += pontos
            paginas += [(loja["nome"], link) for link in links]
            if not pontos and not links:
                avisos.append(f"{loja['nome']}: produto não encontrado (ou loja fora do ar / não é VTEX)")

        # lojas lidas pela página pública do produto (JSON-LD), achada no sitemap (comando catalogo-sitemap)
        por_pagina = {l["nome"]: l for l in self.lojas if l.get("tipo") == "sitemap"}
        for loja, url in self.banco.paginas(ean):
            if loja in por_pagina:
                _, ponto = pagina_produto.ler(self.nav, url, loja, por_pagina[loja].get("cidade"))
                if ponto and ponto.ean == ean:
                    coletados.append(ponto)
                else:
                    avisos.append(f"{loja}: sem preço na página {url} (fora de estoque ou fora do ar)")

        # lojas que bloqueiam robôs: só cópias arquivadas, já catalogadas (comando catalogo-wayback)
        arquivo = {l["nome"] for l in self.lojas if l.get("tipo") == "arquivo"}
        paginas += [(loja, url) for loja, url in self.banco.paginas(ean) if loja in arquivo]

        if usar_wayback:
            for nome_loja, url in dict.fromkeys(paginas):
                log.info("Wayback: %s", url)
                achados = wayback.historico(self.nav, url, ean, nome_loja, max_capturas)
                if not achados:
                    avisos.append(f"Wayback: nenhuma cópia antiga com preço para {url}")
                coletados += achados

        coletados += openprices.buscar(self.nav, ean)

        novos = self.banco.salvar_precos(coletados)
        todos = self.banco.precos(ean)
        return Relatorio(produto, todos, novos, detectar_mudancas(todos), avisos)
