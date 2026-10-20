// Preço com Prova: escaneia o código de barras e mostra onde está mais barato, o histórico e por que o preço mudou.

const conteudo = document.getElementById("conteudo");
const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const pct = (v, sinal = true) => `${sinal && v > 0 ? "+" : ""}${v.toFixed(1).replace(".", ",")}%`;
const LEITOR_ALTERNATIVO = "https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js";

// ---------- ícones (traço 2px, 24x24) ----------

const ICONES = {
  casa: '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  escanear: '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 8v8M10 8v8M13 8v8M17 8v8"/>',
  lista: '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="3.5" cy="6" r="1"/><circle cx="3.5" cy="12" r="1"/><circle cx="3.5" cy="18" r="1"/>',
  busca: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  voltar: '<path d="m15 5-7 7 7 7"/>',
  fechar: '<path d="M6 6l12 12M18 6 6 18"/>',
  seta: '<path d="m9 5 7 7-7 7"/>',
  compartilhar: '<path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7"/><path d="M12 15V3M7 8l5-5 5 5"/>',
  sobe: '<path d="M7 17 17 7M9 7h8v8"/>',
  desce: '<path d="M7 7l10 10M17 9v8H9"/>',
  economia: '<path d="M12 3v18M17 7.5C17 5.6 14.8 4.5 12 4.5S7 5.6 7 7.5 9.2 10.3 12 11s5 1.6 5 3.5-2.2 3-5 3-5-1.1-5-3"/>',
  escudo: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="m9 12 2 2 4-4"/>',
  duvida: '<circle cx="12" cy="12" r="9"/><path d="M9.2 9.2a3 3 0 0 1 5.6 1.3c0 2-2.8 2.4-2.8 4"/><path d="M12 17.5v.01"/>',
  megafone: '<path d="M3 10v4a1 1 0 0 0 1 1h3l6 4V5L7 9H4a1 1 0 0 0-1 1z"/><path d="M17 9a4 4 0 0 1 0 6"/>',
  elo: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
  grafico: '<path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 6-6"/>',
  recibo: '<path d="M6 3h12v18l-2.5-1.5L13 21l-2.5-1.5L8 21l-2-1.5z"/><path d="M9 8h6M9 12h6M9 16h3"/>',
  fonte: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/>',
  relogio: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
};

function icone(nome) {
  const span = document.createElement("span");
  span.className = "ic";
  span.setAttribute("aria-hidden", "true");
  span.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONES[nome] || ""}</svg>`;
  return span;
}

const NIVEIS = {
  "COMPROVADO": { classe: "comprovado", icone: "escudo", texto: "Comprovado" },
  "A CONFIRMAR": { classe: "a-confirmar", icone: "duvida", texto: "A confirmar" },
  "DECLARADO": { classe: "declarado", icone: "megafone", texto: "Declarado" },
  "ASSOCIADO": { classe: "associado", icone: "elo", texto: "Associado" },
  "REFERÊNCIA": { classe: "referencia", icone: "grafico", texto: "Referência" },
};

// ---------- utilidades ----------

function el(tag, attrs = {}, ...filhos) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const f of filhos.flat()) {
    if (f == null || f === false) continue;
    n.append(f instanceof Node ? f : document.createTextNode(String(f)));
  }
  return n;
}

const svgNS = "http://www.w3.org/2000/svg";
function s(tag, attrs = {}, ...filhos) {
  const n = document.createElementNS(svgNS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null) n.setAttribute(k, v);
  for (const f of filhos) n.append(f instanceof Node ? f : document.createTextNode(String(f)));
  return n;
}

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const dia = (iso) => new Date(iso.slice(0, 10) + "T12:00:00");
const dataBR = (iso) => { const [a, m, d] = iso.slice(0, 10).split("-"); return `${d}/${m}/${a}`; };
const mesAno = (iso) => { const d = dia(iso); return `${MESES[d.getMonth()]}/${String(d.getFullYear()).slice(2)}`; };

function idade(iso) {
  const dias = Math.round((Date.now() - dia(iso).getTime()) / 864e5);
  if (dias <= 0) return "hoje";
  if (dias === 1) return "ontem";
  if (dias < 30) return `há ${dias} dias`;
  return `em ${dataBR(iso)}`;
}

function host(url) {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url; }
}

function inicial(nome) {
  return (nome || "?").trim().charAt(0).toUpperCase();
}

// GTIN (EAN-8, UPC-A, EAN-13, GTIN-14): o último dígito confere os anteriores
function gtinValido(codigo) {
  if (!/^\d{8}$|^\d{12,14}$/.test(codigo)) return false;
  const d = codigo.split("").map(Number);
  const verificador = d.pop();
  const soma = d.reverse().reduce((t, n, i) => t + n * (i % 2 === 0 ? 3 : 1), 0);
  return (10 - (soma % 10)) % 10 === verificador;
}

async function carregarJSON(caminho) {
  const r = await fetch(caminho, { cache: "no-cache" });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

let indiceCache = null;
async function indice() {
  if (!indiceCache) {
    try { indiceCache = (await carregarJSON("dados/indice.json")) || { produtos: [] }; } catch { indiceCache = { produtos: [] }; }
  }
  return indiceCache;
}

function avisar(texto) {
  const caixa = document.getElementById("aviso-rapido");
  caixa.textContent = texto;
  caixa.classList.add("visivel");
  clearTimeout(avisar.t);
  avisar.t = setTimeout(() => caixa.classList.remove("visivel"), 2600);
}

// vistos recentemente: conveniência só deste aparelho
const recentes = {
  ler() { try { return JSON.parse(localStorage.getItem("recentes") || "[]"); } catch { return []; } },
  guardar(p) {
    try {
      const melhor = p.ofertas[0];
      const item = { ean: p.ean, nome: p.nome, preco: melhor?.preco ?? null, loja: melhor?.loja ?? null };
      const lista = [item, ...this.ler().filter((r) => r.ean !== p.ean)].slice(0, 12);
      localStorage.setItem("recentes", JSON.stringify(lista));
    } catch { /* navegação privada: segue sem histórico */ }
  },
};

function normalizar(t) {
  return (t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

// ---------- leitor em tela cheia ----------

let pararCamera = null;

async function desligarCamera() {
  if (pararCamera) {
    const parar = pararCamera;
    pararCamera = null;
    try { await parar(); } catch { /* já parada */ }
  }
}

function fecharLeitor() {
  desligarCamera();
  document.querySelector(".leitor")?.remove();
}

function irParaCodigo(codigo, aoFalhar) {
  codigo = String(codigo).replace(/\D/g, "");
  if (!gtinValido(codigo)) {
    aoFalhar?.(codigo);
    return false;
  }
  if (navigator.vibrate) navigator.vibrate(40);
  document.querySelector(".leitor")?.classList.add("lido");
  setTimeout(() => { fecharLeitor(); location.hash = `#/p/${codigo}`; }, 120);
  return true;
}

