"""Preço médio mensal (R$/kg) nas Ceasas, das planilhas de dados do Boletim Hortigranjeiro da Conab (Prohort).

A Conab publica no gov.br, todo mês, o boletim em PDF e uma planilha .xlsx com os dados ("tabelas de dados").
O site próprio do Prohort recusa robôs, mas o gov.br não; a planilha é dado aberto.

Verificado em 21/10/2026: a CEASA-DF quase não informa a Conab (preço em 0 a 3 de 25 meses). Por isso usamos
Goiânia (CEASA-GO, principal origem do hortifrúti do DF) como referência regional e São Paulo como nacional.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from .. import xlsx
from ..rede import Navegador

PASTA = "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/hortigranjeiros-prohort/boletim-hortigranjeiro"
PRODUTOS = ["Alface", "Batata", "Cebola", "Cenoura", "Tomate", "Banana", "Laranja", "Maçã", "Mamão", "Melancia"]

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS conab_prohort (
    produto TEXT NOT NULL, ceasa TEXT NOT NULL, mes TEXT NOT NULL, preco_kg REAL NOT NULL, planilha TEXT NOT NULL,
    coletado_em TEXT NOT NULL,
    PRIMARY KEY (produto, ceasa, mes)
);
"""


def _mes(serial) -> str | None:
    """Coluna de data do Excel (dias desde 30/12/1899) -> 'AAAA-MM'."""
    if isinstance(serial, float) and 30000 < serial < 80000:
        return (date(1899, 12, 30) + timedelta(days=int(serial))).strftime("%Y-%m")
    return None


def ler_planilha(dados: bytes) -> list[tuple[str, str, str, float]]:
    """[(produto, ceasa, 'AAAA-MM', preco_kg)] das abas 'Preços-<produto>' (série mensal por Ceasa)."""
    saida = []
    for aba, linhas in xlsx.ler(dados).items():
        produto = aba.removeprefix("Preços-")
        if not aba.startswith("Preços-") or produto not in PRODUTOS:
            continue
        cab = next((l for l in linhas if len(l) > 3 and all(_mes(x) for x in l[1:4])), None)
        if not cab:
            continue
        meses = [_mes(x) for x in cab]
        for l in linhas[linhas.index(cab) + 1:]:
            nome = l[0].strip() if l and isinstance(l[0], str) else ""
            if not nome or nome.lower().startswith("fonte"):
                continue
            for i, valor in enumerate(l[1:], start=1):
                if i < len(meses) and meses[i] and isinstance(valor, float) and 0 < valor < 1000:
                    saida.append((produto, nome, meses[i], round(valor, 4)))
    return saida


def planilhas(nav: Navegador, anos: list[int]) -> list[str]:
    """Links das planilhas de dados nas pastas anuais do boletim (a mais recente por último)."""
    achadas = []
    for ano in anos:
        pagina = nav.get_texto(f"{PASTA}/{ano}") or ""
        achadas += re.findall(r'href="([^"]+\.xlsx)"', pagina)
    return list(dict.fromkeys(achadas))


def coletar(nav: Navegador, con, anos: list[int] | None = None, so_novas: bool = True) -> dict:
    """Lê as planilhas ainda não lidas. Cada planilha traz ~25 meses, então a mais nova já cobre o histórico recente."""
    from ..modelo import agora_iso

    con.executescript(_ESQUEMA)
    anos = anos or [date.today().year]
    resumo = {"planilhas": 0, "lidas": 0, "linhas": 0}
    lidas = {u for (u,) in con.execute("SELECT DISTINCT planilha FROM conab_prohort")}
    for url in planilhas(nav, anos):
        resumo["planilhas"] += 1
        if so_novas and url in lidas:
            continue
        dados = nav.get_bytes(url)
        if not dados:
            continue
        linhas = ler_planilha(dados)
        agora = agora_iso()
        # a planilha mais nova revisa meses anteriores: INSERT OR REPLACE
        con.executemany("INSERT OR REPLACE INTO conab_prohort VALUES (?, ?, ?, ?, ?, ?)",
                        [(p, c, m, v, url, agora) for p, c, m, v in linhas])
        con.commit()
        resumo["lidas"] += 1
        resumo["linhas"] += len(linhas)
    return resumo


def series(con, ceasas: tuple[str, ...] = ("Ceasa/GO - Goiânia", "Ceagesp - São Paulo", "Ceasa/DF - Brasília")) -> list[dict]:
    """Uma série mensal por produto e Ceasa, com a variação do último mês contra o anterior."""
    con.executescript(_ESQUEMA)
    mais_novo = (con.execute("SELECT MAX(mes) FROM conab_prohort").fetchone() or [None])[0]
    if not mais_novo:
        return []
    a, m = (int(x) for x in mais_novo.split("-"))
    corte = f"{a - (1 if m <= 6 else 0)}-{(m - 6 - 1) % 12 + 1:02d}"  # série parada há mais de 6 meses não entra
    saida = []
    for produto in PRODUTOS:
        for ceasa in ceasas:
            pts = [{"mes": m, "preco_kg": v, "evidencia": u} for m, v, u in con.execute(
                "SELECT mes, preco_kg, planilha FROM conab_prohort WHERE produto = ? AND ceasa = ? ORDER BY mes", (produto, ceasa))]
            if not pts or pts[-1]["mes"] < corte:
                continue
            var = round((pts[-1]["preco_kg"] / pts[-2]["preco_kg"] - 1) * 100, 1) if len(pts) >= 2 else None
            saida.append({"produto": produto, "ceasa": ceasa, "serie": pts, "ultimo": pts[-1], "variacao_pct": var})
    return saida
