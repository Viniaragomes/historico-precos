"""Linha de comando.

  python -m historico_precos buscar 7891000100103
  python -m historico_precos buscar 7891000100103 --url "Loja X=https://loja.com.br/produto/p"
  python -m historico_precos historico 7891000100103 --json saida.json
  python -m historico_precos detectar-lojas
  python -m historico_precos causas 7891000100103 --uf DF
  python -m historico_precos comparar 7891000100103 --atualizar
  python -m historico_precos leis monitorar --desde 2023-01-01
  python -m historico_precos leis aprovar <id> --li-a-norma
  python -m historico_precos mapa-df descobrir
  python -m historico_precos mapa-df coletar --termos CAFE,ARROZ
  python -m historico_precos mapa-df consultar CAFE --filtro 500G
"""

from __future__ import annotations

import argparse
import json
import re
import logging
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .agente import AgenteHistorico, Relatorio, detectar_mudancas
from .armazenamento import Banco
from .causas.analise import AgenteCausas, carregar_categorias
from .comparativo import comparar
from .exportar import exportar as exportar_app
from .qualidade import avaliar as avaliar_qualidade
from .fontes import vtex
from .causas.series import normalizar
from .leis.monitor import MonitorLeis
from .mapa_df.agente import AgenteMapaDF, adivinhar_campos, ultimos_meses
from .viabilidade import AgenteViabilidade, para_markdown, salvar, salvar_diagnostico
from .modelo import Produto
from .rede import Navegador

LOJAS_PADRAO = Path(__file__).resolve().parent.parent / "lojas.json"


def carregar_lojas(caminho: str) -> list[dict]:
    return [l for l in json.loads(Path(caminho).read_text(encoding="utf-8"))["lojas"] if l.get("ativa", True)]


def _url_extra(texto: str) -> tuple[str, str]:
    if "=" in texto and not texto.startswith("http"):
        nome, url = texto.split("=", 1)
        return nome.strip(), url.strip()
    return "página informada", texto


def imprimir(rel: Relatorio) -> None:
    p = rel.produto
    print(f"\nProduto: {p.nome or '(nome não encontrado)'} | {p.marca or ''} {p.quantidade or ''} | EAN {p.ean}")
    print(f"Pontos de preço: {len(rel.pontos)} (novos nesta execução: {rel.novos})\n")
    for pt in rel.pontos:
        de = f" (de R$ {pt.preco_de:.2f})" if pt.preco_de else ""
        print(f"  {pt.data_observada}  R$ {pt.preco:>8.2f}{de}  {pt.loja:<22} [{pt.fonte}]  {pt.url_evidencia}")
    if rel.mudancas:
        print("\nMudanças de preço:")
        for m in rel.mudancas:
            print(
                f"  {m.loja}: {m.data_anterior} R$ {m.preco_anterior:.2f} -> {m.data_nova} R$ {m.preco_novo:.2f}"
                f"  ({m.variacao_pct:+.1f}%)"
            )
    for aviso in rel.avisos:
        print(f"  ! {aviso}")


