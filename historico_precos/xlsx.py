"""Leitor mínimo de planilhas .xlsx (só biblioteca padrão): devolve as linhas de cada aba como listas de valores.

Um .xlsx é um zip de XMLs: xl/workbook.xml (nomes das abas), xl/sharedStrings.xml (textos) e
xl/worksheets/sheetN.xml (células). Fórmulas vêm com o último valor calculado, que é o que interessa.
"""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
       "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
       "pr": "http://schemas.openxmlformats.org/package/2006/relationships"}


def _coluna(ref: str) -> int:
    letras = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for c in letras:
        n = n * 26 + ord(c) - 64
    return n - 1


def ler(dados: bytes) -> dict[str, list[list]]:
    """{nome_da_aba: [[valor, ...], ...]}. Números viram float; vazios viram None."""
    z = zipfile.ZipFile(io.BytesIO(dados))
    textos = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", _NS):
            textos.append("".join(t.text or "" for t in si.iter(f"{{{_NS['m']}}}t")))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")).findall("pr:Relationship", _NS)}
    abas = {}
    for aba in ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", _NS):
        alvo = rels[aba.get(f"{{{_NS['r']}}}id")].lstrip("/")
        caminho = alvo if alvo.startswith("xl/") else f"xl/{alvo}"
        linhas = []
        for row in ET.fromstring(z.read(caminho)).iter(f"{{{_NS['m']}}}row"):
            valores: list = []
            for c in row.findall("m:c", _NS):
                i = _coluna(c.get("r"))
                v = c.find("m:v", _NS)
                tipo = c.get("t")
                if tipo == "inlineStr":
                    valor = "".join(t.text or "" for t in c.iter(f"{{{_NS['m']}}}t"))
                elif v is None:
                    valor = None
                elif tipo == "s":
                    valor = textos[int(v.text)]
                elif tipo in ("str", "e"):
                    valor = v.text
                elif tipo == "b":
                    valor = v.text == "1"
                else:
                    try:
                        valor = float(v.text)
                    except (TypeError, ValueError):
                        valor = v.text
                valores += [None] * (i - len(valores)) + [valor]
            linhas.append(valores)
        abas[aba.get("name")] = linhas
    return abas
