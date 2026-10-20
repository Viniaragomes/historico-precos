"""Agente de encartes e tabloides: lê o encarte (imagem ou PDF) com IA de visão e extrai produto, preço e validade.

Regras de honestidade:
* a IA é instruída a nunca adivinhar um preço ilegível; item sem preço legível não entra;
* preço com condição (leve 3 pague 2, clube, cartão da loja) fica guardado, mas fora do comparativo;
* item só vira preço de um produto (EAN) quando o nome e o tamanho batem com segurança;
  o resto fica numa fila para uma pessoa vincular.

Precisa do pacote `anthropic` e de credencial da API (ANTHROPIC_API_KEY ou `ant auth login`).
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from .armazenamento import Banco
from .causas import embalagem
from .causas.series import normalizar
from .modelo import PontoDePreco, agora_iso
from .rede import Navegador

log = logging.getLogger(__name__)

MODELO = "claude-opus-5-5"
TIPOS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif", ".pdf": "application/pdf"}
LIMIAR_SEMELHANCA = 0.6

INSTRUCOES = """Você está lendo o encarte (tabloide de ofertas) de um supermercado brasileiro.
Extraia cada produto com preço anunciado. Regras:
- Copie a descrição como está no encarte, incluindo marca e tamanho (ex.: "Café Pilão Tradicional 500g").
- Preço em reais como número (R$ 12,99 -> 12.99). Se o preço não estiver legível com certeza, NÃO inclua o item.
- "preco_de": o preço antigo riscado, se houver; senão null.
- "condicao": qualquer condição para o preço valer (leve 3 pague 2, a partir de 2 unidades, só no cartão/app/clube,
  preço por kg no açougue, limite por cliente); senão null.
