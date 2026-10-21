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


class TestExportarCompraDF(unittest.TestCase):
    def test_produto_so_com_preco_de_compra(self):
        import tempfile
        from pathlib import Path

        from historico_precos.armazenamento import Banco
        from historico_precos.exportar import exportar
        from historico_precos.mapa_df import qlik

        with tempfile.TemporaryDirectory() as d:
            banco = Banco(f"{d}/t.db")
            qlik.salvar(banco.con, [{"ean": "7891", "data": "2026-10-15", "unidade": "UN", "mediana": 18.5, "media": 18.6,
                                     "minimo": 17.0, "maximo": 20.0, "quantidade": 100, "itens": 12, "descricao": "CAFE X 500G"}])
            self.assertEqual(exportar(banco, Path(d) / "dados"), 1)
            dado = json.loads((Path(d) / "dados" / "7891.json").read_text())
            self.assertEqual(dado["ofertas"], [])
            self.assertEqual(dado["compra_df"]["serie"][0]["mediana"], 18.5)
            self.assertIn("Não é o preço da prateleira", dado["compra_df"]["aviso"])
            banco.con.close()


class TestComandoExportar(unittest.TestCase):
    """Roda o comando de verdade (python -m historico_precos exportar), como a coleta diária faz."""

    def test_comando(self):
        import subprocess
        import sys
        from pathlib import Path

        from historico_precos.armazenamento import Banco
        from historico_precos.mapa_df import qlik

        with tempfile.TemporaryDirectory() as d:
            banco = Banco(f"{d}/t.db")
            banco.salvar_produto(Produto("7891910030378", nome="Café União 500g"))
            banco.salvar_precos([PontoDePreco(ean="7891910030378", preco=24.9, data_observada="2026-10-20", fonte="vtex",
                                              loja="Atacadão", url_origem="u", url_evidencia="e", metodo="m")])
            qlik.salvar(banco.con, [{"ean": "7896005800027", "data": "2026-10-15", "unidade": "UN", "mediana": 12.0, "media": 12.0,
                                     "minimo": 11.0, "maximo": 13.0, "quantidade": 10.0, "itens": 3, "descricao": "CAFE 3C"}])
            banco.con.close()
            raiz = Path(__file__).resolve().parents[1]
            r = subprocess.run([sys.executable, "-m", "historico_precos", "--banco", f"{d}/t.db", "exportar", "--saida", f"{d}/dados",
                                "--sem-causas"], cwd=raiz, capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr)
            indice = json.loads(Path(f"{d}/dados/indice.json").read_text())
            self.assertEqual(sorted(p["ean"] for p in indice["produtos"]), ["7891910030378", "7896005800027"])
