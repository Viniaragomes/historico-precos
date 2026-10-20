"""Até onde vão os dados do portal da CEASA-DF? Varre meses para o TOMATE (todas as classificações)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historico_precos.fontes import ceasa_df  # noqa: E402
from historico_precos.rede import Navegador  # noqa: E402

nav = Navegador(intervalo=3)
cls = ceasa_df.classificacoes(nav, "1")
print("classificações do TOMATE:", cls)
meses = [(2026, m) for m in range(10, 0, -1)] + [(2025, m) for m in (12, 9, 6, 3)] + [(2024, 6)]
for cid, nome in cls.items():
    for ano, mes in meses:
        c = ceasa_df.precos_do_mes(nav, "1", "TOMATE", cid, nome, ano, mes)
        if c:
            print(f"{nome:<10} {mes:02d}/{ano}: {len(c)} dias, de {c[0].data} a {c[-1].data}, último R$ {c[-1].preco_kg:.2f}/kg")
    print()
# o PDF diário (boletim SIMA) mais recente que a página lista
pagina = nav.get_texto("https://www.portal.ceasadf.com.br/") or ""
import re
print("PDFs na página inicial:", sorted(set(re.findall(r'https://www\.portal\.ceasadf\.com\.br/storage/files/[^"\']+\.pdf', pagina)))[:10])
