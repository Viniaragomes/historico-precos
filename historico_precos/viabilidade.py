"""Agente de viabilidade: testa cada fonte, roda os agentes numa amostra de produtos reais e mede.

O resultado é um relatório com números e uma decisão (seguir / não seguir) por métrica,
em vez de suposições.
"""

from __future__ import annotations

import json
import logging
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

from .agente import AgenteHistorico
from .armazenamento import Banco
from .causas import REFERENCIA
from .causas.analise import AgenteCausas
from .comparativo import comparar
from .fontes import openfoodfacts, vtex, wayback
from .leis import fontes as fontes_leis
from .mapa_df.agente import AgenteMapaDF
from .rede import Navegador

log = logging.getLogger(__name__)

TERMOS_AMOSTRA = [
    "café", "arroz", "feijão", "leite", "óleo de soja", "açúcar", "macarrão",
    "farinha de trigo", "biscoito", "manteiga", "sabão em pó", "papel higiênico", "creme dental",
]

# meta mínima de cada métrica para considerar a parte viável
METAS = {
    "preco_atual_2_lojas": 0.60,
    "historico_6_meses": 0.40,
    "preco_recente": 0.80,
    "mudancas_com_evidencia": 0.50,
}


@dataclass
class Sonda:
    fonte: str
    ok: bool
    detalhe: str


@dataclass
class ResultadoProduto:
    ean: str
    nome: str
    pontos: int
    lojas_hoje: int
    dias_historico: int
    dias_desde_ultimo: int | None
    mudancas: int
    mudancas_com_evidencia: int = 0


@dataclass
class Relatorio:
    data: str
    duracao_min: float
    sondas: list[Sonda]
    produtos: list[ResultadoProduto]
    metricas: dict[str, float | None] = field(default_factory=dict)
    veredito: dict[str, str] = field(default_factory=dict)


def _sonda(fonte: str, teste) -> Sonda:
    try:
        ok, detalhe = teste()
    except Exception as e:  # uma sonda quebrada não pode derrubar o relatório inteiro
        ok, detalhe = False, f"erro: {e}"
    return Sonda(fonte, ok, detalhe)


