"""Vínculo por nome: liga um produto de loja sem código de barras ao EAN de um produto já conhecido.

Usado para lojas cujo site não publica o código de barras (Big Box, Fort). As regras são conservadoras, porque um
vínculo errado mostraria o preço de outro produto:
  1. o tamanho precisa ser igual (500 g = 0,5 kg); sem tamanho do lado da loja, não vincula;
  2. a marca precisa bater quando os dois lados informam a marca; quando só a loja informa, a marca precisa aparecer
     no nome do candidato (sem isso, "Azeite Bertolli 500ml" casaria com um "Azeite extra virgem 500ml" qualquer);
  3. o nome precisa ser parecido (palavras em comum, depois de expandir abreviações de atacado e tirar palavras de
     embalagem); se todas as palavras do nome mais curto (3 ou mais) estão no mais longo, conta como parecido;
  4. sem empate: se o segundo melhor candidato estiver perto do primeiro, não vincula.
Todo preço vinculado sai com metodo="vinculo-nome", o nome original da loja e o link, para quem quiser conferir.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass

from .causas import embalagem

LIMIAR = 0.8  # semelhança mínima (subiu de 0,6 após conferir vínculos reais com sabor ou variante errados)
MARGEM = 0.1  # distância mínima para o segundo melhor
CONTIDO = 0.85  # nota de quando um nome está inteiro dentro do outro (3+ palavras): "Arroz Brilhante Tipo 1 5kg"

# abreviações comuns em nomes de atacado ("BEB.CERV.IMPERIO 350ML LT")
ABREVIACOES = {
    "beb": "bebida", "cerv": "cerveja", "refrig": "refrigerante", "refri": "refrigerante", "achoc": "achocolatado",
    "bisc": "biscoito", "biscoit": "biscoito", "choc": "chocolate", "lte": "leite", "lt": "lata", "cond": "condensado",
    "desn": "desnatado", "integ": "integral", "int": "integral", "trad": "tradicional", "sach": "sache", "deterg": "detergente",
    "amac": "amaciante", "sab": "sabao", "po": "po", "pap": "papel", "hig": "higienico", "macarr": "macarrao",
    "marg": "margarina", "manteig": "manteiga", "azeit": "azeite", "ext": "extra", "virg": "virgem", "tp": "tipo",
    "arr": "arroz", "feij": "feijao", "car": "carioca", "acuc": "acucar", "refin": "refinado", "cafe": "cafe",
}
VAZIAS = {"de", "da", "do", "das", "dos", "e", "com", "sem", "para", "em", "tipo", "pct", "pacote", "un", "und", "unid",
          "cx", "caixa", "lata", "garrafa", "pet", "pote", "sache", "bandeja", "fardo", "kg", "g", "gr", "ml", "l", "lt",
          # embalagem e chamada de oferta: não distinguem produto ("Frasco 1L", "Leve 12 Pague 11")
          "frasco", "vidro", "pouch", "refil", "spray", "unidade", "unidades", "leve", "pague", "atacado"}


# palavras que distinguem variantes: se aparece só de um lado, são produtos diferentes (sabor, ingrediente, versão)
DISTINTIVAS = set("""
guarana bacon morango chocolate baunilha limao laranja uva coco abacaxi maracuja banana manga goiaba pessego cereja
framboesa amora acerola caju melancia melao kiwi limao tangerina mexerica menta hortela canela cafe leite ninho
frango carne bovina suina peru calabresa presunto queijo cheddar mussarela parmesao requeijao catupiry tomate cebola
alho ervas pimenta picante apimentado defumado ovo ovos atum sardinha salmao camarao bacalhau
integral desnatado semidesnatado zero diet light lactose glutem gluten organico sem acucar adocado
tradicional extra forte suave intenso descafeinado expresso gourmet premium
original classic classico cappuccino mocha
""".split()) - {"gourmet", "premium", "original", "classic", "classico", "tradicional"}  # marketing, não variante


def normalizar(texto: str | None) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9,.]+", " ", sem_acento.replace(".", " ")).strip()


def tokens(texto: str | None) -> set[str]:
    sem_qtd = re.sub(r"\d+(?:[.,]\d+)?\s*(kg|g|gr|grs|mg|l|lt|ml|litros?)\b", " ", normalizar(texto))
    saida = set()
    for t in re.findall(r"[a-z0-9]+", sem_qtd):
        t = ABREVIACOES.get(t, t)
        # números que não são tamanho contam (30% x 60% cacau, 46º INPM): diferenciam variantes do mesmo produto
        if (len(t) > 1 or t.isdigit()) and t not in VAZIAS:
            saida.add(t)
    return saida


def semelhanca(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


@dataclass
class Vinculo:
    ean: str
    semelhanca: float
    nome_catalogo: str


class Catalogo:
    """Produtos conhecidos (EAN, nome, marca), indexados por palavra para comparar rápido."""

    def __init__(self, itens: list[tuple[str, str, str | None]]):
        self.itens = []
        self.indice: dict[str, list[int]] = defaultdict(list)
        for ean, nome, marca in itens:
            if not nome:
                continue
            qtd = embalagem.quantidade(nome)
            if not qtd:
                continue  # sem tamanho no nome conhecido, não dá para garantir o vínculo
            tk = tokens(nome) | tokens(marca)
            i = len(self.itens)
            self.itens.append((ean, nome, tokens(marca), qtd, tk))
            for t in tk:
                self.indice[t].append(i)

    def vincular(self, nome: str, marca: str | None = None) -> Vinculo | None:
        qtd = embalagem.quantidade(nome)
        if not qtd:
            return None
        tk = tokens(nome) | tokens(marca)
        marca_tk = tokens(marca)
        contagem: dict[int, int] = defaultdict(int)
        for t in tk:
            for i in self.indice.get(t, ()):
                contagem[i] += 1
        notas = []
        for i, comuns in contagem.items():
            if comuns < 2:
                continue
            ean, nome_cat, marca_cat, qtd_cat, tk_cat = self.itens[i]
            if qtd_cat[1] != qtd[1] or abs(qtd_cat[0] - qtd[0]) > 1e-6:
                continue  # tamanho diferente: produto diferente
            if marca_tk and marca_cat and not (marca_tk & marca_cat):
                continue  # marcas diferentes
            if marca_tk and not (marca_tk & tk_cat):
                continue  # a loja diz a marca, e ela não está no candidato
            if (tk ^ tk_cat) & DISTINTIVAS:
                continue  # um lado tem sabor/ingrediente/variante que o outro não tem
            nota = semelhanca(tk, tk_cat)
            comuns_ = len(tk & tk_cat)
            if comuns_ >= 3 and comuns_ == min(len(tk), len(tk_cat)):
                nota = max(nota, CONTIDO)
            notas.append((nota, ean, nome_cat))
        if not notas:
            return None
        notas.sort(reverse=True)
        melhor = notas[0]
        if melhor[0] < LIMIAR:
            return None
        outro = next((n for n in notas[1:] if n[1] != melhor[1]), None)
        if outro and melhor[0] - outro[0] < MARGEM:
            return None  # ambíguo: dois produtos diferentes quase iguais
        return Vinculo(melhor[1], round(melhor[0], 3), melhor[2])
