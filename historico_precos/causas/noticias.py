"""Causas declaradas na imprensa, pela API pública do GDELT (JSON, sem chave, notícias desde 2017)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode

from ..rede import Navegador
from .series import normalizar

GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"

# motivo -> palavras que, no título, indicam que a notícia atribui a alta a ele
MOTIVOS = {
    "clima": ["seca", "geada", "chuva", "estiagem", "enchente", "clima", "el nino", "la nina", "calor"],
    "safra/oferta": ["safra", "colheita", "oferta", "estoque", "entressafra", "quebra"],
    "câmbio": ["dolar", "cambio"],
    "imposto": ["imposto", "icms", "tribut", "aliquota"],
    "custos": ["diesel", "frete", "combustivel", "energia", "fertilizante", "custo", "embalagem"],
    "demanda/exportação": ["exporta", "china", "demanda"],
    "reajuste da indústria": ["reajuste", "repasse", "anuncia aumento"],
}
PALAVRAS_ALTA = ["preco", "alta", "aumento", "sobe", "subiu", "dispara", "encarece", "reajuste", "caro"]


@dataclass
class Noticia:
    titulo: str
    url: str
    data: str
    veiculo: str
    motivos: list[str]


def _consulta(termos: list[str]) -> str:
    alvo = " OR ".join(f'"{t}"' if " " in t else t for t in termos)
    alvo = f"({alvo})" if len(termos) > 1 else alvo
    return f"{alvo} (preço OR alta OR aumento OR reajuste) sourcecountry:BR sourcelang:portuguese"


def classificar(titulo: str) -> list[str]:
    t = normalizar(titulo)
    if not any(p in t for p in PALAVRAS_ALTA):
        return []
    return [motivo for motivo, palavras in MOTIVOS.items() if any(p in t for p in palavras)]


def buscar(nav: Navegador, termos: list[str], inicio: date, fim: date, maximo: int = 75) -> list[Noticia]:
    params = {
        "query": _consulta(termos),
        "mode": "artlist",
        "format": "json",
        "maxrecords": str(maximo),
        "sort": "datedesc",
        "startdatetime": inicio.strftime("%Y%m%d000000"),
        "enddatetime": fim.strftime("%Y%m%d235959"),
    }
    dado = nav.get_json(f"{GDELT}?{urlencode(params)}")
    noticias = []
    for artigo in (dado or {}).get("articles", []):
        motivos = classificar(artigo.get("title", ""))
        if not motivos:
            continue  # notícia sem motivo identificável no título não entra como evidência
        visto = artigo.get("seendate", "")
        noticias.append(
            Noticia(
                titulo=artigo.get("title", "").strip(),
                url=artigo.get("url", ""),
                data=f"{visto[0:4]}-{visto[4:6]}-{visto[6:8]}" if len(visto) >= 8 else "",
                veiculo=artigo.get("domain", ""),
                motivos=motivos,
            )
        )
    return noticias
