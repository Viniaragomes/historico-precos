import unittest

from historico_precos.vinculo import Catalogo, tokens

CATALOGO = Catalogo([
    ("7896005800027", "Café Torrado e Moído 3 Corações Tradicional 500g", "3 Corações"),
    ("7896005800362", "Café em Pó a Vácuo Tradicional 3 Corações 250g", "3 Corações"),
    ("7891910030378", "Café Torrado Moído Tradicional Vácuo União 500g", "União"),
    ("7896051111108", "Leite UHT Integral Natural Milk Itambé 1L", "Itambé"),
    ("7896051111115", "Leite UHT Desnatado Natural Milk Itambé 1L", "Itambé"),
    ("7898000000001", "Cerveja Império Puro Malte Lata 350ml", "Império"),
    ("7898000000002", "Cerveja Império Helles Lata 350ml", "Império"),
    ("7890000000009", "Produto Sem Tamanho", "X"),
])


class TestVinculo(unittest.TestCase):
    def test_vincula_mesmo_produto_com_nome_diferente(self):
        v = CATALOGO.vincular("Café 3 Corações Tradicional Torrado e Moído 500g", "3 Corações")
        self.assertEqual(v.ean, "7896005800027")

    def test_tamanho_diferente_nao_vincula(self):
        self.assertIsNone(CATALOGO.vincular("Café 3 Corações Tradicional 1kg", "3 Corações"))

    def test_mesmo_tamanho_em_outra_unidade(self):
        self.assertEqual(CATALOGO.vincular("Leite Integral Natural Milk Itambé 1000ml", "Itambé").ean, "7896051111108")

    def test_marca_diferente_nao_vincula(self):
        self.assertIsNone(CATALOGO.vincular("Café Torrado Moído Tradicional Vácuo 500g", "Pilão"))

    def test_abreviacao_de_atacado(self):
        self.assertIn("cerveja", tokens("BEB.CERV.IMPERIO 350ML PURO MALTE"))
        self.assertEqual(CATALOGO.vincular("BEB.CERV.IMPERIO 350ML PURO MALTE", "Imperio").ean, "7898000000001")

    def test_variedade_decide(self):
        self.assertEqual(CATALOGO.vincular("Leite Desnatado Natural Milk Itambé 1L", "Itambé").ean, "7896051111115")

    def test_sem_tamanho_nao_vincula(self):
        self.assertIsNone(CATALOGO.vincular("Café 3 Corações Tradicional", "3 Corações"))

    def test_ambiguo_nao_vincula(self):
        cat = Catalogo([("1", "Biscoito Recheado Chocolate Marca 100g", "Marca"), ("2", "Biscoito Recheado Morango Marca 100g", "Marca")])
        self.assertIsNone(cat.vincular("Biscoito Recheado Marca 100g", "Marca"))


if __name__ == "__main__":
    unittest.main()


class TestCasosReais(unittest.TestCase):
    """Casos vistos no teste real de 21/10/2026 (Big Box x Open Food Facts)."""

    def setUp(self):
        self.cat = Catalogo([
            ("7891000377765", "Achocolatado Pó 30 Cacau Nescau Lata 180g", "Nescau"),
            ("7896594972310", "Sorbet Açaí Frooty Pote 1,5l", "Frooty"),
            ("7896005800010", "Café Torrado E Moído Tradicional 3 Corações Pacote 500g", "3 Corações"),
            ("7891000379691", "Achocolatado em pó - Nescau 370g", "Nescau"),
        ])

    def test_percentual_diferente_nao_vincula(self):
        self.assertIsNone(self.cat.vincular("Achocolatado em Pó 60% Cacau Nescau Extra Cacau Lata 180g", "Nescau"))
        self.assertEqual(self.cat.vincular("Achocolatado em Pó 30% Cacau Nescau Lata 180g", "Nescau").ean, "7891000377765")

    def test_sabor_a_mais_nao_vincula(self):
        self.assertIsNone(self.cat.vincular("Sorbet Açaí com Guaraná Frooty Pote 1,5l", "Frooty"))

    def test_casos_certos_continuam(self):
        self.assertEqual(self.cat.vincular("Café Torrado e Moído Tradicional 3 Corações Pacote 500g", "3 Corações").ean, "7896005800010")
        self.assertEqual(self.cat.vincular("Achocolatado em Pó Nescau 370G", "Nescau").ean, "7891000379691")
