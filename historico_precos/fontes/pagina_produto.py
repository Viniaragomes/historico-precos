"""Preço lido direto da página pública do produto, pelo dado estruturado que a loja publica para buscadores.

Muitas lojas bloqueiam robôs na API de catálogo, mas liberam no robots.txt as páginas de produto e publicam um
mapa do site (sitemap) com todas elas. Cada página traz um bloco JSON-LD (schema.org/Product) com nome, GTIN,
marca e preço: é o que o Google lê. Aqui lemos o mesmo, respeitando o robots.txt e o intervalo entre acessos.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
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


# ---------------- lojas sem código de barras no site: vínculo por nome ----------------

_ESQUEMA_LOJA = """
CREATE TABLE IF NOT EXISTS produtos_loja (
    loja TEXT NOT NULL, url TEXT PRIMARY KEY, nome TEXT, marca TEXT, preco REAL, data TEXT,
    ean TEXT, semelhanca REAL, nome_catalogo TEXT, lido_em TEXT
);
CREATE INDEX IF NOT EXISTS produtos_loja_ean ON produtos_loja (ean);
"""


def ean_valido(codigo: str) -> bool:
    """Confere o dígito verificador de EAN-8, UPC-12, EAN-13 e GTIN-14."""
    if not re.fullmatch(r"\d{8}|\d{12,14}", codigo or ""):
        return False
    corpo, dv = codigo[:-1], int(codigo[-1])
    soma = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(corpo)))
    return (10 - soma % 10) % 10 == dv


def _dados_pagina(html: str) -> dict | None:
    """Nome, marca, preço, GTIN e estoque do JSON-LD de produto."""
    import json

    for bloco in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html or "", re.S | re.I):
        try:
            dado = json.loads(bloco.strip())
        except json.JSONDecodeError:
            continue
        for obj in (dado if isinstance(dado, list) else [dado] + (dado.get("@graph", []) if isinstance(dado, dict) else [])):
            if not isinstance(obj, dict) or "Product" not in (obj.get("@type") if isinstance(obj.get("@type"), list) else [obj.get("@type")]):
                continue
            ofertas = obj.get("offers") or {}
            ofertas = ofertas[0] if isinstance(ofertas, list) and ofertas else ofertas
            if isinstance(ofertas, dict) and isinstance(ofertas.get("offers"), list) and ofertas["offers"]:
                ofertas = ofertas["offers"][0]
            ofertas = ofertas if isinstance(ofertas, dict) else {}
            marca = obj.get("brand")
            from ..extratores import para_float

            return {
                "nome": obj.get("name"), "marca": marca.get("name") if isinstance(marca, dict) else marca,
                "gtin": str(obj.get("gtin13") or obj.get("gtin") or obj.get("gtin14") or obj.get("gtin12") or obj.get("gtin8") or ""),
                "preco": para_float(ofertas.get("price") or ofertas.get("lowPrice")),
                "sem_estoque": "OutOfStock" in str(ofertas.get("availability") or ""),
            }
    return None


def revincular(banco, loja: dict, catalogo, dias: int = 30, hoje: date | None = None) -> dict:
    """Refaz o vínculo das páginas já lidas e ainda sem código de barras, sem acessar o site de novo (útil quando a
    referência cresce ou as regras melhoram). O preço entra com a data em que a página foi lida."""
    con = banco.con
    con.executescript(_ESQUEMA_LOJA)
    desde = ((hoje or date.today()) - timedelta(days=dias)).isoformat()
    usados = {e for (e,) in con.execute("SELECT ean FROM produtos_loja WHERE loja = ? AND ean IS NOT NULL", (loja["nome"],))}
    resumo, pontos = {"sem_vinculo": 0, "vinculadas": 0, "precos": 0}, []
    for url, nome, marca, preco, dia in list(con.execute(
            "SELECT url, nome, marca, preco, data FROM produtos_loja WHERE loja = ? AND ean IS NULL AND nome IS NOT NULL "
            "AND preco IS NOT NULL AND data >= ?", (loja["nome"], desde))):
        resumo["sem_vinculo"] += 1
        v = catalogo.vincular(nome, marca)
        if not v or v.ean in usados:  # um código de barras só vale para um produto da mesma loja
            continue
        usados.add(v.ean)
        con.execute("UPDATE produtos_loja SET ean=?, semelhanca=?, nome_catalogo=? WHERE url=?", (v.ean, v.semelhanca, v.nome_catalogo, url))
        resumo["vinculadas"] += 1
        pontos.append(PontoDePreco(ean=v.ean, preco=preco, data_observada=dia, fonte="pagina-produto", loja=loja["nome"],
                                   cidade=loja.get("cidade"), url_origem=url, url_evidencia=url, metodo="vinculo-nome",
                                   descricao=nome))
    con.commit()
    resumo["precos"] = banco.salvar_precos(pontos)
    return resumo


def catalogar_por_nome(nav: Navegador, banco, loja: dict, catalogo, limite: int = 1000, hoje: date | None = None, ate=None) -> dict:
    """Lê, em rodízio, até `limite` páginas de produto da loja (as nunca lidas primeiro, depois as mais antigas)
    e vincula cada uma a um EAN pelo nome. Preço só entra quando o vínculo passa nas regras de `vinculo`."""
    from ..modelo import agora_iso

    con = banco.con
    con.executescript(_ESQUEMA_LOJA)
    dia = (hoje or date.today()).isoformat()
    conhecidas = {u for (u,) in con.execute("SELECT url FROM produtos_loja WHERE loja = ?", (loja["nome"],))}
    novas = [u for u in urls_do_sitemap(nav, loja["sitemap"], loja.get("padrao_produto", r"/p/")) if u not in conhecidas]
    con.executemany("INSERT OR IGNORE INTO produtos_loja (loja, url) VALUES (?, ?)", [(loja["nome"], u) for u in novas])
    con.commit()
    fila = [u for (u,) in con.execute("SELECT url FROM produtos_loja WHERE loja = ? ORDER BY lido_em IS NOT NULL, lido_em LIMIT ?",
                                      (loja["nome"], limite))]
    resumo = {"novas_no_sitemap": len(novas), "lidas": 0, "com_preco": 0, "vinculadas": 0, "precos": 0, "bloqueios": 0}
    pontos = []
    for url in fila:
        if ate and ate():
            resumo["parou"] = "tempo da rodada acabou; a próxima continua de onde parou"
            break
        html = nav.get_texto(url)
        if html is None:
            ultimo = nav.registro[-1] if nav.registro else {}
            if ultimo.get("status") in (403, 429, -1):
                resumo["bloqueios"] += 1
                if resumo["bloqueios"] >= 5:
                    resumo["parou"] = f"o site recusou {resumo['bloqueios']} acessos seguidos (HTTP {ultimo.get('status')}); paramos"
                    break
            continue
        resumo["bloqueios"] = 0
        resumo["lidas"] += 1
        d = _dados_pagina(html) or {}
        ean, nota, nome_cat, por_codigo = None, None, None, False
        if ean_valido(re.sub(r"\D", "", d.get("gtin") or "")):
            ean, nota, por_codigo = re.sub(r"\D", "", d["gtin"]), 1.0, True
        elif d.get("nome"):
            v = catalogo.vincular(d["nome"], d.get("marca"))
            # um código de barras só pode valer para um produto da mesma loja: o primeiro vínculo fica
            ja = v and con.execute("SELECT 1 FROM produtos_loja WHERE loja = ? AND ean = ? AND url <> ? LIMIT 1",
                                   (loja["nome"], v.ean, url)).fetchone()
            if v and not ja:
                ean, nota, nome_cat = v.ean, v.semelhanca, v.nome_catalogo
        con.execute("UPDATE produtos_loja SET nome=?, marca=?, preco=?, data=?, ean=?, semelhanca=?, nome_catalogo=?, lido_em=? WHERE url=?",
                    (d.get("nome"), d.get("marca"), d.get("preco"), dia, ean, nota, nome_cat, agora_iso(), url))
        if d.get("preco") and not d.get("sem_estoque"):
            resumo["com_preco"] += 1
            if ean:
                resumo["vinculadas"] += 1
                pontos.append(PontoDePreco(
                    ean=ean, preco=d["preco"], data_observada=dia, fonte="pagina-produto", loja=loja["nome"],
                    cidade=loja.get("cidade"), url_origem=url, url_evidencia=url,
                    metodo="json-ld" if por_codigo else "vinculo-nome", descricao=d.get("nome"),
                ))
    con.commit()
    resumo["precos"] = banco.salvar_precos(pontos)
    return resumo
