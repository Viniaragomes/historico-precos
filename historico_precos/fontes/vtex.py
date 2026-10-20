"""Preço atual em lojas que usam a plataforma VTEX, pelo catálogo público em JSON (sem chave).

O mesmo endpoint devolve o link da página do produto, que depois é usado para procurar
cópias antigas no Wayback Machine.
"""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import quote

from ..modelo import PontoDePreco
from ..rede import Navegador

BUSCA = "https://{dominio}/api/catalog_system/pub/products/search?fq=alternateIds_Ean:{ean}"
REGIOES = "https://{dominio}/api/checkout/pub/regions?country=BRA&postalCode={cep}"

_regioes: dict[tuple[str, str], str | None] = {}


def regiao(nav: Navegador, loja: dict) -> str | None:
    """Região VTEX do CEP configurado: sem ela, a loja devolve o preço de uma região padrão (outra cidade)."""
    cep = re.sub(r"\D", "", str(loja.get("cep") or ""))
    if not cep:
        return None
    chave = (loja["dominio"], cep)
    if chave not in _regioes:
        dado = nav.get_json(REGIOES.format(dominio=loja["dominio"], cep=cep))
        _regioes[chave] = dado[0].get("id") if isinstance(dado, list) and dado and dado[0].get("id") else None
    return _regioes[chave]


def _parametros_regiao(nav: Navegador, loja: dict) -> tuple[str, str | None]:
    """Devolve o trecho de URL da região e a cidade que pode ser afirmada com segurança."""
    extra = f"&sc={loja['sc']}" if loja.get("sc") else ""
    id_regiao = regiao(nav, loja)
    if id_regiao:
        return extra + f"&regionId={quote(id_regiao)}", loja.get("cidade")
    # sem região confirmada, não dá para dizer de que cidade é o preço
    return extra, (loja.get("cidade") if loja.get("sc") else None)


def url_busca(loja: dict, ean: str, extra: str = "") -> str:
    return BUSCA.format(dominio=loja["dominio"], ean=quote(ean)) + extra


def buscar_por_ean(nav: Navegador, loja: dict, ean: str) -> tuple[list[PontoDePreco], list[str]]:
    extra, cidade = _parametros_regiao(nav, loja)
    url = url_busca(loja, ean, extra)
    produtos = nav.get_json(url)
    if not isinstance(produtos, list):
        return [], []
    hoje = date.today().isoformat()
    pontos, links = [], []
    for produto in produtos:
        link = produto.get("link") or f"https://{loja['dominio']}/{produto.get('linkText', '')}/p"
        itens = [i for i in produto.get("items", []) if str(i.get("ean", "")).lstrip("0") == ean.lstrip("0")]
        if not itens:
            continue
        links.append(link)
        for item in itens:
            for vendedor in item.get("sellers", []):
                oferta = vendedor.get("commertialOffer") or {}  # grafia da própria VTEX
                preco = oferta.get("Price")
                if not oferta.get("IsAvailable") or not preco:
                    continue
                lista = oferta.get("ListPrice")
                pontos.append(
                    PontoDePreco(
                        ean=ean,
                        preco=float(preco),
                        preco_de=float(lista) if lista and lista > preco else None,
                        data_observada=hoje,
                        fonte="vtex",
                        loja=loja["nome"],
                        cidade=cidade,
                        url_origem=link,
                        url_evidencia=url,
                        metodo="vtex-api",
                        descricao=produto.get("productName"),
                    )
                )
    return pontos, list(dict.fromkeys(links))


def eh_vtex(nav: Navegador, dominio: str) -> bool:
    dado = nav.get_json(f"https://{dominio}/api/catalog_system/pub/products/search?_from=0&_to=0")
    return isinstance(dado, list)


def buscar_texto(nav: Navegador, loja: dict, termo: str, limite: int = 5) -> list[tuple[str, str]]:
    """Busca por nome e devolve [(ean, nome)] reais da loja, usados para montar amostras."""
    extra, _ = _parametros_regiao(nav, loja)
    url = f"https://{loja['dominio']}/api/catalog_system/pub/products/search?ft={quote(termo)}&_from=0&_to={limite - 1}" + extra
    produtos = nav.get_json(url)
    achados = []
    for produto in produtos if isinstance(produtos, list) else []:
        for item in produto.get("items", []):
            ean = str(item.get("ean") or "").strip()
            if ean.isdigit() and len(ean) in (8, 12, 13, 14):
                achados.append((ean, produto.get("productName", "")))
                break
    return achados
