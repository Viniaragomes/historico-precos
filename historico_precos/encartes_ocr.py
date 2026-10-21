"""Encartes do dia dos mercados do DF, lidos com reconhecimento de texto gratuito (Tesseract), sem IA paga.

Fonte da lista de encartes: encartesdf.com.br (robots.txt libera tudo; lista pelo JSON público do WordPress).
Cada imagem passa pelo Tesseract (português); o texto vira trechos "nome do produto + preço". A leitura de
encarte por reconhecimento de texto erra às vezes (letras estilizadas, preços em destaque), por isso o app sempre
mostra o trecho lido e o link do encarte para a pessoa conferir. Nada disso entra como preço comprovado.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from .fontes import encartesdf
from .rede import Navegador

RE_PRECO = re.compile(r"(?:R\$\s*)?(\d{1,4})\s*[,.]\s*(\d{2})\b")
RE_G_COMO_9 = re.compile(r"\b(\d{1,3}0)9\b")  # "5009": o leitor costuma confundir o "g" de "500g" com 9


@dataclass
class Trecho:
    texto: str
    preco: float


@dataclass
class EncarteLido:
    mercado: str
    post: str
    publicado: str
    validade_fim: str | None
    imagens: list[str]
    trechos: list[Trecho] = field(default_factory=list)


def tesseract_disponivel() -> bool:
    return shutil.which("tesseract") is not None


def linhas_do_tsv(tsv: str) -> list[dict]:
    """TSV do Tesseract -> linhas {texto, topo, base, esquerda, direita, bloco}, na ordem de leitura."""
    grupos: dict[tuple, list] = defaultdict(list)
    for linha in tsv.splitlines()[1:]:
        c = linha.split("\t")
        if len(c) < 12 or not c[11].strip() or c[10] in ("-1", ""):
            continue
        try:
            if float(c[10]) < 20:  # confiança baixa: lixo do fundo
                continue
        except ValueError:
            continue
        chave = (int(c[2]), int(c[3]), int(c[4]))  # bloco, parágrafo, linha
        grupos[chave].append((int(c[6]), int(c[7]), int(c[8]), int(c[9]), c[11]))
    saida = []
    for (bloco, _p, _l), palavras in grupos.items():
        palavras.sort()
        esq = min(p[0] for p in palavras)
        topo = min(p[1] for p in palavras)
        dir_ = max(p[0] + p[2] for p in palavras)
        base = max(p[1] + p[3] for p in palavras)
        saida.append({"texto": " ".join(p[4] for p in palavras), "topo": topo, "base": base, "esquerda": esq, "direita": dir_, "bloco": bloco})
    saida.sort(key=lambda l: (l["topo"], l["esquerda"]))
    return saida


def trechos_das_linhas(linhas: list[dict]) -> list[Trecho]:
    """Para cada preço, junta o texto do produto: o que vem antes na mesma linha ou nas linhas logo acima,
    na mesma coluna. Ignora trechos sem letras suficientes."""
    trechos = []
    for i, l in enumerate(linhas):
        achado = RE_PRECO.search(l["texto"])
        if not achado:
            continue
        preco = float(f"{achado.group(1)}.{achado.group(2)}")
        if not 0.2 <= preco <= 2000:
            continue
        nome = l["texto"][:achado.start()].replace("R$", "").strip()
        # linhas acima, na mesma coluna (sobreposição horizontal) e perto na vertical
        acima = []
        for anterior in reversed(linhas[:i]):
            if l["topo"] - anterior["base"] > 2.5 * max(1, l["base"] - l["topo"]):
                break
            sobrepoe = min(anterior["direita"], l["direita"]) - max(anterior["esquerda"], l["esquerda"]) > 0
            if sobrepoe and not RE_PRECO.search(anterior["texto"]):
                acima.insert(0, anterior["texto"])
            if len(acima) >= 3:
                break
        texto = " ".join(acima + ([nome] if nome else [])).strip(" -:|")
        texto = RE_G_COMO_9.sub(r"\1g", texto)
        if len(re.findall(r"[A-Za-zÀ-ú]", texto)) >= 4:
            trechos.append(Trecho(" ".join(texto.split())[:120], preco))
    return trechos


def ocr(caminho: Path) -> list[Trecho]:
    tsv = subprocess.run(["tesseract", str(caminho), "stdout", "-l", "por", "--psm", "11", "tsv"],
                         capture_output=True, text=True, timeout=120).stdout
    return trechos_das_linhas(linhas_do_tsv(tsv))


def _preparar(dados: bytes, pasta: Path, nome: str) -> Path:
    """Salva a imagem; se der, converte para PNG e amplia (o Tesseract lê melhor letras maiores)."""
    caminho = pasta / nome
    caminho.write_bytes(dados)
    try:
        from PIL import Image

        img = Image.open(caminho).convert("L")
        if img.width < 1600:
            fator = 1600 / img.width
            img = img.resize((1600, int(img.height * fator)))
        png = caminho.with_suffix(".png")
        img.save(png)
        return png
    except Exception:
        return caminho


def ler_encartes(nav: Navegador, dias: int = 4, hoje: date | None = None, max_imagens: int = 120) -> list[EncarteLido]:
    """Encartes vigentes (validade de hoje em diante) publicados nos últimos `dias`, com os trechos lidos."""
    hoje = hoje or date.today()
    saida, lidas = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for e in encartesdf.listar(nav, dias=dias, hoje=hoje):
            if e.validade_fim and e.validade_fim < hoje.isoformat():
                continue
            lido = EncarteLido(e.mercado, e.post, e.publicado, e.validade_fim, e.imagens)
            for i, url in enumerate(e.imagens):
                if lidas >= max_imagens or not tesseract_disponivel():
                    break
                dados = nav.get_bytes(url)
                if not dados:
                    continue
                lidas += 1
                lido.trechos += ocr(_preparar(dados, Path(tmp), f"{len(saida)}-{i}{Path(url.split('?')[0]).suffix or '.img'}"))
            saida.append(lido)
    return saida


def para_json(encartes: list[EncarteLido]) -> list[dict]:
    return [{**{k: v for k, v in asdict(e).items() if k != "trechos"},
             "trechos": [{"t": t.texto, "p": t.preco} for t in e.trechos]} for e in encartes]
