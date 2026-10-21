import io
import unittest
import zipfile

from historico_precos import xlsx


def planilha() -> bytes:
    arq = io.BytesIO()
    with zipfile.ZipFile(arq, "w") as z:
        z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   '<sheet name="Tomate" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/sharedStrings.xml", '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                   '<si><t>Ceasa</t></si><si><t>CEASA/DF</t></si></sst>')
        z.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                   '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="C1" t="inlineStr"><is><t>set/26</t></is></c></row>'
                   '<row r="2"><c r="A2" t="s"><v>1</v></c><c r="B2"><v>4.5</v></c><c r="C2"><f>B2*2</f><v>9</v></c></row>'
                   '</sheetData></worksheet>')
    return arq.getvalue()


class TestXlsx(unittest.TestCase):
    def test_ler(self):
        abas = xlsx.ler(planilha())
        self.assertEqual(abas["Tomate"], [["Ceasa", None, "set/26"], ["CEASA/DF", 4.5, 9.0]])


def planilha_conab() -> bytes:
    """Aba 'Preços-Tomate' no formato da Conab: cabeçalho com datas seriais do Excel."""
    arq = io.BytesIO()
    linhas = [
        '<row r="1"><c r="I1" t="inlineStr"><is><t>Setembro de 2026</t></is></c></row>',
        '<row r="4"><c r="A4" t="inlineStr"><is><t>Ceasa</t></is></c><c r="B4"><v>46204</v></c><c r="C4"><v>46235</v></c><c r="D4"><v>46266</v></c></row>',
        '<row r="5"><c r="A5" t="inlineStr"><is><t>Ceasa/GO - Goiânia</t></is></c><c r="B5"><v>5</v></c><c r="C5"><v>5.5</v></c><c r="D5"><v>6.05</v></c></row>',
        '<row r="6"><c r="A6" t="inlineStr"><is><t>Ceasa/DF - Brasília</t></is></c><c r="B6"><v>0</v></c><c r="C6" t="str"><v>#DIV/0!</v></c></row>',
        '<row r="7"><c r="A7" t="inlineStr"><is><t>Fonte: Conab.</t></is></c></row>',
    ]
    with zipfile.ZipFile(arq, "w") as z:
        z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   '<sheet name="Preços-Tomate" sheetId="1" r:id="rId1"/><sheet name="Principal" sheetId="2" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                   + "".join(linhas) + '</sheetData></worksheet>')
    return arq.getvalue()


class TestConab(unittest.TestCase):
    def test_ler_planilha_e_series(self):
        import sqlite3

        from historico_precos.fontes import conab_prohort

        linhas = conab_prohort.ler_planilha(planilha_conab())
        self.assertEqual(linhas, [("Tomate", "Ceasa/GO - Goiânia", "2026-07", 5.0), ("Tomate", "Ceasa/GO - Goiânia", "2026-08", 5.5),
                                  ("Tomate", "Ceasa/GO - Goiânia", "2026-09", 6.05)])  # zero e #DIV/0! do DF ficam de fora
        con = sqlite3.connect(":memory:")
        con.executescript(conab_prohort._ESQUEMA)
        con.executemany("INSERT INTO conab_prohort VALUES (?, ?, ?, ?, 'u', 'agora')", linhas)
        s = conab_prohort.series(con)
        self.assertEqual(len(s), 1)
        self.assertEqual((s[0]["ceasa"], s[0]["ultimo"]["mes"], s[0]["variacao_pct"]), ("Ceasa/GO - Goiânia", "2026-09", 10.0))
