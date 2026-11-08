"""Teste real das fontes novas: encartes do Ultrabox e do Assaí DF (lista + leitura de uma página) e 30 produtos
de cada loja do Super Veneza com vínculo pelo nome (banco e dicionário do ramo dados)."""

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos import encartes_ocr  # noqa: E402
from historico_precos.__main__ import LOJAS_PADRAO, carregar_lojas  # noqa: E402
from historico_precos.armazenamento import Banco  # noqa: E402
from historico_precos.fontes import folhetos_df, pagina_produto  # noqa: E402
from historico_precos.ramo_dados import recuperar  # noqa: E402
from historico_precos.rede import Navegador  # noqa: E402
from historico_precos.vinculo import montar_catalogo  # noqa: E402

nav = Navegador()
recuperar("precos.db")
subprocess.run(["git", "show", "origin/dados:dicionario.db.gz"], stdout=open("dicionario.db.gz", "wb"))
banco = Banco("precos.db")
dic = encartes_ocr.abrir_dicionario("dicionario.db.gz")
vocab = encartes_ocr.vocabulario(banco.con, dic)
catalogo = montar_catalogo(banco.con, dic)

for fonte in (folhetos_df.ultrabox, folhetos_df.assai_df):
    lista = fonte(nav)
    print(f"\n===== {fonte.__name__}: {len(lista)} encarte(s)")
    for e in lista:
        print(f"  {e.titulo} | publicado {e.publicado} | até {e.validade_fim} | {len(e.imagens)} imagem(ns) | {e.post}")
    if lista and encartes_ocr.tesseract_disponivel():
        e = lista[0]
        lido = encartes_ocr.EncarteLido(e.mercado, e.post, e.publicado, e.validade_fim, e.imagens[:2])
        with tempfile.TemporaryDirectory() as tmp:
            for i, url in enumerate(e.imagens[:2]):
                dados = nav.get_bytes(url)
                print(f"  imagem {i}: {len(dados or b'')} bytes")
                if dados:
                    png = encartes_ocr._preparar(dados, Path(tmp), f"{i}.jpg")
                    for cor in (False, True):
                        encartes_ocr._ler_imagem(lido, encartes_ocr.ocr_linhas(png, cor=cor), vocab, True)
        encartes_ocr.triangular([lido], catalogo)
        print(f"  lidos: {len(lido.trechos)} preço(s), {len(lido.nomes)} nome(s) sem preço")
        for t in lido.trechos[:15]:
            print(f"     R$ {t.preco:>7.2f}  {t.texto[:60]:<60} códigos: {len(t.eans)}")

for loja in [l for l in carregar_lojas(str(LOJAS_PADRAO)) if l["nome"].startswith("Super Veneza")]:
    r = pagina_produto.catalogar_por_nome(nav, banco, loja, catalogo, limite=30)
    print(f"\n===== {loja['nome']}: {r}")
    for linha in banco.con.execute("SELECT nome, preco, ean, nome_catalogo FROM produtos_loja WHERE loja = ? AND lido_em IS NOT NULL LIMIT 30",
                                   (loja["nome"],)):
        print("   ", linha)
