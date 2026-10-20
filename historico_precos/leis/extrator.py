"""Lê o texto de uma norma e extrai o que interessa: tributo, alíquotas, vigência e produtos atingidos.

É feito com regras simples e visíveis, sem IA, para que qualquer extração possa ser conferida.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from ..causas.series import normalizar

TRIBUTOS = {
    "ICMS": ["icms", "imposto sobre operacoes relativas a circulacao de mercadorias"],
    "IPI": ["ipi", "imposto sobre produtos industrializados"],
    "PIS/Cofins": ["pis/pasep", "cofins", "pis e cofins", "pis/cofins"],
    "CBS": ["cbs", "contribuicao social sobre bens e servicos"],
    "IBS": ["ibs", "imposto sobre bens e servicos"],
    "Imposto Seletivo": ["imposto seletivo"],
}
PALAVRAS_ALIQUOTA = ["aliquota", "carga tributaria", "reducao de base de calculo", "isencao", "isento"]
MESES = {m: i for i, m in enumerate(
    ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho",
     "agosto", "setembro", "outubro", "novembro", "dezembro"], start=1)}

_NUM = r"(\d{1,2}(?:,\d{1,2})?)"
_RE_DE_PARA = re.compile(_NUM + r"\s*%[^.;%]{0,60}?\bpara\s+" + _NUM + r"\s*%")
_RE_DE_PARA_2 = re.compile(r"\bde\s+" + _NUM + r"\s*%\s*(?:\([^)]{0,40}\)\s*)?para\s+" + _NUM + r"\s*%")
_RE_PERCENT = re.compile(_NUM + r"\s*%")
_RE_VIG_EXTENSO = re.compile(
    r"(?:a partir de|vigor em|efeitos a partir de|produz(?:indo)? efeitos? (?:a partir )?de)\s+"
    r"(\d{1,2})[ºo°]?\s+de\s+([a-z]+)\s+de\s+(\d{4})"
)
_RE_VIG_NUM = re.compile(
    r"(?:a partir de|vigor em|efeitos a partir de|produz(?:indo)? efeitos? (?:a partir )?de)\s+"
    r"(\d{1,2})[ºo°]?/(\d{1,2})/(\d{4})"
)


@dataclass
class Extracao:
    tributos: list[str]
    aliquota_anterior: float | None
    aliquota_nova: float | None
    percentuais: list[float]
    vigencia: date | None
    categorias: list[str]
    pontuacao: int  # quanto maior, mais provável que mude imposto de produto de mercado
    trecho: str = ""
    motivos: list[str] = field(default_factory=list)


def _f(numero: str) -> float:
    return float(numero.replace(",", "."))


def _tem(texto: str, termo: str) -> bool:
    # siglas curtas (ibs, cbs, ipi) precisam ser palavra inteira
    if len(termo) <= 4:
        return re.search(rf"\b{re.escape(termo)}\b", texto) is not None
    return termo in texto


def _vigencia(texto: str) -> date | None:
    for achado in _RE_VIG_EXTENSO.finditer(texto):
        dia, mes, ano = achado.groups()
        if mes in MESES:
            try:
                return date(int(ano), MESES[mes], int(dia))
            except ValueError:
                continue
    for achado in _RE_VIG_NUM.finditer(texto):
        dia, mes, ano = achado.groups()
        try:
            return date(int(ano), int(mes), int(dia))
        except ValueError:
            continue
    return None


def _trecho(original: str, normal: str, chaves: list[str], tamanho: int = 320) -> str:
    """Pedaço do texto original em volta da primeira menção relevante, para a pessoa conferir."""
    posicoes = [normal.find(c) for c in chaves if normal.find(c) >= 0]
    inicio = max(0, min(posicoes) - tamanho // 3) if posicoes else 0
    return " ".join(original[inicio:inicio + tamanho].split())


def extrair(texto: str, categorias: dict[str, list[str]] | None = None) -> Extracao:
    """`categorias`: {chave: [palavras]} (as mesmas de categorias.json) para saber quais produtos a norma cita."""
    normal = normalizar(texto)
    tributos = [t for t, termos in TRIBUTOS.items() if any(_tem(normal, termo) for termo in termos)]

    anterior = nova = None
    achado = _RE_DE_PARA_2.search(normal) or _RE_DE_PARA.search(normal)
    if achado:
        anterior, nova = _f(achado.group(1)), _f(achado.group(2))
    percentuais = sorted({_f(p) for p in _RE_PERCENT.findall(normal) if 0 < _f(p) <= 40})

    cats = []
    for chave, palavras in (categorias or {}).items():
        if any(normalizar(p).strip() in normal for p in palavras):
            cats.append(chave)
    if "cesta basica" in normal:
        cats.append("cesta_basica")

    motivos, pontos = [], 0
    if tributos:
        pontos += 2
        motivos.append("cita " + ", ".join(tributos))
    if any(p in normal for p in PALAVRAS_ALIQUOTA):
        pontos += 2
        motivos.append("fala de alíquota/isenção")
    if anterior is not None:
        pontos += 3
        motivos.append(f"mudança de {anterior:g}% para {nova:g}%")
    elif percentuais:
        pontos += 1
    vigencia = _vigencia(normal)
    if vigencia:
        pontos += 1
        motivos.append(f"vigência {vigencia:%d/%m/%Y}")
    if cats:
        pontos += 2
        motivos.append("cita produtos: " + ", ".join(cats))

    chaves = ["aliquota"] + [t.lower() for t in tributos]
    return Extracao(tributos, anterior, nova, percentuais, vigencia, cats, pontos, _trecho(texto, normal, chaves), motivos)
