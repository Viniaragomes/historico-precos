"""Boletins da CEASA-DF (SIMA e Preço no Atacado): o texto do PDF dá para ler?"""

import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historico_precos.rede import Navegador  # noqa: E402
from pypdf import PdfReader  # noqa: E402

nav = Navegador(intervalo=3)
pagina = nav.get_texto("https://www.portal.ceasadf.com.br/informacao-mercado") or ""
for url in sorted(set(re.findall(r'https://www\.portal\.ceasadf\.com\.br/storage/files/[^"\'\s<>]+\.pdf', pagina))):
    if "calendario" in url:
        continue
    dados = nav.get_bytes(url)
    print(f"\n===== {url}: {len(dados or b'')} bytes")
    if not dados:
        continue
    leitor = PdfReader(io.BytesIO(dados))
    print("páginas:", len(leitor.pages))
    for i, pg in enumerate(leitor.pages[:2]):
        print(f"--- página {i + 1} ---")
        print((pg.extract_text() or "")[:3000])
