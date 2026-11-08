"""Segunda checagem: robots completo do Super Veneza (sinais de conteúdo), página de ofertas do Ultrabox, folheto do Assaí DF."""

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos.rede import USER_AGENT  # noqa: E402


def pegar(url, t=25):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR"})
    try:
        with urllib.request.urlopen(req, timeout=t) as r:
            return r.status, r.read(3_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, repr(e)[:100]


def pode(base, url):
    st, txt = pegar(base + "/robots.txt")
    rp = RobotFileParser()
    rp.parse(txt.splitlines() if st == 200 else [])
    return rp.can_fetch(USER_AGENT, url)


print("===== robots.txt completo (sem comentários) do Super Veneza e do domínio das páginas de produto")
for base in ["https://superveneza.instabuy.com.br", "https://superveneza.instabuy.app.br", "https://bigboxdelivery.com.br"]:
    st, txt = pegar(base + "/robots.txt")
    linhas = [l for l in txt.splitlines() if l.strip() and not l.startswith("#")]
    print(f"\n{base} (HTTP {st}):\n  " + "\n  ".join(linhas[:40]))
    print("  produto permitido?", pode(base, base + "/p/Abacate-Kg"))

print("\n===== Ultrabox /ofertas/")
st, h = pegar("https://ultraboxatacado.com.br/ofertas/")
print("HTTP", st, "| permitido:", pode("https://ultraboxatacado.com.br", "https://ultraboxatacado.com.br/ofertas/"))
imgs = sorted(set(re.findall(r'(https?://[^"\'\s]+?\.(?:jpe?g|png|webp|pdf))', h, re.I)))
print("imagens/pdf:", len(imgs), [i for i in imgs if not re.search(r"logo|icon|favicon", i, re.I)][:15])
print("texto:", " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)).split())[:800])
st, f = pegar("https://ultraboxatacado.com.br/feed/")
print("feed HTTP", st, re.findall(r"<title>([^<]+)</title>", f)[:8])
for u in ["https://ultraboxatacado.com.br/wp-json/wp/v2/pages?per_page=30&_fields=slug,link,modified",
          "https://ultraboxatacado.com.br/wp-json/wp/v2/media?per_page=10&_fields=source_url,date"]:
    st, x = pegar(u)
    print(u.split(".br")[1], "HTTP", st, x[:600])

print("\n===== Portafolhetos: folheto Assaí DF")
st, h = pegar("https://www.portafolhetos.com.br/assai-atacadista/")
links = sorted(set(re.findall(r'href="(/assai-atacadista/[^"]*ofertas-df[^"]*)"', h)))
print("folhetos DF na página da rede:", links[:6])
if links:
    u = urljoin("https://www.portafolhetos.com.br/", links[-1])
    print("permitido:", pode("https://www.portafolhetos.com.br", u))
    st, p = pegar(u)
    imgs = sorted(set(re.findall(r'(https?://[^"\'\s]+?\.(?:jpe?g|png|webp))', p, re.I)))
    print("HTTP", st, "| imagens:", len(imgs), imgs[:8])
    print("validade/datas:", re.findall(r"(?:válid[oa]s?|até|de)\s+\d{2}/\d{2}(?:/\d{4})?[^<]{0,40}", p)[:5])
    print("páginas internas:", sorted(set(re.findall(r'href="([^"]*' + re.escape(links[-1].rstrip("/")) + r'[^"]*)"', p)))[:6])
    print("trecho:", " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", p, flags=re.S)).split())[:700])
    for i in imgs[:2]:
        host = re.match(r"https?://[^/]+", i).group(0)
        print("  imagem", i, "permitida:", pode(host, i))
