"""Explica cada mudança de preço juntando as evidências, cada uma com seu nível de prova."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from ..agente import Mudanca, detectar_mudancas
from ..armazenamento import Banco
from ..modelo import PontoDePreco
from ..rede import Navegador
from . import A_CONFIRMAR, ASSOCIADO, COMPROVADO, DECLARADO, REFERENCIA, embalagem, noticias, series, tributos
from .series import normalizar

log = logging.getLogger(__name__)

CATEGORIAS_PADRAO = Path(__file__).resolve().parents[2] / "categorias.json"


def _pct(v: float) -> str:
    """+2,5% (vírgula decimal, como se lê no Brasil)."""
    return f"{v:+.1f}%".replace(".", ",")


def _aliq(v: float) -> str:
    return f"{v:g}".replace(".", ",")


@dataclass
class Evidencia:
    nivel: str
    tipo: str
    descricao: str
    efeito_pct: float | None = None  # só preenchido quando o efeito é calculável
    fontes: list[str] = field(default_factory=list)


@dataclass
class Explicacao:
    mudanca: Mudanca
    evidencias: list[Evidencia]

    @property
    def comprovado_pct(self) -> float:
        """Parte da variação explicada só por fatos comprovados (efeitos compostos)."""
        fator = 1.0
        for e in self.evidencias:
            if e.nivel == COMPROVADO and e.efeito_pct is not None and e.tipo == "imposto":
                fator *= 1 + e.efeito_pct / 100
        return (fator - 1) * 100

    @property
    def nao_explicado_pct(self) -> float:
        """O que sobra da variação depois de descontar o que foi comprovado."""
        total = 1 + self.mudanca.variacao_pct / 100
        return (total / (1 + self.comprovado_pct / 100) - 1) * 100


def carregar_categorias(caminho: Path | str = CATEGORIAS_PADRAO) -> dict:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def detectar_categoria(categorias: dict, *textos: str | None) -> str | None:
    texto = normalizar(" ".join(t for t in textos if t))
    for chave, cat in categorias["categorias"].items():
        if any(normalizar(p) in texto for p in cat["palavras"]):
            return chave
    return None


class AgenteCausas:
    def __init__(
        self,
        nav: Navegador,
        banco: Banco,
        categorias: dict | None = None,
        eventos: list[tributos.EventoTributario] | None = None,
        usar_noticias: bool = True,
    ):
        self.nav = nav
        self.banco = banco
        self.cfg = categorias or carregar_categorias()
        self.eventos = eventos if eventos is not None else tributos.carregar()
        self.usar_noticias = usar_noticias
        self._cache_subitem: dict[str, tuple[str, str] | None] = {}

    def explicar(self, ean: str, uf: str = "DF", categoria: str | None = None) -> tuple[str | None, list[Explicacao]]:
        pontos = self.banco.precos(ean)
        produto = self.banco.produto(ean)
        if categoria is None:
            categoria = detectar_categoria(
                self.cfg, produto.nome if produto else None, *(p.descricao for p in pontos)
            )
        explicacoes = []
        for m in detectar_mudancas(pontos):
            antes, depois = self._pontos_da_mudanca(pontos, m)
            explicacoes.append(Explicacao(m, self._evidencias(m, antes, depois, uf, categoria)))
        return categoria, explicacoes

    @staticmethod
    def _pontos_da_mudanca(pontos: list[PontoDePreco], m: Mudanca) -> tuple[PontoDePreco, PontoDePreco]:
        def achar(data, preco):
            return next(p for p in pontos if p.loja == m.loja and p.data_observada == data and abs(p.preco - preco) < 0.005)

        return achar(m.data_anterior, m.preco_anterior), achar(m.data_nova, m.preco_novo)

    def _evidencias(self, m: Mudanca, antes: PontoDePreco, depois: PontoDePreco, uf: str, categoria: str | None):
        ini, fim = date.fromisoformat(m.data_anterior), date.fromisoformat(m.data_nova)
        cat = self.cfg["categorias"].get(categoria, {}) if categoria else {}
        evidencias: list[Evidencia] = []

        # 1. Imposto: lei com data de vigência dentro do período -> efeito calculável
        for e in tributos.no_periodo(self.eventos, uf, categoria, ini, fim):
            if e.calculo == "sem_efeito":  # ex.: teste da reforma em 2026, compensado; não explica mudança de preço
                continue
            nivel = COMPROVADO if e.verificado else A_CONFIRMAR
            alcance = "" if categoria in e.categorias else f" Vale para: {e.abrangencia}."
            evidencias.append(
                Evidencia(
                    nivel,
                    "imposto",
                    f"{e.tributo} ({e.uf}) passou de {_aliq(e.aliquota_anterior)}% para {_aliq(e.aliquota_nova)}% "
                    f"em {e.vigencia:%d/%m/%Y}. Se repassado por inteiro, explica {_pct(e.efeito_pct())} do preço."
                    f"{alcance} {e.observacao}".strip(),
                    e.efeito_pct(),
                    e.fontes,
                )
            )

        # 2. Embalagem: o próprio nome do produto nas duas datas mostra a quantidade
        troca = embalagem.comparar(antes.descricao, depois.descricao, antes.preco, depois.preco)
        if troca:
            qa, qd, un, var_unit = troca
            evidencias.append(
                Evidencia(
                    COMPROVADO,
                    "embalagem",
                    f"A embalagem mudou de {qa:g}{un} para {qd:g}{un}. O preço por {'kg' if un == 'g' else 'litro'} "
                    f"variou {_pct(var_unit)}, "
                    f"contra {_pct(m.variacao_pct)} no preço da prateleira.",
                    var_unit,
                    [antes.url_evidencia, depois.url_evidencia],
                )
            )

        # 3. Referência: o que a mesma categoria fez na cidade (IPCA do IBGE)
        if cat.get("ipca_subitem"):
            evidencias += self._referencia_ipca(cat["ipca_subitem"], uf, ini, fim, m.variacao_pct)

        # 4. Indicadores associados (câmbio, commodities), com defasagem
        for s in cat.get("series_bcb", []) + self.cfg.get("series_bcb_gerais", []):
            defasagem = timedelta(days=30 * s.get("defasagem_meses", 0))
            serie = series.serie_bcb(self.nav, s["codigo"], ini - defasagem - timedelta(days=10), fim - defasagem)
            var = series.variacao_nivel(serie, ini - defasagem, fim - defasagem)
            if var is None:
                continue
            quando = f" (período deslocado {s['defasagem_meses']} meses antes)" if s.get("defasagem_meses") else ""
            evidencias.append(
                Evidencia(
                    ASSOCIADO,
                    "indicador",
                    f"{s['nome']} variou {_pct(var)} no período{quando}.",
                    None,
                    [f"https://www3.bcb.gov.br/sgspub/ (série {s['codigo']})"],
                )
            )

        # 5. Causas declaradas na imprensa durante o período
        if self.usar_noticias and cat.get("termos_noticia"):
            for n in noticias.buscar(self.nav, cat["termos_noticia"], ini - timedelta(days=60), fim)[:8]:
                evidencias.append(
                    Evidencia(DECLARADO, "noticia", f"{n.data} {n.veiculo}: \"{n.titulo}\" -> {', '.join(n.motivos)}",
                              None, [n.url])
                )
        return evidencias

    def _referencia_ipca(self, nome_subitem: str, uf: str, ini: date, fim: date, variacao_produto: float):
        if nome_subitem not in self._cache_subitem:
            self._cache_subitem[nome_subitem] = series.achar_subitem_ipca(self.nav, nome_subitem)
        achado = self._cache_subitem[nome_subitem]
        if not achado:
            return []
        id_subitem, nome = achado
        localidades = self.cfg.get("localidades_ipca", {})
        for rotulo, localidade in ((uf, localidades.get(uf)), ("Brasil", "N1[all]")):
            if not localidade:
                continue
            var = series.acumular_mensal(series.ipca_subitem(self.nav, id_subitem, localidade, ini, fim), ini, fim)
            if var is None:
                continue
            diferenca = variacao_produto - var
            return [
                Evidencia(
                    REFERENCIA,
                    "categoria",
                    f"IPCA de '{nome}' ({rotulo}) acumulou {_pct(var)} de {ini:%m/%Y} a {fim:%m/%Y}. "
                    f"Este produto variou {_pct(diferenca)[:-1]} pontos em relação à categoria.",
                    var,
                    [f"https://sidra.ibge.gov.br/tabela/{series.TABELA_IPCA}"],
                )
            ]
        return []
