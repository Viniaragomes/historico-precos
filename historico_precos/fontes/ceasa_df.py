"""Preço no atacado da CEASA-DF (portal.ceasadf.com.br/precos): preço mais comum, em R$/kg, dia a dia.

A página pública de cotações tem um formulário (produto, classificação, mês, ano). Ao filtrar, a própria página
pede ao servidor, sem login:
  POST /classification  produto=<id>                      -> [{id, classification}]
  POST /precos          month, year, product, classification -> {priceMonth: [{dia, price}], priceYear: [{mes, price}]}
Fazemos o mesmo pedido, com o robô identificado e intervalo entre acessos. Fonte: CEASA-DF (Centrais de
Abastecimento do Distrito Federal), dado público.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import date

from ..extratores import para_float
from ..rede import Navegador

BASE = "https://www.portal.ceasadf.com.br"
PAGINA = f"{BASE}/precos"

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS ceasa_df (
    produto_id TEXT NOT NULL, produto TEXT, classificacao_id TEXT NOT NULL, classificacao TEXT,
    data TEXT NOT NULL, preco_kg REAL NOT NULL, coletado_em TEXT NOT NULL,
    PRIMARY KEY (produto_id, classificacao_id, data)
);
"""


@dataclass
class Cotacao:
    produto_id: str
    produto: str
    classificacao_id: str
    classificacao: str
    data: str  # AAAA-MM-DD
    preco_kg: float


def produtos(nav: Navegador) -> dict[str, str]:
    """{id: nome} do seletor de produtos da página de cotações."""
    pagina = nav.get_texto(PAGINA) or ""
    seletor = re.search(r'id="productChart".*?</select>', pagina, re.S)
    if not seletor:
        return {}
    return {v: " ".join(html.unescape(t).split()) for v, t in re.findall(r'<option value="(\d+)">\s*([^<]+)', seletor.group(0))}


def _json(texto: str | None):
    try:
        return json.loads(texto) if texto else None
    except json.JSONDecodeError:
        return None


def classificacoes(nav: Navegador, produto_id: str) -> dict[str, str]:
    dado = _json(nav.post_texto(f"{BASE}/classification", {"product": produto_id}))
    return {str(c["id"]): str(c.get("classification") or "").strip() for c in (dado or []) if isinstance(c, dict) and "id" in c}


def precos_do_mes(nav: Navegador, produto_id: str, produto: str, classificacao_id: str, classificacao: str,
                  ano: int, mes: int) -> list[Cotacao]:
    dado = _json(nav.post_texto(PAGINA, {"month": f"{mes:02d}", "year": str(ano), "product": produto_id,
                                         "classification": classificacao_id}))
    if not isinstance(dado, dict):
        return []
    saida = []
    for item in dado.get("priceMonth") or []:
        preco = para_float(item.get("price"))
        try:
            dia = date(ano, mes, int(str(item.get("dia")).strip()))
        except (TypeError, ValueError):
            continue
        if preco:
            saida.append(Cotacao(produto_id, produto, classificacao_id, classificacao, dia.isoformat(), preco))
    return saida


