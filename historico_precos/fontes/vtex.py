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


def _pontos(produto: dict, loja: dict, url: str, cidade: str | None, hoje: str, ean: str | None = None) -> tuple[list[PontoDePreco], str]:
    """Preços disponíveis de um produto da API VTEX (só itens com EAN; com `ean`, só desse código)."""
    link = produto.get("link") or f"https://{loja['dominio']}/{produto.get('linkText', '')}/p"
    pontos = []
    for item in produto.get("items", []):
        codigo = str(item.get("ean") or "").strip()
        if not codigo.isdigit() or (ean and codigo.lstrip("0") != ean.lstrip("0")):
            continue
        for vendedor in item.get("sellers", []):
            oferta = vendedor.get("commertialOffer") or {}  # grafia da própria VTEX
            preco = oferta.get("Price")
            if not oferta.get("IsAvailable") or not preco:
                continue
            lista = oferta.get("ListPrice")
            pontos.append(PontoDePreco(
                ean=ean or codigo, preco=float(preco), preco_de=float(lista) if lista and lista > preco else None,
                data_observada=hoje, fonte="vtex", loja=loja["nome"], cidade=cidade, url_origem=link, url_evidencia=url,
                metodo="vtex-api", descricao=produto.get("productName"),
            ))
            break  # um preço por item: o do primeiro vendedor disponível
    return pontos, link


def buscar_por_ean(nav: Navegador, loja: dict, ean: str) -> tuple[list[PontoDePreco], list[str]]:
    extra, cidade = _parametros_regiao(nav, loja)
    url = url_busca(loja, ean, extra)
    produtos = nav.get_json(url)
    if not isinstance(produtos, list):
        return [], []
    hoje = date.today().isoformat()
    pontos, links = [], []
    for produto in produtos:
        achados, link = _pontos(produto, loja, url, cidade, hoje, ean)
        if achados or any(str(i.get("ean", "")).lstrip("0") == ean.lstrip("0") for i in produto.get("items", [])):
            links.append(link)
        pontos += achados
    return pontos, list(dict.fromkeys(links))


ARVORE = "https://{dominio}/api/catalog_system/pub/category/tree/3"
POR_CATEGORIA = "https://{dominio}/api/catalog_system/pub/products/search?fq=C:{caminho}&_from={de}&_to={ate}"
POR_PAGINA = 50  # máximo da API
LIMITE_API = 2500  # a API não pagina além disto por consulta


def _folhas(nos: list, caminho: str = "/") -> list[tuple[str, str]]:
    """(caminho 'C:/1/2/', nome) das categorias mais específicas da árvore."""
    saida = []
    for no in nos or []:
        atual = f"{caminho}{no.get('id')}/"
        filhos = no.get("children") or []
        saida += _folhas(filhos, atual) if filhos else [(atual, no.get("name") or "")]
    return saida


def catalogo(nav: Navegador, loja: dict, max_paginas: int | None = None):
    """Percorre o catálogo inteiro da loja pela API pública, categoria por categoria.

    Gera (Produto, [PontoDePreco]) para cada produto com EAN. Preço da região do CEP da loja, quando configurado.
    """
    from ..modelo import Produto

    extra, cidade = _parametros_regiao(nav, loja)
    hoje = date.today().isoformat()
    arvore = nav.get_json(ARVORE.format(dominio=loja["dominio"]))
    folhas = _folhas(arvore if isinstance(arvore, list) else [])
    vistos: set[str] = set()
    paginas = 0
    for caminho, _nome in folhas:
        for de in range(0, LIMITE_API, POR_PAGINA):
            if max_paginas is not None and paginas >= max_paginas:
                return
            url = POR_CATEGORIA.format(dominio=loja["dominio"], caminho=caminho, de=de, ate=de + POR_PAGINA - 1) + extra
            produtos = nav.get_json(url)
            paginas += 1
            if not isinstance(produtos, list) or not produtos:
                break
            for produto in produtos:
                pid = str(produto.get("productId"))
                if pid in vistos:
                    continue
                vistos.add(pid)
                pontos, _ = _pontos(produto, loja, url, cidade, hoje)
                for ponto in pontos:
                    yield Produto(ponto.ean, nome=produto.get("productName"), marca=produto.get("brand"),
                                  fonte=f"catálogo {loja['nome']}"), [ponto]
            if len(produtos) < POR_PAGINA:
                break


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
