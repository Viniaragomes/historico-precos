"""Leitura de preço estilizado de encarte: centavos pequenos no alto ("4" grande + "99" pequeno, sem vírgula) e
letra branca em etiqueta colorida. O Tesseract sozinho lê "4º" ou nada nesses casos.

Como funciona, sem IA paga:
  1. acha as regiões candidatas: etiquetas de cor forte (manchas saturadas) e números bem maiores que o texto ao redor;
  2. em cada região, separa a tinta do fundo (seja qual for a cor) e divide os algarismos em formas conectadas;
  3. algarismos altos são os reais, algarismos baixos à direita e no alto são os centavos; cada grupo é lido à parte
     pelo Tesseract só com dígitos.
"""

from __future__ import annotations

import re
import statistics
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageOps


def _ler_digitos(img: Image.Image) -> str:
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        img.save(f.name)
        r = subprocess.run(["tesseract", f.name, "stdout", "-l", "por", "--psm", "7", "-c", "tessedit_char_whitelist=0123456789"],
                           capture_output=True, text=True, timeout=60)
    return re.sub(r"\D", "", r.stdout)


def binaria(recorte: Image.Image) -> Image.Image:
    """Tinta preta em fundo branco, qualquer que seja a cor do fundo: tinta é o que difere bem da cor dominante."""
    g = ImageOps.autocontrast(recorte.convert("L"))
    hist = g.histogram()
    fundo = max(range(256), key=lambda v: sum(hist[max(0, v - 8):v + 9]))  # tom mais comum (com folga)
    return g.point(lambda v: 0 if abs(v - fundo) > 70 else 255)


def componentes(b: Image.Image) -> list[tuple[int, int, int, int]]:
    """Formas de tinta conectadas: (x0, x1, topo, base)."""
    px = b.load()
    largura, altura = b.size
    visto = bytearray(largura * altura)
    saida = []
    for y in range(altura):
        for x in range(largura):
            if px[x, y] == 0 and not visto[y * largura + x]:
                pilha = [(x, y)]
                visto[y * largura + x] = 1
                x0 = x1 = x
                y0 = y1 = y
                while pilha:
                    a, c = pilha.pop()
                    x0, x1, y0, y1 = min(x0, a), max(x1, a), min(y0, c), max(y1, c)
                    for d, e in ((a + 1, c), (a - 1, c), (a, c + 1), (a, c - 1)):
                        if 0 <= d < largura and 0 <= e < altura and px[d, e] == 0 and not visto[e * largura + d]:
                            visto[e * largura + d] = 1
                            pilha.append((d, e))
                saida.append((x0, x1 + 1, y0, y1 + 1))
    return sorted(saida)


def preco_da_regiao(recorte: Image.Image) -> float | None:
    """Preço com centavos pequenos no alto, ou None se a região não tiver esse formato."""
    b = binaria(recorte)
    if b.width > 500:
        b = b.resize((500, max(1, int(b.height * 500 / b.width))))
    largura, altura = b.size
    # forma que encosta na borda é moldura ou pedaço de outra coisa, não algarismo
    formas = [s for s in componentes(b) if s[3] - s[2] > 4 and s[0] > 0 and s[2] > 0 and s[1] < largura and s[3] < altura]
    if not formas:
        return None
    alto = max(s[3] - s[2] for s in formas)
    grandes = [s for s in formas if s[3] - s[2] >= 0.7 * alto]
    gx0, gx1 = min(s[0] for s in grandes), max(s[1] for s in grandes)
    gtopo, gbase = min(s[2] for s in grandes), max(s[3] for s in grandes)
    pequenos = [s for s in formas if s[0] >= gx1 - 2 and s[3] - s[2] < 0.7 * alto and s[2] < gtopo + 0.5 * alto]
    if not pequenos or len(grandes) > 4:
        return None
    px0, px1 = min(s[0] for s in pequenos), max(s[1] for s in pequenos)
    ptopo, pbase = min(s[2] for s in pequenos), max(s[3] for s in pequenos)
    margem = lambda img: ImageOps.expand(img, 20, fill=255)  # noqa: E731
    reais = _ler_digitos(margem(b.crop((gx0, gtopo, gx1, gbase))))
    centavos = _ler_digitos(margem(b.crop((px0, ptopo, px1, pbase)).resize(((px1 - px0) * 2, (pbase - ptopo) * 2))))
    if not reais or len(reais) > 4 or len(centavos) < 2:
        return None
    preco = float(f"{int(reais)}.{centavos[:2]}")
    return preco if 0.2 <= preco <= 2000 else None