def salvar(con, cotacoes: list[Cotacao]) -> int:
    from ..modelo import agora_iso

    con.executescript(_ESQUEMA)
    agora = agora_iso()
    con.executemany("INSERT OR REPLACE INTO ceasa_df VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [(c.produto_id, c.produto, c.classificacao_id, c.classificacao, c.data, c.preco_kg, agora) for c in cotacoes])
    con.commit()
    return len(cotacoes)


def coletar(nav: Navegador, con, nomes: list[str], meses: list[tuple[int, int]]) -> dict:
    """Coleta os produtos cujo nome começa com um dos `nomes` (ex.: 'TOMATE', 'BANANA PRATA'), em todas as classificações."""
    catalogo = produtos(nav)
    alvos = {pid: nome for pid, nome in catalogo.items() if any(nome.upper() == n.upper() for n in nomes)}
    resumo = {"no_portal": len(catalogo), "produtos": len(alvos), "series": 0, "cotacoes": 0, "nao_achados": sorted(
        set(n.upper() for n in nomes) - {n.upper() for n in alvos.values()})}
    for pid, nome in alvos.items():
        for cid, cnome in classificacoes(nav, pid).items():
            resumo["series"] += 1
            for ano, mes in meses:
                resumo["cotacoes"] += salvar(con, precos_do_mes(nav, pid, nome, cid, cnome, ano, mes))
    return resumo


# ---------------- boletim diário "Preço no Atacado" (PDF), a fonte atual ----------------

INFORMACAO_MERCADO = f"{BASE}/informacao-mercado"
_ESQUEMA_BOLETIM = """
CREATE TABLE IF NOT EXISTS ceasa_df_boletim (
    data TEXT NOT NULL, produto TEXT NOT NULL, unidade TEXT, minimo REAL, comum REAL NOT NULL, maximo REAL,
    kg_por_unidade REAL, comum_kg REAL, url TEXT NOT NULL, coletado_em TEXT NOT NULL,
    PRIMARY KEY (data, produto)
);
"""
_NUM = r"\d{1,3}(?:\.\d{3})*,\d{2}"
_RE_LINHA = re.compile(rf"^(?P<resto>.+?)\s+(?P<min>{_NUM})\s+(?P<mc>{_NUM})\s+(?P<max>{_NUM})\s*$")
_RE_UNIDADE = re.compile(r"\s(?=(?:Und\b|Mç|Cxta|Cx|Sc|Dúzia|Bandeja|Pcte|Balde|Unidade|\d+(?:,\d+)?\s*kg))", re.I)
_RE_KG = re.compile(r"(\d+(?:[,.]\d+)?)\s*(?:a\s*(\d+(?:[,.]\d+)?))?\s*kg", re.I)
_RE_DATA = re.compile(r"DATA\s*[–-]\s*(\d{2})\.(\d{2})\.(\d{4})")


@dataclass
class LinhaBoletim:
    produto: str
    unidade: str
    minimo: float
    comum: float
    maximo: float
    kg_por_unidade: float | None

    @property
    def comum_kg(self) -> float | None:
        return round(self.comum / self.kg_por_unidade, 2) if self.kg_por_unidade else None


def _br(numero: str) -> float:
    return float(numero.replace(".", "").replace(",", "."))


def ler_boletim(texto: str) -> tuple[str | None, list[LinhaBoletim]]:
    """Texto do PDF 'Cotações de preços no atacado' -> (data AAAA-MM-DD, linhas com preço)."""
    data = _RE_DATA.search(texto)
    linhas = []
    for bruta in texto.splitlines():
        m = _RE_LINHA.match(" ".join(bruta.split()))
        if not m:
            continue
        minimo, comum, maximo = _br(m["min"]), _br(m["mc"]), _br(m["max"])
        if comum <= 0:
            continue  # 0,00 = sem negociação no dia
        partes = _RE_UNIDADE.split(m["resto"], maxsplit=1)
        produto, unidade = (partes[0].strip(), partes[1].strip()) if len(partes) == 2 else (m["resto"].strip(), "")
        kg = _RE_KG.search(unidade)
        if kg and not re.search(r"\bunidades?\b", unidade, re.I):
            a_, b_ = float(kg[1].replace(",", ".")), float((kg[2] or kg[1]).replace(",", "."))
            peso = (a_ + b_) / 2 if b_ >= a_ else a_
        else:
            peso = None
        linhas.append(LinhaBoletim(produto, unidade, minimo, comum, maximo, peso or None))
    return (f"{data[3]}-{data[2]}-{data[1]}" if data else None), linhas


def coletar_boletim(nav: Navegador, con, texto_do_pdf) -> dict:
    """Acha o boletim 'Preço no Atacado' mais recente na página pública e grava (só se for novo).
    `texto_do_pdf(bytes) -> str` extrai o texto (pypdf), para manter este módulo sem dependências."""
    from ..modelo import agora_iso

    con.executescript(_ESQUEMA_BOLETIM)
    pagina = nav.get_texto(INFORMACAO_MERCADO) or ""
    urls = sorted(set(re.findall(rf"{re.escape(BASE)}/storage/files/[^\"'\s<>]*atacado[^\"'\s<>]*\.pdf", pagina)))
    if not urls:
        return {"boletim": None, "linhas": 0, "nota": "nenhum boletim de atacado na página"}
    url = urls[-1]
    if con.execute("SELECT 1 FROM ceasa_df_boletim WHERE url = ? LIMIT 1", (url,)).fetchone():
        return {"boletim": url, "linhas": 0, "nota": "boletim já coletado"}
    dados = nav.get_bytes(url)
    if not dados:
        return {"boletim": url, "linhas": 0, "nota": "não deu para baixar o PDF"}
    data, linhas = ler_boletim(texto_do_pdf(dados))
    if not data:
        return {"boletim": url, "linhas": 0, "nota": "data do boletim não encontrada no PDF"}
    agora = agora_iso()
    con.executemany("INSERT OR REPLACE INTO ceasa_df_boletim VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [(data, l.produto, l.unidade, l.minimo, l.comum, l.maximo, l.kg_por_unidade, l.comum_kg, url, agora)
                     for l in linhas])
    con.commit()
    return {"boletim": url, "data": data, "linhas": len(linhas)}