def exportar(rel: Relatorio, caminho: str) -> None:
    dado = {
        "produto": asdict(rel.produto),
        "precos": [pt.para_dict() for pt in rel.pontos],
        "mudancas": [{**asdict(m), "variacao_pct": round(m.variacao_pct, 2)} for m in rel.mudancas],
        "avisos": rel.avisos,
    }
    Path(caminho).write_text(json.dumps(dado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nExportado para {caminho}")


def _causas(args, nav: Navegador, banco: Banco) -> int:
    agente = AgenteCausas(nav, banco, usar_noticias=not args.sem_noticias)
    categoria, explicacoes = agente.explicar(args.ean, uf=args.uf, categoria=args.categoria)
    produto = banco.produto(args.ean)
    print(f"\nProduto: {(produto and produto.nome) or args.ean} | categoria: {categoria or 'não identificada'} | UF {args.uf}")
    if not explicacoes:
        print("Nenhuma mudança de preço no banco. Rode antes: python -m historico_precos buscar", args.ean)
        return 0
    for ex in explicacoes:
        m = ex.mudanca
        print(f"\n{m.loja}: {m.data_anterior} R$ {m.preco_anterior:.2f} -> {m.data_nova} R$ {m.preco_novo:.2f}"
              f"  ({m.variacao_pct:+.1f}%)")
        for e in ex.evidencias:
            print(f"  [{e.nivel}] {e.descricao}")
            for f in e.fontes:
                print(f"      fonte: {f}")
        print(f"  => Comprovado: {ex.comprovado_pct:+.1f}%  |  Sem causa comprovada: {ex.nao_explicado_pct:+.1f}%")
    print("\nComprovado = fato documentado com efeito calculável. Os demais níveis NÃO provam causa.")
    if args.json:
        dado = {"ean": args.ean, "categoria": categoria, "explicacoes": [
            {"mudanca": {**asdict(ex.mudanca), "variacao_pct": round(ex.mudanca.variacao_pct, 2)},
             "evidencias": [asdict(e) for e in ex.evidencias],
             "comprovado_pct": round(ex.comprovado_pct, 2), "nao_explicado_pct": round(ex.nao_explicado_pct, 2)}
            for ex in explicacoes]}
        Path(args.json).write_text(json.dumps(dado, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Exportado para {args.json}")
    return 0


def _comparar(args, banco: Banco) -> int:
    comp = comparar(banco.precos(args.ean), max_dias=args.max_dias, cidade=args.cidade)
    produto = banco.produto(args.ean)
    print(f"\nOnde está mais barato: {(produto and produto.nome) or args.ean}\n")
    if not comp.ofertas:
        print(f"Nenhum preço dos últimos {args.max_dias} dias. Rode com --atualizar ou use: buscar {args.ean}")
    for i, o in enumerate(comp.ofertas, 1):
        selo = "MAIS BARATO" if i == 1 else f"+R$ {o.diferenca_rs:.2f} ({o.diferenca_pct:+.1f}%)"
        promo = f" promoção, era R$ {o.preco_de:.2f}" if o.em_promocao else ""
        idade = "hoje" if o.dias == 0 else f"há {o.dias} dia(s)" + (" ⚠ pode estar desatualizado" if o.desatualizado else "")
        print(f"  {i}. {o.loja:<24} R$ {o.preco:>7.2f}  {selo:<20} {idade}{promo}  [{o.fonte}]")
    if len(comp.ofertas) > 1:
        print(f"\n  Média: R$ {comp.media:.2f} | Economia comprando no mais barato: até R$ {comp.economia_maxima:.2f}")
    if comp.ignoradas:
        print(f"\n  Fora da comparação (preço com mais de {args.max_dias} dias): "
              + ", ".join(f"{o.loja} R$ {o.preco:.2f} em {o.data}" for o in comp.ignoradas))
    print("\n  Preços online podem diferir da loja física.")
    if args.json:
        dado = {"ean": args.ean, "ofertas": [asdict(o) for o in comp.ofertas],
                "ignoradas": [asdict(o) for o in comp.ignoradas]}
        Path(args.json).write_text(json.dumps(dado, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Exportado para {args.json}")
    return 0


def _mostrar_candidato(c, detalhe: bool = False) -> None:
    aliq = f"{c.aliquota_anterior:g}% -> {c.aliquota_nova:g}%" if c.aliquota_anterior is not None else "alíquotas: ?"
    print(f"\n[{c.id}] {c.data_publicacao or 's/ data'} {c.fonte} ({c.uf}) pontuação {c.pontuacao}")
    print(f"  {c.titulo}")
    print(f"  {', '.join(c.tributos) or 'tributo: ?'} | {aliq} | vigência: {c.vigencia or '?'} | "
          f"produtos: {', '.join(c.categorias) or '?'}")
    print(f"  {c.url}")
    if detalhe:
        print(f"  Por que apareceu: {'; '.join(c.motivos)}")
        print(f"  Percentuais citados: {', '.join(f'{p:g}%' for p in c.percentuais) or 'nenhum'}")
        print(f"  Trecho: {c.trecho}")


def _leis(args, nav: Navegador, banco: Banco) -> int:
    monitor = MonitorLeis(nav, banco, categorias=carregar_categorias())
    if args.acao == "monitorar":
        ate = date.fromisoformat(args.ate) if args.ate else None
        novos = monitor.monitorar(date.fromisoformat(args.desde), ate)
        print(f"\n{len(novos)} candidato(s) novo(s) para conferir.")
        for c in novos:
            _mostrar_candidato(c)
    elif args.acao == "pendentes":
        pendentes = monitor.candidatos("pendente")
        print(f"\n{len(pendentes)} candidato(s) pendente(s).")
        for c in pendentes:
            _mostrar_candidato(c)
    elif args.acao == "ver":
        c = monitor.candidato(args.id)
        if not c:
            print("Candidato não encontrado.")
            return 1
        _mostrar_candidato(c, detalhe=True)
    elif args.acao == "descartar":
        print("Descartado." if monitor.descartar(args.id) else "Candidato não encontrado.")
    else:
        categorias = [x.strip() for x in args.categorias.split(",")] if args.categorias else None
        try:
            evento = monitor.aprovar(
                args.id, evento_id=args.evento_id, uf=args.uf, tributo=args.tributo,
                aliquota_anterior=args.anterior, aliquota_nova=args.nova, vigencia=args.vigencia,
                categorias=categorias, calculo=args.calculo, abrangencia=args.abrangencia,
            )
        except ValueError as e:
            print(f"Não aprovado: {e}")
            return 1
        print(f"Evento '{evento['id']}' gravado como COMPROVADO em eventos_tributarios.json")
        print(f"  {evento['tributo']} ({evento['uf']}): {evento['aliquota_anterior']:g}% -> "
              f"{evento['aliquota_nova']:g}% a partir de {evento['vigencia']} | fonte: {evento['fontes'][0]}")
    return 0


def _mapa_df(args, nav: Navegador, banco: Banco) -> int:
    agente = AgenteMapaDF(nav, banco)
    if args.acao == "precos":
        from .mapa_df import qlik

        eans = [e.strip() for e in (args.eans or "").split(",") if e.strip()]
        if args.arquivo:
            eans += [l.split()[0] for l in Path(args.arquivo).read_text(encoding="utf-8").splitlines() if l.strip()]
        if args.do_banco:
            # só produtos com preço em alguma loja: o cadastro também guarda milhares de produtos só de referência
            eans += [l[0] for l in banco.con.execute("SELECT DISTINCT ean FROM precos")]
        if not eans:
            print("Informe --eans, --arquivo ou --do-banco.")
            return 1
        r = qlik.coletar(banco.con, eans)
        print(f"{r['gtins']} código(s) consultado(s): {r['com_dados']} com notas no DF, {r['linhas']} dia(s)/unidade gravados.")
        for ean in sorted(set(eans))[:40]:
            s_ = qlik.serie(banco.con, ean)
            if s_:
                t = s_["tendencia"] or {}
                ult = s_["pontos"][-1]
                var = f"{t['variacao_pct']:+.1f}% em 7 dias" if t.get("variacao_pct") is not None else (t.get("nota") or "")
                print(f"  {ean} {s_['descricao'][:40]:<40} {ult['data']} R$ {ult['mediana'] or 0:>8.2f}/{s_['unidade']}  {len(s_['pontos'])} dias  {var}")
        return 0
    if args.acao == "dicionario":
        import sqlite3
        import time

        from .mapa_df import qlik

        con = sqlite3.connect(args.banco_dicionario)
        motor = qlik.Motor()
        try:
            doc = motor.abrir_app()
            fim = time.monotonic() + args.minutos * 60
            r = qlik.dicionario(motor, doc, con, ate=lambda: time.monotonic() > fim)
        finally:
            motor.fechar()
        n = con.execute("SELECT COUNT(DISTINCT ean) FROM mapa_df_dicionario").fetchone()[0]
        print(f"Painel: {r['linhas_no_painel']} linhas (código x unidade); {r['gravadas']} gravadas em {r['paginas']} páginas; "
              f"{n} códigos de barras no dicionário. {r.get('parou') or ''}")
        return 0
    if args.acao == "qlik":
        from .mapa_df import qlik

        r = qlik.explorar(linhas=args.linhas)
        Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
        Path(args.saida).write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        if not r["ok"]:
            print(f"Não abriu o app Qlik: {r.get('erro') or r.get('tentativas')}")
            return 1
        print(f"{r['titulo']} (última carga {r['ultima_carga']}): {len(r['campos'])} campos")
        print("Campos:", ", ".join(r["campos"][:80]))
        for t in r["tabelas"]:
            print(f"  {t['elemento']} {t['titulo'] or ''}: {t['dimensoes']} | {t['medidas']} | {t['linhas_total']} linhas {t['erro'] or ''}")
        print(f"Detalhes em {args.saida}")
        return 0
    if args.acao == "descobrir":
        desc = agente.descobrir(Path(args.bruto))
        if desc is None:
            print("Não consegui abrir o painel (fora do ar, bloqueado ou robots.txt não permite).")
            return 1
        print(f"\nPainel: {desc.url}\nHTML salvo em {args.bruto}/painel.html\n")
        if desc.paineis_embutidos:
            print("⚠ O painel é um dashboard embutido (Power BI/Qlik/Tableau). A coleta por formulário não vai funcionar:")
            for p in desc.paineis_embutidos:
                print(f"   {p}")
        for i, f in enumerate(desc.formularios):
            papeis = adivinhar_campos(f)
            print(f"Formulário {i}: {f.metodo.upper()} {f.acao}")
            for c in f.campos:
                papel = next((p for p, n in papeis.items() if n == c.nome), "")
                opcoes = f"  opções: {', '.join(t for _, t in c.opcoes[:8])}{'...' if len(c.opcoes) > 8 else ''}" if c.opcoes else ""
                print(f"   - {c.nome} ({c.tipo}){' <- ' + papel if papel else ''}{opcoes}")
        if not desc.formularios:
            print("Nenhum formulário encontrado.")
        if desc.endpoints:
            print("\nEndereços de consulta achados no JavaScript:")
            for e in desc.endpoints[:15]:
                print(f"   {e}")
        print(f"\nTabelas na página inicial: {desc.tabelas}")
        print("\nPróximo passo: python -m historico_precos mapa-df coletar --termos CAFE --bruto mapa_df_bruto")
        return 0

    if args.acao == "coletar":
        termos = [t.strip() for t in args.termos.split(",")] if args.termos else agente.cfg["termos_padrao"]
        if args.meses:
            meses = [(int(m[:4]), int(m[5:7])) for m in args.meses.split(",")]
        else:
            meses = ultimos_meses(agente.cfg.get("meses_por_coleta", 4))
        novos = agente.coletar(termos, meses, Path(args.bruto) if args.bruto else None)
        print(f"{novos} registro(s) novo(s) guardado(s) de {len(termos)} termo(s) x {len(meses)} mês(es).")
        if novos == 0:
            print("Nada guardado. Rode 'mapa-df descobrir' e 'coletar --bruto pasta' e me mande os arquivos da pasta.")
        return 0

    serie = agente.serie_mensal(args.termo, args.filtro)
    print(f"\nMapa de Preços do DF (NF-e, não é preço de prateleira): {args.termo}"
          f"{' / ' + args.filtro if args.filtro else ''}\n")
    if not serie:
        print("Nada guardado para este termo.")
        return 0
    anterior = None
    for s in serie:
        var = f"  ({(s['mediana'] / anterior - 1) * 100:+.1f}%)" if anterior else ""
        print(f"  {s['mes']:02d}/{s['ano']}  mediana R$ {s['mediana']:>9.2f}  (mín {s['minimo']:.2f}, "
              f"máx {s['maximo']:.2f}, {s['itens']} itens){var}")
        anterior = s["mediana"]
    if args.detalhe:
        print()
        for r in agente.registros(args.termo):
            if args.filtro and normalizar(args.filtro) not in normalizar(r.descricao):
                continue
            print(f"  {r.mes:02d}/{r.ano}  R$ {r.valor_medio:>9.2f}  {r.unidade or '':<6} {r.descricao}")
    return 0


def _servir(args) -> int:
    import functools
    import http.server

    pasta = Path(args.pasta).resolve()
    if not (pasta / "index.html").exists():
        print(f"Não achei {pasta}/index.html")
        return 1
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(pasta))
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.porta), handler) as srv:
        print(f"App em http://localhost:{args.porta}  (Ctrl+C para parar)")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="historico_precos", description="Varre fontes públicas de preço por EAN.")
    ap.add_argument("--banco", default="precos.db")
    ap.add_argument("--lojas", default=str(LOJAS_PADRAO))
    ap.add_argument("--intervalo", type=float, default=2.0, help="segundos entre acessos ao mesmo site")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="comando", required=True)

    b = sub.add_parser("buscar", help="varre as fontes e mostra o histórico")
    b.add_argument("ean")
    b.add_argument("--sem-wayback", action="store_true")
    b.add_argument("--max-capturas", type=int, default=40, help="cópias antigas por página")
    b.add_argument("--url", action="append", default=[], help='página extra: "Nome da loja=https://..."')
    b.add_argument("--json", help="exporta o resultado para um arquivo JSON")

    h = sub.add_parser("historico", help="mostra o que já está no banco, sem acessar a internet")
    h.add_argument("ean")
    h.add_argument("--json")

    sub.add_parser("detectar-lojas", help="testa quais lojas do lojas.json respondem como VTEX")

    c = sub.add_parser("causas", help="explica cada mudança de preço, separando o que é comprovado do que não é")
    c.add_argument("ean")
    c.add_argument("--uf", default="DF")
    c.add_argument("--categoria", help="força a categoria (ver categorias.json)")
    c.add_argument("--sem-noticias", action="store_true")
    c.add_argument("--json")

    m = sub.add_parser("comparar", help="mostra em qual loja o produto está mais barato agora")
    m.add_argument("ean")
    m.add_argument("--atualizar", action="store_true", help="consulta as lojas antes de comparar")
    m.add_argument("--max-dias", type=int, default=30, help="ignora preços mais antigos que isso")
    m.add_argument("--cidade")
    m.add_argument("--json")

    lei = sub.add_parser("leis", help="monitor de leis que mudam impostos (com aprovação humana)")
    lsub = lei.add_subparsers(dest="acao", required=True)
    lm = lsub.add_parser("monitorar", help="varre Diário Oficial e outras fontes")
    lm.add_argument("--desde", required=True, help="AAAA-MM-DD")
    lm.add_argument("--ate", help="AAAA-MM-DD (padrão: hoje)")
    lsub.add_parser("pendentes", help="lista candidatos esperando conferência")
    lv = lsub.add_parser("ver", help="mostra um candidato em detalhe")
    lv.add_argument("id")
    ld = lsub.add_parser("descartar", help="marca um candidato como irrelevante")
    ld.add_argument("id")
    la = lsub.add_parser("aprovar", help="depois de ler a norma oficial, grava o evento como COMPROVADO")
    la.add_argument("id")
    la.add_argument("--li-a-norma", action="store_true", required=True,
                    help="obrigatório: confirma que você abriu e conferiu a norma oficial")
    la.add_argument("--evento-id", help="atualiza um evento existente (ex.: df-icms-modal-2024)")
    la.add_argument("--uf")
    la.add_argument("--tributo")
    la.add_argument("--anterior", type=float, help="alíquota anterior em %%")
    la.add_argument("--nova", type=float, help="alíquota nova em %%")
    la.add_argument("--vigencia", help="AAAA-MM-DD")
    la.add_argument("--categorias", help='separadas por vírgula, ou "*" para alíquota geral')
    la.add_argument("--calculo", choices=["por_dentro", "por_fora", "sem_efeito"])
    la.add_argument("--abrangencia")

    md = sub.add_parser("mapa-df", help="Mapa de Preços do DF (NF-e, painel da Secretaria de Economia)")
    msub = md.add_subparsers(dest="acao", required=True)
    mds = msub.add_parser("descobrir", help="mapeia formulários e campos do painel e salva o HTML para análise")
    mds.add_argument("--bruto", default="mapa_df_bruto", help="pasta onde salvar o HTML")
    mdc = msub.add_parser("coletar", help="consulta o painel por produto e mês e guarda")
    mdc.add_argument("--termos", help="separados por vírgula (padrão: termos_padrao do mapa_df.json)")
    mdc.add_argument("--meses", help="AAAA-MM separados por vírgula (padrão: últimos meses)")
    mdc.add_argument("--bruto", help="salva as respostas nesta pasta (útil para ajustar o agente)")
    mdd = msub.add_parser("dicionario", help="baixa o dicionário de códigos (todos os GTIN das notas do DF, com nome e preço de compra)")
    mdd.add_argument("--banco-dicionario", default="dicionario.db")
    mdd.add_argument("--minutos", type=float, default=50)
    mdx = msub.add_parser("qlik", help="abre o app Qlik do painel como a página pública e descreve campos e tabelas")
    mdx.add_argument("--saida", default="relatorios/mapa-df-qlik.json")
    mdx.add_argument("--linhas", type=int, default=20, help="linhas de amostra por tabela")
    mdp = msub.add_parser("precos", help="preço de compra no DF (mediana diária das NF-e) por código de barras")
    mdp.add_argument("--eans", help="separados por vírgula")
    mdp.add_argument("--arquivo", help="arquivo com um EAN por linha (o resto da linha é ignorado)")
    mdp.add_argument("--do-banco", action="store_true", help="todos os produtos já cadastrados no banco")
    mdq = msub.add_parser("consultar", help="mostra o histórico mensal guardado de um termo")
    mdq.add_argument("termo")
    mdq.add_argument("--filtro", help="só descrições que contenham este texto (ex.: '500G')")
    mdq.add_argument("--detalhe", action="store_true", help="lista cada item, não só a mediana")

    v = sub.add_parser("viabilidade", help="testa as fontes, roda os agentes numa amostra real e gera relatório")
    v.add_argument("--amostra", type=int, default=60, help="quantidade de produtos")
    v.add_argument("--max-capturas", type=int, default=10, help="cópias do Wayback por página")
    v.add_argument("--com-causas", type=int, default=15, help="quantos produtos passam pelo agente de causas")
    v.add_argument("--saida", default="relatorios")
    v.add_argument("--so-fontes", action="store_true", help="só testa se as fontes respondem (rápido)")

    bl = sub.add_parser("buscar-lista", help="roda 'buscar' para cada EAN de um arquivo (um por linha)")
    bl.add_argument("arquivo")
    bl.add_argument("--sem-wayback", action="store_true")
    bl.add_argument("--max-capturas", type=int, default=10)

    en = sub.add_parser("encarte", help="lê encartes e tabloides com IA de visão (precisa de credencial da API)")
    esub = en.add_subparsers(dest="acao", required=True)
    el_ = esub.add_parser("ler", help="lê um encarte (arquivo ou URL: PNG, JPG, WEBP, GIF ou PDF)")
    el_.add_argument("origem")
    el_.add_argument("--loja", required=True)
    el_.add_argument("--cidade", default="Brasília")
    el_.add_argument("--data", help="AAAA-MM-DD, se o encarte não trouxer a validade")
    el_.add_argument("--fonte", help="página onde o encarte foi publicado (vira o link de prova)")
    edf = esub.add_parser("encartesdf", help="lê os encartes novos publicados no encartesdf.com.br")
    edf.add_argument("--dias", type=int, default=7, help="publicados nos últimos N dias")
    edf.add_argument("--max-imagens", type=int, default=20, help="teto de imagens lidas (cada uma custa uma chamada de IA)")
    edf.add_argument("--mercados", help="só estes mercados, separados por vírgula (parte do nome basta)")
    edf.add_argument("--listar", action="store_true", help="só lista os encartes, sem ler (não precisa de credencial)")
    esub.add_parser("pendentes", help="itens que não foram associados a um produto com segurança")
    ev = esub.add_parser("vincular", help="associa um item pendente a um EAN, depois de conferir")
    ev.add_argument("id")
    ev.add_argument("ean")
    ed = esub.add_parser("descartar", help="descarta um item pendente")
    ed.add_argument("id")

    cw = sub.add_parser("catalogo-wayback", help="cataloga páginas arquivadas de lojas que bloqueiam robôs (tipo 'arquivo')")
    cw.add_argument("--termos", required=True, help="separados por vírgula, ex.: cafe,arroz")
    cw.add_argument("--limite", type=int, default=20, help="páginas por termo e por loja")

    cv = sub.add_parser("catalogo-vtex", help="lê o catálogo inteiro das lojas VTEX ativas (todas as categorias) e grava o preço de hoje")
    cv.add_argument("--max-paginas", type=int, help="teto de páginas de 50 produtos por loja (para testes)")
    cv.add_argument("--minutos", type=float, help="tempo máximo por loja; a próxima rodada continua de onde parou")

    sub.add_parser("referencia-off", help="baixa a exportação completa do Open Food Facts e guarda os produtos do Brasil (referência do vínculo por nome)")

    pd = sub.add_parser("pedidos", help="lê os códigos que as pessoas escanearam e o app não conhecia (Supabase) e grava a lista")
    pd.add_argument("--saida", default="pedidos.txt")
    pd.add_argument("--config", default="site/config.json")

    cp_ = sub.add_parser("cupons", help="lê os cupons fiscais enviados pelo app (precisa da chave secreta SUPABASE_SERVICE_ROLE)")
    cp_.add_argument("--config", default="site/config.json")

    cn = sub.add_parser("catalogo-nome", help="lojas sem código de barras no site: lê páginas de produto em rodízio e vincula pelo nome")
    cn.add_argument("--minutos", type=float, default=60, help="tempo máximo por loja")
    cn.add_argument("--limite", type=int, default=5000, help="teto de páginas por loja")
    cn.add_argument("--dicionario", default="dicionario.db.gz", help="dicionário de códigos do DF como referência extra (se existir)")

    cs = sub.add_parser("catalogo-sitemap", help="acha páginas de produto pelo sitemap das lojas (tipo 'sitemap') e lê nome, GTIN e preço")
    cs.add_argument("--termos", required=True, help="separados por vírgula, ex.: cafe,arroz (procurados no endereço da página)")
    cs.add_argument("--limite", type=int, default=100, help="páginas lidas por termo e por loja")

    cd = sub.add_parser("ceasa-df", help="preço no atacado da CEASA-DF (R$/kg por dia), pela página pública de cotações")
    cd.add_argument("--produtos", help="produtos do formulário (com --historico), separados por vírgula (padrão: ceasa_df.json)")
    cd.add_argument("--historico", type=int, default=0,
                    help="também lê o formulário de preços (R$/kg por dia) destes últimos N meses; o portal parou em 01/06/2026")
    cd.add_argument("--exportar", help="grava as séries em JSON para o app (ex.: site/dados/ceasa-df.json)")

    cb = sub.add_parser("conab", help="preço médio mensal nas Ceasas (planilhas do Boletim Hortigranjeiro da Conab, gov.br)")
    cb.add_argument("--anos", default=str(date.today().year), help="pastas anuais a ler, separados por vírgula")
    cb.add_argument("--exportar", help="grava as séries em JSON para o app (ex.: site/dados/conab.json)")

    ed = sub.add_parser("encartes-dia", help="encartes vigentes dos mercados do DF lidos com Tesseract (grátis, sem IA paga)")
    ed.add_argument("--dias", type=int, default=4, help="encartes publicados nestes últimos dias")
    ed.add_argument("--max-imagens", type=int, default=120)
    ed.add_argument("--exportar", help="grava em JSON para o app (ex.: site/dados/encartes.json)")
    ed.add_argument("--dicionario", default="dicionario.db.gz", help="dicionário de códigos (vocabulário de nomes de produtos)")

    ci = sub.add_parser("conferencia-impostos", help="gera o checklist de conferência das leis de impostos")
    ci.add_argument("--saida", default="docs/conferencia-impostos.md")

    q = sub.add_parser("qualidade", help="lista preços suspeitos (todos os produtos ou um EAN)")
    q.add_argument("ean", nargs="?")

    ex = sub.add_parser("exportar", help="gera os arquivos JSON que o app lê")
    ex.add_argument("--saida", default="site/dados")
    ex.add_argument("--sem-causas", action="store_true", help="não consulta IBGE/Banco Central (mais rápido)")
    ex.add_argument("--com-noticias", action="store_true", help="inclui notícias (GDELT) nas causas")

    ec = sub.add_parser("exportar-codigos", help="divide o dicionário de códigos em arquivos por prefixo, para o app")
    ec.add_argument("dicionario", help="dicionario.db ou dicionario.db.gz")
    ec.add_argument("--saida", default="site/dados/codigos")

    rb = sub.add_parser("banco", help="recupera ou comprime o banco guardado no ramo 'dados'")
    rb.add_argument("acao", choices=["recuperar", "comprimir"])
    rb.add_argument("--saida", help="comprimir: arquivo .gz de destino")

    sv = sub.add_parser("servir", help="abre o app no computador em http://localhost:8000")
    sv.add_argument("--porta", type=int, default=8000)
    sv.add_argument("--pasta", default="site")

    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(message)s")
    if args.comando == "servir":
        return _servir(args)
    if args.comando == "banco":
        from . import ramo_dados

        if args.acao == "recuperar":
            if ramo_dados.recuperar(args.banco):
                print(f"Banco recuperado: {Path(args.banco).stat().st_size / 2**20:.1f} MB")
            else:
                print("Ainda não há banco no ramo 'dados': começa vazio.")
            return 0
        tamanho = ramo_dados.comprimir(args.banco, args.saida or f"{args.banco}.gz")
        print(f"Banco {Path(args.banco).stat().st_size / 2**20:.1f} MB, comprimido {tamanho / 2**20:.1f} MB")
        return 0
    if args.comando == "conferencia-impostos":
        from .conferencia import gerar

        Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
        Path(args.saida).write_text(gerar(), encoding="utf-8")
        print(f"Checklist salvo em {args.saida}")
        return 0
    banco = Banco(args.banco)
    nav = Navegador(intervalo=args.intervalo)

    if args.comando == "encartes-dia":
        from . import encartes_ocr
        from .modelo import agora_iso

        if not encartes_ocr.tesseract_disponivel():
            print("Tesseract não instalado (apt install tesseract-ocr tesseract-ocr-por): só a lista de encartes sai.")
        vocab = encartes_ocr.vocabulario(banco.con, *filter(None, [encartes_ocr.abrir_dicionario(args.dicionario)]))
        print(f"Vocabulário de nomes de produtos: {len(vocab)} palavras" + ("" if len(vocab) >= 5000 else " (pouco: sem filtro)"))
        encartes = encartes_ocr.ler_encartes(nav, dias=args.dias, max_imagens=args.max_imagens, vocab=vocab)
        for e in encartes:
            print(f"  {e.mercado:<28} até {e.validade_fim or '?':<10} {len(e.imagens):>2} imagem(ns) {len(e.trechos):>4} trecho(s) com preço")
            for t in e.trechos[:3]:
                print(f"      R$ {t.preco:>7.2f}  {t.texto}")
        print(f"{len(encartes)} encarte(s) vigente(s), {sum(len(e.trechos) for e in encartes)} trecho(s) com preço.")
        comparacoes = encartes_ocr.comparar_mercados(encartes)
        if args.exportar:
            Path(args.exportar).parent.mkdir(parents=True, exist_ok=True)
            Path(args.exportar).write_text(json.dumps({
                "fonte": "encartesdf.com.br (encartes publicados pelos mercados), texto lido por Tesseract",
                "aviso": "Leitura automática da imagem: pode errar. Confira sempre no encarte.",
                "atualizado_em": agora_iso(), "encartes": encartes_ocr.para_json(encartes),
                "comparacoes": comparacoes}, ensure_ascii=False), encoding="utf-8")
            print(f"Exportado em {args.exportar}")
        print(f"{len(comparacoes)} produto(s) anunciado(s) em 2 ou mais mercados:")
        for c in comparacoes[:10]:
            print(f"  {c['produto']}: " + " · ".join(
                f"{o['mercado']} " + (f"R$ {o['p']:.2f}" if o["p"] is not None else "(preço no encarte)") for o in c["ofertas"]))
        return 0
    if args.comando == "conab":
        from .fontes import conab_prohort
        from .modelo import agora_iso

        r = conab_prohort.coletar(nav, banco.con, [int(a) for a in args.anos.split(",")])
        print(f"{r['planilhas']} planilha(s) no gov.br, {r['lidas']} lida(s) agora, {r['linhas']} preço(s) mensais gravados.")
        series = conab_prohort.series(banco.con)
        for s_ in series:
            v = f"{s_['variacao_pct']:+.1f}%" if s_["variacao_pct"] is not None else "—"
            print(f"  {s_['produto']:<9} {s_['ceasa']:<24} {s_['ultimo']['mes']} R$ {s_['ultimo']['preco_kg']:.2f}/kg  {v}")
        if args.exportar:
            Path(args.exportar).parent.mkdir(parents=True, exist_ok=True)
            Path(args.exportar).write_text(json.dumps({
                "fonte": "Conab, Boletim Hortigranjeiro (planilhas de dados), preço médio mensal R$/kg",
                "evidencia": conab_prohort.PASTA, "atualizado_em": agora_iso(), "series": series}, ensure_ascii=False), encoding="utf-8")
            print(f"Exportado em {args.exportar}")
        return 0
    if args.comando == "ceasa-df":
        from .fontes import ceasa_df
        from .mapa_df.agente import ultimos_meses
        from .modelo import agora_iso

        try:
            import io

            from pypdf import PdfReader
        except ImportError:
            print("Instale o leitor de PDF: pip install -r requirements-ceasa.txt")
            return 1
        texto_pdf = lambda dados: "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(dados)).pages)  # noqa: E731
        r = ceasa_df.coletar_boletim(nav, banco.con, texto_pdf)
        print(f"Boletim 'Preço no Atacado': {r.get('data') or ''} {r['linhas']} produto(s) gravado(s). {r.get('nota') or ''}")
        if args.historico:
            nomes = [n.strip() for n in args.produtos.split(",")] if args.produtos else \
                json.loads(Path("ceasa_df.json").read_text(encoding="utf-8"))["produtos"]
            h = ceasa_df.coletar(nav, banco.con, nomes, ultimos_meses(args.historico))
            print(f"Histórico do formulário: {h['produtos']} produto(s), {h['cotacoes']} cotação(ões) (o portal parou em 01/06/2026).")
        series = ceasa_df.series_boletim(banco.con)
        for s_ in sorted(series, key=lambda x: -abs(x["variacao_pct"] or 0))[:25]:
            v = f"{s_['variacao_pct']:+.1f}%" if s_["variacao_pct"] is not None else "—"
            kg = f" (R$ {s_['ultimo']['preco_kg']:.2f}/kg)" if s_["ultimo"]["preco_kg"] else ""
            print(f"  {s_['produto']:<30} {s_['ultimo']['data']} R$ {s_['ultimo']['preco']:>7.2f} {s_['unidade'][:22]:<22}{kg} {v}")
        if args.exportar:
            Path(args.exportar).parent.mkdir(parents=True, exist_ok=True)
            Path(args.exportar).write_text(json.dumps({
                "fonte": "CEASA-DF, boletim 'Cotações de preços no atacado' (preço mais comum)",
                "evidencia": ceasa_df.INFORMACAO_MERCADO, "atualizado_em": agora_iso(), "series": series},
                ensure_ascii=False), encoding="utf-8")
            print(f"Exportado em {args.exportar}")
        return 0
    if args.comando == "catalogo-vtex":
        from .fontes import vtex

        import time

        banco.con.execute("CREATE TABLE IF NOT EXISTS catalogo_progresso (loja TEXT PRIMARY KEY, proxima INTEGER, total INTEGER, em TEXT)")
        for loja in [l for l in carregar_lojas(args.lojas) if l.get("tipo", "vtex") == "vtex"]:
            produtos, pontos, lote = 0, 0, []
            linha = banco.con.execute("SELECT proxima FROM catalogo_progresso WHERE loja = ?", (loja["nome"],)).fetchone()
            fim = time.monotonic() + args.minutos * 60 if args.minutos else None
            estado = {"i": linha[0] if linha else 0, "total": 0}

            def progresso(i, total, estado=estado):
                estado.update(i=0 if i >= total else i, total=total)

            for produto, pts in vtex.catalogo(nav, loja, args.max_paginas, inicio=estado["i"],
                                              ate=(lambda: time.monotonic() > fim) if fim else None, progresso=progresso):
                produtos += 1
                if not banco.produto(produto.ean):
                    banco.salvar_produto(produto)
                lote += pts
                if len(lote) >= 500:
                    pontos += banco.salvar_precos(lote)
                    lote = []
            pontos += banco.salvar_precos(lote)
            banco.con.execute("INSERT OR REPLACE INTO catalogo_progresso VALUES (?, ?, ?, datetime('now'))",
                              (loja["nome"], estado["i"], estado["total"]))
            banco.con.commit()
            onde = f"próxima rodada começa na categoria {estado['i'] + 1} de {estado['total']}" if estado["total"] else "sem categorias"
            print(f"{loja['nome']}: {produtos} produto(s) com código de barras, {pontos} preço(s) novo(s); {onde}.")
        return 0
    if args.comando == "referencia-off":
        from .fontes import openfoodfacts

        novos = vistos = 0
        try:
            for p_ in openfoodfacts.referencia_brasil(nav):
                vistos += 1
                if not banco.produto(p_.ean):
                    banco.salvar_produto(p_)
                    novos += 1
                if vistos % 5000 == 0:
                    banco.con.commit()
        except PermissionError as e:
            print(f"Open Food Facts: {e}.")
            return 1
        banco.con.commit()
        total = banco.con.execute("SELECT COUNT(*) FROM produtos WHERE fonte = 'Open Food Facts'").fetchone()[0]
        print(f"Open Food Facts: {vistos} produto(s) do Brasil na exportação, {novos} novo(s) na referência; {total} no total.")
        return 0
    if args.comando == "pedidos":
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8")).get("comunidade") or {}
        if not (cfg.get("url") and cfg.get("chave_publica")):
            print("Comunidade online não configurada (site/config.json): sem pedidos para ler.")
            Path(args.saida).write_text("", encoding="utf-8")
            return 0
        import urllib.request

        req = urllib.request.Request(f"{cfg['url'].rstrip('/')}/rest/v1/codigos_pedidos?select=ean",
                                     headers={"apikey": cfg["chave_publica"], "Authorization": f"Bearer {cfg['chave_publica']}",
                                              "User-Agent": nav.user_agent})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                eans = [x["ean"] for x in json.loads(r.read())]
        except Exception as e:
            print(f"Não deu para ler os pedidos: {e}")
            eans = []
        Path(args.saida).write_text("\n".join(eans) + ("\n" if eans else ""), encoding="utf-8")
        print(f"{len(eans)} código(s) pedido(s) gravado(s) em {args.saida}.")
        return 0
    if args.comando == "cupons":
        import hashlib
        import os
        import urllib.request

        from .fontes import nfce_df
        from .vinculo import Catalogo

        cfg = json.loads(Path(args.config).read_text(encoding="utf-8")).get("comunidade") or {}
        chave = os.environ.get("SUPABASE_SERVICE_ROLE", "").strip()
        if not (cfg.get("url") and chave):
            print("Sem comunidade online ou sem a chave secreta SUPABASE_SERVICE_ROLE: nenhum cupom para ler.")
            return 0
        base = f"{cfg['url'].rstrip('/')}/rest/v1/cupons_recebidos"
        cab = {"apikey": chave, "Authorization": f"Bearer {chave}", "User-Agent": nav.user_agent, "Content-Type": "application/json"}

        def api(url, metodo="GET", corpo=None):
            req = urllib.request.Request(url, method=metodo, headers=cab, data=json.dumps(corpo).encode() if corpo is not None else None)
            with urllib.request.urlopen(req, timeout=60) as r:
                texto = r.read().decode()
                return json.loads(texto) if texto else None

        pendentes = api(f"{base}?select=id,url&status=eq.pendente&url=not.is.null&limit=300") or []
        catalogo = Catalogo(list(banco.con.execute(
            "SELECT ean, nome, marca FROM produtos WHERE nome IS NOT NULL "
            "UNION SELECT DISTINCT x.ean, x.descricao, p.marca FROM precos x LEFT JOIN produtos p USING (ean) "
            "WHERE x.descricao IS NOT NULL AND x.metodo NOT IN ('vinculo-nome', 'nfce-vinculo-nome')")))
        lidos = itens = precos_novos = 0
        for c in pendentes:
            html = nav.get_texto(c["url"])
            cupom = nfce_df.ler_cupom(html) if html else None
            ok = bool(cupom and cupom.itens and cupom.emissao)
            if ok:
                resumo = hashlib.sha256(re.search(r"p=(\d{44})", c["url"]).group(1).encode()).hexdigest()
                pontos = nfce_df.pontos_do_cupom(cupom, catalogo, resumo)
                precos_novos += banco.salvar_precos(pontos)
                itens += len(cupom.itens)
                lidos += 1
            # o link é apagado sempre, lido ou não: ele pode dar acesso a dados do consumidor
            api(f"{base}?id=eq.{c['id']}", "PATCH", {"status": "lido" if ok else "falhou", "url": None,
                                                     "itens": len(cupom.itens) if cupom else 0})
        print(f"{len(pendentes)} cupom(ns) pendente(s): {lidos} lido(s), {itens} item(ns), {precos_novos} preço(s) novo(s).")
        return 0
    if args.comando == "catalogo-nome":
        import time

        from .fontes import pagina_produto
        from .vinculo import Catalogo

        from .encartes_ocr import abrir_dicionario

        # referência: nomes do cadastro, os nomes com que as lojas com código de barras mostram cada produto e as
        # descrições das notas fiscais do DF (dicionário de códigos: 163 mil códigos de barras)
        referencia = list(banco.con.execute(
            "SELECT ean, nome, marca FROM produtos WHERE nome IS NOT NULL "
            "UNION SELECT DISTINCT x.ean, x.descricao, p.marca FROM precos x LEFT JOIN produtos p USING (ean) "
            "WHERE x.descricao IS NOT NULL AND x.metodo <> 'vinculo-nome'"))
        dic = abrir_dicionario(args.dicionario) if args.dicionario else None
        if dic:
            referencia += list(dic.execute("SELECT ean, descricao, NULL FROM mapa_df_dicionario WHERE descricao IS NOT NULL"))
        catalogo = Catalogo(referencia)
        print(f"Catálogo de referência: {len(catalogo.itens)} nomes com código de barras e tamanho"
              + (" (inclui o dicionário de códigos do DF)." if dic else " (sem o dicionário de códigos)."))
        for loja in [l for l in carregar_lojas(args.lojas) if l.get("tipo") == "sitemap" and l.get("vinculo") == "nome"]:
            rv = pagina_produto.revincular(banco, loja, catalogo)
            print(f"{loja['nome']}: refeito o vínculo das páginas já lidas: {rv['vinculadas']} de {rv['sem_vinculo']} ligadas agora, "
                  f"{rv['precos']} preço(s) novo(s).")
            fim = time.monotonic() + args.minutos * 60
            r = pagina_produto.catalogar_por_nome(nav, banco, loja, catalogo, args.limite, ate=lambda fim=fim: time.monotonic() > fim)
            total = banco.con.execute("SELECT COUNT(*), SUM(ean IS NOT NULL), SUM(lido_em IS NOT NULL) FROM produtos_loja WHERE loja = ?",
                                      (loja["nome"],)).fetchone()
            print(f"{loja['nome']}: {r['lidas']} página(s) lida(s) agora, {r['com_preco']} com preço, {r['vinculadas']} vinculada(s), "
                  f"{r['precos']} preço(s) novo(s). Catálogo da loja: {total[0]} produtos, {total[2] or 0} já lidos, "
                  f"{total[1] or 0} vinculados. {r.get('parou') or ''}")
        return 0
    if args.comando == "catalogo-sitemap":
        from .fontes import pagina_produto

        for loja in [l for l in carregar_lojas(args.lojas) if l.get("tipo") == "sitemap" and l.get("vinculo") != "nome"]:
            arquivo = [loja["arquivo"]] if loja.get("arquivo") else []
            for termo in [t.strip() for t in args.termos.split(",") if t.strip()]:
                r = pagina_produto.catalogar(nav, banco, loja, [termo], limite=args.limite, lojas_arquivo=arquivo)
                print(f"{loja['nome']} · {termo}: {r['no_sitemap']} página(s) novas no sitemap, {r['lidas']} lida(s), "
                      f"{r['com_gtin']} com GTIN, {r['precos']} preço(s) novo(s)")
        return 0
    if args.comando == "catalogo-wayback":
        from .viabilidade import catalogar_arquivo

        lojas = carregar_lojas(args.lojas)
        total = 0
        for termo in [t.strip() for t in args.termos.split(",") if t.strip()]:
            achados = catalogar_arquivo(nav, banco, lojas, termo, quantos=10**6, por_loja=args.limite)
            total += len(achados)
            print(f"{termo}: {len(achados)} página(s) com código de barras")
        print(f"{total} página(s) catalogada(s). O histórico vem das cópias arquivadas: python -m historico_precos buscar <EAN>")
        return 0
    if args.comando == "encarte":
        from .encartes import AgenteEncartes, ErroEncarte

        agente = AgenteEncartes(banco, nav=nav)
        try:
            if args.acao == "encartesdf":
                from .fontes import encartesdf

                if args.listar:
                    for enc in encartesdf.listar(nav, dias=args.dias):
                        print(f"{enc.publicado} {enc.mercado:<32} até {enc.validade_fim or '?'}  {len(enc.imagens)} imagem(ns)  {enc.post}")
                    return 0
                mercados = [m.strip() for m in (args.mercados or "").split(",") if m.strip()]
                r = encartesdf.coletar(nav, agente, dias=args.dias, max_imagens=args.max_imagens, mercados=mercados)
                print(f"{r['encartes']} encarte(s), {r['imagens_lidas']} imagem(ns) lida(s) agora, {r['ja_lidas']} já lida(s), "
                      f"{r['falhas']} falha(s): {r['itens']} itens, {r['precos_novos']} preço(s) novo(s), {r['pendentes']} pendente(s).")
                return 0
            elif args.acao == "ler":
                r = agente.processar(args.origem, loja=args.loja, cidade=args.cidade, data_coleta=args.data, fonte=args.fonte)
                print(f"{r['itens']} itens lidos (validade {r['validade'][0] or '?'} a {r['validade'][1] or '?'}): "
                      f"{r['vinculados']} viraram preço, {r['pendentes']} pendentes, {r['condicionais']} com condição.")
                if r["pendentes"]:
                    print("Veja e vincule: python -m historico_precos encarte pendentes")
            elif args.acao == "pendentes":
                for it in agente.itens("pendente"):
                    print(f"[{it.id}] {it.data} {it.loja:<18} R$ {it.preco:>7.2f}  {it.descricao}")
                print("Para vincular: python -m historico_precos encarte vincular <id> <EAN>")
            elif args.acao == "vincular":
                print(f"{agente.vincular(args.id, args.ean)} preço(s) criado(s).")
            else:
                agente.descartar(args.id)
                print("Descartado.")
        except ErroEncarte as e:
            print(f"Não deu certo: {e}")
            return 1
        return 0
    if args.comando == "qualidade":
        eans = [args.ean] if args.ean else [l[0] for l in banco.con.execute("SELECT DISTINCT ean FROM precos ORDER BY ean")]
        total = 0
        for ean in eans:
            for a in avaliar_qualidade(banco.precos(ean)):
                total += 1
                print(f"[{a.severidade.upper():8}] {a.ean} {a.loja:<20} {a.data} R$ {a.preco:>8.2f}  {a.tipo}: {a.mensagem}")
                print(f"           fonte: {a.evidencia}")
        print(f"\n{total} alerta(s) em {len(eans)} produto(s). Bloqueios não são exportados para o app.")
        return 0
    if args.comando == "exportar-codigos":
        from .exportar import exportar_codigos

        n = exportar_codigos(Path(args.dicionario), Path(args.saida))
        print(f"{n} código(s) de barras exportado(s) para {args.saida}")
        return 0
    if args.comando == "exportar":
        causas = None if args.sem_causas else AgenteCausas(nav, banco, usar_noticias=args.com_noticias)
        n = exportar_app(banco, Path(args.saida), causas)
        print(f"{n} produto(s) exportado(s) para {args.saida}")
        return 0
    if args.comando == "viabilidade":
        agente = AgenteViabilidade(nav, banco, carregar_lojas(args.lojas))
        if args.so_fontes:
            for s in agente.sondar():
                print(f"{'OK ' if s.ok else 'NÃO'}  {s.fonte:<35} {s.detalhe}")
            salvar_diagnostico(nav, Path(args.saida))
            return 0
        rel = agente.executar(args.amostra, args.max_capturas, args.com_causas, Path(args.saida) / "amostra.tsv")
        md, _ = salvar(rel, Path(args.saida))
        salvar_diagnostico(nav, Path(args.saida))
        print(para_markdown(rel))
        print(f"Relatório salvo em {md}")
        return 0
    if args.comando == "buscar-lista":
        agente = AgenteHistorico(nav, banco, carregar_lojas(args.lojas))
        eans = [l.split("\t")[0].strip() for l in Path(args.arquivo).read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")]
        total = 0
        for i, ean in enumerate(eans, 1):
            rel = agente.executar(ean, usar_wayback=not args.sem_wayback, max_capturas=args.max_capturas)
            total += rel.novos
            print(f"({i}/{len(eans)}) {ean}: {rel.novos} preço(s) novo(s)")
        print(f"Total: {total} preço(s) novo(s).")
        return 0
    if args.comando == "mapa-df":
        return _mapa_df(args, nav, banco)
    if args.comando == "leis":
        return _leis(args, nav, banco)
    if args.comando == "causas":
        return _causas(args, nav, banco)
    if args.comando == "comparar":
        if args.atualizar:
            AgenteHistorico(nav, banco, carregar_lojas(args.lojas)).executar(args.ean, usar_wayback=False)
        return _comparar(args, banco)

    if args.comando == "buscar":
        agente = AgenteHistorico(nav, banco, carregar_lojas(args.lojas))
        rel = agente.executar(
            args.ean,
            usar_wayback=not args.sem_wayback,
            max_capturas=args.max_capturas,
            urls_extras=[_url_extra(u) for u in args.url],
        )
    elif args.comando == "historico":
        pontos = banco.precos(args.ean)
        produto = banco.produto(args.ean)
        rel = Relatorio(produto or Produto(args.ean), pontos, 0, detectar_mudancas(pontos))
    else:
        for loja in json.loads(Path(args.lojas).read_text(encoding="utf-8"))["lojas"]:
            ok = vtex.eh_vtex(nav, loja["dominio"])
            print(f"{'VTEX ok ' if ok else 'não     '} {loja['nome']:<25} {loja['dominio']}")
        return 0

    imprimir(rel)
    if args.json:
        exportar(rel, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
