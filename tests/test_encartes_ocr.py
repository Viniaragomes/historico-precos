import shutil
import tempfile
import unittest
from pathlib import Path

from historico_precos import encartes_ocr
from historico_precos.fontes import folhetos_df

TSV = "\n".join([
    "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
    # coluna da esquerda: nome em duas linhas e preço embaixo
    "5\t1\t1\t1\t1\t1\t10\t100\t80\t20\t90\tCAFÉ",
    "5\t1\t1\t1\t1\t2\t95\t100\t120\t20\t90\tPILÃO",
    "5\t1\t1\t1\t2\t1\t10\t125\t60\t20\t88\t500g",
    "5\t1\t1\t1\t3\t1\t10\t150\t40\t30\t85\tR$",
    "5\t1\t1\t1\t3\t2\t55\t150\t70\t30\t85\t14,98",
    # coluna da direita: nome e preço na mesma linha
    "5\t1\t2\t1\t1\t1\t400\t100\t90\t20\t91\tARROZ",
    "5\t1\t2\t1\t1\t2\t495\t100\t90\t20\t91\tCAMIL",
    "5\t1\t2\t1\t1\t3\t590\t100\t40\t20\t91\t5KG",
    "5\t1\t2\t1\t1\t4\t640\t100\t70\t20\t91\t24,90",
    # lixo com confiança baixa
    "5\t1\t3\t1\t1\t1\t10\t500\t40\t20\t10\tXX",
    # preço sem nome (só números): fica de fora
    "5\t1\t4\t1\t1\t1\t10\t700\t60\t20\t90\t9,99",
])


class TestOCR(unittest.TestCase):
    def test_pareia_nome_e_preco(self):
        trechos = encartes_ocr.trechos_das_linhas(encartes_ocr.linhas_do_tsv(TSV))
        self.assertEqual(sorted((t.texto, t.preco) for t in trechos), sorted([("CAFÉ PILÃO 500g", 14.98), ("ARROZ CAMIL 5KG", 24.9)]))


    @unittest.skipUnless(shutil.which("pdftotext"), "sem pdftotext")
    def test_pdf_com_texto(self):
        try:
            from reportlab.pdfgen import canvas
        except ImportError:
            self.skipTest("sem reportlab")
        with tempfile.TemporaryDirectory() as tmp:
            arq = Path(tmp) / "e.pdf"
            c = canvas.Canvas(str(arq), pagesize=(600, 800))
            for x, nome, tam, preco in [(40, "FEIJÃO KICALDO", "CARIOCA 1kg", "7,99"), (330, "AÇÚCAR UNIÃO", "REFINADO 1kg", "4,49")]:
                c.setFont("Helvetica-Bold", 18); c.drawString(x, 700, nome)
                c.setFont("Helvetica", 14); c.drawString(x, 675, tam)
                c.setFont("Helvetica-Bold", 36); c.drawString(x, 625, "R$ " + preco)
            c.showPage(); c.save()
            trechos = encartes_ocr.texto_do_pdf(arq)
        self.assertEqual(sorted((t.texto, t.preco) for t in trechos),
                         [("AÇÚCAR UNIÃO REFINADO 1kg", 4.49), ("FEIJÃO KICALDO CARIOCA 1kg", 7.99)])