def series_boletim(con, dias: int = 120) -> list[dict]:
    """Uma série por produto do boletim, com a variação do preço mais comum contra o boletim anterior."""
    con.executescript(_ESQUEMA_BOLETIM)
    linhas = con.execute("SELECT produto, unidade, data, comum, comum_kg, url FROM ceasa_df_boletim "
                         "WHERE data >= date('now', ?) ORDER BY produto, data", (f"-{dias} days",)).fetchall()
    grupos: dict[str, dict] = {}
    for produto, unidade, data, comum, comum_kg, url in linhas:
        g = grupos.setdefault(produto, {"produto": produto, "unidade": unidade, "serie": []})
        g["serie"].append({"data": data, "preco": comum, "preco_kg": comum_kg, "evidencia": url})
        g["unidade"] = unidade
    saida = []
    for g in grupos.values():
        s = g["serie"]
        g["ultimo"] = s[-1]
        g["variacao_pct"] = round((s[-1]["preco"] / s[-2]["preco"] - 1) * 100, 1) if len(s) >= 2 and s[-2]["preco"] else None
        saida.append(g)
    return saida


def series(con, dias: int = 120) -> list[dict]:
    """Uma série por produto e classificação, com a variação dos últimos 7 dias de pregão."""
    con.executescript(_ESQUEMA)
    linhas = con.execute("SELECT produto_id, produto, classificacao_id, classificacao, data, preco_kg FROM ceasa_df "
                         "WHERE data >= date('now', ?) ORDER BY produto, classificacao, data", (f"-{dias} days",)).fetchall()
    grupos: dict[tuple, dict] = {}
    for pid, nome, cid, cnome, data, preco in linhas:
        g = grupos.setdefault((pid, cid), {"produto": nome, "classificacao": cnome, "serie": []})
        g["serie"].append({"data": data, "preco_kg": preco})
    saida = []
    for g in grupos.values():
        s = g["serie"]
        g["ultimo"] = s[-1]
        if len(s) >= 6:
            atual = sorted(p["preco_kg"] for p in s[-3:])[1]
            antes = sorted(p["preco_kg"] for p in s[-6:-3])[1]
            g["variacao_pct"] = round((atual / antes - 1) * 100, 1) if antes else None
        else:
            g["variacao_pct"] = None
        saida.append(g)
    return saida
