"""Varre as fontes, guarda candidatos no banco e, com aprovação humana, grava eventos comprovados."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from ..armazenamento import Banco
from ..causas import tributos
from ..modelo import agora_iso
from ..rede import Navegador
from . import fontes
from .extrator import extrair

log = logging.getLogger(__name__)

CONFIG_PADRAO = Path(__file__).resolve().parents[2] / "monitor_leis.json"

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS candidatos_leis (
    id TEXT PRIMARY KEY, fonte TEXT, titulo TEXT, url TEXT UNIQUE, data_publicacao TEXT, uf TEXT,
    tributos TEXT, aliquota_anterior REAL, aliquota_nova REAL, percentuais TEXT, vigencia TEXT,
    categorias TEXT, pontuacao INTEGER, motivos TEXT, trecho TEXT,
    status TEXT NOT NULL,  -- pendente | baixa_relevancia | aprovado | descartado
    criado_em TEXT NOT NULL
);
"""

# como o imposto entra no preço: ICMS e PIS/Cofins incidem sobre a própria receita (por dentro)
CALCULO_POR_TRIBUTO = {"ICMS": "por_dentro", "PIS/Cofins": "por_dentro"}


@dataclass
class Candidato:
    id: str
    fonte: str
    titulo: str
    url: str
    data_publicacao: str
    uf: str
    tributos: list[str]
    aliquota_anterior: float | None
    aliquota_nova: float | None
    percentuais: list[float]
    vigencia: str | None
    categorias: list[str]
    pontuacao: int
    motivos: list[str]
    trecho: str
    status: str
    criado_em: str


_JSON = ("tributos", "percentuais", "categorias", "motivos")


def carregar_config(caminho: Path | str = CONFIG_PADRAO) -> dict:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