class TestVocabulario(unittest.TestCase):
    def test_descarta_palavra_inventada(self):
        import sqlite3

        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE produtos (ean, nome, marca, quantidade, fonte)")
        con.executemany("INSERT INTO produtos VALUES (?,?,?,?,?)", [("1", "Asa de frango Sadia 1kg", "Sadia", "", ""),
                                                                    ("2", "Sabonete Dove Original 90g", "Dove", "", "")])
        vocab = encartes_ocr.vocabulario(con, minimo=1)
        self.assertTrue(encartes_ocr.conhecido("ASA DE FRANGO SADIA", vocab))
        self.assertTrue(encartes_ocr.conhecido("Sabonete Dove original", vocab))
        self.assertFalse(encartes_ocr.conhecido("asa alma ad", vocab))  # "asa" (3 letras) não conta; "alma" não existe
        self.assertFalse(encartes_ocr.conhecido("posta sesaos", vocab))

    def test_nomes_sem_preco(self):
        vocab = {"file", "peito", "frango", "seara", "congelado", "pacote", "uva", "thompson", "bandeja"}
        linha = lambda t, topo, esq=10: {"texto": t, "pagina": 1, "topo": topo, "base": topo + 20, "esquerda": esq, "direita": esq + 300}
        linhas = [linha("Filé de Peito de Frango Seara", 100), linha("Congelado Pacote 1kg", 124), linha("ácie: ;99", 150),
                  linha("Uva Thompson", 300), linha("Bandeja 5009", 324), linha("asa alma ad", 500)]
        self.assertEqual(encartes_ocr.nomes_das_linhas(linhas, vocab),
                         ["Filé de Peito de Frango Seara Congelado Pacote 1kg", "Uva Thompson Bandeja 500g"])


class TestPlausivel(unittest.TestCase):
    def test_precos_impossiveis(self):
        T = encartes_ocr.Trecho
        self.assertFalse(encartes_ocr.plausivel(T("Banana Prata", 192.99)))
        self.assertFalse(encartes_ocr.plausivel(T("PÉ DE FRANGO RESFRIADO COPACOL", 169.90)))
        self.assertTrue(encartes_ocr.plausivel(T("CESTA BÁSICA", 150.0)))
        self.assertTrue(encartes_ocr.plausivel(T("ARROZ CAMIL 5kg", 24.9)))
        self.assertTrue(encartes_ocr.plausivel(T("Whisky Fardo 12 un", 300.0)))

    def test_propaganda_nao_e_produto(self):
        vocab = {"preco", "baixo", "todo", "vila", "jose", "picanha", "bovina"}
        self.assertFalse(encartes_ocr.conhecido("é preço baixo todo", vocab))
        self.assertTrue(encartes_ocr.conhecido("Picanha Bovina", vocab))


class TestComparar(unittest.TestCase):
    def test_agrupa_mesmo_produto_entre_mercados(self):
        T, E = encartes_ocr.Trecho, encartes_ocr.EncarteLido
        a = E("Dia a Dia", "https://a", "2026-10-20", "2026-10-25", [], "https://a.pdf",
              trechos=[T("BANANA NANICA", 2.49), T("LEITE ITAMBÉ INTEGRAL 1L", 4.79), T("CAFÉ PILÃO 500g", 14.98)])
        b = E("Super Big", "https://b", "2026-10-20", "2026-10-22", [],
              trechos=[T("BANANA NANICA", 4.99), T("LEITE ITAMBÉ DESNATADO 1L", 4.59), T("Café Pilão Tradicional 500g", 15.49)])
        c = E("Tatico", "https://c", "2026-10-20", None, [],
              trechos=[T("LEITE PIRACANJUBA INTEGRAL 1L", 4.39), T("CAFÉ PILÃO 250g", 8.99)])
        comp = encartes_ocr.comparar_mercados([a, b, c])
        resumo = {x["produto"]: [(o["mercado"], o["p"]) for o in x["ofertas"]] for x in comp}
        self.assertEqual(resumo, {"BANANA NANICA": [("Dia a Dia", 2.49), ("Super Big", 4.99)],
                                  "CAFÉ PILÃO 500g": [("Dia a Dia", 14.98), ("Super Big", 15.49)]})
        self.assertEqual(comp[0]["produto"], "BANANA NANICA")  # maior diferença primeiro

    def test_nome_sem_preco_entra_como_tambem_anunciado(self):
        T, E = encartes_ocr.Trecho, encartes_ocr.EncarteLido
        a = E("Dia a Dia", "https://a", "2026-10-20", None, [], trechos=[T("CAFÉ PILÃO 500g", 14.98)])
        b = E("Dona", "https://b", "2026-10-20", None, [], nomes=["Café Pilão Tradicional 500g"])
        (c,) = encartes_ocr.comparar_mercados([a, b])
        self.assertEqual([(o["mercado"], o["p"]) for o in c["ofertas"]], [("Dia a Dia", 14.98), ("Dona", None)])
        self.assertEqual(c["diferenca"], 0)


