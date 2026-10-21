"""Encartes DF (encartesdf.com.br): site que republica os tabloides de supermercados do DF e do entorno.

É um WordPress cujo robots.txt libera tudo; a lista de posts vem do JSON público do próprio WordPress
(/wp-json/wp/v2/posts). Os preços estão nas imagens, por isso cada imagem passa pelo agente de encartes
(leitura por IA de visão). O link do post vira a prova de cada preço.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from html import unescape
from urllib.parse import urlencode

from ..rede import Navegador

API = "https://encartesdf.com.br/wp-json/wp/v2/posts"
_RE_ATE = re.compile(r"\s*(?:-|–)?\s*at[ée]\s+(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\s*$", re.I)
_RE_IMG = re.compile(r'<img[^>]+src=["\'](https://encartesdf\.com\.br/wp-content/uploads/[^"\']+)["\']', re.I)
_RE_MINIATURA = re.compile(r"-\d{2,4}x\d{2,4}(?=\.\w+$)")  # ex.: foto-768x1024.webp

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS encartesdf_lidos (
    imagem TEXT PRIMARY KEY, post TEXT, lido_em TEXT, resultado TEXT
);
"""


@dataclass
class Encarte:
    post: str  # link do post (prova)
    titulo: str
    mercado: str
    publicado: str  # AAAA-MM-DD
    validade_fim: str | None
    imagens: list[str] = field(default_factory=list)
    pdf: str | None = None  # quando o mercado publica o encarte em PDF (o texto do PDF é mais confiável que a imagem)


def _limpar(html: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", html or "")).split())


def separar_titulo(titulo: str) -> tuple[str, str | None]:
    """'Supermercado União até 22-10-2026' -> ('Supermercado União', '2026-10-22')."""
    titulo = re.sub(r"^\s*encarte\s+vencido\s*[-–:]?\s*", "", titulo, flags=re.I)  # o site marca assim os antigos
    achado = _RE_ATE.search(titulo)
    if not achado:
        return titulo.strip(), None
    d, m, a = (int(x) for x in achado.groups())
    try:
        fim = date(a, m, d).isoformat()
    except ValueError:
        fim = None
    return titulo[: achado.start()].strip(), fim


def imagens_do_post(html: str) -> list[str]:
    """Imagens do encarte em tamanho original, sem repetir e na ordem do post."""
    vistas, saida = set(), []
    for src in _RE_IMG.findall(html or ""):
        original = _RE_MINIATURA.sub("", src.replace(" ", "%20"))
        if original not in vistas and not re.search(r"logo|favicon|icone|banner", original, re.I):
            vistas.add(original)
            saida.append(original)
    return saida


def listar(nav: Navegador, dias: int = 7, por_pagina: int = 20, max_paginas: int = 5, hoje: date | None = None) -> list[Encarte]:
    """Encartes publicados nos últimos `dias`, do mais novo para o mais antigo."""
    desde = (hoje or date.today()) - timedelta(days=dias)
    encartes = []
    for pagina in range(1, max_paginas + 1):
        params = {"per_page": por_pagina, "page": pagina, "after": f"{desde.isoformat()}T00:00:00",
                  "_fields": "date,link,title,content"}
        posts = nav.get_json(f"{API}?{urlencode(params)}")
        if not isinstance(posts, list) or not posts:
            break
        for p in posts:
            titulo = _limpar((p.get("title") or {}).get("rendered", ""))
            mercado, fim = separar_titulo(titulo)
            imagens = imagens_do_post((p.get("content") or {}).get("rendered", ""))
            if imagens:
                encartes.append(Encarte(post=p.get("link", ""), titulo=titulo, mercado=mercado,
                                        publicado=(p.get("date") or "")[:10], validade_fim=fim, imagens=imagens))
        if len(posts) < por_pagina:
            break
    return encartes


def coletar(nav: Navegador, agente, dias: int = 7, max_imagens: int = 20, mercados: list[str] | None = None) -> dict:
    """Lê com o agente de encartes as imagens ainda não lidas. Cada imagem lida custa uma chamada de IA."""
    from ..modelo import agora_iso

    con = agente.con
    con.executescript(_ESQUEMA)
    filtro = [m.lower() for m in (mercados or [])]
    resumo = {"encartes": 0, "imagens_lidas": 0, "ja_lidas": 0, "falhas": 0, "itens": 0, "precos_novos": 0, "pendentes": 0}
    for enc in listar(nav, dias=dias):
        if filtro and not any(m in enc.mercado.lower() for m in filtro):
            continue
        resumo["encartes"] += 1
        for img in enc.imagens:
            if con.execute("SELECT 1 FROM encartesdf_lidos WHERE imagem = ?", (img,)).fetchone():
                resumo["ja_lidas"] += 1
                continue
            if resumo["imagens_lidas"] + resumo["falhas"] >= max_imagens:
                return resumo
            try:
                r = agente.processar(img, loja=enc.mercado, cidade=None, data_coleta=enc.publicado, fonte=enc.post)
            except Exception as e:  # imagem fora do ar, formato estranho, falha da IA: segue para a próxima
                resumo["falhas"] += 1
                con.execute("INSERT OR REPLACE INTO encartesdf_lidos VALUES (?, ?, ?, ?)",
                            (img, enc.post, agora_iso(), f"falha: {str(e)[:200]}"))
                con.commit()
                continue
            resumo["imagens_lidas"] += 1
            resumo["itens"] += r["itens"]
            resumo["precos_novos"] += r["precos_novos"]
            resumo["pendentes"] += r["pendentes"]
            con.execute("INSERT OR REPLACE INTO encartesdf_lidos VALUES (?, ?, ?, ?)",
                        (img, enc.post, agora_iso(), f"{r['itens']} itens"))
            con.commit()
    return resumo