function abrirLeitor() {
  if (document.querySelector(".leitor")) return;
  const dica = el("p", { class: "leitor-dica", role: "status" }, "Centralize o código de barras");
  const entrada = el("input", { inputmode: "numeric", placeholder: "Digitar o código", "aria-label": "Código de barras", autocomplete: "off" });
  const tela = el("div", { class: "leitor", role: "dialog", "aria-modal": "true", "aria-label": "Escanear código de barras" },
    el("video", { playsinline: true, muted: true }),
    el("div", { id: "leitor-alternativo" }),
    el("div", { class: "moldura" }, el("div", { class: "laser" })),
    el("div", { class: "leitor-topo" },
      el("button", { class: "botao-redondo", type: "button", "aria-label": "Fechar", onclick: fecharLeitor }, icone("fechar")),
      el("strong", {}, "Escanear produto"),
      el("span", { style: "width:44px" })),
    dica,
    el("div", { class: "leitor-base" },
      el("form", {
        onsubmit: (ev) => {
          ev.preventDefault();
          irParaCodigo(entrada.value, () => { avisar("Esse código não parece válido. Confira os números."); entrada.focus(); });
        },
      }, entrada, el("button", { type: "submit" }, "Ver"))));
  document.body.append(tela);
  ligarCamera(tela, dica);
}

async function ligarCamera(tela, dica) {
  if (!navigator.mediaDevices || !window.isSecureContext) {
    dica.textContent = "A câmera precisa de conexão segura. Digite o código abaixo.";
    return;
  }
  const formatos = ["ean_13", "ean_8", "upc_a", "upc_e"];
  let nativo = false;
  if ("BarcodeDetector" in window) {
    try { nativo = (await BarcodeDetector.getSupportedFormats()).some((f) => formatos.includes(f)); }
    catch { nativo = false; }
  }
  const lido = (codigo) => irParaCodigo(codigo, () => { dica.textContent = "Não consegui ler direito. Aproxime um pouco."; });
  try {
    if (nativo) await cameraNativa(tela, formatos, lido);
    else await cameraAlternativa(lido);
  } catch (e) {
    dica.textContent = e && e.name === "NotAllowedError"
      ? "Sem permissão para a câmera. Libere nas configurações ou digite o código abaixo."
      : "Não consegui abrir a câmera. Digite o código abaixo.";
  }
}

