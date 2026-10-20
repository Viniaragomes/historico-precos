"""Preço lido direto da página pública do produto, pelo dado estruturado que a loja publica para buscadores.

Muitas lojas bloqueiam robôs na API de catálogo, mas liberam no robots.txt as páginas de produto e publicam um
mapa do site (sitemap) com todas elas. Cada página traz um bloco JSON-LD (schema.org/Product) com nome, GTIN,
marca e preço: é o que o Google lê. Aqui lemos o mesmo, respeitando o robots.txt e o intervalo entre acessos.
"""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlsplit

from ..modelo import PontoDePreco, Produto
from ..rede import Navegador
from ..extratores import precos_json_ld

_RE_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")


def ler(nav: Navegador, url: str, loja: str, cidade: str | None = None, hoje: date | None = None) -> tuple[Produto | None, PontoDePreco | None]:
    """Lê uma página de produto. Só devolve preço se a página declara GTIN válido e o produto está em estoque."""
    html = nav.get_texto(url)
    if not html:
        return None, None
    for p in precos_json_ld(html):
        gtin = re.sub(r"\D", "", p.gtin or "")
        if not re.fullmatch(r"\d{8}|\d{12,14}", gtin):
            continue
        produto = Produto(gtin, nome=p.nome, fonte=f"página da loja ({loja})")
        if re.search(r'"availability"\s*:\s*"[^"]*OutOfStock', html):
            return produto, None  # sem estoque: o preço exibido não vale como preço de venda
        return produto, PontoDePreco(
            ean=gtin, preco=p.preco, preco_de=p.preco_de, data_observada=(hoje or date.today()).isoformat(),
            fonte="pagina-produto", loja=loja, url_origem=url, url_evidencia=url, metodo="json-ld", cidade=cidade,
            descricao=p.nome,
        )
    return None, None


def urls_do_sitemap(nav: Navegador, sitemap: str, padrao_produto: str = r"/p$", termos: list[str] | None = None,
                    max_arquivos: int = 60) -> list[str]:
    """URLs de produto listadas no sitemap da loja; com `termos`, só as que têm o termo no endereço."""
    from .wayback import normalizar_slug

    padrao = re.compile(padrao_produto)
    filtros = [re.sub(r"[^a-z0-9]+", "-", normalizar_slug(t)).strip("-") for t in (termos or [])]
    fila, lidos, achadas = [sitemap], 0, []
    while fila and lidos < max_arquivos:
        texto = nav.get_texto(fila.pop(0))
        lidos += 1
        if not texto:
            continue
        locs = _RE_LOC.findall(texto)
        if "<sitemapindex" in texto:
            # índices: primeiro os sitemaps de produto
            fila = sorted(locs, key=lambda u: 0 if re.search(r"product|produto", u, re.I) else 1) + fila
            fila = [u for u in fila if not re.search(r"categor|brand|marca|institucional|collection", u, re.I)]
            continue
        for u in locs:
            caminho = urlsplit(u).path
            if padrao.search(caminho) and (not filtros or any(f in caminho.lower() for f in filtros)):
                achadas.append(u)
    return list(dict.fromkeys(achadas))


def catalogar(nav: Navegador, banco, loja: dict, termos: list[str], limite: int = 100, lojas_arquivo: list[str] | None = None,
              ja_conhecidas: set[str] | None = None) -> dict:
    """Acha páginas de produto pelo sitemap, lê cada uma (no máximo `limite`) e guarda produto, página e preço de hoje.

    A mesma página também entra para as lojas do tipo 'arquivo' do mesmo domínio, para o histórico vir do Wayback.
    """
    conhecidas = ja_conhecidas if ja_conhecidas is not None else {
        u for (u,) in banco.con.execute("SELECT url FROM paginas_produto WHERE loja = ?", (loja["nome"],))}
    urls = [u for u in urls_do_sitemap(nav, loja["sitemap"], loja.get("padrao_produto", r"/p$"), termos) if u not in conhecidas]
    resumo = {"no_sitemap": len(urls), "lidas": 0, "com_gtin": 0, "precos": 0}
    pontos = []
    for url in urls[:limite]:
        produto, ponto = ler(nav, url, loja["nome"], loja.get("cidade"))
        resumo["lidas"] += 1
        if produto is None:
            continue
        resumo["com_gtin"] += 1
        if not banco.produto(produto.ean):
            banco.salvar_produto(produto)
        for nome in [loja["nome"], *(lojas_arquivo or [])]:
            banco.salvar_pagina(produto.ean, nome, url)
        if ponto:
            pontos.append(ponto)
    resumo["precos"] = banco.salvar_precos(pontos)
    return resumo