class MonitorLeis:
    def __init__(self, nav: Navegador, banco: Banco, config: dict | None = None, categorias: dict | None = None):
        self.nav = nav
        self.con = banco.con
        self.con.executescript(_ESQUEMA)
        self.cfg = config or carregar_config()
        cats = (categorias or {}).get("categorias", {})
        self.palavras_categoria = {k: c.get("palavras", []) for k, c in cats.items()}

    # ---------------- varredura ----------------

    def _publicacoes(self, desde: date, ate: date) -> list[fontes.Publicacao]:
        pubs: list[fontes.Publicacao] = []
        cfg = self.cfg.get("fontes", {})
        dou = cfg.get("dou", {})
        if dou.get("ativa", True):
            for termo in dou.get("termos", []):
                pubs += fontes.buscar_dou(self.nav, termo, desde, ate)
        lexml = cfg.get("lexml", {})
        if lexml.get("ativa", False):
            for consulta in lexml.get("consultas", []):
                pubs += fontes.buscar_lexml(self.nav, consulta, desde, ate)
        qd = cfg.get("querido_diario", {})
        if qd.get("ativa", False):
            for territorio in qd.get("territorios", []):
                for termo in qd.get("termos", []):
                    pubs += fontes.buscar_querido_diario(
                        self.nav, territorio["id"], termo, desde, ate, territorio["uf"]
                    )
        for pagina in cfg.get("paginas", []):
            if pagina.get("ativa", True):
                pubs += fontes.links_da_pagina(
                    self.nav, pagina["url"], pagina.get("palavras", ["icms", "alíquota"]), pagina["uf"], pagina["nome"]
                )
        return list({p.url: p for p in pubs if p.url}.values())

    def monitorar(self, desde: date, ate: date | None = None) -> list[Candidato]:
        """Devolve só os candidatos novos e relevantes desta varredura."""
        ate = ate or date.today()
        minimo = self.cfg.get("pontuacao_minima", 5)
        novos = []
        for pub in self._publicacoes(desde, ate):
            if self.con.execute("SELECT 1 FROM candidatos_leis WHERE url = ?", (pub.url,)).fetchone():
                continue
            ex = extrair(f"{pub.titulo}. {pub.texto}", self.palavras_categoria)
            cand = Candidato(
                id=hashlib.sha1(pub.url.encode()).hexdigest()[:10],
                fonte=pub.fonte,
                titulo=pub.titulo,
                url=pub.url,
                data_publicacao=pub.data,
                uf=pub.uf,
                tributos=ex.tributos,
                aliquota_anterior=ex.aliquota_anterior,
                aliquota_nova=ex.aliquota_nova,
                percentuais=ex.percentuais,
                vigencia=ex.vigencia.isoformat() if ex.vigencia else None,
                categorias=ex.categorias,
                pontuacao=ex.pontuacao,
                motivos=ex.motivos,
                trecho=ex.trecho,
                status="pendente" if ex.pontuacao >= minimo else "baixa_relevancia",
                criado_em=agora_iso(),
            )
            self._salvar(cand)
            if cand.status == "pendente":
                novos.append(cand)
        return sorted(novos, key=lambda c: -c.pontuacao)

    def _salvar(self, c: Candidato) -> None:
        linha = asdict(c)
        for campo in _JSON:
            linha[campo] = json.dumps(linha[campo], ensure_ascii=False)
        colunas = ", ".join(linha)
        self.con.execute(f"INSERT OR IGNORE INTO candidatos_leis ({colunas}) VALUES ({', '.join(':' + k for k in linha)})", linha)
        self.con.commit()

    def _ler(self, linha: tuple, nomes: list[str]) -> Candidato:
        d = dict(zip(nomes, linha))
        for campo in _JSON:
            d[campo] = json.loads(d[campo] or "[]")
        return Candidato(**d)

    def candidatos(self, status: str = "pendente") -> list[Candidato]:
        cur = self.con.execute(
            "SELECT * FROM candidatos_leis WHERE status = ? ORDER BY pontuacao DESC, data_publicacao DESC", (status,)
        )
        nomes = [d[0] for d in cur.description]
        return [self._ler(l, nomes) for l in cur.fetchall()]

    def candidato(self, id_: str) -> Candidato | None:
        cur = self.con.execute("SELECT * FROM candidatos_leis WHERE id = ?", (id_,))
        linha = cur.fetchone()
        return self._ler(linha, [d[0] for d in cur.description]) if linha else None

    def descartar(self, id_: str) -> bool:
        cur = self.con.execute("UPDATE candidatos_leis SET status = 'descartado' WHERE id = ?", (id_,))
        self.con.commit()
        return cur.rowcount > 0

    # ---------------- aprovação humana ----------------

    def aprovar(
        self,
        id_: str,
        caminho_eventos: Path | str = tributos.ARQUIVO_PADRAO,
        evento_id: str | None = None,
        uf: str | None = None,
        tributo: str | None = None,
        aliquota_anterior: float | None = None,
        aliquota_nova: float | None = None,
        vigencia: str | None = None,
        categorias: list[str] | None = None,
        calculo: str | None = None,
        abrangencia: str | None = None,
    ) -> dict:
        """Grava o evento como verificado. Qualquer valor não extraído precisa ser informado."""
        c = self.candidato(id_)
        if c is None:
            raise ValueError(f"candidato {id_} não existe")

        uf = uf or c.uf
        if uf == "CONFAZ":
            raise ValueError("convênio do Confaz só vale no DF depois de internalizado: informe --uf DF "
                             "e use como fonte o decreto distrital, se existir")
        tributo = tributo or (c.tributos[0] if c.tributos else None)
        anterior = aliquota_anterior if aliquota_anterior is not None else c.aliquota_anterior
        nova = aliquota_nova if aliquota_nova is not None else c.aliquota_nova
        vigencia = vigencia or c.vigencia
        cats = categorias or c.categorias
        faltando = [nome for nome, v in (("--tributo", tributo), ("--anterior", anterior), ("--nova", nova),
                                         ("--vigencia", vigencia), ("--categorias", cats or None)) if v is None]
        if faltando:
            raise ValueError("não deu para extrair da norma; informe: " + ", ".join(faltando))
        date.fromisoformat(vigencia)  # valida o formato AAAA-MM-DD

        evento = {
            "id": evento_id or re.sub(r"[^a-z0-9]+", "-", f"{uf}-{tributo}-{vigencia}".lower()).strip("-"),
            "tributo": tributo,
            "uf": uf,
            "vigencia": vigencia,
            "aliquota_anterior": anterior,
            "aliquota_nova": nova,
            "calculo": calculo or CALCULO_POR_TRIBUTO.get(tributo, "por_fora"),
            "abrangencia": abrangencia or c.titulo,
            "categorias": cats,
            "verificado": True,
            "fontes": [c.url],
            "observacao": f"Aprovado por pessoa em {date.today():%d/%m/%Y} a partir do candidato {c.id} ({c.fonte}).",
        }

        caminho = Path(caminho_eventos)
        dado = json.loads(caminho.read_text(encoding="utf-8"))
        existente = next((e for e in dado["eventos"] if e["id"] == evento["id"]), None)
        if existente:
            existente.update({k: v for k, v in evento.items() if k != "fontes"})
            existente["fontes"] = [c.url] + [f for f in existente.get("fontes", []) if f != c.url]
            evento = existente
        else:
            dado["eventos"].append(evento)
        caminho.write_text(json.dumps(dado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        self.con.execute("UPDATE candidatos_leis SET status = 'aprovado' WHERE id = ?", (id_,))
        self.con.commit()
        return evento