async function cameraNativa(tela, formatos, lido) {
  const video = tela.querySelector("video");
  const fluxo = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
  video.srcObject = fluxo;
  await video.play();
  const suportados = await BarcodeDetector.getSupportedFormats();
  const detector = new BarcodeDetector({ formats: formatos.filter((f) => suportados.includes(f)) });
  let ativo = true;
  pararCamera = async () => { ativo = false; fluxo.getTracks().forEach((t) => t.stop()); video.srcObject = null; };
  const procurar = async () => {
    if (!ativo) return;
    try {
      for (const a of await detector.detect(video)) if (lido(a.rawValue)) return;
    } catch { /* quadro ainda não pronto */ }
    setTimeout(procurar, 180);
  };
  procurar();
}

// iPhone e navegadores sem leitor nativo: biblioteca carregada só quando precisa
async function cameraAlternativa(lido) {
  if (!window.Html5Qrcode) {
    await new Promise((ok, erro) => {
      const t = el("script", { src: LEITOR_ALTERNATIVO });
      t.onload = ok;
      t.onerror = () => erro(new Error("leitor indisponível"));
      document.head.append(t);
    });
  }
  const F = window.Html5QrcodeSupportedFormats;
  const leitor = new window.Html5Qrcode("leitor-alternativo", { formatsToSupport: [F.EAN_13, F.EAN_8, F.UPC_A, F.UPC_E], verbose: false });
  await leitor.start({ facingMode: "environment" }, { fps: 12, qrbox: { width: 280, height: 130 } }, (t) => { lido(t); }, () => {});
  pararCamera = async () => { await leitor.stop(); leitor.clear(); };
}

// ---------- tela inicial ----------

async function telaInicio() {
  const busca = el("input", { type: "search", placeholder: "Buscar produto ou código", "aria-label": "Buscar produto ou código", enterkeyhint: "search" });
  const formBusca = el("form", { class: "busca", role: "search", onsubmit: (ev) => {
    ev.preventDefault();
    const t = busca.value.trim();
    if (/^\d{8,14}$/.test(t)) irParaCodigo(t, () => avisar("Esse código não parece válido."));
    else location.hash = `#/produtos?q=${encodeURIComponent(t)}`;
  } }, icone("busca"), busca);

  const vistos = recentes.ler();
  const { produtos } = await indice();

  conteudo.replaceChildren(
    el("header", { class: "hero" },
      el("div", { class: "hero-barra" },
        el("span", { class: "marca-logo" }, el("img", { src: "icone.svg", alt: "" }), "Preço com Prova")),
      el("h1", {}, "Quanto custa de verdade?"),
      el("p", {}, "Escaneie um produto e veja onde está mais barato, quanto ele já custou e por que mudou."),
      el("button", { class: "botao-escanear-grande", type: "button", onclick: abrirLeitor }, icone("escanear"), "Escanear produto")),
    el("div", { class: "folha" },
      el("div", { class: "entrar" }, formBusca),
      vistos.length ? [
        el("div", { class: "titulo-secao entrar entrar-2" }, el("h2", {}, "Vistos por você")),
        el("div", { class: "carrossel entrar entrar-2" }, vistos.map((r) =>
          el("a", { class: "mini", href: `#/p/${r.ean}` },
            el("span", { class: "nome" }, r.nome || r.ean),
            el("span", { class: "valor" }, r.preco != null ? brl.format(r.preco) : "—"),
            el("span", { class: "loja" }, r.loja ? `em ${r.loja}` : "sem preço recente")))),
      ] : null,
      el("div", { class: "titulo-secao entrar entrar-3" }, el("h2", {}, "Como funciona")),
      el("section", { class: "cartao passos entrar entrar-3" },
        passo("fonte", "Preço com fonte", "Cada preço tem o link de onde veio."),
        passo("grafico", "Histórico real", "Veja quanto o produto já custou em cada loja."),
        passo("escudo", "Causa com prova", "Separamos o que é fato comprovado do que é só suposição.")),
      produtos.length ? [
        el("div", { class: "titulo-secao entrar entrar-4" }, el("h2", {}, "Produtos acompanhados"), el("a", { href: "#/produtos" }, "Ver todos")),
        el("section", { class: "cartao entrar entrar-4" }, listaProdutos(produtos.slice(0, 5))),
      ] : null,
      el("p", { class: "rodape-nota" }, "Preços coletados de fontes públicas. A câmera funciona só no seu aparelho.")));
}

function passo(nomeIcone, titulo, texto) {
  return el("div", { class: "passo" }, el("span", { class: "icone-passo" }, icone(nomeIcone)),
    el("div", {}, el("strong", {}, titulo), el("span", {}, texto)));
}

