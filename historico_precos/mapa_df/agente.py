"""Consulta o Mapa de Preços do DF por produto e mês, e guarda os resultados mês a mês.

O painel mostra só os últimos meses. Rodando todo mês, o histórico guardado aqui passa dessa janela.
"""

from __future__ import annotations

import json
import logging
import re
import statistics
from dataclasses import asdict, dataclass, fields
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from ..armazenamento import Banco
from ..causas.series import normalizar
from ..extratores import para_float
from ..modelo import agora_iso
from ..rede import Navegador
from . import html as leitor_html

log = logging.getLogger(__name__)

CONFIG_PADRAO = Path(__file__).resolve().parents[2] / "mapa_df.json"

MESES = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]

# como reconhecer cada campo do formulário e cada coluna da tabela pelo nome
PISTAS_CAMPO = {
    "produto": ["produto", "descricao", "desc", "item", "busca", "pesquisa", "termo", "q"],
    "mes": ["mes"],
    "ano": ["ano", "exercicio"],
}
PISTAS_COLUNA = {
    "descricao": ["descri", "produto", "item"],
    "unidade": ["unid", "un.", "medida"],
    "valor_medio": ["medio", "media"],
    "valor_min": ["min"],
    "valor_max": ["max"],
    "quantidade": ["qtd", "quant", "notas", "ocorr"],
    "ncm": ["ncm"],
    "gtin": ["gtin", "ean", "codigo de barras"],
    "uf_origem": ["uf", "origem"],
}


@dataclass
class RegistroMapa:
    termo: str
    descricao: str
    valor_medio: float
    ano: int
    mes: int
    url_consulta: str
    unidade: str | None = None
    valor_min: float | None = None
    valor_max: float | None = None
    quantidade: float | None = None
    ncm: str | None = None
    gtin: str | None = None
    uf_origem: str | None = None
    coletado_em: str = ""


_CAMPOS = [f.name for f in fields(RegistroMapa)]
_ESQUEMA = """
CREATE TABLE IF NOT EXISTS mapa_precos_df (
    termo TEXT, descricao TEXT, valor_medio REAL, ano INTEGER, mes INTEGER, url_consulta TEXT,
    unidade TEXT, valor_min REAL, valor_max REAL, quantidade REAL, ncm TEXT, gtin TEXT, uf_origem TEXT,
    coletado_em TEXT,
    UNIQUE (termo, descricao, unidade, ano, mes, uf_origem, valor_medio)
);
"""


def carregar_config(caminho: Path | str = CONFIG_PADRAO) -> dict:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def _casa(nome: str, pistas: list[str]) -> bool:
    n = normalizar(nome)
    return any(n == p or (len(p) > 2 and p in n) for p in pistas)


def adivinhar_campos(form: leitor_html.Formulario) -> dict[str, str]:
    """{papel: nome do campo}, ex.: {"produto": "txtProduto", "mes": "cboMes"}."""
    achados = {}
    for papel, pistas in PISTAS_CAMPO.items():
        for c in form.campos:
            if c.tipo == "hidden" or c.nome in achados.values():
                continue
            if _casa(c.nome, pistas):
                achados[papel] = c.nome
                break
    return achados


def escolher_opcao(campo: leitor_html.Campo, numero: int, nome: str | None = None) -> str:
    """Para um <select>, devolve o value da opção que corresponde ao número (mês 3, ano 2026...)."""
    if not campo.opcoes:
        return str(numero)
    for valor, texto in campo.opcoes:
        t = normalizar(texto)
        if valor.strip().lstrip("0") == str(numero) or t == str(numero) or (nome and (t == nome or t.startswith(nome[:3]))):
            return valor
    return str(numero)


def mapear_colunas(cabecalhos: list[str], forcado: dict | None = None) -> dict[str, str]:
    mapa = dict(forcado or {})
    for campo, pistas in PISTAS_COLUNA.items():
        if campo in mapa:
            continue
        for cab in cabecalhos:
            if cab in mapa.values():
                continue
            if any(p in normalizar(cab) for p in pistas):
                mapa[campo] = cab
                break
    if "valor_medio" not in mapa:  # tabela com uma única coluna de valor
        valor = next((c for c in cabecalhos if "valor" in normalizar(c) or "preco" in normalizar(c)), None)
        if valor and valor not in mapa.values():
            mapa["valor_medio"] = valor
    return mapa


def para_registros(linhas: list[dict], termo: str, ano: int, mes: int, url: str, forcado: dict | None = None) -> list[RegistroMapa]:
    if not linhas:
        return []
    mapa = mapear_colunas(list(linhas[0].keys()), forcado)
    if "descricao" not in mapa or "valor_medio" not in mapa:
        return []
    registros = []
    for l in linhas:
        medio = para_float(l.get(mapa["valor_medio"]))
        descricao = str(l.get(mapa["descricao"], "")).strip()
        if medio is None or not descricao:
            continue
        def opcional(campo, conv=lambda v: str(v).strip() or None):
            return conv(l.get(mapa[campo])) if campo in mapa and l.get(mapa[campo]) not in (None, "") else None
        registros.append(RegistroMapa(
            termo=termo, descricao=descricao, valor_medio=medio, ano=ano, mes=mes, url_consulta=url,
            unidade=opcional("unidade"), valor_min=opcional("valor_min", para_float),
            valor_max=opcional("valor_max", para_float), quantidade=opcional("quantidade", para_float),
            ncm=opcional("ncm"), gtin=opcional("gtin"), uf_origem=opcional("uf_origem"), coletado_em=agora_iso(),
        ))
    return registros


