"""Séries oficiais em JSON público: Banco Central (SGS) e IBGE (SIDRA)."""

from __future__ import annotations

import unicodedata
from datetime import date, timedelta
from urllib.parse import quote

from ..rede import Navegador

SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial={ini}&dataFinal={fim}"
SIDRA = "https://servicodados.ibge.gov.br/api/v3/agregados"
TABELA_IPCA = "7060"  # IPCA a partir de jan/2020
VARIAVEL_VARIACAO_MENSAL = "63"
CLASSIFICACAO_SUBITENS = "315"


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower().strip()


def _br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def serie_bcb(nav: Navegador, codigo: int, inicio: date, fim: date) -> dict[date, float]:
    dado = nav.get_json(SGS.format(codigo=codigo, ini=_br(inicio), fim=_br(fim)))
    serie = {}
    for linha in dado or []:
        try:
            d, m, a = linha["data"].split("/")
            serie[date(int(a), int(m), int(d))] = float(linha["valor"])
        except (KeyError, ValueError):
            continue
    return serie


def valor_em(serie: dict[date, float], dia: date) -> float | None:
    """Último valor disponível até o dia (séries diárias não têm fim de semana)."""
    anteriores = [d for d in serie if d <= dia]
    return serie[max(anteriores)] if anteriores else None


def variacao_nivel(serie: dict[date, float], inicio: date, fim: date) -> float | None:
    a, b = valor_em(serie, inicio), valor_em(serie, fim)
    if not a or b is None:
        return None
    return (b / a - 1) * 100


def acumular_mensal(variacoes_pct: dict[str, float], inicio: date, fim: date) -> float | None:
    """Compõe variações mensais (chave AAAAMM) dos meses depois de `inicio` até o mês de `fim`."""
    mes_ini = inicio.year * 100 + inicio.month
    mes_fim = fim.year * 100 + fim.month
    meses = sorted(k for k in variacoes_pct if mes_ini < int(k) <= mes_fim)
    if not meses:
        return None
    fator = 1.0
    for k in meses:
        fator *= 1 + variacoes_pct[k] / 100
    return (fator - 1) * 100


def achar_subitem_ipca(nav: Navegador, nome: str) -> tuple[str, str] | None:
    """Procura o código do subitem do IPCA pelo nome (ex.: 'Café moído') nos metadados do IBGE."""
    meta = nav.get_json(f"{SIDRA}/{TABELA_IPCA}/metadados")
    if not isinstance(meta, dict):
        return None
    alvo = normalizar(nome)
    for classificacao in meta.get("classificacoes", []):
        if str(classificacao.get("id")) != CLASSIFICACAO_SUBITENS:
            continue
        categorias = classificacao.get("categorias", [])
        exatas = [c for c in categorias if normalizar(c["nome"]).split(".", 1)[-1] == alvo]
        parciais = [c for c in categorias if alvo in normalizar(c["nome"])]
        escolhida = (exatas or parciais or [None])[0]
        if escolhida:
            return str(escolhida["id"]), escolhida["nome"]
    return None


def ipca_subitem(nav: Navegador, id_subitem: str, localidade: str, inicio: date, fim: date) -> dict[str, float]:
    """Variação mensal (%) do subitem, chave AAAAMM. `localidade` no formato do SIDRA, ex.: N6[5300108]."""
    periodos = []
    d = date(inicio.year, inicio.month, 1)
    while d <= fim:
        periodos.append(f"{d.year}{d.month:02d}")
        d = (d + timedelta(days=32)).replace(day=1)
    url = (
        f"{SIDRA}/{TABELA_IPCA}/periodos/{'|'.join(periodos)}/variaveis/{VARIAVEL_VARIACAO_MENSAL}"
        f"?localidades={quote(localidade)}&classificacao={CLASSIFICACAO_SUBITENS}[{id_subitem}]"
    )
    dado = nav.get_json(url)
    resultado = {}
    try:
        serie = dado[0]["resultados"][0]["series"][0]["serie"]
    except (TypeError, IndexError, KeyError):
        return {}
    for periodo, valor in serie.items():
        try:
            resultado[periodo] = float(valor)
        except (TypeError, ValueError):  # o IBGE usa "-", "..." etc. para dado ausente
            continue
    return resultado
