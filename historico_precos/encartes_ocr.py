"""Encartes do dia dos mercados do DF, lidos com reconhecimento de texto gratuito (Tesseract), sem IA paga.

Fontes: sites dos próprios mercados (Atacadão Dia a Dia, Dona; ver fontes/folhetos_df.py) e encartesdf.com.br
(robots.txt libera tudo; JSON público do WordPress). PDF com texto é lido direto; imagem passa pelo Tesseract
(português). O texto vira trechos "nome do produto + preço". A leitura de encarte por reconhecimento de texto erra às vezes (letras estilizadas, preços em destaque), por isso o app sempre
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

from .fontes import encartesdf, folhetos_df
from .rede import Navegador

RE_PRECO = re.compile(r"(?:R\$\s*)?(\d{1,4})\s*[,.]\s*(\d{2})\b")
RE_G_COMO_9 = re.compile(r"\b(\d{1,3}0)[96]\b")  # "5009"/"5006": o leitor confunde o "g"/"G" de "500g" com 9 ou 6
RE_PREFIXO = re.compile(r"^(?:(?:distrito federal e entorno|a cada|cada|r\$|apenas|por|só|so|oferta|ofertas)(?=[\s.:,-]|$)[\s.:,-]*)+", re.I)
RE_PALAVRA_BOA = re.compile(r"^[A-Za-zÀ-ú][A-Za-zÀ-ú-]{2,}[.,]?$")


def limpar_nome(texto: str) -> str | None:
    """Tira o que não é nome de produto e descarta leitura ruim (a maioria das palavras precisa ser palavra de verdade)."""
    texto = RE_G_COMO_9.sub(r"\1g", " ".join(texto.split()))
    texto = RE_PREFIXO.sub("", texto).strip(" -:|“”\"'[]()>*+.,")
    # siglas e medidas (BDJ, C/5UN, KG, 1) não contam nem a favor nem contra
    partes = [p for p in texto.split() if not re.match(r"^(?:[A-Z]{1,3}|[A-Z0-9/]*[0-9/][A-Z0-9/]*)$", p)]
    boas = [p for p in partes if RE_PALAVRA_BOA.match(p) and re.search(r"[aeiouáéíóúâêôãõAEIOUÁÉÍÓÚÂÊÔÃÕ]", p)
            or re.match(r"^\d+(?:[.,]\d+)?(?:kg|g|ml|l|un)$", p, re.I)]
    if not partes or len(boas) / len(partes) < 0.6 or not any(len(p) >= 4 for p in boas):
        return None
    return texto[:120]


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
    pdf: str | None = None
    titulo: str = ""
    trechos: list[Trecho] = field(default_factory=list)
    nomes: list[str] = field(default_factory=list)  # produtos cujo nome foi lido, mas o preço não (preço estilizado)


def tesseract_disponivel() -> bool:
    return shutil.which("tesseract") is not None


def linhas_do_tsv(tsv: str) -> list[dict]:
    """TSV do Tesseract ou do pdftotext -tsv -> linhas {texto, pagina, topo, base, esquerda, direita}, na ordem de leitura."""
    grupos: dict[tuple, list] = defaultdict(list)
    for linha in tsv.splitlines()[1:]:
        c = linha.split("\t")
        if len(c) < 12 or not c[11].strip() or c[10] in ("-1", "") or c[11].startswith("###"):
            continue
        try:
            if float(c[10]) < 20:  # confiança baixa: lixo do fundo
                continue
            chave = (int(c[1]), int(c[2]), int(c[3]), int(c[4]))  # página, bloco/parágrafo, parágrafo/bloco, linha
            grupos[chave].append((float(c[6]), float(c[7]), float(c[8]), float(c[9]), c[11]))
        except ValueError:
            continue
    saida = []
    for (pagina, *_), palavras in grupos.items():
        palavras.sort()
        saida.append({"texto": " ".join(p[4] for p in palavras), "pagina": pagina,
                      "topo": min(p[1] for p in palavras), "base": max(p[1] + p[3] for p in palavras),
                      "esquerda": min(p[0] for p in palavras), "direita": max(p[0] + p[2] for p in palavras)})
    saida.sort(key=lambda l: (l["pagina"], l["topo"], l["esquerda"]))
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
            if anterior["pagina"] != l["pagina"] or l["topo"] - anterior["base"] > 2.5 * max(1, l["base"] - l["topo"]):
                break
            sobrepoe = min(anterior["direita"], l["direita"]) - max(anterior["esquerda"], l["esquerda"]) > 0
            if sobrepoe and not RE_PRECO.search(anterior["texto"]):
                acima.insert(0, anterior["texto"])
            if len(acima) >= 3:
                break
        texto = limpar_nome(" ".join(acima + ([nome] if nome else [])))
        if texto:
            trechos.append(Trecho(texto, preco))
    return trechos


# hortifrúti, açougue e granel quase não têm código de barras, então pouco aparecem no dicionário das notas fiscais
VOCAB_BASE = set("""
banana nanica prata maca laranja limao tomate batata cebola alho cenoura beterraba abobora abobrinha chuchu couve alface
repolho brocolis pepino pimentao mamao formosa papaya melao melancia abacaxi manga palmer tommy uva thompson crimson
morango goiaba maracuja tangerina mexerica ponkan pera kiwi coco ovos ovo frango coxa sobrecoxa peito file carne bovina
bovino suina suino picanha alcatra maminha patinho acem costela linguica toscana calabresa pernil lombo bisteca
fraldinha cupim musculo moida peixe tilapia salmao sardinha merluza queijo presunto mussarela granel bandeja unidade
quilo pacote cheiro verde mandioca inhame milho vagem quiabo jilo berinjela rucula agriao espinafre salsa cebolinha
coentro hortela gengibre batata doce baroa mandioquinha abacate pessego ameixa caqui lima rosa amarelo amarela grape
cereja resfriado resfriada congelado congelada vacuo peca inteiro inteira fatiado fatiada temperado temperada
""".split())


# propaganda e endereço: aparecem em todo encarte, mas não são produto
NAO_PRODUTO = set("""
preco precos baixo todo todos toda voce precisa oferta ofertas loja lojas modulo lote quadra valido valida validas
validos estoque estoques enquanto durarem cliente clientes clube exclusivo exclusiva sempre aproveite imperdivel
desconto descontos cada leve pague somente apenas partir vila setor avenida rua shopping conjunto norte centro
endereco telefone whatsapp delivery entrega site aplicativo cartao pagamento parcela parcelas dias semana
""".split())
HORTIFRUTI = set("""banana maca laranja limao tomate batata cebola alho cenoura beterraba abobora abobrinha chuchu couve
alface repolho pepino pimentao mamao melao melancia abacaxi manga uva goiaba tangerina mexerica pera mandioca""".split())


def plausivel(t: Trecho) -> bool:
    """Preço lido de imagem que não pode ser verdade: hortifrúti acima de R$ 30, qualquer item acima de R$ 100 sem
    indicar volume (fardo, caixa, kit, cesta, 5 kg ou mais). Quase sempre é centavo colado no real ("1,99" + "2")."""
    from .vinculo import normalizar

    nome = normalizar(t.texto)
    if HORTIFRUTI & set(nome.split()) and t.preco > 30:
        return False
    volume = re.search(r"fardo|caixa|\bcx\b|\bkit\b|cesta|\b([5-9]|\d{2,})\s*(kg|l|litros?)\b|com \d+|\d+\s*un", nome)
    return t.preco <= 100 or bool(volume)


def vocabulario(*cons, minimo: int = 20) -> set[str]:
    """Palavras (sem acento, 4+ letras) dos nomes de produtos que já conhecemos: catálogos das lojas, Open Food Facts,
    descrições de preços e o dicionário de códigos das notas fiscais do DF. Serve para descartar leitura de imagem que
    parece palavra mas não é ("posta sesaos"). Só vale palavra que aparece em `minimo` nomes diferentes: as notas fiscais
    têm muita abreviação e erro de digitação, e uma palavra rara ali não prova nada."""
    from collections import Counter

    from .vinculo import normalizar

    contagem: Counter = Counter()
    consultas = ["SELECT nome FROM produtos", "SELECT marca FROM produtos", "SELECT DISTINCT descricao FROM precos",
                 "SELECT nome FROM produtos_loja", "SELECT descricao FROM mapa_df_dicionario"]
    for con in cons:
        for sql in consultas:
            try:
                for (nome,) in con.execute(sql):
                    contagem.update(set(re.findall(r"[a-z]{4,}", normalizar(nome))))
            except Exception:  # tabela ainda não existe neste banco
                continue
    return {w for w, n in contagem.items() if n >= minimo} | VOCAB_BASE


def conhecido(texto: str, vocab: set[str]) -> bool:
    """A maioria das palavras de 4+ letras do trecho existe em nomes de produtos (as de 3 letras não contam)."""
    from .vinculo import normalizar

    ws = re.findall(r"[a-z]{4,}", normalizar(texto))
    return bool(ws) and sum(w in vocab and w not in NAO_PRODUTO for w in ws) / len(ws) >= 0.6


def abrir_dicionario(caminho: str | Path):
    """Conexão com o dicionário de códigos (dicionario.db ou .db.gz), ou None se não existir."""
    import gzip
    import sqlite3

    caminho = Path(caminho)
    if not caminho.exists():
        return None
    if caminho.suffix == ".gz":
        destino = Path(tempfile.mkdtemp()) / "dicionario.db"
        with gzip.open(caminho, "rb") as origem, open(destino, "wb") as saida:
            shutil.copyfileobj(origem, saida)
        caminho = destino
    return sqlite3.connect(caminho)


def nomes_das_linhas(linhas: list[dict], vocab: set[str]) -> list[str]:
    """Linhas sem preço que são nome de produto conhecido; linhas seguidas na mesma coluna viram um nome só."""
    nomes, atual, anterior = [], [], None
    for l in linhas:
        junto = (anterior is not None and l["pagina"] == anterior["pagina"]
                 and 0 <= l["topo"] - anterior["base"] < 1.2 * max(1, l["base"] - l["topo"])
                 and min(l["direita"], anterior["direita"]) - max(l["esquerda"], anterior["esquerda"]) > 0)
        boa = not RE_PRECO.search(l["texto"]) and limpar_nome(l["texto"]) is not None
        if (not junto or not boa) and atual:
            nomes.append(" ".join(atual))
            atual = []
        if boa:
            atual.append(l["texto"])
        anterior = l
    if atual:
        nomes.append(" ".join(atual))
    saida = []
    for n in nomes:
        n = limpar_nome(n)
        if n and len(n.split()) >= 2 and conhecido(n, vocab) and n not in saida:
            saida.append(n)
    return saida


def ocr_linhas(caminho: Path) -> list[dict]:
    tsv = subprocess.run(["tesseract", str(caminho), "stdout", "-l", "por", "--psm", "11", "tsv"],
                         capture_output=True, text=True, timeout=120).stdout
    return linhas_do_tsv(tsv)


def ocr(caminho: Path) -> list[Trecho]:
    return trechos_das_linhas(ocr_linhas(caminho))


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


def texto_do_pdf(caminho: Path) -> list[Trecho]:
    """Texto embutido no PDF (pdftotext -tsv tem o mesmo formato do Tesseract). Vazio se o PDF for só imagem."""
    if not shutil.which("pdftotext"):
        return []
    tsv = subprocess.run(["pdftotext", "-tsv", str(caminho), "-"], capture_output=True, text=True, timeout=120).stdout
    return trechos_das_linhas(linhas_do_tsv(tsv))


def paginas_do_pdf(caminho: Path, max_paginas: int = 8) -> list[Path]:
    """PDF só de imagem: vira PNG por página para o Tesseract."""
    if not shutil.which("pdftoppm"):
        return []
    subprocess.run(["pdftoppm", "-r", "120", "-l", str(max_paginas), "-png", str(caminho), str(caminho.with_suffix(""))],
                   capture_output=True, timeout=300)
    return sorted(caminho.parent.glob(caminho.stem + "-*.png"))


def _ler_imagem(lido: EncarteLido, linhas: list[dict], vocab: set[str] | None, filtrar: bool) -> None:
    lido.trechos += [t for t in trechos_das_linhas(linhas) if plausivel(t) and (not filtrar or conhecido(t.texto, vocab))]
    if filtrar:  # sem vocabulário, nome sem preço seria mais lixo que informação
        com_preco = {t.texto for t in lido.trechos}
        lido.nomes += [n for n in nomes_das_linhas(linhas, vocab) if n not in com_preco and n not in lido.nomes][:300]


def ler_encartes(nav: Navegador, dias: int = 4, hoje: date | None = None, max_imagens: int = 120,
                 vocab: set[str] | None = None) -> list[EncarteLido]:
    """Encartes vigentes (validade de hoje em diante): do encartesdf.com.br e dos sites dos próprios mercados.
    Com `vocab` (palavras de nomes conhecidos, ao menos 5 mil), trechos lidos de imagem só ficam se forem nome de produto."""
    filtrar = vocab is not None and len(vocab - VOCAB_BASE) >= 5000
    hoje = hoje or date.today()
    saida, lidas = [], 0
    try:
        lista = folhetos_df.todos(nav) + encartesdf.listar(nav, dias=dias, hoje=hoje)
    except Exception as e:
        print(f"lista de encartes: {e!r}")
        lista = folhetos_df.todos(nav)
    with tempfile.TemporaryDirectory() as tmp:
        pasta = Path(tmp)
        for n, e in enumerate(lista):
            if e.validade_fim and e.validade_fim < hoje.isoformat():
                continue
            lido = EncarteLido(e.mercado, e.post, e.publicado, e.validade_fim, e.imagens, e.pdf, e.titulo)
            if e.pdf and lidas < max_imagens:
                dados = nav.get_bytes(e.pdf)
                if dados:
                    arq = pasta / f"{n}.pdf"
                    arq.write_bytes(dados)
                    lido.trechos = texto_do_pdf(arq)
                    if len(lido.trechos) < 3 and not e.imagens and tesseract_disponivel():
                        for pagina in paginas_do_pdf(arq):
                            lidas += 1
                            png = _preparar(pagina.read_bytes(), pasta, f"{n}-{pagina.stem}.png")
                            _ler_imagem(lido, ocr_linhas(png), vocab, filtrar)
            if len(lido.trechos) < 3 and not lido.nomes:
                lido.trechos = []
                for i, url in enumerate(e.imagens):
                    if lidas >= max_imagens or not tesseract_disponivel():
                        break
                    dados = nav.get_bytes(url)
                    if not dados:
                        continue
                    lidas += 1
                    _ler_imagem(lido, ocr_linhas(_preparar(dados, pasta, f"{n}-{i}{Path(url.split('?')[0]).suffix or '.img'}")),
                                vocab, filtrar)
            saida.append(lido)
    return saida


def para_json(encartes: list[EncarteLido]) -> list[dict]:
    return [{**{k: v for k, v in asdict(e).items() if k != "trechos"},
             "trechos": [{"t": t.texto, "p": t.preco} for t in e.trechos]} for e in encartes]