function listaProdutos(itens) {
  return el("ul", { class: "lista" }, itens.map((p) => el("li", {},
    el("a", { class: "item-produto", href: `#/p/${p.ean}` },
      el("span", { class: "avatar", "aria-hidden": "true" }, inicial(p.nome)),
      el("span", { class: "meio" },
        el("span", { class: "nome", style: "display:block" }, p.nome || p.ean),
        el("span", { class: "detalhe" }, p.loja ? `${p.loja}${p.lojas > 1 ? ` e mais ${p.lojas - 1}` : ""}` : "sem preço recente")),
      el("span", { class: "valor" }, p.menor_preco != null ? brl.format(p.menor_preco) : "—"),
      icone("seta")))));
}

// ---------- lista de produtos ----------

async function telaProdutos(consulta = "") {
  const { produtos, atualizado_em } = await indice();
  const lista = el("div");
  const busca = el("input", { type: "search", placeholder: "Buscar produto ou código", "aria-label": "Buscar produto", value: consulta });
  const desenhar = () => {
    const f = normalizar(busca.value);
    const itens = produtos.filter((p) => !f || p.ean.includes(f) || normalizar(p.nome).includes(f));
    lista.replaceChildren(itens.length
      ? el("section", { class: "cartao" }, listaProdutos(itens))
      : el("section", { class: "cartao" }, el("p", { class: "sub", style: "margin:0" },
          produtos.length ? "Nenhum produto com esse nome por aqui ainda." : "Os produtos aparecem aqui depois da primeira coleta.")));
  };
  busca.addEventListener("input", desenhar);
  conteudo.replaceChildren(
    el("header", { class: "hero" },
      el("div", { class: "hero-barra" }, el("span", { class: "marca-logo" }, el("img", { src: "icone.svg", alt: "" }), "Preço com Prova")),
      el("h1", {}, "Produtos acompanhados"),
      el("p", {}, produtos.length ? `${produtos.length} produtos${atualizado_em ? ` · atualizado ${idade(atualizado_em)}` : ""}` : "Nenhum produto ainda")),
    el("div", { class: "folha" },
      el("div", { class: "busca entrar", style: "margin-bottom:14px" }, icone("busca"), busca),
      el("div", { class: "entrar entrar-2" }, lista)));
  desenhar();
}

// ---------- produto ----------

function esqueletoProduto() {
  const bloco = (w, h, extra = "") => el("div", { class: "esqueleto", style: `width:${w};height:${h}px;${extra}` });
  conteudo.replaceChildren(
    el("header", { class: "hero" },
      el("div", { class: "hero-barra" }, bloco("44px", 44, "border-radius:50%")),
      bloco("60%", 18, "margin-bottom:22px"), bloco("40%", 14, "margin-bottom:8px"), bloco("55%", 44, "margin-bottom:10px"), bloco("35%", 16)),
    el("div", { class: "folha" },
      el("section", { class: "cartao" }, bloco("45%", 20, "margin-bottom:18px"), bloco("100%", 44, "margin-bottom:12px"), bloco("100%", 44)),
      el("section", { class: "cartao" }, bloco("35%", 20, "margin-bottom:18px"), bloco("100%", 180))));
}

function tendencia(p) {
  // variação do menor preço de hoje contra o preço da mesma loja há ~1 ano (ou o mais antigo que houver)
  const melhor = p.ofertas[0];
  if (!melhor) return null;
  const daLoja = p.historico.filter((h) => h.loja === melhor.loja).sort((a, b) => a.data.localeCompare(b.data));
  if (daLoja.length < 2) return null;
  const umAno = new Date(dia(melhor.data).getTime() - 365 * 864e5).toISOString().slice(0, 10);
  const base = daLoja.filter((h) => h.data <= umAno).pop() || daLoja[0];
  if (base.data === melhor.data) return null;
  const variacao = (melhor.preco / base.preco - 1) * 100;
  const periodo = base.data <= umAno ? "em 1 ano" : `desde ${mesAno(base.data)}`;
  return { variacao, periodo };
}

async function telaProduto(ean) {
  esqueletoProduto();
  let p;
  try { p = await carregarJSON(`dados/${ean}.json`); } catch {
    conteudo.replaceChildren(heroSimples("Sem conexão", "Não deu para carregar este produto agora. Tente de novo em instantes."));
    return;
  }
  if (!p) {
    conteudo.replaceChildren(
      heroSimples("Ainda não acompanhamos este produto", `Código ${ean}. A lista cresce a cada coleta, e ele pode aparecer em breve.`),
      el("div", { class: "folha" }, el("section", { class: "cartao" },
        el("button", { class: "botao-escanear-grande", style: "margin:0;background:var(--marca);color:var(--sobre-marca)", type: "button", onclick: abrirLeitor },
          icone("escanear"), "Escanear outro produto"))));
    return;
  }
  recentes.guardar(p);
  document.title = `${p.nome || ean} · Preço com Prova`;
  conteudo.replaceChildren(heroProduto(p), el("div", { class: "folha" },
    cartaoOndeComprar(p),
    cartaoHistorico(p),
    cartaoCausas(p),
    cartaoImpostos(),
    el("p", { class: "rodape-nota" }, p.aviso, ` Atualizado ${idade(p.atualizado_em)}.`)));
}