@unittest.skipUnless(shutil.which("tesseract"), "sem tesseract")
class TestPrecoEstilizado(unittest.TestCase):
    def test_centavos_pequenos_e_etiqueta_colorida(self):
        import glob

        from PIL import Image, ImageDraw, ImageFont

        fontes = glob.glob("/usr/share/fonts/**/DejaVuSans-Bold.ttf", recursive=True)
        if not fontes:
            self.skipTest("sem fonte DejaVu")
        f = lambda n: ImageFont.truetype(fontes[0], n)  # noqa: E731
        img = Image.new("RGB", (1200, 520), "white")
        d = ImageDraw.Draw(img)
        for x, nome, tam, reais, cent, fundo in [(40, "CAFÉ PILÃO", "500g", "14", "98", None),
                                                  (640, "ARROZ CAMIL", "TIPO 1 5kg", "24", "90", (200, 20, 20))]:
            d.text((x, 60), nome, fill="black", font=f(40))
            d.text((x, 115), tam, fill="black", font=f(32))
            if fundo:
                d.rectangle((x - 10, 170, x + 330, 320), fill=fundo)
            cor = "white" if fundo else "red"
            d.text((x + 70, 170), reais, fill=cor, font=f(120))
            d.text((x + 75 + d.textlength(reais, font=f(120)), 180), cent, fill=cor, font=f(56))
        with tempfile.TemporaryDirectory() as tmp:
            png = encartes_ocr._preparar(_bytes(img), Path(tmp), "e.jpg")
            lidos = sorted((t.texto, t.preco) for t in encartes_ocr.trechos_das_linhas(encartes_ocr.ocr_linhas(png)))
        self.assertEqual(lidos, [("ARROZ CAMIL TIPO 1 5kg", 24.9), ("CAFÉ PILÃO 500g", 14.98)])


@unittest.skipUnless(shutil.which("tesseract"), "sem tesseract")
class TestPrecoPertoDoNome(unittest.TestCase):
    def test_acha_preco_abaixo_do_nome(self):
        import glob

        from PIL import Image, ImageDraw, ImageFont

        fontes = glob.glob("/usr/share/fonts/**/DejaVuSans-Bold.ttf", recursive=True)
        if not fontes:
            self.skipTest("sem fonte DejaVu")
        img = Image.new("RGB", (900, 420), "white")
        d = ImageDraw.Draw(img)
        d.text((40, 40), "CAFÉ PILÃO TRADICIONAL 500g", fill="black", font=ImageFont.truetype(fontes[0], 40))
        d.text((40, 270), "R$ 14,98", fill="red", font=ImageFont.truetype(fontes[0], 60))  # longe do nome
        with tempfile.TemporaryDirectory() as tmp:
            png = encartes_ocr._preparar(_bytes(img), Path(tmp), "e.jpg")
            linhas = encartes_ocr.ocr_linhas(png, estilizados=False)
            self.assertEqual(encartes_ocr.trechos_das_linhas(linhas), [])  # a página inteira não junta os dois
            lido = encartes_ocr.EncarteLido("Mercado", "https://e", "2026-11-08", None, [])
            encartes_ocr._ler_imagem(lido, linhas, {"cafe", "pilao", "tradicional"}, True, png)
        self.assertEqual([(t.texto, t.preco) for t in lido.trechos], [("CAFÉ PILÃO TRADICIONAL 500g", 14.98)])
        self.assertEqual(lido.nomes, [])


def _bytes(img):
    import io

    b = io.BytesIO()
    img.save(b, "JPEG", quality=92)
    return b.getvalue()


