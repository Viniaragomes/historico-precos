import json
import os
import tempfile
import unittest
from types import SimpleNamespace

from historico_precos.armazenamento import Banco
from historico_precos.encartes import AgenteEncartes, ErroEncarte, casar, semelhanca
from historico_precos.modelo import Produto
from historico_precos.rede import Navegador

LEITURA = {
    "loja": "Mercado Exemplo",
    "validade_inicio": "2026-10-16",
    "validade_fim": "2026-10-22",
    "itens": [
        {"descricao": "CAFÉ TORRADO E MOÍDO EXEMPLO 500G", "preco": 22.9, "preco_de": 27.9, "unidade_venda": "un", "condicao": None, "ean": None},
        {"descricao": "Leite Condensado Exemplo 395g", "preco": 5.49, "preco_de": None, "unidade_venda": "un", "condicao": "Leve 3 pague 2", "ean": None},
        {"descricao": "Arroz Branco Desconhecido 5kg", "preco": 24.9, "preco_de": None, "unidade_venda": "un", "condicao": None, "ean": None},
        {"descricao": "Café Torrado e Moído Exemplo 250g", "preco": 12.5, "preco_de": None, "unidade_venda": "un", "condicao": None, "ean": None},
        {"descricao": "Biscoito com código", "preco": 3.99, "preco_de": None, "unidade_venda": "un", "condicao": None, "ean": "7891234567895"},
        {"descricao": "preço ilegível", "preco": 0, "preco_de": None, "unidade_venda": None, "condicao": None, "ean": None},
    ],
}


class ClienteFalso:
    """Imita client.beta.messages.create e guarda o pedido feito."""

    def __init__(self, resposta=LEITURA, stop_reason="end_turn"):
        self.pedidos = []
        bloco = SimpleNamespace(type="text", text=json.dumps(resposta))
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self._resposta = SimpleNamespace(stop_reason=stop_reason, content=[bloco] if stop_reason != "refusal" else [])

    def _create(self, **kwargs):
        self.pedidos.append(kwargs)
        return self._resposta


