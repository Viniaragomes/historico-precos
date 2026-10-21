"""Consulta pública da NFC-e no DF (QR code do cupom): robots.txt, acesso e formato da página."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import investigar_fontes as inv  # noqa: E402

for base, caminhos in {
    "https://dec.fazenda.df.gov.br": ["/NFCE/", "/ConsultarNFCe.aspx"],
    "https://www.fazenda.df.gov.br": ["/nfce/qrcode", "/nfce/consulta"],
    "http://www.fazenda.df.gov.br": ["/nfce/qrcode"],
}.items():
    r = inv.baixar(base + "/robots.txt")
    print(f"\n== {base}: robots HTTP {r['status']} {r.get('erro') or ''}")
    if r["status"] == 200 and "<html" not in (r.get("texto") or "")[:200].lower():
        print("   ", (r.get("texto") or "")[:600].replace("\n", " | "))
    for c in caminhos:
        p = inv.baixar(base + c)
        a = inv.analisar(p)
        print(f"   {c}: HTTP {p['status']} {p.get('erro') or ''} | título: {a.get('titulo')} | anti-robô: {a.get('antirrobo')}")
        texto = p.get("texto") or ""
        if texto:
            print("      formulários:", re.findall(r"<form[^>]*>", texto)[:3])
            print("      texto:", " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", texto, flags=re.S)).split())[:500])
