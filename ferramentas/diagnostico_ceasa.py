"""Página 'Informação de Mercado' da CEASA-DF: lista de boletins e como ela pagina."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historico_precos.rede import Navegador  # noqa: E402

nav = Navegador(intervalo=3)
texto = nav.get_texto("https://www.portal.ceasadf.com.br/informacao-mercado") or ""
print(len(texto), "bytes")
corpo = re.sub(r"<script.*?</script>|<style.*?</style>", " ", texto, flags=re.S)
print(" ".join(re.sub(r"<[^>]+>", " ", corpo).split())[:2500])
print("\nPDFs:", sorted(set(re.findall(r'[^"\'\s<>]*storage/files/[^"\'\s<>]+', texto)))[:40])
print("\nlinks:", sorted(set(re.findall(r'href="([^"#]+)"', texto)))[:80])
print("\nformulários:", re.findall(r"<form[^>]*>", texto), re.findall(r'<select[^>]*name="([^"]+)"', texto))
i = texto.find("fetch(")
print("\nfetch:", texto[i - 300:i + 600] if i >= 0 else "nenhum")
