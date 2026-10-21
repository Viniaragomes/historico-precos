"""Confere o app publicado no GitHub Pages: página, manifesto, service worker e dados de atacado."""

import json
import urllib.request

BASE = "https://viniaragomes.github.io/historico-precos/"
for caminho in ["", "manifest.webmanifest", "sw.js", "app.js", "icone-192.png", "dados/indice.json", "dados/ceasa-df.json", "dados/conab.json"]:
    try:
        with urllib.request.urlopen(BASE + caminho, timeout=30) as r:
            corpo = r.read()
            extra = ""
            if caminho.endswith(".json") and caminho.startswith("dados/"):
                d = json.loads(corpo)
                extra = f"{len(d.get('series', d.get('produtos', [])))} séries/produtos"
            print(f"{r.status} {caminho or '/'} {len(corpo)} bytes {r.headers.get('Content-Type')} {extra}")
    except Exception as e:
        print(f"ERRO {caminho or '/'}: {e}")
