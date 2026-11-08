"""Banco da coleta guardado no ramo "dados" do repositório.

O banco vai comprimido (precos.db.gz): o GitHub recusa arquivo acima de 100 MB e, com os catálogos completos, o
banco cresce rápido. Bancos antigos sem compressão (precos.db) ainda são lidos.
"""

from __future__ import annotations

import gzip
import shutil
import subprocess
from pathlib import Path

LIMITE_GITHUB = 95 * 1024 * 1024  # margem abaixo dos 100 MB


def recuperar(destino: str | Path = "precos.db", ref: str = "origin/dados") -> bool:
    """Baixa o banco do ramo "dados" para `destino`. Falso se ainda não houver banco guardado."""
    subprocess.run(["git", "fetch", "-q", "origin", "dados"], check=False)
    destino = Path(destino)
    for nome, comprimido in (("precos.db.gz", True), ("precos.db", False)):
        r = subprocess.run(["git", "show", f"{ref}:{nome}"], capture_output=True)
        if r.returncode == 0 and r.stdout:
            destino.write_bytes(gzip.decompress(r.stdout) if comprimido else r.stdout)
            return True
    return False


def comprimir(origem: str | Path, destino: str | Path) -> int:
    """Grava `origem` comprimido em `destino` e devolve o tamanho; erro se passar do limite do GitHub."""
    with open(origem, "rb") as f, gzip.open(destino, "wb", compresslevel=9) as g:
        shutil.copyfileobj(f, g)
    tamanho = Path(destino).stat().st_size
    if tamanho > LIMITE_GITHUB:
        raise SystemExit(f"Banco comprimido com {tamanho / 2**20:.0f} MB: passa do limite do GitHub (100 MB). "
                         "É hora de dividir o banco ou apagar histórico antigo.")
    return tamanho


def lojas_do_grupo(lojas: list[dict], grupo: int | None, grupos: int | None) -> list[dict]:
    """Parte `grupo` (0, 1, ...) de `grupos` partes: as lojas lidas em paralelo por servidores diferentes."""
    if grupo is None or not grupos:
        return lojas
    return lojas[grupo::grupos]


def juntar(destino, origem, lojas: list[str]) -> dict:
    """Traz para o banco `destino` o que a parte paralela gravou no banco `origem` para as `lojas` dela: as páginas de
    produto lidas (produtos_loja) e os preços vindos dessas páginas. O que a parte refez substitui o que havia (inclusive
    vínculos desfeitos, que somem); o resto do banco de destino fica como está."""
    import sqlite3

    con = sqlite3.connect(destino)
    con.execute("ATTACH DATABASE ? AS outro", (str(origem),))
    marcas = ",".join("?" * len(lojas))
    resumo = {"lojas": len(lojas), "paginas": 0, "precos": 0}
    tem = {r[0] for r in con.execute("SELECT name FROM outro.sqlite_master WHERE type='table'")}
    if "produtos_loja" in tem and lojas:
        colunas = [r[1] for r in con.execute("PRAGMA outro.table_info(produtos_loja)")]
        con.execute("CREATE TABLE IF NOT EXISTS main.produtos_loja AS SELECT * FROM outro.produtos_loja WHERE 0")
        con.execute(f"DELETE FROM main.produtos_loja WHERE loja IN ({marcas})", lojas)
        lista = ",".join(colunas)
        cur = con.execute(f"INSERT INTO main.produtos_loja ({lista}) SELECT {lista} FROM outro.produtos_loja WHERE loja IN ({marcas})", lojas)
        resumo["paginas"] = cur.rowcount
    if "precos" in tem and lojas:
        con.execute(f"DELETE FROM main.precos WHERE fonte = 'pagina-produto' AND loja IN ({marcas})", lojas)
        cur = con.execute(f"INSERT OR IGNORE INTO main.precos SELECT * FROM outro.precos WHERE fonte = 'pagina-produto' AND loja IN ({marcas})", lojas)
        resumo["precos"] = cur.rowcount
    con.commit()
    con.execute("DETACH DATABASE outro")
    con.close()
    return resumo

