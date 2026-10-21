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