class TestLimpeza(unittest.TestCase):
    def test_sobras_no_comeco(self):
        self.assertEqual(encartes_ocr.limpar_nome("AR e A A ei Costela Suína Sadia em Fatias"), "Costela Suína Sadia em Fatias")
        self.assertEqual(encartes_ocr.limpar_nome("Pé de frango Copacol"), "Pé de frango Copacol")


class TestTriangulacao(unittest.TestCase):
    def test_anuncios_diferentes_do_mesmo_codigo_se_juntam(self):
        from historico_precos.vinculo import Catalogo

        cat = Catalogo([("7891000100103", "Achocolatado em Pó Nescau 2.0 Lata 370g", "Nescau"),
                        ("7891000100104", "Achocolatado em Pó Toddy Original Lata 370g", "Toddy")])
        T, E = encartes_ocr.Trecho, encartes_ocr.EncarteLido
        a = E("Dia a Dia", "https://a", "2026-10-20", None, [], trechos=[T("NESCAU 370G", 8.99)])
        b = E("Tatico", "https://b", "2026-10-20", None, [], trechos=[T("ACHOCOLATADO NESCAU LATA 370G", 9.49)])
        c = E("Fort", "https://c", "2026-10-20", None, [], trechos=[T("TODDY 370G", 8.49)])
        encartes_ocr.triangular([a, b, c], cat)
        self.assertEqual(a.trechos[0].eans, ["7891000100103"])
        self.assertEqual(c.trechos[0].eans, ["7891000100104"])
        (comp,) = encartes_ocr.comparar_mercados([a, b, c])  # Toddy fica de fora: outro produto, um mercado só
        self.assertEqual([(o["mercado"], o["p"]) for o in comp["ofertas"]], [("Dia a Dia", 8.99), ("Tatico", 9.49)])
        self.assertEqual(comp["eans"], ["7891000100103"])


class TestFontesNovas(unittest.TestCase):
    def test_ultrabox_agrupa_paginas_recentes(self):
        from datetime import date

        midia = [{"source_url": "https://ultraboxatacado.com.br/wp-content/uploads/2026/11/ultrabox-rede-2026-11-07-pagina-2.jpeg"},
                 {"source_url": "https://ultraboxatacado.com.br/wp-content/uploads/2026/11/ultrabox-rede-2026-11-07-pagina-1.jpeg"},
                 {"source_url": "https://ultraboxatacado.com.br/wp-content/uploads/2026/02/campanha-668-pagina-1-1.jpeg"},
                 {"source_url": "https://ultraboxatacado.com.br/wp-content/uploads/2026/09/ultrabox-rede-2026-09-01-pagina-1.jpeg"}]
        (e,) = folhetos_df.ultrabox(NavFalso(json=midia), hoje=date(2026, 11, 8))
        self.assertEqual(e.mercado, "Supermercado Ultrabox")
        self.assertEqual([u.rsplit("-", 1)[1] for u in e.imagens], ["1.jpeg", "2.jpeg"])

    def test_assai_df_pelo_portafolhetos(self):
        from datetime import date

        lista = ('<a href="/assai-atacadista/assai-atacadista-ofertas-df-de-domingo-08-11-2026-481900/">'
                 '<a href="/assai-atacadista/assai-atacadista-ofertas-df-de-segunda-feira-02-11-2026-479570/">'
                 '<a href="/assai-atacadista/assai-atacadista-ofertas-de-quinta-feira-05-11-2026-481348/">')
        folheto = ('"description":"Assaí ofertas válidas de 08/11/2026 até 10/11/2026" '
                   '<img src="https://na.leafletscdn.com/thumbor/abc=/0x0/filters:format(webp)/com.br/data/7/481900/0.jpg">')

        class Nav:
            def get_texto(self, url):
                return lista if url.endswith("/assai-atacadista/") else folheto

        (e,) = folhetos_df.assai_df(Nav(), hoje=date(2026, 11, 8))
        self.assertEqual((e.mercado, e.publicado, e.validade_fim), ("Assaí Atacadista", "2026-11-08", "2026-11-10"))
        self.assertEqual(e.imagens, ["https://na.leafletscdn.com/thumbor/abc=/0x0/filters:format(webp)/com.br/data/7/481900/0.jpg"])