def manchas_coloridas(img: Image.Image, passo: int = 8, min_celulas: int = 40) -> list[tuple[int, int, int, int]]:
    """Etiquetas de cor forte (onde o preço costuma vir em letra branca): caixas (x0, y0, x1, y1)."""
    hsv = img.convert("HSV")
    largura, altura = max(1, img.width // passo), max(1, img.height // passo)
    pequena = hsv.resize((largura, altura))
    s, v = pequena.getchannel("S").load(), pequena.getchannel("V").load()
    cor = [[s[i, j] > 110 and v[i, j] > 70 for j in range(altura)] for i in range(largura)]
    visto = [[False] * altura for _ in range(largura)]
    caixas = []
    for i in range(largura):
        for j in range(altura):
            if cor[i][j] and not visto[i][j]:
                pilha, xs, ys = [(i, j)], [], []
                visto[i][j] = True
                while pilha:
                    a, b = pilha.pop()
                    xs.append(a)
                    ys.append(b)
                    for c, d in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                        if 0 <= c < largura and 0 <= d < altura and cor[c][d] and not visto[c][d]:
                            visto[c][d] = True
                            pilha.append((c, d))
                # etiqueta de preço: nem minúscula nem faixa ou banner (até 8% da página)
                if min_celulas <= len(xs) <= largura * altura * 0.08:
                    caixas.append((min(xs) * passo, min(ys) * passo, (max(xs) + 1) * passo, (max(ys) + 1) * passo))
    return caixas


def numeros_grandes(palavras: list[tuple], img: Image.Image) -> list[tuple[int, int, int, int]]:
    """Palavras com dígito bem mais altas que o texto comum: o Tesseract costuma ler "14º" no lugar de "14,98"."""
    alturas = [p[3] for p in palavras]
    if not alturas:
        return []
    mediana = statistics.median(alturas)
    caixas = []
    for x, y, w, h, texto in palavras:
        if h >= 1.6 * mediana and re.search(r"\d", texto) and not re.search(r"\d[,.]\d{2}", texto):
            caixas.append((max(0, int(x - 0.1 * w)), max(0, int(y - 0.15 * h)), min(img.width, int(x + 1.6 * w)), min(img.height, int(y + 1.1 * h))))
    return caixas


def linhas_de_preco(caminho: Path, palavras: list[tuple], max_regioes: int = 40) -> list[dict]:
    """Linhas sintéticas "R$ 14,98" com a posição de cada preço estilizado achado, no formato de linhas_do_tsv."""
    img = Image.open(caminho).convert("RGB")
    caixas = numeros_grandes(palavras, img) + manchas_coloridas(img)
    saida = []
    for x0, y0, x1, y1 in caixas[:max_regioes]:
        if x1 - x0 < 20 or y1 - y0 < 20:
            continue
        if any(not (x1 <= l["esquerda"] or x0 >= l["direita"] or y1 <= l["topo"] or y0 >= l["base"]) for l in saida):
            continue  # já achado por outra região
        preco = preco_da_regiao(img.crop((x0, y0, x1, y1)))
        if preco is not None:
            saida.append({"texto": f"R$ {preco:.2f}".replace(".", ","), "pagina": 1, "topo": y0, "base": y1,
                          "esquerda": x0, "direita": x1, "estilizado": True})
    return saida