def ultimos_meses(n: int, hoje: date | None = None) -> list[tuple[int, int]]:
    hoje = hoje or date.today()
    ano, mes = hoje.year, hoje.month
    meses = []
    for _ in range(n):
        meses.append((ano, mes))
        mes -= 1
        if mes == 0:
            ano, mes = ano - 1, 12
    return meses


class AgenteMapaDF:
    def __init__(self, nav: Navegador, banco: Banco, config: dict | None = None):
        self.nav = nav
        self.con = banco.con
        self.con.executescript(_ESQUEMA)
        self.cfg = config or carregar_config()

    def descobrir(self, pasta_bruto: Path | None = None) -> leitor_html.Descoberta | None:
        html = self.nav.get_texto(self.cfg["url"])
        if html is None:
            return None
        if pasta_bruto:
            pasta_bruto.mkdir(parents=True, exist_ok=True)
            (pasta_bruto / "painel.html").write_text(html, encoding="utf-8")
        return leitor_html.descobrir(self.cfg["url"], html)

    def _formulario(self) -> tuple[leitor_html.Formulario | None, str | None]:
        """Abre o painel de novo a cada consulta para pegar campos ocultos atualizados (tokens de sessão)."""
        html = self.nav.get_texto(self.cfg["url"])
        if html is None:
            return None, None
        desc = leitor_html.descobrir(self.cfg["url"], html)
        if not desc.formularios:
            return None, html
        indice = self.cfg.get("formulario_indice")
        if indice is not None:
            return desc.formularios[indice], html
        com_produto = [f for f in desc.formularios if "produto" in adivinhar_campos(f)]
        return (com_produto or desc.formularios)[0], html

    def consultar_painel(self, termo: str, ano: int, mes: int, pasta_bruto: Path | None = None) -> list[RegistroMapa]:
        form, _ = self._formulario()
        if form is None:
            log.warning("nenhum formulário no painel; rode 'mapa-df descobrir' e veja o relatório")
            return []
        papeis = {**adivinhar_campos(form), **{k: v for k, v in self.cfg.get("campos", {}).items() if v}}
        if "produto" not in papeis:
            log.warning("não achei o campo de produto; preencha 'campos.produto' em mapa_df.json")
            return []
        valores = {c.nome: c.valor for c in form.campos}
        valores[papeis["produto"]] = termo
        if "mes" in papeis:
            campo = form.campo(papeis["mes"])
            valores[papeis["mes"]] = escolher_opcao(campo, mes, MESES[mes - 1]) if campo else str(mes)
        if "ano" in papeis:
            campo = form.campo(papeis["ano"])
            valores[papeis["ano"]] = escolher_opcao(campo, ano) if campo else str(ano)
        valores.update(self.cfg.get("fixos", {}))

        destino = self.cfg.get("endpoint") or form.acao
        if form.metodo == "post":
            resposta = self.nav.post_texto(destino, valores)
            url_consulta = f"{destino} (POST {urlencode(valores)})"
        else:
            url_consulta = f"{destino}{'&' if '?' in destino else '?'}{urlencode(valores)}"
            resposta = self.nav.get_texto(url_consulta)
        if resposta is None:
            return []
        if pasta_bruto:
            pasta_bruto.mkdir(parents=True, exist_ok=True)
            nome = re.sub(r"[^a-z0-9]+", "_", normalizar(termo))
            (pasta_bruto / f"resposta_{nome}_{ano}{mes:02d}.html").write_text(resposta, encoding="utf-8")

        forcado = self.cfg.get("colunas") or None
        linhas = leitor_html.linhas_json(resposta)
        if linhas is not None:
            return para_registros(linhas, termo, ano, mes, url_consulta, forcado)
        # entre as tabelas da página, usa a que produzir mais registros
        melhores = max((para_registros(t, termo, ano, mes, url_consulta, forcado) for t in leitor_html.tabelas(resposta)),
                       key=len, default=[])
        return melhores

    def coletar(self, termos: list[str], meses: list[tuple[int, int]], pasta_bruto: Path | None = None) -> int:
        antes = self.con.total_changes
        for termo in termos:
            for ano, mes in meses:
                registros = self.consultar_painel(termo, ano, mes, pasta_bruto)
                log.info("%s %02d/%d: %d registros", termo, mes, ano, len(registros))
                self.con.executemany(
                    f"INSERT OR IGNORE INTO mapa_precos_df ({', '.join(_CAMPOS)}) VALUES ({', '.join(':' + c for c in _CAMPOS)})",
                    [asdict(r) for r in registros],
                )
        self.con.commit()
        return self.con.total_changes - antes

    def registros(self, termo: str) -> list[RegistroMapa]:
        cur = self.con.execute(
            f"SELECT {', '.join(_CAMPOS)} FROM mapa_precos_df WHERE termo = ? COLLATE NOCASE ORDER BY ano, mes, valor_medio",
            (termo,),
        )
        return [RegistroMapa(**dict(zip(_CAMPOS, l))) for l in cur]

    def serie_mensal(self, termo: str, filtro_descricao: str | None = None) -> list[dict]:
        """Mediana do valor médio por mês. A mediana evita que uma nota fora do padrão distorça a série."""
        por_mes: dict[tuple[int, int], list[RegistroMapa]] = {}
        alvo = normalizar(filtro_descricao) if filtro_descricao else None
        for r in self.registros(termo):
            if alvo and alvo not in normalizar(r.descricao):
                continue
            por_mes.setdefault((r.ano, r.mes), []).append(r)
        serie = []
        for (ano, mes), regs in sorted(por_mes.items()):
            valores = [r.valor_medio for r in regs]
            serie.append({"ano": ano, "mes": mes, "mediana": statistics.median(valores),
                          "minimo": min(valores), "maximo": max(valores), "itens": len(regs)})
        return serie