class TestFontesNovas2(unittest.TestCase):
    def test_costa_so_df_e_sem_tamanhos_repetidos(self):
        from datetime import date

        up = "https://costaatacadao.com.br/wp-content/uploads"
        html = " ".join(f'<img src="{u}">' for u in [
            f"{up}/2026/11/feed-festival-de-bebidas-e-churrasco-df_0000_01.png",
            f"{up}/2026/11/feed-festival-de-bebidas-e-churrasco-df_0001_02.png",
            f"{up}/2026/11/feed-festival-de-bebidas-e-churrasco-go-e-entorno_0000_01.png",
            f"{up}/2026/11/tabloide-digital-festival-do-bebe-df-01-scaled.png",
            f"{up}/2026/11/tabloide-digital-festival-do-bebe-df-01-scaled.png",
            f"{up}/2026/03/tabloide-antigo-df-01.png"])
        encartes = folhetos_df.costa_df(NavFalso(texto=html), hoje=date(2026, 11, 8))
        self.assertEqual(sorted((e.titulo, len(e.imagens)) for e in encartes),
                         [("feed festival de bebidas e churrasco df", 2), ("tabloide digital festival do bebe df", 1)])

    def test_primor_ultimos_dias(self):
        from datetime import date

        midia = [{"date": "2026-11-07T08:50:00", "source_url": "https://primorsupermercado.com.br/wp-content/uploads/2026/11/WhatsApp-Image-2026-11-07-at-08.50.04.jpeg"},
                 {"date": "2026-11-07T08:51:00", "source_url": "https://primorsupermercado.com.br/wp-content/uploads/2026/11/Copia-de-Fixo-LinkedIn-Article-Cover-Image-1.png"},
                 {"date": "2026-10-01T08:00:00", "source_url": "https://primorsupermercado.com.br/wp-content/uploads/2026/10/WhatsApp-Image-2026-10-01.jpeg"}]
        (e,) = folhetos_df.primor(NavFalso(json=midia), hoje=date(2026, 11, 8))
        self.assertEqual((e.mercado, e.publicado, len(e.imagens)), ("Supermercado Primor", "2026-11-07", 1))


class TestFiltrosDePreco(unittest.TestCase):
    def test_frase_de_preco_unitario(self):
        T = encartes_ocr.Trecho
        self.assertFalse(encartes_ocr.plausivel(T("Nesta embalagem, o quilo sai por", 49.9)))
        self.assertFalse(encartes_ocr.plausivel(T("com 36 unidades. Valor unitário", 0.85)))
        self.assertTrue(encartes_ocr.plausivel(T("Uva Thompson Bandeja 500g", 5.98)))

    def test_conferencia_com_preco_das_lojas(self):
        T, E = encartes_ocr.Trecho, encartes_ocr.EncarteLido
        e = E("Ultrabox", "https://u", "2026-11-08", None, [], trechos=[
            T("Amaciante Ypê 2L", 0.98, eans=["7896098900208"]),  # leitura errada: lojas cobram ~R$ 15
            T("Amaciante Ypê 2L", 12.98, eans=["7896098900208"]),  # promoção plausível
            T("Produto sem código", 0.98)])  # sem referência: segue os filtros de sempre
        self.assertEqual(encartes_ocr.conferir_com_lojas([e], {"7896098900208": 15.49}), 1)
        self.assertEqual([t.preco for t in e.trechos], [12.98, 0.98])