class TestEncartes(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.banco = Banco(os.path.join(self.dir.name, "t.db"))
        self.banco.salvar_produto(Produto("7896005800027", nome="Café Torrado e Moído Exemplo 500g"))
        self.banco.salvar_produto(Produto("7891000100103", nome="Leite Condensado Exemplo 395g"))
        self.imagem = os.path.join(self.dir.name, "encarte.png")
        with open(self.imagem, "wb") as f:
            f.write(b"\x89PNG fake")

    def tearDown(self):
        self.banco.con.close()
        self.dir.cleanup()

    def test_semelhanca_e_casamento(self):
        catalogo = [("1", "Café Torrado e Moído Exemplo 500g"), ("2", "Café Torrado e Moído Exemplo 250g")]
        self.assertEqual(casar("CAFÉ TORRADO E MOÍDO EXEMPLO 500G", catalogo)[0], "1")
        self.assertEqual(casar("Café Torrado e Moído Exemplo 250g", catalogo)[0], "2")  # o tamanho decide
        self.assertIsNone(casar("Café Torrado e Moído Exemplo 1kg", catalogo))
        self.assertIsNone(casar("Arroz Branco 5kg", catalogo))
        self.assertGreater(semelhanca("Café Pilão 500g", "CAFE PILAO 500 G"), 0.99)

    def test_processar(self):
        cliente = ClienteFalso()
        agente = AgenteEncartes(self.banco, cliente)
        r = agente.processar(self.imagem, loja="Mercado Exemplo", cidade="Brasília", fonte="https://mercado.exemplo/encarte")
        self.assertEqual((r["itens"], r["vinculados"], r["pendentes"], r["condicionais"]), (5, 2, 2, 1))
        self.assertEqual(r["precos_novos"], 2)

        # pedido para a IA: modelo, saída estruturada, fallback e imagem em base64
        pedido = cliente.pedidos[0]
        self.assertEqual(pedido["model"], "claude-opus-5-5")
        self.assertEqual(pedido["fallbacks"], "default")
        self.assertEqual(pedido["output_config"]["format"]["type"], "json_schema")
        self.assertEqual(pedido["messages"][0]["content"][0]["source"]["media_type"], "image/png")

        # o café de 500g virou preço, com a data da validade e a fonte do encarte
        cafe = [p for p in self.banco.precos("7896005800027") if p.fonte == "encarte"][0]
        self.assertEqual((cafe.preco, cafe.preco_de, cafe.data_observada, cafe.url_evidencia),
                         (22.9, 27.9, "2026-10-16", "https://mercado.exemplo/encarte"))
        # o leite condensado tem condição: não vira preço
        self.assertFalse([p for p in self.banco.precos("7891000100103") if p.fonte == "encarte"])
        # EAN impresso no encarte é usado direto
        self.assertEqual(self.banco.precos("7891234567895")[0].preco, 3.99)

    def test_fila_e_vinculo_manual(self):
        agente = AgenteEncartes(self.banco, ClienteFalso())
        agente.processar(self.imagem, loja="Mercado Exemplo")
        pendentes = agente.itens("pendente")
        self.assertEqual(sorted(i.descricao for i in pendentes), ["Arroz Branco Desconhecido 5kg", "Café Torrado e Moído Exemplo 250g"])
        arroz = next(i for i in pendentes if "Arroz" in i.descricao)
        self.assertEqual(agente.vincular(arroz.id, "7890000000017"), 1)
        self.assertEqual(self.banco.precos("7890000000017")[0].preco, 24.9)
        condicional = agente.itens("condicional")[0]
        with self.assertRaises(ErroEncarte):
            agente.vincular(condicional.id, "7891000100103")

    def test_recusa_e_formato(self):
        with self.assertRaises(ErroEncarte):
            AgenteEncartes(self.banco, ClienteFalso(stop_reason="refusal")).processar(self.imagem, loja="X")
        with self.assertRaises(ErroEncarte):
            AgenteEncartes(self.banco, ClienteFalso()).processar(os.path.join(self.dir.name, "a.txt"), loja="X")

    def test_baixar_da_internet_respeita_robots(self):
        nav = Navegador(intervalo=0, abrir=lambda url, dados=None: (200, "User-agent: *\nDisallow: /privado/"),
                        dormir=lambda s: None, abrir_bytes=lambda url: b"%PDF fake")
        agente = AgenteEncartes(self.banco, ClienteFalso(), nav)
        with self.assertRaises(ErroEncarte):
            agente.processar("https://mercado.exemplo/privado/encarte.pdf", loja="X")
        r = agente.processar("https://mercado.exemplo/ofertas/encarte.pdf", loja="X")
        self.assertEqual(r["vinculados"], 2)


if __name__ == "__main__":
    unittest.main()


class TestEncartesDF(unittest.TestCase):
    POSTS = [
        {"date": "2026-10-20T09:17:49", "link": "https://encartesdf.com.br/supermercado-uniao-ate-22-10-2026/",
         "title": {"rendered": "Supermercado Uni&atilde;o até 22-10-2026"},
         "content": {"rendered": '<img src="https://encartesdf.com.br/wp-content/uploads/2026/10/WhatsApp Image 1.jpeg">'
                                 '<img src="https://encartesdf.com.br/wp-content/uploads/2026/10/pag2-768x1024.webp">'
                                 '<img src="https://encartesdf.com.br/wp-content/uploads/2026/10/pag2.webp">'
                                 '<img src="https://outro.site/anuncio.jpg">'}},
        {"date": "2026-10-19T08:00:00", "link": "https://encartesdf.com.br/so-texto/",
         "title": {"rendered": "Dicas de economia"}, "content": {"rendered": "<p>sem imagem</p>"}},
    ]

    def setUp(self):
        from test_agente import Fake

        self.dir = tempfile.TemporaryDirectory()
        self.banco = Banco(os.path.join(self.dir.name, "t.db"))
        self.banco.salvar_produto(Produto("7896005800027", nome="Café Torrado e Moído Exemplo 500g"))
        self.fake = Fake([("https://encartesdf.com.br/robots.txt", (200, "User-agent: *\nDisallow:")),
                          ("https://encartesdf.com.br/wp-json/wp/v2/posts", (200, json.dumps(self.POSTS)))])
        self.baixadas = []
        self.nav = Navegador(intervalo=0, abrir=self.fake, dormir=lambda s: None,
                             abrir_bytes=lambda u: self.baixadas.append(u) or b"\x89PNG fake")

    def tearDown(self):
        self.banco.con.close()
        self.dir.cleanup()

    def test_titulo_e_imagens(self):
        from historico_precos.fontes import encartesdf

        self.assertEqual(encartesdf.separar_titulo("Supermercado União até 22-10-2026"), ("Supermercado União", "2026-10-22"))
        self.assertEqual(encartesdf.separar_titulo("Dicas"), ("Dicas", None))
        self.assertEqual(encartesdf.separar_titulo("Encarte Vencido Assaí Atacadista até 18-10-2026"), ("Assaí Atacadista", "2026-10-18"))
        encs = encartesdf.listar(self.nav, dias=7, hoje=__import__("datetime").date(2026, 10, 20))
        self.assertEqual(len(encs), 1)  # o post sem imagem fica de fora
        self.assertEqual(encs[0].mercado, "Supermercado União")
        self.assertEqual(encs[0].imagens, ["https://encartesdf.com.br/wp-content/uploads/2026/10/WhatsApp%20Image%201.jpeg",
                                           "https://encartesdf.com.br/wp-content/uploads/2026/10/pag2.webp"])
        self.assertIn("after=2026-10-13", self.fake.acessos[-1])

    def test_coletar_nao_le_a_mesma_imagem_duas_vezes(self):
        from historico_precos.fontes import encartesdf

        cliente = ClienteFalso()
        agente = AgenteEncartes(self.banco, cliente=cliente, nav=self.nav)
        r = encartesdf.coletar(self.nav, agente, dias=7)
        self.assertEqual((r["encartes"], r["imagens_lidas"], r["falhas"]), (1, 2, 0))
        self.assertGreater(r["precos_novos"], 0)
        prova = self.banco.con.execute("SELECT DISTINCT loja, url_evidencia FROM precos").fetchall()
        self.assertEqual(prova, [("Supermercado União", "https://encartesdf.com.br/supermercado-uniao-ate-22-10-2026/")])
        r2 = encartesdf.coletar(self.nav, agente, dias=7)
        self.assertEqual((r2["imagens_lidas"], r2["ja_lidas"]), (0, 2))
        self.assertEqual(len(cliente.pedidos), 2)

    def test_limite_de_imagens(self):
        from historico_precos.fontes import encartesdf

        agente = AgenteEncartes(self.banco, cliente=ClienteFalso(), nav=self.nav)
        self.assertEqual(encartesdf.coletar(self.nav, agente, dias=7, max_imagens=1)["imagens_lidas"], 1)
