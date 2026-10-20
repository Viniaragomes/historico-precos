"""Gera o checklist de conferência das leis de impostos a partir de site/impostos.json.

Quem confere lê o texto oficial, preenche "conferencia" na categoria do impostos.json
(conferido_em, por, links) e apaga o "pendente". O app passa a mostrar "LEI CONFERIDA".
"""

from __future__ import annotations

import json
from pathlib import Path

TABELA = Path(__file__).resolve().parents[1] / "site" / "impostos.json"

ONDE_CONFERIR = {
    "icms": [
        ("Lei distrital 5.745/2016 (cesta básica com carga de 7%)", "https://www.sinj.df.gov.br/sinj/"),
        ("RICMS-DF, Decreto 18.955/1997, Anexo I, Caderno II, item 11 (redução de base de cálculo)", "https://www.sinj.df.gov.br/sinj/"),
        ("Lei distrital 7.326/2023 (alíquota geral de 20%)", "https://www.sinj.df.gov.br/sinj/"),
    ],
    "pis_cofins": [
        ("Lei 10.925/2004, art. 1º (incisos de alíquota zero)", "https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2004/lei/l10.925.htm"),
        ("Lei 12.839/2013 (cesta básica: carnes, café, açúcar, óleos, higiene)", "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/lei/l12839.htm"),
        ("Tabela TIPI, para achar o NCM do produto", "https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/legislacao/documentos-e-arquivos/tipi.pdf"),
    ],
    "reforma": [
        ("LC 214/2025, Anexo I (cesta básica nacional, alíquota zero)", "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp214.htm"),
        ("LC 214/2025, Anexos com redução de 60% (alimentos e higiene)", "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp214.htm"),
    ],
}

PERGUNTAS = {
    "icms": {
        "cesta": "O produto está na lista da Lei 5.745/2016 / RICMS-DF com carga efetiva de 7%? Qual o percentual de redução da base hoje?",
        "modal": "O produto NÃO tem redução no RICMS-DF e paga a alíquota geral de 20%? (procure o NCM no Caderno II do Anexo I)",
    },
    "pis_cofins": {
        "geral": "O produto NÃO tem alíquota zero de PIS/Cofins e paga 1,65% + 7,6% no regime não cumulativo?",
        "zero_10925": "Qual inciso do art. 1º da Lei 10.925/2004 zera PIS/Cofins para este produto? Com qual NCM?",
        "zero_12839": "A Lei 12.839/2013 zera PIS/Cofins para este produto? Com qual NCM?",
    },
    "reforma": {
        "zero": "O produto (pelo NCM) está no Anexo I da LC 214/2025, com alíquota zero de IBS e CBS?",
        "reduzida_60": "Em qual anexo da LC 214/2025 está a redução de 60% para este produto? Ele não está no Anexo I?",
        "cheia": "O produto não aparece em nenhum anexo com redução da LC 214/2025?",
    },
}


def gerar(tabela_path: Path = TABELA) -> str:
    t = json.loads(tabela_path.read_text(encoding="utf-8"))
    linhas = [
        "# Conferência das leis de impostos (DF)",
        "",
        f"_Gerado a partir de `site/impostos.json` (revisado em {t['revisado_em']}). Não edite este arquivo: rode "
        "`python -m historico_precos conferencia-impostos` de novo depois de mudar a tabela._",
        "",
        "## Como conferir",
        "",
        "1. Para cada categoria abaixo, abra o **texto oficial** (Planalto, SINJ-DF ou Diário Oficial), nunca um resumo de blog.",
        "2. Responda às três perguntas e anote o **link do artigo** que comprova cada resposta.",
        "3. Se a resposta for diferente da tabela, corrija `icms`, `pis_cofins` ou `reforma` da categoria em `site/impostos.json`.",
        "4. Preencha na categoria:",
        "",
        "```json",
        '"conferencia": {"conferido_em": "AAAA-MM-DD", "por": "Nome de quem conferiu",',
        '                "links": ["link do artigo do ICMS", "link do PIS/Cofins", "link da Reforma"]}',
        "```",
        "",
        '5. Apague o campo `"pendente"` (ou deixe `null`). O app passa a mostrar **LEI CONFERIDA** com a data.',
        "6. Rode `node --test tests/impostos.test.mjs`: o teste recusa categoria conferida sem os três links.",
        "",
        "## Regras gerais (valem para todas as categorias)",
        "",
        "- [ ] Alíquota geral do ICMS no DF é 20% desde 22/01/2024 (Lei 7.326/2023). Confirmar a data no DODF.",
        "- [ ] PIS/Cofins não cumulativo: 1,65% + 7,6% (Leis 10.637/2002 e 10.833/2003).",
        "- [ ] O ICMS não entra na base do PIS/Cofins (STF, RE 574.706, Tema 69): conferir a modulação de efeitos.",
        "- [ ] Alíquota de referência da Reforma: trocar 26,5% pelo valor oficial quando o Senado publicar a resolução.",
        "",
        "## Onde conferir",
        "",
    ]
    for grupo, fontes in ONDE_CONFERIR.items():
        nome = {"icms": "ICMS (DF)", "pis_cofins": "PIS/Cofins", "reforma": "Reforma Tributária"}[grupo]
        linhas.append(f"**{nome}**")
        linhas += [f"- [{titulo}]({url})" for titulo, url in fontes]
        linhas.append("")
    linhas += ["## Categorias", ""]
    for c in t["categorias"]:
        conf = c.get("conferencia") or {}
        feito = "✅ conferida em " + conf["conferido_em"] + f" por {conf.get('por')}" if conf.get("conferido_em") else "⬜ não conferida"
        linhas += [
            f"### {c['nome']} ({feito})",
            "",
            f"Palavras que identificam: {', '.join(c['palavras'])}",
            "",
            f"- [ ] **ICMS**, hoje `{c['icms']}`: {PERGUNTAS['icms'][c['icms']]}",
            f"- [ ] **PIS/Cofins**, hoje `{c['pis_cofins']}`: {PERGUNTAS['pis_cofins'][c['pis_cofins']]}",
            f"- [ ] **Reforma**, hoje `{c['reforma']}`: {PERGUNTAS['reforma'][c['reforma']]}",
        ]
        if c.get("pendente"):
            linhas.append(f"- ⚠️ Pendência registrada: {c['pendente']}")
        linhas.append("")
    return "\n".join(linhas)