class AgenteViabilidade:
    def __init__(self, nav: Navegador, banco: Banco, lojas: list[dict]):
        self.nav = nav
        self.banco = banco
        self.lojas = lojas

    # ---------- 1. as fontes respondem? ----------

    def sondar(self) -> list[Sonda]:
        hoje = date.today()
        n = self.nav
        sondas = [
            _sonda(f"Loja VTEX: {l['nome']}", lambda l=l: (vtex.eh_vtex(n, l["dominio"]), l["dominio"]))
            for l in self.lojas
        ]
        sondas += [
            _sonda("Open Food Facts", lambda: (
                bool(openfoodfacts.buscar_texto(n, "café", 1)), "busca de produtos do Brasil")),
            _sonda("Wayback Machine (CDX)", lambda: (
                bool(wayback.listar_capturas(n, "www.carrefour.com.br", limite=3)), "lista de cópias arquivadas")),
            _sonda("Open Prices", lambda: (
                isinstance(n.get_json("https://prices.openfoodfacts.org/api/v1/prices?size=1"), dict), "API de preços")),
            _sonda("IBGE SIDRA (IPCA)", lambda: (
                isinstance(n.get_json("https://servicodados.ibge.gov.br/api/v3/agregados/7060/metadados"), dict),
                "metadados da tabela 7060")),
            _sonda("Banco Central (SGS)", lambda: (
                bool(n.get_json(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/5?formato=json")),
                "série 1 (dólar)")),
            _sonda("GDELT (notícias)", lambda: (
                isinstance(n.get_json("https://api.gdeltproject.org/api/v2/doc/doc?query="
                                      + quote("café sourcecountry:BR") + "&mode=artlist&format=json&maxrecords=5"), dict),
                "busca de notícias")),
            _sonda("Diário Oficial da União", lambda: self._sonda_dou(hoje)),
            _sonda("Mapa de Preços do DF", self._sonda_mapa_df),
        ]
        return sondas

    def _sonda_dou(self, hoje: date):
        pubs = fontes_leis.buscar_dou(self.nav, "ICMS", hoje - timedelta(days=30), hoje)
        return bool(pubs), f"{len(pubs)} publicações sobre ICMS nos últimos 30 dias"

    def _sonda_mapa_df(self):
        desc = AgenteMapaDF(self.nav, self.banco).descobrir()
        if desc is None:
            return False, "painel não abriu"
        if desc.paineis_embutidos:
            return False, "dashboard embutido (Power BI/Qlik): coleta por formulário inviável"
        return bool(desc.formularios), f"{len(desc.formularios)} formulário(s), {len(desc.endpoints)} endereço(s) de consulta"

    # ---------- 2. amostra de produtos reais ----------

    def montar_amostra(self, tamanho: int, termos: list[str] = TERMOS_AMOSTRA) -> list[tuple[str, str]]:
        por_termo = max(1, -(-tamanho // len(termos)))  # divisão arredondando para cima
        amostra: dict[str, str] = {}
        for termo in termos:
            achados: list[tuple[str, str]] = []
            for loja in self.lojas:
                achados += vtex.buscar_texto(self.nav, loja, termo, por_termo)
                if len(achados) >= por_termo:
                    break
            if len(achados) < por_termo:
                achados += openfoodfacts.buscar_texto(self.nav, termo, por_termo)
            for ean, nome in achados[:por_termo]:
                amostra.setdefault(ean, nome)
        return list(amostra.items())[:tamanho]

    # ---------- 3. rodar e medir ----------

    def medir_produto(self, ean: str, nome: str, max_capturas: int, analisar_causas: bool) -> ResultadoProduto:
        AgenteHistorico(self.nav, self.banco, self.lojas).executar(ean, usar_wayback=True, max_capturas=max_capturas)
        pontos = self.banco.precos(ean)
        hoje = date.today()
        datas = sorted(date.fromisoformat(p.data_observada) for p in pontos)
        comp = comparar(pontos, hoje=hoje, max_dias=7)
        resultado = ResultadoProduto(
            ean=ean,
            nome=nome,
            pontos=len(pontos),
            lojas_hoje=len(comp.ofertas),
            dias_historico=(datas[-1] - datas[0]).days if datas else 0,
            dias_desde_ultimo=(hoje - datas[-1]).days if datas else None,
            mudancas=0,
        )
        if analisar_causas:
            _, explicacoes = AgenteCausas(self.nav, self.banco).explicar(ean)
            resultado.mudancas = len(explicacoes)
            resultado.mudancas_com_evidencia = sum(
                1 for ex in explicacoes if any(e.nivel != REFERENCIA for e in ex.evidencias)
            )
        return resultado

    def executar(self, tamanho: int = 60, max_capturas: int = 10, produtos_com_causas: int = 15,
                 arquivo_amostra: Path | None = None) -> Relatorio:
        inicio = time.monotonic()
        sondas = self.sondar()
        amostra = self.montar_amostra(tamanho)
        if arquivo_amostra:
            arquivo_amostra.parent.mkdir(parents=True, exist_ok=True)
            arquivo_amostra.write_text("".join(f"{e}\t{n}\n" for e, n in amostra), encoding="utf-8")
        produtos = []
        for i, (ean, nome) in enumerate(amostra):
            log.info("(%d/%d) %s %s", i + 1, len(amostra), ean, nome)
            produtos.append(self.medir_produto(ean, nome, max_capturas, analisar_causas=i < produtos_com_causas))
        rel = Relatorio(date.today().isoformat(), round((time.monotonic() - inicio) / 60, 1), sondas, produtos)
        rel.metricas, rel.veredito = calcular_metricas(produtos, produtos_com_causas)
        return rel


def calcular_metricas(produtos: list[ResultadoProduto], com_causas: int) -> tuple[dict, dict]:
    def fracao(condicao, grupo):
        return round(sum(1 for p in grupo if condicao(p)) / len(grupo), 3) if grupo else None

    analisados = produtos[:com_causas]
    total_mudancas = sum(p.mudancas for p in analisados)
    metricas = {
        "produtos_na_amostra": len(produtos),
        "preco_qualquer_fonte": fracao(lambda p: p.pontos > 0, produtos),
        "preco_atual_2_lojas": fracao(lambda p: p.lojas_hoje >= 2, produtos),
        "historico_6_meses": fracao(lambda p: p.dias_historico >= 180, produtos),
        "preco_recente": fracao(lambda p: p.dias_desde_ultimo is not None and p.dias_desde_ultimo <= 7, produtos),
        "mediana_dias_historico": statistics.median([p.dias_historico for p in produtos]) if produtos else None,
        "mudancas_analisadas": total_mudancas,
        "mudancas_com_evidencia": (round(sum(p.mudancas_com_evidencia for p in analisados) / total_mudancas, 3)
                                   if total_mudancas else None),
    }
    veredito = {}
    for chave, meta in METAS.items():
        valor = metricas[chave]
        if valor is None:
            veredito[chave] = "sem dados"
        else:
            veredito[chave] = "VIÁVEL" if valor >= meta else "ABAIXO DA META"
    return metricas, veredito


NOMES = {
    "preco_atual_2_lojas": "Preço de hoje em 2 ou mais lojas",
    "historico_6_meses": "Histórico de 6 meses ou mais",
    "preco_recente": "Último preço com até 7 dias",
    "mudancas_com_evidencia": "Mudanças com evidência além da categoria",
}


def para_markdown(rel: Relatorio) -> str:
    def pct(v):
        return "—" if v is None else f"{v * 100:.0f}%"

    linhas = [
        f"# Relatório de viabilidade: {rel.data}",
        "",
        f"Duração: {rel.duracao_min} min. Produtos na amostra: {rel.metricas.get('produtos_na_amostra')}.",
        "",
        "## Fontes",
        "",
        "| Fonte | Responde? | Detalhe |",
        "|---|---|---|",
    ]
    linhas += [f"| {s.fonte} | {'✅' if s.ok else '❌'} | {s.detalhe} |" for s in rel.sondas]
    linhas += ["", "## Métricas", "", "| Métrica | Resultado | Meta | Decisão |", "|---|---|---|---|"]
    for chave, meta in METAS.items():
        linhas.append(f"| {NOMES[chave]} | {pct(rel.metricas.get(chave))} | {pct(meta)} | {rel.veredito.get(chave)} |")
    linhas += [
        "",
        f"- Produtos com algum preço encontrado: {pct(rel.metricas.get('preco_qualquer_fonte'))}",
        f"- Mediana de dias de histórico por produto: {rel.metricas.get('mediana_dias_historico')}",
        f"- Mudanças de preço analisadas para causas: {rel.metricas.get('mudancas_analisadas')}",
        "",
        "## Produtos",
        "",
        "| EAN | Produto | Pontos | Lojas hoje | Dias de histórico | Último preço há | Mudanças (com evidência) |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in rel.produtos:
        ultimo = "—" if p.dias_desde_ultimo is None else f"{p.dias_desde_ultimo} d"
        linhas.append(f"| {p.ean} | {p.nome[:50]} | {p.pontos} | {p.lojas_hoje} | {p.dias_historico} | {ultimo} | "
                      f"{p.mudancas} ({p.mudancas_com_evidencia}) |")
    linhas += ["", "_Gerado automaticamente pelo agente de viabilidade. Nenhum número deste relatório é estimado._", ""]
    return "\n".join(linhas)


def salvar(rel: Relatorio, pasta: Path) -> tuple[Path, Path]:
    pasta.mkdir(parents=True, exist_ok=True)
    md = pasta / f"viabilidade-{rel.data}.md"
    js = pasta / f"viabilidade-{rel.data}.json"
    md.write_text(para_markdown(rel), encoding="utf-8")
    js.write_text(json.dumps(asdict(rel), ensure_ascii=False, indent=2), encoding="utf-8")
    return md, js
