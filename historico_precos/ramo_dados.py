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
