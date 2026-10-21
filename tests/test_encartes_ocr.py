import unittest

from historico_precos import encartes_ocr

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


if __name__ == "__main__":
    unittest.main()
