"""Gera os arquivos que o app lê: um JSON por produto e um índice. Assim o app funciona sem servidor."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .agente import detectar_mudancas
from .armazenamento import Banco
from .causas.analise import AgenteCausas
from .comparativo import comparar
from .modelo import Produto, agora_iso

log = logging.getLogger(__name__)

AVISO = "Preços online podem diferir da loja física. Cada preço tem um link para a fonte."


def dados_do_produto(banco: Banco, ean: str, causas: AgenteCausas | None, hoje: date | None = None) -> dict | None:
    pontos = banco.precos(ean)
    if not pontos:
        return None
    produto = banco.produto(ean) or Produto(ean)
    comp = comparar(pontos, hoje=hoje, max_dias=30)

    if causas is not None:
        _, explicacoes = causas.explicar(ean)
        mudancas = [
            {
                **asdict(ex.mudanca),
                "variacao_pct": round(ex.mudanca.variacao_pct, 2),
                "comprovado_pct": round(ex.comprovado_pct, 2),
                "nao_explicado_pct": round(ex.nao_explicado_pct, 2),
                "evidencias": [asdict(e) for e in ex.evidencias],
            }
            for ex in explicacoes
        ]
    else:
        mudancas = [{**asdict(m), "variacao_pct": round(m.variacao_pct, 2), "evidencias": []}
                    for m in detectar_mudancas(pontos)]

    def oferta(o):
        d = asdict(o)
        d.pop("dias")  # o app calcula a idade na hora, a partir da data
        d["em_promocao"] = o.em_promocao
        return d

    return {
        "ean": ean,
        "nome": produto.nome or next((p.descricao for p in reversed(pontos) if p.descricao), None),
        "marca": produto.marca,
        "quantidade": produto.quantidade,
        "atualizado_em": agora_iso(),
        "ofertas": [oferta(o) for o in comp.ofertas],
        "ofertas_antigas": [oferta(o) for o in comp.ignoradas],
        "historico": [
            {"data": p.data_observada, "preco": p.preco, "preco_de": p.preco_de, "loja": p.loja,
             "fonte": p.fonte, "evidencia": p.url_evidencia, "descricao": p.descricao}
            for p in pontos
        ],
        "mudancas": sorted(mudancas, key=lambda m: m["data_nova"], reverse=True),
        "aviso": AVISO,
    }


def exportar(banco: Banco, pasta: Path, causas: AgenteCausas | None = None) -> int:
    pasta.mkdir(parents=True, exist_ok=True)
    eans = [l[0] for l in banco.con.execute("SELECT DISTINCT ean FROM precos ORDER BY ean")]
    indice = []
    for ean in eans:
        dado = dados_do_produto(banco, ean, causas)
        if dado is None:
            continue
        (pasta / f"{ean}.json").write_text(json.dumps(dado, ensure_ascii=False), encoding="utf-8")
        mais_barata = dado["ofertas"][0] if dado["ofertas"] else None
        indice.append({
            "ean": ean,
            "nome": dado["nome"],
            "menor_preco": mais_barata["preco"] if mais_barata else None,
            "loja": mais_barata["loja"] if mais_barata else None,
            "lojas": len(dado["ofertas"]),
        })
    (pasta / "indice.json").write_text(
        json.dumps({"atualizado_em": agora_iso(), "produtos": indice}, ensure_ascii=False), encoding="utf-8"
    )
    return len(indice)