function heroSimples(titulo, texto) {
  return el("header", { class: "hero" },
    el("div", { class: "hero-barra" },
      el("button", { class: "botao-redondo", type: "button", "aria-label": "Voltar", onclick: voltar }, icone("voltar"))),
    el("h1", {}, titulo), el("p", {}, texto));
}

function voltar() {
  if (history.length > 1) history.back();
  else location.hash = "#/";
}

function heroProduto(p) {
  const melhor = p.ofertas[0];
  const subtitulo = [p.marca, p.quantidade].filter(Boolean).join(" · ");
  const economia = p.ofertas.length > 1 ? p.ofertas[p.ofertas.length - 1].preco - melhor.preco : 0;
  const tend = tendencia(p);
  return el("header", { class: "hero" },
    el("div", { class: "hero-barra" },
      el("button", { class: "botao-redondo", type: "button", "aria-label": "Voltar", onclick: voltar }, icone("voltar")),
      el("button", { class: "botao-redondo", type: "button", "aria-label": "Compartilhar", onclick: () => compartilhar(p) }, icone("compartilhar"))),
    el("p", { class: "produto-nome entrar" }, p.nome || "Produto sem nome", subtitulo ? el("small", {}, subtitulo) : null),
    melhor ? [
      el("p", { class: "rotulo entrar" }, "Menor preço agora"),
      el("p", { class: "preco-hero entrar" }, brl.format(melhor.preco)),
      el("p", { class: "onde entrar" }, `em ${melhor.loja} · ${idade(melhor.data)}`),
    ] : [
      el("p", { class: "rotulo" }, "Sem preço recente"),
      el("p", { class: "onde" }, "Não encontramos preço deste produto nos últimos 30 dias."),
    ],
    el("div", { class: "pilulas entrar entrar-2" },
      economia > 0.004 ? el("span", { class: "pilula" }, icone("economia"), `Economize até ${brl.format(economia)}`) : null,
      tend ? el("span", { class: "pilula" }, icone(tend.variacao >= 0 ? "sobe" : "desce"), `${pct(tend.variacao)} ${tend.periodo}`) : null,
      melhor?.em_promocao ? el("span", { class: "pilula" }, "Em promoção") : null));
}

async function compartilhar(p) {
  const melhor = p.ofertas[0];
  const texto = melhor
    ? `${p.nome}: ${brl.format(melhor.preco)} em ${melhor.loja}. Veja o histórico e as provas no Preço com Prova.`
    : `${p.nome} no Preço com Prova.`;
  try {
    if (navigator.share) await navigator.share({ title: p.nome, text: texto, url: location.href });
    else { await navigator.clipboard.writeText(`${texto} ${location.href}`); avisar("Link copiado"); }
  } catch { /* compartilhamento cancelado */ }
}

function cartaoOndeComprar(p) {
  const cartao = el("section", { class: "cartao entrar" }, el("h2", {}, "Onde comprar"));
  if (!p.ofertas.length) {
    cartao.append(el("p", { class: "sub", style: "margin:0" }, "Nenhuma loja com preço nos últimos 30 dias."));
    return cartao;
  }
  cartao.append(el("p", { class: "sub" }, p.ofertas.length > 1 ? `Comparamos ${p.ofertas.length} lojas.` : "Só uma loja com preço recente."));
  cartao.append(el("ul", { class: "lojas" }, p.ofertas.map((o, i) => el("li", {},
    el("div", { class: "loja-linha" },
      el("span", { class: `posicao${i === 0 ? " primeiro" : ""}`, "aria-label": `${i + 1}º lugar` }, i + 1),
      el("div", { class: "meio" },
        el("div", { class: "nome" }, o.loja,
          i === 0 && p.ofertas.length > 1 ? el("span", { class: "etiqueta melhor" }, "Mais barato") : null,
          o.em_promocao ? el("span", { class: "etiqueta promo" }, "Promoção") : null),
        el("div", { class: "detalhe" }, `${idade(o.data)} · `, el("a", { href: o.evidencia, target: "_blank", rel: "noopener" }, "ver fonte"))),
      el("div", { class: "direita" },
        el("div", { class: "valor" }, brl.format(o.preco)),
        el("div", { class: "diferenca" }, i === 0
          ? (o.em_promocao && o.preco_de ? `era ${brl.format(o.preco_de)}` : "")
          : `+${brl.format(o.diferenca_rs)}`)))))));
  if (p.ofertas_antigas.length) {
    cartao.append(el("p", { class: "minusculo", style: "margin:10px 0 0" }, "Preços antigos, fora da comparação: ",
      p.ofertas_antigas.map((o) => `${o.loja} ${brl.format(o.preco)} em ${dataBR(o.data)}`).join("; ")));
  }
  return cartao;
}