- "unidade_venda": "kg" quando o preço for por quilo, "un" quando for por unidade/embalagem.
- "ean": só se o código de barras estiver impresso e legível; senão null. Nunca invente.
- Validade: datas do período da oferta no formato AAAA-MM-DD, se impressas; senão null.
Não inclua itens que não sejam produtos (frases de propaganda, logotipos)."""

ESQUEMA = {
    "type": "object",
    "properties": {
        "loja": {"type": ["string", "null"]},
        "validade_inicio": {"type": ["string", "null"]},
        "validade_fim": {"type": ["string", "null"]},
        "itens": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "descricao": {"type": "string"},
                    "preco": {"type": "number"},
                    "preco_de": {"type": ["number", "null"]},
                    "unidade_venda": {"type": ["string", "null"]},
                    "condicao": {"type": ["string", "null"]},
                    "ean": {"type": ["string", "null"]},
                },
                "required": ["descricao", "preco", "preco_de", "unidade_venda", "condicao", "ean"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["loja", "validade_inicio", "validade_fim", "itens"],
    "additionalProperties": False,
}

_ESQUEMA_DB = """
CREATE TABLE IF NOT EXISTS encartes_itens (
    id TEXT PRIMARY KEY, arquivo TEXT, fonte TEXT, loja TEXT, cidade TEXT, data TEXT, validade_fim TEXT,
    descricao TEXT, preco REAL, preco_de REAL, unidade_venda TEXT, condicao TEXT, ean_lido TEXT,
    ean TEXT, semelhanca REAL, status TEXT NOT NULL,  -- vinculado | pendente | condicional | descartado
    coletado_em TEXT NOT NULL
);
"""


class ErroEncarte(Exception):
    pass


@dataclass
class ItemEncarte:
    id: str
    arquivo: str
    fonte: str
    loja: str
    cidade: str | None
    data: str
    validade_fim: str | None
    descricao: str
    preco: float
    preco_de: float | None
    unidade_venda: str | None
    condicao: str | None
    ean_lido: str | None
    ean: str | None
    semelhanca: float | None
    status: str
    coletado_em: str


# ---------- leitura pela IA ----------

def _bloco(conteudo: bytes, tipo: str) -> dict:
    dados = base64.standard_b64encode(conteudo).decode("utf-8")
    if tipo == "application/pdf":
        return {"type": "document", "source": {"type": "base64", "media_type": tipo, "data": dados}}
    return {"type": "image", "source": {"type": "base64", "media_type": tipo, "data": dados}}


def ler_encarte(cliente, conteudo: bytes, tipo: str) -> dict:
    """Manda o encarte para a IA e devolve o JSON validado pelo esquema."""
    resposta = cliente.beta.messages.create(
        model=MODELO,
        max_tokens=16000,
        # se o pedido for recusado por um classificador, a API tenta outro modelo recomendado
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"format": {"type": "json_schema", "schema": ESQUEMA}},
        messages=[{"role": "user", "content": [_bloco(conteudo, tipo), {"type": "text", "text": INSTRUCOES}]}],
    )
    if resposta.stop_reason == "refusal":
        raise ErroEncarte("A IA recusou ler este arquivo.")
    if resposta.stop_reason == "max_tokens":
        raise ErroEncarte("O encarte tem itens demais para uma leitura; divida em páginas.")
    texto = next((b.text for b in resposta.content if b.type == "text"), None)
    if texto is None:
        raise ErroEncarte("A IA não devolveu a lista de itens.")
    return json.loads(texto)


# ---------- associação com produtos conhecidos ----------

_PALAVRAS_VAZIAS = {"de", "da", "do", "e", "com", "tipo", "pct", "pacote", "un", "und", "cx", "lata", "garrafa", "pet"}


def _tokens(texto: str) -> set[str]:
    sem_qtd = re.sub(r"\d+(?:[.,]\d+)?\s*(kg|g|gr|mg|l|lt|ml|litros?)\b", " ", normalizar(texto))
    return {t for t in re.findall(r"[a-z0-9]+", sem_qtd) if len(t) > 1 and t not in _PALAVRAS_VAZIAS}


def semelhanca(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def casar(descricao: str, catalogo: list[tuple[str, str]]) -> tuple[str, float] | None:
    """Acha o EAN cujo nome mais se parece com a descrição. O tamanho, quando os dois têm, precisa ser igual."""
    qtd = embalagem.quantidade(descricao)
    melhor = None
    for ean, nome in catalogo:
        q = embalagem.quantidade(nome)
        if qtd and q and (qtd[1] != q[1] or abs(qtd[0] - q[0]) > 1e-6):
            continue
        s = semelhanca(descricao, nome)
        if melhor is None or s > melhor[1]:
            melhor = (ean, s)
    return melhor if melhor and melhor[1] >= LIMIAR_SEMELHANCA else None


# ---------- agente ----------

class AgenteEncartes:
    def __init__(self, banco: Banco, cliente=None, nav: Navegador | None = None):
        self.banco = banco
        self.con = banco.con
        self.con.executescript(_ESQUEMA_DB)
        self._cliente = cliente
        self.nav = nav

    def cliente(self):
        if self._cliente is None:
            try:
                import anthropic
            except ImportError as e:
                raise ErroEncarte("Instale o SDK: pip install -r requirements-encartes.txt") from e
            self._cliente = anthropic.Anthropic()
        return self._cliente

    def _catalogo(self) -> list[tuple[str, str]]:
        """Nome de cada produto conhecido, mais as descrições vistas nas lojas."""
        nomes = list(self.con.execute("SELECT ean, nome FROM produtos WHERE nome IS NOT NULL"))
        nomes += list(self.con.execute("SELECT DISTINCT ean, descricao FROM precos WHERE descricao IS NOT NULL"))
        return nomes

    def _abrir(self, origem: str) -> tuple[bytes, str]:
        sufixo = Path(origem.split("?")[0]).suffix.lower()
        tipo = TIPOS.get(sufixo)
        if not tipo:
            raise ErroEncarte(f"Formato não suportado: {sufixo or 'sem extensão'} (use PNG, JPG, WEBP, GIF ou PDF).")
        if origem.startswith(("http://", "https://")):
            if self.nav is None:
                raise ErroEncarte("Sem navegador configurado para baixar o encarte.")
            conteudo = self.nav.get_bytes(origem)
            if conteudo is None:
                raise ErroEncarte("Não foi possível baixar o encarte (fora do ar ou robots.txt não permite).")
            return conteudo, tipo
        return Path(origem).read_bytes(), tipo

    def processar(self, origem: str, loja: str, cidade: str | None = None, data_coleta: str | None = None,
                  fonte: str | None = None) -> dict:
        """Lê um encarte, guarda os itens e cria preços para os que foram associados com segurança."""
        conteudo, tipo = self._abrir(origem)
        lido = ler_encarte(self.cliente(), conteudo, tipo)
        data = lido.get("validade_inicio") or data_coleta or date.today().isoformat()
        date.fromisoformat(data)
        evidencia = fonte or (origem if origem.startswith("http") else f"arquivo:{Path(origem).name}")
        assinatura = hashlib.sha1(conteudo).hexdigest()[:12]
        catalogo = self._catalogo()

        itens, pontos = [], []
        for i, bruto in enumerate(lido.get("itens", [])):
            preco = bruto.get("preco")
            if not isinstance(preco, (int, float)) or not 0 < preco < 100000:
                continue
            ean_lido = bruto.get("ean") if re.fullmatch(r"\d{8,14}", str(bruto.get("ean") or "")) else None
            achado = (ean_lido, 1.0) if ean_lido else casar(bruto["descricao"], catalogo)
            if bruto.get("condicao"):
                status = "condicional"  # preço só vale com condição: fora do comparativo
            elif achado:
                status = "vinculado"
            else:
                status = "pendente"
            item = ItemEncarte(
                id=f"{assinatura}-{i}", arquivo=Path(origem.split("?")[0]).name, fonte=evidencia, loja=loja, cidade=cidade,
                data=data, validade_fim=lido.get("validade_fim"), descricao=bruto["descricao"].strip(), preco=float(preco),
                preco_de=bruto.get("preco_de"), unidade_venda=bruto.get("unidade_venda"), condicao=bruto.get("condicao"),
                ean_lido=ean_lido, ean=achado[0] if achado else None, semelhanca=achado[1] if achado else None,
                status=status, coletado_em=agora_iso(),
            )
            itens.append(item)
            if status == "vinculado":
                pontos.append(self._ponto(item))

        campos = list(asdict(itens[0]).keys()) if itens else []
        if itens:
            self.con.executemany(
                f"INSERT OR IGNORE INTO encartes_itens ({', '.join(campos)}) VALUES ({', '.join(':' + c for c in campos)})",
                [asdict(it) for it in itens],
            )
            self.con.commit()
        novos = self.banco.salvar_precos(pontos)
        return {
            "itens": len(itens),
            "vinculados": sum(1 for it in itens if it.status == "vinculado"),
            "pendentes": sum(1 for it in itens if it.status == "pendente"),
            "condicionais": sum(1 for it in itens if it.status == "condicional"),
            "precos_novos": novos,
            "validade": (lido.get("validade_inicio"), lido.get("validade_fim")),
        }

    @staticmethod
    def _ponto(item: ItemEncarte) -> PontoDePreco:
        return PontoDePreco(
            ean=item.ean, preco=item.preco, preco_de=item.preco_de if (item.preco_de or 0) > item.preco else None,
            data_observada=item.data, fonte="encarte", loja=item.loja, cidade=item.cidade,
            url_origem=item.fonte, url_evidencia=item.fonte, metodo="encarte-ia", descricao=item.descricao,
        )

    def itens(self, status: str) -> list[ItemEncarte]:
        cur = self.con.execute("SELECT * FROM encartes_itens WHERE status = ? ORDER BY data DESC, loja", (status,))
        nomes = [d[0] for d in cur.description]
        return [ItemEncarte(**dict(zip(nomes, l))) for l in cur.fetchall()]

    def vincular(self, item_id: str, ean: str) -> int:
        """Uma pessoa confirma qual produto é: o item vira preço daquele EAN."""
        if not re.fullmatch(r"\d{8,14}", ean):
            raise ErroEncarte("EAN inválido.")
        cur = self.con.execute("SELECT * FROM encartes_itens WHERE id = ?", (item_id,))
        linha = cur.fetchone()
        if not linha:
            raise ErroEncarte("Item não encontrado.")
        item = ItemEncarte(**dict(zip([d[0] for d in cur.description], linha)))
        if item.status == "condicional":
            raise ErroEncarte("Preço com condição não entra no comparativo.")
        item.ean, item.status, item.semelhanca = ean, "vinculado", None
        self.con.execute("UPDATE encartes_itens SET ean = ?, status = 'vinculado' WHERE id = ?", (ean, item_id))
        self.con.commit()
        return self.banco.salvar_precos([self._ponto(item)])

    def descartar(self, item_id: str) -> None:
        self.con.execute("UPDATE encartes_itens SET status = 'descartado' WHERE id = ?", (item_id,))
        self.con.commit()
