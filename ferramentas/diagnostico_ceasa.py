"""Mostra a resposta crua do portal da CEASA-DF para um produto (diagnóstico do coletor)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historico_precos.fontes import ceasa_df  # noqa: E402
from historico_precos.rede import Navegador  # noqa: E402

nav = Navegador(intervalo=3)
cls = ceasa_df.classificacoes(nav, "1")
print("classificações do TOMATE:", cls)
for cid in list(cls)[:2]:
    for ano, mes in [(2026, 10), (2026, 9)]:
        for formato in ("urlencoded", "multipart"):
            campos = {"month": f"{mes:02d}", "year": str(ano), "product": "1", "classification": cid}
            if formato == "urlencoded":
                bruto = nav.post_texto(ceasa_df.PAGINA, campos)
            else:
                limite = "----hp"
                corpo = "".join(f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in campos.items()) + f"--{limite}--\r\n"
                import urllib.request
                req = urllib.request.Request(ceasa_df.PAGINA, data=corpo.encode(), headers={
                    "User-Agent": nav.user_agent, "Content-Type": f"multipart/form-data; boundary={limite}"})
                try:
                    with urllib.request.urlopen(req, timeout=40) as r:
                        bruto = r.read().decode("utf-8", "replace")
                except Exception as e:
                    bruto = f"ERRO {e}"
            print(f"\n== classificação {cid} {mes:02d}/{ano} {formato}:\n{(bruto or 'None')[:800]}")
print("\nregistro de falhas:", nav.registro[-5:])
