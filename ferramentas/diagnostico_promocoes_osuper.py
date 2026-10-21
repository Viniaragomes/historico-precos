"""Como as páginas de promoções do Fort e do Big Box carregam os preços (estado embutido, scripts, APIs) e o robots.txt."""

import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos.rede import USER_AGENT  # noqa: E402


def pegar(url, t=30):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR"})
    with urllib.request.urlopen(req, timeout=t) as r:
        return r.read().decode("utf-8", "replace")


def robots(url):
    p = urlsplit(url)
    try:
        rp = RobotFileParser()
        rp.parse(pegar(f"{p.scheme}://{p.netloc}/robots.txt", 15).splitlines())
        return rp.can_fetch(USER_AGENT, url)
    except Exception as e:
        return f"robots erro {e!r}"[:60]


for pagina in ["https://www.fortatacadista.com.br/promocoes", "https://bigboxdelivery.com.br/promocoes"]:
    print("\n=====", pagina, "robots:", robots(pagina))
    html = pegar(pagina)
    print("robots.txt do site:\n", pegar(urljoin(pagina, "/robots.txt"))[:600])
    for nome in re.findall(r'<script[^>]+id="([^"]+)"', html)[:10]:
        print("  script id:", nome)
    for m in re.finditer(r"(window\.__[A-Z_]+__|__NEXT_DATA__|__NUXT__|__APOLLO_STATE__|__INITIAL_STATE__|self\.__next_f)", html):
        print("  estado embutido:", m.group(1), "em", m.start())
    blocos = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
    print("  scripts inline:", len(blocos), "maiores:", sorted((len(b) for b in blocos), reverse=True)[:5])
    for b in sorted(blocos, key=len, reverse=True)[:2]:
        print("   trecho:", b[:400].replace("\n", " "))
    precos = [m.start() for m in re.finditer(r'"(?:price|preco|salePrice|promotionalPrice|valor)"\s*:', html)]
    print("  chaves de preço no HTML:", len(precos))
    for i in precos[:3]:
        print("   ", html[max(0, i - 300):i + 100].replace("\n", " "))
    srcs = re.findall(r'<script[^>]+src="([^"]+)"', html)
    print("  scripts externos:", srcs[:15])
    hosts = sorted(set(re.findall(r'https?://([a-z0-9.-]*(?:api|graphql|osuper|vtex|bff)[a-z0-9.-]*)', html)))
    print("  hosts de API citados no HTML:", hosts)
    for s in srcs[:12]:
        u = urljoin(pagina, s)
        try:
            js = pegar(u, 30)
        except Exception as e:
            print("   js falhou", u, repr(e)[:60])
            continue
        achados = sorted(set(re.findall(r'https?://[a-z0-9.-]+(?:/[A-Za-z0-9_./{}-]*)?(?:graphql|api)[A-Za-z0-9_./{}-]*', js)))[:10]
        ops = sorted(set(re.findall(r'(?:query|mutation)\s+([A-Za-z]+)\s*[({]', js)))[:25]
        if achados or ops:
            print("   ", u[-60:], "| endpoints:", achados, "| operações:", ops)