// ---------- histórico ----------

function cartaoHistorico(p) {
  const cartao = el("section", { class: "cartao entrar entrar-2" }, el("h2", {}, "Histórico do preço"));
  const pontos = p.historico.map((h) => ({ ...h, t: dia(h.data).getTime() }));
  if (new Set(pontos.map((h) => h.data)).size < 2) {
    cartao.append(el("div", { class: "vazio-curto" }, "O histórico começa agora. A cada coleta este gráfico ganha mais pontos."));
    return cartao;
  }

  // até 3 lojas (as mais observadas); a cor segue a loja (ordem alfabética), nunca a posição no ranking
  const porLoja = new Map();
  for (const h of pontos) porLoja.set(h.loja, [...(porLoja.get(h.loja) || []), h]);
  const lojas = [...porLoja.keys()].sort((a, b) => porLoja.get(b).length - porLoja.get(a).length).slice(0, 3).sort();
  const cores = ["var(--serie-1)", "var(--serie-2)", "var(--serie-3)"];
  const todasSeries = lojas.map((loja, i) => ({ loja, cor: cores[i], pts: porLoja.get(loja).sort((a, b) => a.t - b.t) }));
  const fim = Math.max(...pontos.map((h) => h.t));
  const inicioTotal = Math.min(...pontos.map((h) => h.t));

  const periodos = [["6M", 182], ["1A", 365], ["Tudo", null]];
  let escolhido = (fim - inicioTotal) / 864e5 > 5 * 365 ? "1A" : "Tudo";
  const seg = el("div", { class: "segmentado", role: "group", "aria-label": "Período" });
  const caixa = el("div", { class: "grafico" });
  const desenharPeriodo = () => {
    seg.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.p === escolhido)));
    const dias = periodos.find(([n]) => n === escolhido)[1];
    const inicio = dias ? Math.max(inicioTotal, fim - dias * 864e5) : inicioTotal;
    const series = todasSeries.map((serie) => {
      const anteriores = serie.pts.filter((h) => h.t < inicio);
      const dentro = serie.pts.filter((h) => h.t >= inicio);
      const ancora = anteriores.length ? [{ ...anteriores[anteriores.length - 1], t: inicio, ancora: true }] : [];
      return { ...serie, pts: [...ancora, ...dentro] };
    }).filter((serie) => serie.pts.length);
    grafico(caixa, series, inicio, fim);
  };
  for (const [nome] of periodos) {
    seg.append(el("button", { type: "button", "data-p": nome, onclick: () => { escolhido = nome; desenharPeriodo(); } }, nome));
  }

  cartao.append(el("p", { class: "sub" }, `Desde ${mesAno(new Date(inicioTotal).toISOString())} · ${pontos.length} preços registrados`), seg);
  if (todasSeries.length > 1) {
    cartao.append(el("ul", { class: "legenda" }, todasSeries.map((serie) =>
      el("li", {}, el("span", { class: "amostra", style: `background:${serie.cor}` }), serie.loja))));
  } else {
    cartao.append(el("p", { class: "minusculo", style: "margin:0 0 6px" }, todasSeries[0].loja));
  }
  cartao.append(caixa);

  let largura = 0;
  new ResizeObserver(([e]) => {
    const w = Math.floor(e.contentRect.width);
    if (w > 0 && w !== largura) { largura = w; desenharPeriodo(); }
  }).observe(caixa);

  const linhas = [...p.historico].reverse().map((h) => el("tr", {},
    el("td", {}, dataBR(h.data)), el("td", {}, h.loja), el("td", { class: "num" }, brl.format(h.preco)),
    el("td", {}, el("a", { href: h.evidencia, target: "_blank", rel: "noopener" }, "fonte"))));
  cartao.append(el("details", { class: "expansivel" },
    el("summary", {}, `Ver os ${p.historico.length} preços e fontes`, icone("seta")),
    el("table", { class: "tabela" },
      el("thead", {}, el("tr", {}, el("th", {}, "Data"), el("th", {}, "Loja"), el("th", { class: "num" }, "Preço"), el("th", {}, ""))),
      el("tbody", {}, linhas))));
  return cartao;
}

