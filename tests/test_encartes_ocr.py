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
        vocab = encartes_ocr.vocabulario(con)
        self.assertTrue(encartes_ocr.conhecido("ASA DE FRANGO SADIA", vocab))
        self.assertTrue(encartes_ocr.conhecido("Sabonete Dove original", vocab))
        self.assertFalse(encartes_ocr.conhecido("asa alma ad", vocab))
        self.assertFalse(encartes_ocr.conhecido("posta sesaos", vocab))

    def test_nomes_sem_preco(self):
        vocab = {"file", "peito", "frango", "seara", "congelado", "pacote", "uva", "thompson", "bandeja"}
        linha = lambda t, topo, esq=10: {"texto": t, "pagina": 1, "topo": topo, "base": topo + 20, "esquerda": esq, "direita": esq + 300}
        linhas = [linha("Filé de Peito de Frango Seara", 100), linha("Congelado Pacote 1kg", 124), linha("ácie: ;99", 150),
                  linha("Uva Thompson", 300), linha("Bandeja 5009", 324), linha("asa alma ad", 500)]
        self.assertEqual(encartes_ocr.nomes_das_linhas(linhas, vocab),
                         ["Filé de Peito de Frango Seara Congelado Pacote 1kg", "Uva Thompson Bandeja 500g"])


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