class TestUnidadeDeVenda(unittest.TestCase):
    def test_kg_nao_compara_com_unidade(self):
        T, E = encartes_ocr.Trecho, encartes_ocr.EncarteLido
        a = E("A", "https://a", "2026-11-08", None, [], trechos=[T("BANANA NANICA KG", 4.99)])
        b = E("B", "https://b", "2026-11-08", None, [], trechos=[T("BANANA NANICA", 2.49)])
        c = E("C", "https://c", "2026-11-08", None, [], trechos=[T("BANANA NANICA KG", 5.49)])
        (comp,) = encartes_ocr.comparar_mercados([a, b, c])
        self.assertEqual([o["mercado"] for o in comp["ofertas"]], ["A", "C"])
        self.assertEqual(encartes_ocr.unidade_venda("Arroz Camil 5kg"), "un")


class TestRede(unittest.TestCase):
    def test_mesma_rede_com_outro_nome(self):
        self.assertEqual(encartes_ocr.nome_da_rede("Dia a Dia Atacadista"), "Atacadão Dia a Dia")
        self.assertEqual(encartes_ocr.nome_da_rede("Supermercado Tatico"), "Supermercado Tatico")


class TestComandoEncartes(unittest.TestCase):
    def test_exporta_e_imprime_com_nome_sem_preco(self):
        import io
        import json
        from contextlib import redirect_stdout
        from unittest import mock

        from historico_precos import __main__ as cli

        T, E = encartes_ocr.Trecho, encartes_ocr.EncarteLido
        lidos = [E("Dia a Dia", "https://a", "2026-10-20", None, [], trechos=[T("CAFÉ PILÃO 500g", 14.98)]),
                 E("Dona", "https://b", "2026-10-20", None, [], nomes=["Café Pilão Tradicional 500g"])]
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(encartes_ocr, "ler_encartes", return_value=lidos), \
                redirect_stdout(io.StringIO()) as saida:
            cli.main(["--banco", f"{tmp}/b.db", "encartes-dia", "--dicionario", f"{tmp}/nao-existe.gz",
                      "--exportar", f"{tmp}/e.json"])
            d = json.loads(Path(f"{tmp}/e.json").read_text(encoding="utf-8"))
        self.assertEqual(len(d["comparacoes"]), 1)
        self.assertIn("(preço no encarte)", saida.getvalue())


class NavFalso:
    def __init__(self, json=None, texto=None):
        self.json, self.texto = json, texto

    def get_json(self, url):
        return self.json

    def get_texto(self, url):
        return self.texto


class TestFolhetosDF(unittest.TestCase):
    def test_dia_a_dia_so_df(self):
        base = {"date": "2026-10-20T18:00:09", "link": "https://ofertas.diaadiaatacadista.com.br/ofertas/x/",
                "publishpress_future_action": {"enabled": True, "date": "2026-10-21 22:11:00"}}
        tab = [{"pdf_do_tabloide": "https://o/x.pdf", "paginas_do_tabloide": ["https://o/p1.jpeg"]}]
        nav = NavFalso(json=[
            {**base, "title": {"rendered": "Dia de Feira &#8211; 21/10 &#8211; DF E ENTORNO"},
             "acf": {"regiao": ["DF"], "segmentacao_df": ["Gama", "Guará II"], "tabloide": tab}},
            {**base, "title": {"rendered": "Dia de Feira &#8211; GOIAS"}, "acf": {"regiao": ["GO"], "tabloide": tab}},
        ])
        (e,) = folhetos_df.dia_a_dia(nav)
        self.assertEqual((e.mercado, e.validade_fim, e.pdf, e.imagens), ("Atacadão Dia a Dia", "2026-10-21", "https://o/x.pdf", ["https://o/p1.jpeg"]))
        self.assertEqual(e.titulo, "Dia de Feira – 21/10 – DF E ENTORNO (2 lojas)")

    def test_dona_pdf_e_validade(self):
        html = '<a href="https://donafazbem.com.br/wp-content/uploads/2026/10/DONA-Festival-Carrinho-Cheio-19-a-21-10-2026.pdf">BAIXAR</a>'
        (e,) = folhetos_df.dona(NavFalso(texto=html * 2))
        self.assertEqual((e.mercado, e.validade_fim, e.publicado), ("Dona", "2026-10-21", "2026-10-01"))


if __name__ == "__main__":
    unittest.main()