function grafico(caixa, series, t0, t1) {
  const W = Math.floor(caixa.clientWidth);
  if (!W) return;
  const H = 210, L = 64, R = 8, T = 10, B = 24;
  const usados = series.flatMap((x) => x.pts);
  let y0 = Math.min(...usados.map((h) => h.preco)), y1 = Math.max(...usados.map((h) => h.preco));
  const folga = (y1 - y0) * 0.15 || y1 * 0.1;
  y0 = Math.max(0, y0 - folga); y1 += folga;
  const x = (t) => L + ((t - t0) / (t1 - t0 || 1)) * (W - L - R);
  const y = (v) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);

  const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img",
    "aria-label": `Histórico de preço de ${series.map((x) => x.loja).join(", ")}` });
  for (let i = 0; i <= 3; i++) {
    const v = y0 + ((y1 - y0) * i) / 3;
    svg.append(s("line", { class: "grade", x1: L, x2: W - R, y1: y(v), y2: y(v) }));
    svg.append(s("text", { class: "eixo", x: L - 8, y: y(v) + 4, "text-anchor": "end" }, brl.format(v)));
  }
  [[t0, "start"], [(t0 + t1) / 2, "middle"], [t1, "end"]].forEach(([t, ancora]) =>
    svg.append(s("text", { class: "eixo", x: x(t), y: H - 4, "text-anchor": ancora }, mesAno(new Date(t).toISOString()))));

  for (const serie of series) {
    // degraus: cada preço vale até a próxima observação
    let d = `M${x(serie.pts[0].t)},${y(serie.pts[0].preco)}`;
    for (const h of serie.pts.slice(1)) d += ` H${x(h.t)} V${y(h.preco)}`;
    svg.append(s("path", { d, fill: "none", stroke: serie.cor, "stroke-width": 2.5, "stroke-linejoin": "round", "stroke-linecap": "round" }));
    for (const h of serie.pts) {
      if (h.ancora) continue;
      svg.append(s("circle", { cx: x(h.t), cy: y(h.preco), r: 4, fill: serie.cor, stroke: "var(--superficie)", "stroke-width": 2 }));
    }
  }

  const mira = s("line", { class: "mira-x", y1: T, y2: H - B, visibility: "hidden" });
  const area = s("rect", { x: L, y: 0, width: W - L - R, height: H, fill: "transparent" });
  svg.append(mira, area);
  const dica = el("div", { class: "dica", hidden: true });
  const instantes = [...new Set(usados.filter((h) => !h.ancora).map((h) => h.t))].sort((a, b) => a - b);

  const mostrar = (ev) => {
    if (!instantes.length) return;
    const px = ev.clientX - svg.getBoundingClientRect().left;
    const t = instantes.reduce((m, c) => (Math.abs(x(c) - px) < Math.abs(x(m) - px) ? c : m), instantes[0]);
    mira.setAttribute("x1", x(t)); mira.setAttribute("x2", x(t)); mira.setAttribute("visibility", "visible");
    const itens = series.map((serie) => {
      const vigente = serie.pts.filter((h) => h.t <= t).pop();
      return vigente ? el("div", { class: "item" }, el("span", { class: "amostra", style: `background:${serie.cor}` }),
        el("strong", {}, brl.format(vigente.preco)), ` ${serie.loja}`) : null;
    }).filter(Boolean);
    dica.replaceChildren(el("div", { class: "data" }, dataBR(new Date(t).toISOString())), ...itens);
    dica.hidden = false;
    dica.style.left = `${Math.min(Math.max(x(t) - 80, 0), W - 170)}px`;
    dica.style.top = "0px";
  };
  area.addEventListener("pointermove", mostrar);
  area.addEventListener("pointerdown", mostrar);
  area.addEventListener("pointerleave", () => { dica.hidden = true; mira.setAttribute("visibility", "hidden"); });
  caixa.replaceChildren(svg, dica);
}

// ---------- por que mudou ----------

function seloNivel(nivel) {
  const n = NIVEIS[nivel] || NIVEIS["ASSOCIADO"];
  return el("span", { class: `nivel ${n.classe}` }, icone(n.icone), n.texto.toUpperCase());
}

