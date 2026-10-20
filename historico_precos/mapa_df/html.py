"""Leitura genérica de HTML: formulários, endereços de consulta em JavaScript, painéis embutidos e tabelas."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin


@dataclass
class Campo:
    nome: str
    tipo: str  # text | hidden | select | textarea | ...
    valor: str = ""
    opcoes: list[tuple[str, str]] = field(default_factory=list)  # (value, texto) dos <select>


@dataclass
class Formulario:
    acao: str
    metodo: str
    campos: list[Campo] = field(default_factory=list)

    def campo(self, nome: str) -> Campo | None:
        return next((c for c in self.campos if c.nome == nome), None)


@dataclass
class Descoberta:
    url: str
    formularios: list[Formulario]
    endpoints: list[str]  # URLs de consulta achadas no JavaScript
    paineis_embutidos: list[str]  # iframes de Power BI, Qlik, Tableau...
    tabelas: int


class _Leitor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.formularios: list[Formulario] = []
        self.iframes: list[str] = []
        self.scripts: list[str] = []
        self._form: Formulario | None = None
        self._select: Campo | None = None
        self._opcao: list | None = None
        self._script = False
        # tabelas
        self.tabelas: list[list[list[str]]] = []
        self._pilha_tabelas: list[list[list[str]]] = []
        self._linha: list[str] | None = None
        self._celula: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "form":
            self._form = Formulario(a.get("action", ""), (a.get("method") or "get").lower())
            self.formularios.append(self._form)
        elif tag == "input" and a.get("name"):
            tipo = a.get("type", "text").lower()
            if tipo in ("submit", "button", "image", "reset"):
                return
            if tipo in ("checkbox", "radio") and "checked" not in a:
                return
            self._adicionar(Campo(a["name"], tipo, a.get("value", "")))
        elif tag == "select" and a.get("name"):
            self._select = Campo(a["name"], "select")
            self._adicionar(self._select)
        elif tag == "option" and self._select is not None:
            self._opcao = [a.get("value"), "", "selected" in a]
        elif tag == "textarea" and a.get("name"):
            self._adicionar(Campo(a["name"], "textarea"))
        elif tag == "iframe" and a.get("src"):
            self.iframes.append(a["src"])
        elif tag == "script":
            self._script = True
            if a.get("src"):
                self.scripts.append(f"src:{a['src']}")
        elif tag == "table":
            self._pilha_tabelas.append([])
        elif tag == "tr" and self._pilha_tabelas:
            self._linha = []
        elif tag in ("td", "th") and self._linha is not None:
            self._celula = []

    def handle_endtag(self, tag):
        if tag == "form":
            self._form = None
        elif tag == "option" and self._opcao is not None and self._select is not None:
            valor, texto, marcado = self._opcao
            texto = " ".join(texto.split())
            self._select.opcoes.append((texto if valor is None else valor, texto))
            if marcado or len(self._select.opcoes) == 1:
                self._select.valor = self._select.opcoes[-1][0]
            self._opcao = None
        elif tag == "select":
            self._select = None
        elif tag == "script":
            self._script = False
        elif tag in ("td", "th") and self._celula is not None and self._linha is not None:
            self._linha.append(" ".join("".join(self._celula).split()))
            self._celula = None
        elif tag == "tr" and self._linha is not None and self._pilha_tabelas:
            if self._linha:
                self._pilha_tabelas[-1].append(self._linha)
            self._linha = None
        elif tag == "table" and self._pilha_tabelas:
            self.tabelas.append(self._pilha_tabelas.pop())

    def handle_data(self, data):
        if self._opcao is not None:
            self._opcao[1] += data
        if self._script:
            self.scripts.append(data)
        if self._celula is not None:
            self._celula.append(data)

    def _adicionar(self, campo: Campo):
        if self._form is None:  # campo solto: cria um formulário implícito
            self._form = Formulario("", "get")
            self.formularios.append(self._form)
        self._form.campos.append(campo)


_RE_ENDPOINT = [
    re.compile(r"""(?:fetch|axios(?:\.(?:get|post))?|\$\.(?:ajax|get|post|getJSON))\(\s*['"]([^'"]+)['"]"""),
    re.compile(r"""url\s*:\s*['"]([^'"]+)['"]"""),
    re.compile(r"""['"]([^'"\s]+\.(?:php|json|aspx|ashx)(?:\?[^'"\s]*)?)['"]"""),
]
_PAINEIS = ("powerbi", "app.powerbi.com", "qlik", "tableau", "metabase", "looker", "datastudio", "lookerstudio")


def ler(html: str) -> _Leitor:
    leitor = _Leitor()
    leitor.feed(html)
    leitor.close()
    return leitor


def descobrir(url: str, html: str) -> Descoberta:
    leitor = ler(html)
    for f in leitor.formularios:
        f.acao = urljoin(url, f.acao or url)
    js = "\n".join(s for s in leitor.scripts if not s.startswith("src:"))
    endpoints = []
    for regex in _RE_ENDPOINT:
        endpoints += [urljoin(url, e) for e in regex.findall(js) if not e.startswith(("#", "javascript:"))]
    endpoints += [urljoin(url, s[4:]) for s in leitor.scripts if s.startswith("src:")]
    paineis = [urljoin(url, i) for i in leitor.iframes if any(p in i.lower() for p in _PAINEIS)]
    return Descoberta(url, leitor.formularios, list(dict.fromkeys(endpoints)), paineis, len(leitor.tabelas))


def tabelas(html: str) -> list[list[dict[str, str]]]:
    """Cada tabela vira uma lista de dicionários {cabeçalho: valor}. A primeira linha é o cabeçalho."""
    resultado = []
    for linhas in ler(html).tabelas:
        if len(linhas) < 2:
            continue
        cabecalho = linhas[0]
        resultado.append([dict(zip(cabecalho, l)) for l in linhas[1:] if len(l) == len(cabecalho)])
    return resultado


def linhas_json(texto: str) -> list[dict] | None:
    """Aceita lista de objetos, {"data": [...]} (DataTables) ou {"rows"/"items"/"resultados": [...]}."""
    try:
        dado = json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(dado, dict):
        dado = next((dado[k] for k in ("data", "rows", "items", "resultados", "dados") if isinstance(dado.get(k), list)), None)
    if not isinstance(dado, list):
        return None
    if dado and isinstance(dado[0], list):  # DataTables sem nomes de coluna
        return [{f"col{i}": v for i, v in enumerate(l)} for l in dado]
    return [d for d in dado if isinstance(d, dict)]
