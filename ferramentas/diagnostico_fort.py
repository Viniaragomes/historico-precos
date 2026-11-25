"""Por que o Fort Atacadista recusa (HTTP 403) desde 14/11? Só lê: robots.txt, sitemap e 1 página de produto,
sempre com o nosso nome de robô. Mostra status, cabeçalhos de servidor/proteção e o começo da resposta."""

import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos.rede import USER_AGENT  # noqa: E402

URLS = [
    "https://fortatacadista.com.br/robots.txt",
    "https://fortatacadista.com.br/",
    "https://fortatacadista.com.br/sitemap.xml",
    "https://fortatacadista.com.br/produtos/7897383/molho-de-tomate-stella-doro-tradicional-sache-300g",
]
for url in URLS:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status, cab, corpo = r.status, dict(r.headers), r.read(3000)
    except urllib.error.HTTPError as e:
        status, cab, corpo = e.code, dict(e.headers), e.read(3000)
    except Exception as e:  # noqa: BLE001
        print(url, "ERRO", e)
        continue
    print("=" * 80)
    print(url, "->", status)
    for k, v in cab.items():
        if k.lower() in ("server", "cf-ray", "cf-mitigated", "x-cache", "via", "x-amz-cf-id", "content-type",
                         "x-akamai-transformed", "x-sucuri-id", "x-vercel-id", "x-powered-by", "retry-after"):
            print(f"  {k}: {v}")
    print(corpo.decode("utf-8", "replace")[:1500])