function cartaoCausas(p) {
  const cartao = el("section", { class: "cartao entrar entrar-3" }, el("h2", {}, "Por que o preço mudou"));
  if (!p.mudancas.length) {
    cartao.append(el("div", { class: "vazio-curto" }, "Nenhuma mudança de preço registrada ainda."));
    return cartao;
  }
  cartao.append(el("p", { class: "sub" }, "Toque numa mudança para ver as provas."));
  const aberta = p.mudancas.slice(0, 8).findIndex((m) => m.evidencias.length);
  p.mudancas.slice(0, 8).forEach((m, i) => {
    const sobe = m.variacao_pct > 0;
    const provas = m.evidencias.map((e) => {
      const fontes = e.fontes.slice(0, 2);
      const mesmoSite = fontes.length === 2 && host(fontes[0]) === host(fontes[1]);
      return el("li", { class: "prova" },
        seloNivel(e.nivel),
        el("div", {}, e.descricao),
        fontes.length ? el("div", { class: "fontes" }, fontes.map((f, j) => f.startsWith("http")
          ? el("a", { href: f, target: "_blank", rel: "noopener" }, icone("fonte"), mesmoSite ? ["Fonte antes", "Fonte depois"][j] : host(f))
          : el("span", { class: "minusculo" }, f))) : null);
    });
    cartao.append(el("details", { class: "mudanca", open: i === aberta },
      el("summary", {},
        el("span", { class: `seta-var ${sobe ? "sobe" : "desce"}` }, icone(sobe ? "sobe" : "desce")),
        el("span", { class: "meio" },
          el("span", { class: "linha-titulo" },
            el("span", { class: `titulo ${sobe ? "sobe" : "desce"}` }, `${sobe ? "Subiu" : "Caiu"} ${pct(Math.abs(m.variacao_pct), false)}`),
            el("span", { class: `contagem${m.evidencias.length ? " com" : ""}` },
              m.evidencias.length ? `${m.evidencias.length} prova${m.evidencias.length > 1 ? "s" : ""}` : "sem provas")),
          el("span", { class: "detalhe", style: "display:block" },
            `${m.loja} · ${brl.format(m.preco_anterior)} → ${brl.format(m.preco_novo)}`),
          el("span", { class: "detalhe", style: "display:block" }, `${mesAno(m.data_anterior)} a ${mesAno(m.data_nova)}`)),
        el("span", { class: "chevron" }, icone("seta"))),
      provas.length
        ? el("ul", { class: "provas" }, provas)
        : el("p", { class: "minusculo", style: "margin:0 14px 14px" }, "Ainda não encontramos evidências para este período."),
      m.comprovado_pct
        ? el("p", { class: "resumo-prova" }, `Imposto comprovado explica ${pct(m.comprovado_pct)}. O restante (${pct(m.nao_explicado_pct)}) ainda não tem causa comprovada.`)
        : null));
  });
  if (p.mudancas.length > 8) cartao.append(el("p", { class: "minusculo", style: "margin:12px 0 0" }, `E mais ${p.mudancas.length - 8} mudanças anteriores.`));

  cartao.append(el("details", { class: "expansivel" },
    el("summary", {}, "Como lemos as provas", icone("seta")),
    el("div", { class: "legenda-niveis" }, Object.keys(NIVEIS).map(seloNivel)),
    el("p", { class: "explica-niveis" },
      "Comprovado: fato documentado, com efeito que dá para calcular. A confirmar: encontramos, mas a lei ainda não foi conferida. ",
      "Declarado: alguém afirmou publicamente. Associado e Referência: aconteceram no mesmo período, mas não provam a causa.")));
  return cartao;
}

function cartaoImpostos() {
  return el("section", { class: "cartao entrar entrar-4" },
    el("div", { class: "em-breve" },
      el("span", { class: "icone-grande" }, icone("recibo")),
      el("div", {},
        el("span", { class: "selo-breve" }, "EM BREVE"),
        el("h2", {}, "Quanto do preço é imposto"),
        el("p", { class: "sub", style: "margin:4px 0 0" }, "Vamos calcular direto da lei, com o artigo de cada alíquota, e mostrar como fica com a Reforma Tributária."))));
}

// ---------- rotas ----------

async function rotear() {
  fecharLeitor();
  const hash = location.hash || "#/";
  const produto = hash.match(/^#\/p\/(\d{8,14})$/);
  const lista = hash.match(/^#\/produtos(?:\?q=(.*))?$/);
  document.querySelectorAll(".abas a").forEach((a) =>
    a.classList.toggle("ativa", (a.dataset.aba === "produtos" && !!lista) || (a.dataset.aba === "inicio" && hash === "#/")));
  document.title = "Preço com Prova";
  if (produto) await telaProduto(produto[1]);
  else if (lista) await telaProdutos(decodeURIComponent(lista[1] || ""));
  else await telaInicio();
  conteudo.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}

document.querySelectorAll("[data-icone]").forEach((n) => n.replaceWith(icone(n.dataset.icone)));
document.getElementById("aba-escanear").addEventListener("click", abrirLeitor);
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") fecharLeitor(); });
window.addEventListener("hashchange", rotear);
rotear();

if ("serviceWorker" in navigator && location.protocol !== "file:") {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
