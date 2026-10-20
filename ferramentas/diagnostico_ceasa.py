"""Onde o portal da CEASA-DF lista os boletins diários (SIMA)? Procura em páginas e no sitemap."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historico_precos.rede import Navegador  # noqa: E402

nav = Navegador(intervalo=3)
BASE = "https://www.portal.ceasadf.com.br"
vistos = set()
for caminho in ["/", "/sitemap.xml", "/boletins", "/boletim", "/sima", "/publicacoes", "/documentos", "/precos", "/blog", "/noticias"]:
    texto = nav.get_texto(BASE + caminho)
    if not texto:
        print(f"{caminho}: sem resposta ({nav.registro[-1] if nav.registro else ''})")
        continue
    pdfs = sorted(set(re.findall(r'(?:https://www\.portal\.ceasadf\.com\.br)?/storage/files/[^"\'\s<>]+\.pdf', texto)))
    links = sorted({l for l in re.findall(r'href="(https://www\.portal\.ceasadf\.com\.br/[^"#?]+)"', texto) if l not in vistos})
    vistos |= set(links)
    titulo = re.search(r"<title>(.*?)</title>", texto, re.S)
    print(f"\n{caminho}: {titulo.group(1).strip() if titulo else ''} | {len(texto)} bytes | {len(pdfs)} PDF(s)")
    for p in pdfs[:15]:
        print("   pdf", p)
    if caminho == "/":
        print("   links:", links[:60])
