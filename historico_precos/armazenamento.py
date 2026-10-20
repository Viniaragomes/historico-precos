"""Guarda produtos e pontos de preço em SQLite, sem duplicar."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, fields

from .modelo import PontoDePreco, Produto

_CAMPOS = [f.name for f in fields(PontoDePreco)]

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS produtos (
    ean TEXT PRIMARY KEY, nome TEXT, marca TEXT, quantidade TEXT, fonte TEXT
);
CREATE TABLE IF NOT EXISTS precos (
    ean TEXT NOT NULL, preco REAL NOT NULL, data_observada TEXT NOT NULL, fonte TEXT NOT NULL,
    loja TEXT NOT NULL, url_origem TEXT NOT NULL, url_evidencia TEXT NOT NULL, metodo TEXT NOT NULL,
    preco_de REAL, cidade TEXT, descricao TEXT, coletado_em TEXT NOT NULL,
    UNIQUE (ean, loja, data_observada, preco, fonte)
);
CREATE INDEX IF NOT EXISTS idx_precos_ean ON precos (ean, data_observada);
-- páginas de produto conhecidas por loja (ex.: cópias arquivadas de lojas que bloqueiam robôs)
CREATE TABLE IF NOT EXISTS paginas_produto (
    ean TEXT NOT NULL, loja TEXT NOT NULL, url TEXT NOT NULL, descoberto_em TEXT NOT NULL,
    UNIQUE (ean, loja, url)
);
"""


class Banco:
    def __init__(self, caminho: str = "precos.db"):
        self.con = sqlite3.connect(caminho)
        self.con.executescript(_ESQUEMA)
        colunas = {linha[1] for linha in self.con.execute("PRAGMA table_info(precos)")}
        if "descricao" not in colunas:  # bancos criados pela versão 0.1
            self.con.execute("ALTER TABLE precos ADD COLUMN descricao TEXT")

    def salvar_produto(self, p: Produto) -> None:
        # não apaga um nome já conhecido se a nova consulta não trouxe nada
        self.con.execute(
            """INSERT INTO produtos VALUES (:ean, :nome, :marca, :quantidade, :fonte)
               ON CONFLICT(ean) DO UPDATE SET
                 nome = COALESCE(excluded.nome, nome), marca = COALESCE(excluded.marca, marca),
                 quantidade = COALESCE(excluded.quantidade, quantidade), fonte = COALESCE(excluded.fonte, fonte)""",
            asdict(p),
        )
        self.con.commit()

    def produto(self, ean: str) -> Produto | None:
        linha = self.con.execute("SELECT ean, nome, marca, quantidade, fonte FROM produtos WHERE ean = ?", (ean,)).fetchone()
        return Produto(*linha) if linha else None

    def salvar_precos(self, pontos: list[PontoDePreco]) -> int:
        antes = self.con.total_changes
        self.con.executemany(
            f"INSERT OR IGNORE INTO precos ({', '.join(_CAMPOS)}) VALUES ({', '.join(':' + c for c in _CAMPOS)})",
            [{**asdict(p), "preco": round(p.preco, 2)} for p in pontos],
        )
        self.con.commit()
        return self.con.total_changes - antes

    def precos(self, ean: str) -> list[PontoDePreco]:
        cursor = self.con.execute(
            f"SELECT {', '.join(_CAMPOS)} FROM precos WHERE ean = ? ORDER BY data_observada, loja", (ean,)
        )
        return [PontoDePreco(**dict(zip(_CAMPOS, linha))) for linha in cursor]

    def salvar_pagina(self, ean: str, loja: str, url: str) -> bool:
        from .modelo import agora_iso

        cur = self.con.execute("INSERT OR IGNORE INTO paginas_produto VALUES (?, ?, ?, ?)", (ean, loja, url, agora_iso()))
        self.con.commit()
        return cur.rowcount > 0

    def paginas(self, ean: str) -> list[tuple[str, str]]:
        """[(loja, url)] de páginas conhecidas deste produto."""
        return list(self.con.execute("SELECT loja, url FROM paginas_produto WHERE ean = ? ORDER BY loja", (ean,)))
