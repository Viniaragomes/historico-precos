import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from historico_precos.armazenamento import Banco
from historico_precos.exportar import dados_do_produto, exportar
from historico_precos.modelo import PontoDePreco, Produto

EAN = "7896005800027"


def ponto(preco, data, loja, descricao="Café 450g", **extra):
    return PontoDePreco(ean=EAN, preco=preco, data_observada=data, fonte="vtex", loja=loja,
                        url_origem="u", url_evidencia=f"https://fonte/{loja}/{data}", metodo="m",
                        descricao=descricao, **extra)


class TestExportar(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.banco = Banco(os.path.join(self.dir.name, "t.db"))
        self.banco.salvar_produto(Produto(EAN, nome="Café Exemplo", marca="Marca"))
        self.banco.salvar_precos([
            ponto(20.0, "2026-01-10", "Loja A"),
            ponto(24.0, "2026-10-18", "Loja A"),
            ponto(22.5, "2026-10-19", "Loja B", preco_de=25.0),
        ])

    def tearDown(self):
        self.banco.con.close()
        self.dir.cleanup()

    def test_dados_do_produto(self):
        d = dados_do_produto(self.banco, EAN, None, hoje=date(2026, 10, 20))
        self.assertEqual([o["loja"] for o in d["ofertas"]], ["Loja B", "Loja A"])
        self.assertTrue(d["ofertas"][0]["em_promocao"])
        self.assertNotIn("dias", d["ofertas"][0])  # o app calcula a idade na hora
        self.assertEqual(len(d["historico"]), 3)
        self.assertEqual(d["mudancas"][0]["variacao_pct"], 20.0)
        self.assertEqual(d["mudancas"][0]["evidencias"], [])

    def test_produto_sem_preco(self):
        self.assertIsNone(dados_do_produto(self.banco, "123", None))

    def test_exportar_gera_arquivos_e_indice(self):
        pasta = Path(self.dir.name) / "dados"
        self.assertEqual(exportar(self.banco, pasta), 1)
        indice = json.loads((pasta / "indice.json").read_text(encoding="utf-8"))
        self.assertEqual(indice["produtos"][0]["ean"], EAN)
        self.assertEqual(indice["produtos"][0]["nome"], "Café Exemplo")
        produto = json.loads((pasta / f"{EAN}.json").read_text(encoding="utf-8"))
        self.assertEqual(produto["marca"], "Marca")


if __name__ == "__main__":
    unittest.main()
