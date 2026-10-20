"""Resume o teste com usuários: sucesso e facilidade por tarefa, nota SUS e onde as pessoas travaram.

Uso: python ferramentas/resumo_teste.py docs/teste-com-usuarios-planilha.csv docs/teste-com-usuarios-sus.csv
Na coluna "resultado", use: sucesso, parcial ou falha.
"""

from __future__ import annotations

import csv
import statistics
import sys
from collections import defaultdict

META_SUCESSO = 0.8
META_FACILIDADE = 5
META_SUS = 68


def nota_sus(respostas: list[int]) -> float:
    """Itens ímpares: resposta - 1; pares: 5 - resposta; soma x 2,5 (de 0 a 100)."""
    if len(respostas) != 10 or not all(1 <= r <= 5 for r in respostas):
        raise ValueError("SUS precisa de 10 respostas de 1 a 5")
    return sum((r - 1) if i % 2 == 0 else (5 - r) for i, r in enumerate(respostas)) * 2.5


def resumir_tarefas(linhas: list[dict]) -> list[dict]:
    por_tarefa = defaultdict(list)
    for l in linhas:
        if (l.get("resultado") or "").strip():
            por_tarefa[l["tarefa"].strip()].append(l)
    resumo = []
    for tarefa in sorted(por_tarefa):
        grupo = por_tarefa[tarefa]
        pontos = {"sucesso": 1, "parcial": 0.5, "falha": 0}
        sucesso = sum(pontos.get(l["resultado"].strip().lower(), 0) for l in grupo) / len(grupo)
        facilidades = [int(l["facilidade_1a7"]) for l in grupo if (l.get("facilidade_1a7") or "").strip()]
        tempos = [float(l["tempo_seg"]) for l in grupo if (l.get("tempo_seg") or "").strip()]
        resumo.append({
            "tarefa": tarefa,
            "pessoas": len(grupo),
            "sucesso": sucesso,
            "facilidade": statistics.mean(facilidades) if facilidades else None,
            "tempo_mediano": statistics.median(tempos) if tempos else None,
            "travou": [l["onde_travou"].strip() for l in grupo if (l.get("onde_travou") or "").strip()],
        })
    return resumo


def main(planilha: str, planilha_sus: str | None = None) -> int:
    with open(planilha, encoding="utf-8") as f:
        tarefas = resumir_tarefas(list(csv.DictReader(f)))
    if not tarefas:
        print("Nenhuma tarefa preenchida ainda.")
        return 1
    print("Tarefa  Pessoas  Sucesso  Facilidade  Tempo mediano")
    for t in tarefas:
        ok = "✅" if t["sucesso"] >= META_SUCESSO and (t["facilidade"] or 0) >= META_FACILIDADE else "⚠️"
        fac = f"{t['facilidade']:.1f}" if t["facilidade"] is not None else "-"
        tempo = f"{t['tempo_mediano']:.0f}s" if t["tempo_mediano"] is not None else "-"
        print(f"{ok} {t['tarefa']:<5} {t['pessoas']:>5}  {t['sucesso'] * 100:>6.0f}%  {fac:>10}  {tempo:>13}")
    for t in tarefas:
        for onde in t["travou"]:
            print(f"   {t['tarefa']} travou em: {onde}")
    if planilha_sus:
        with open(planilha_sus, encoding="utf-8") as f:
            notas = []
            for l in csv.DictReader(f):
                valores = [l.get(f"q{i}", "").strip() for i in range(1, 11)]
                if all(valores):
                    notas.append(nota_sus([int(v) for v in valores]))
        if notas:
            media = statistics.mean(notas)
            print(f"\nSUS: média {media:.1f} ({len(notas)} pessoas) {'✅' if media >= META_SUS else '⚠️ abaixo de 68'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
