// Preço com Prova: escaneia o código de barras e mostra onde está mais barato, o histórico e por que o preço mudou.
import { calcular, categoria } from "./impostos.js";
import { confiancaPreco, nivelPorPontos, precoSugerido, utilidade, chavePreco, chaveCausa, PONTOS, NIVEIS as NIVEIS_COMUNIDADE } from "./confianca.js";
import { criarComunidade, consentimento, ErroComunidade, TIPOS_REPORTE } from "./comunidade.js";

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
  marcador: '<path d="M6 3h12v18l-6-4-6 4z"/>',
  marcadorCheio: '<path d="M6 3h12v18l-6-4-6 4z" fill="currentColor"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.01"/>',
  lixeira: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  cadeado: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  estrela: '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
  polegarCima: '<path d="M7 11v9H4v-9zM7 11l4-8a2 2 0 0 1 2 2v4h5a2 2 0 0 1 2 2.3l-1.2 7A2 2 0 0 1 16.8 20H7"/>',
  polegarBaixo: '<path d="M17 13V4h3v9zM17 13l-4 8a2 2 0 0 1-2-2v-4H6a2 2 0 0 1-2-2.3l1.2-7A2 2 0 0 1 7.2 4H17"/>',
  usuario: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  documento: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
  bandeira: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
  martelo: '<path d="m14 6 4 4M12 8l4 4-7 7-4-4zM15 3l6 6"/>',
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

// produtos que a pessoa acompanha: guarda o preço visto para avisar quando mudar
const favoritos = {
  ler() { try { return JSON.parse(localStorage.getItem("favoritos") || "[]"); } catch { return []; } },
  tem(ean) { return this.ler().some((f) => f.ean === ean); },
  salvar(lista) { try { localStorage.setItem("favoritos", JSON.stringify(lista)); return true; } catch { return false; } },
  alternar(p) {
    const lista = this.ler();
    if (lista.some((f) => f.ean === p.ean)) { this.salvar(lista.filter((f) => f.ean !== p.ean)); return false; }
    const preco = p.ofertas?.[0]?.preco ?? null;
    return this.salvar([{ ean: p.ean, nome: p.nome, preco_visto: preco }, ...lista]);
  },
  // ao abrir o produto, o preço atual vira o novo "visto"
  visto(p) {
    const preco = p.ofertas?.[0]?.preco;
    if (preco == null) return;
    this.salvar(this.ler().map((f) => (f.ean === p.ean ? { ...f, nome: p.nome, preco_visto: preco } : f)));
  },
};

let configCache = null;
async function config() {
  if (!configCache) {
    try { configCache = (await carregarJSON("config.json")) || {}; } catch { configCache = {}; }
  }
  return configCache;
}

let comunidadeCache = null;
async function comunidade() {
  if (!comunidadeCache) comunidadeCache = criarComunidade(await config());
  return comunidadeCache;
}

// janela que sobe de baixo, como nos apps de banco
function abrirFolha(titulo, ...filhos) {
  const fundo = el("div", { class: "folha-modal-fundo" });
  const fechar = () => { fundo.remove(); document.removeEventListener("keydown", aoTeclar); };
  const aoTeclar = (ev) => { if (ev.key === "Escape") fechar(); };
  fundo.addEventListener("click", (ev) => { if (ev.target === fundo) fechar(); });
  const painel = el("div", { class: "folha-modal", role: "dialog", "aria-modal": "true", "aria-label": titulo },
    el("div", { class: "puxador", "aria-hidden": "true" }),
    el("div", { class: "folha-modal-topo" }, el("h2", {}, titulo),
      el("button", { class: "botao-fechar", type: "button", "aria-label": "Fechar", onclick: fechar }, icone("fechar"))),
    ...filhos);
  fundo.append(painel);
  document.body.append(fundo);
  document.addEventListener("keydown", aoTeclar);
  setTimeout(() => painel.querySelector("button.principal, input, textarea")?.focus(), 50);
  return fechar;
}

function fecharFolhas() {
  document.querySelectorAll(".folha-modal-fundo").forEach((f) => f.remove());
}

// consentimento pedido no primeiro voto, nunca ao abrir o app
async function garantirConsentimento() {
  if (consentimento.valido()) return true;
  const modo = (await comunidade()).modo;
  return new Promise((resolver) => {
    let decidido = false;
    const decidir = (sim) => { if (!decidido) { decidido = true; resolver(sim); } fechar(); };
    const caixa = el("input", { type: "checkbox", id: "aceite" });
    const botao = el("button", { class: "botao-principal", type: "button", disabled: true, onclick: () => { consentimento.dar(); decidir(true); } },
      "Concordo e quero colaborar");
    caixa.addEventListener("change", () => { botao.disabled = !caixa.checked; });
    const fechar = abrirFolha("Antes de colaborar",
      modo === "teste" ? el("p", { class: "faixa-teste" }, "Modo de teste: por enquanto, suas contribuições ficam só neste aparelho.") : null,
      el("p", { class: "texto-folha" }, "Sua confirmação ajuda todo mundo a saber se a informação está certa. Para isso, guardamos:"),
      el("ul", { class: "lista-consentimento" },
        el("li", {}, "um identificador anônimo deste aparelho (sem e-mail, telefone, CPF ou localização);"),
        el("li", {}, "o que você confirmou ou informou, com data, e seus pontos;"),
        el("li", {}, "um apelido, só se você quiser aparecer no ranking.")),
      el("p", { class: "texto-folha" }, "Os outros só veem totais, sem saber quem votou. Tudo é apagado em 12 meses, e você pode apagar antes, a qualquer hora, no seu perfil."),
      el("label", { class: "checagem", for: "aceite" }, caixa,
        el("span", {}, "Tenho 18 anos ou mais e li os ", el("a", { href: "#/termos", target: "_blank" }, "termos de uso"), " e a ",
          el("a", { href: "#/privacidade", target: "_blank" }, "política de privacidade"), ".")),
      botao,
      el("button", { class: "botao-texto", type: "button", onclick: () => decidir(false) }, "Agora não"));
    const observador = new MutationObserver(() => { if (!document.body.contains(botao)) { observador.disconnect(); if (!decidido) { decidido = true; resolver(false); } } });
    observador.observe(document.body, { childList: true });
  });
}

// executa uma contribuição com consentimento, aviso de pontos e tratamento de erro
async function contribuir(acao) {
  if (!(await garantirConsentimento())) return false;
  try {
    const { ganho } = await acao(await comunidade());
    avisar(ganho ? `Obrigado! +${ganho} ponto${ganho > 1 ? "s" : ""}` : "Obrigado! Vamos conferir antes de publicar.");
    return true;
  } catch (e) {
    avisar(e instanceof ErroComunidade ? e.message : "Não deu certo agora. Tente de novo.");
    return false;
  }
}

function estrelas(n, rotulo) {
  return el("span", { class: "estrelas", role: "img", "aria-label": rotulo || `${String(n).replace(".", ",")} de 5 estrelas` },
    el("span", { class: "estrelas-fundo", "aria-hidden": "true" }, "★★★★★"),
    el("span", { class: "estrelas-cheias", "aria-hidden": "true", style: `width:${(n / 5) * 100}%` }, "★★★★★"));
}

let tabelaImpostos = null;
async function impostos() {
  if (!tabelaImpostos) {
    try { tabelaImpostos = await carregarJSON("impostos.json"); } catch { tabelaImpostos = null; }
  }
  return tabelaImpostos;
}

// nome e foto pela base aberta Open Food Facts (consulta feita pelo próprio aparelho)
const cacheOFF = new Map();
function produtoAberto(ean) {
  if (!cacheOFF.has(ean)) {
    const controle = new AbortController();
    setTimeout(() => controle.abort(), 5000);
    cacheOFF.set(ean, fetch(`https://world.openfoodfacts.org/api/v2/product/${ean}.json?fields=product_name,product_name_pt,brands,quantity,image_front_small_url,image_front_url`,
      { signal: controle.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => (d && d.status === 1 ? {
        nome: d.product.product_name_pt || d.product.product_name || null,
        marca: d.product.brands || null,
        quantidade: d.product.quantity || null,
        foto: d.product.image_front_small_url || d.product.image_front_url || null,
      } : null))
      .catch(() => null));
  }
  return cacheOFF.get(ean);
}

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
        el("span", { class: "marca-logo" }, el("img", { src: "icone.svg", alt: "" }), "Preço com Prova"),
        el("span", { class: "acoes-hero" },
          el("a", { class: "botao-redondo", href: "#/perfil", "aria-label": "Seu perfil e pontos" }, icone("usuario")),
          el("a", { class: "botao-redondo", href: "#/sobre", "aria-label": "Sobre e privacidade" }, icone("info")))),
      el("h1", {}, "Quanto custa de verdade?"),
      el("p", {}, "Escaneie um produto e veja onde está mais barato, quanto ele já custou e por que mudou."),
      el("button", { class: "botao-escanear-grande", type: "button", onclick: abrirLeitor }, icone("escanear"), "Escanear produto")),
    el("div", { class: "folha" },
      el("div", { class: "entrar" }, formBusca),
      secaoSeusProdutos(produtos),
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

function secaoSeusProdutos(produtos) {
  const meus = favoritos.ler();
  if (!meus.length) return null;
  const atual = new Map(produtos.map((p) => [p.ean, p]));
  return [
    el("div", { class: "titulo-secao entrar entrar-2" }, el("h2", {}, "Seus produtos")),
    el("section", { class: "cartao entrar entrar-2" }, el("ul", { class: "lista" }, meus.map((f) => {
      const agora = atual.get(f.ean)?.menor_preco ?? null;
      const dif = agora != null && f.preco_visto != null ? agora - f.preco_visto : 0;
      const status = Math.abs(dif) < 0.005
        ? el("span", { class: "detalhe" }, "sem mudança desde sua última visita")
        : el("span", { class: `detalhe ${dif < 0 ? "texto-desce" : "texto-sobe"}` },
            `${dif < 0 ? "baixou" : "subiu"} ${brl.format(Math.abs(dif))} desde sua última visita`);
      return el("li", {}, el("a", { class: "item-produto", href: `#/p/${f.ean}` },
        el("span", { class: "avatar", "aria-hidden": "true" }, icone("marcadorCheio")),
        el("span", { class: "meio" }, el("span", { class: "nome", style: "display:block" }, f.nome || f.ean), status),
        el("span", { class: "valor" }, agora != null ? brl.format(agora) : "—"),
        icone("seta")));
    }))),
  ];
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
  const [tabela, aberto] = await Promise.all([impostos(), produtoAberto(ean)]);
  if (!p) {
    await telaNaoAcompanhado(ean, aberto, tabela);
    return;
  }
  recentes.guardar(p);
  favoritos.visto(p);
  document.title = `${p.nome || ean} · Preço com Prova`;
  const com = await comunidade();
  const [votos, evidencias] = await Promise.all([com.votos(ean).catch(() => []), com.evidenciasPublicas(ean).catch(() => [])]);
  const contexto = { p, votos, evidencias, ean };
  contexto.atualizar = async (chaveAberta) => {
    contexto.votos = await com.votos(ean).catch(() => contexto.votos);
    document.querySelector('[data-cartao="onde"]')?.replaceWith(cartaoOndeComprar(contexto));
    document.querySelector('[data-cartao="causas"]')?.replaceWith(cartaoCausas(contexto, chaveAberta));
  };
  conteudo.replaceChildren(heroProduto(p, aberto?.foto), el("div", { class: "folha" },
    cartaoOndeComprar(contexto),
    cartaoHistorico(p),
    cartaoCompraDF(p),
    cartaoCausas(contexto),
    cartaoImpostos(tabela, [p.nome, aberto?.nome], p.ofertas[0]?.preco ?? null),
    cartaoReportar(ean),
    el("p", { class: "rodape-nota" }, p.aviso, ` Atualizado ${idade(p.atualizado_em)}.`)));
}

function cartaoReportar(ean) {
  return el("section", { class: "cartao reportar" },
    el("div", { class: "passo" }, el("span", { class: "icone-passo" }, icone("bandeira")),
      el("div", {}, el("strong", {}, "Encontrou algum erro?"),
        el("span", {}, "Avise a gente. Lojas e fabricantes também podem contestar uma informação por aqui."))),
    el("button", { class: "botao-secundario-neutro", type: "button", onclick: () => abrirReporte(ean) }, "Reportar um problema"));
}

async function abrirReporte(ean = null, tipoInicial = null) {
  const contato = (await config()).contato;
  let tipo = tipoInicial;
  const opcoes = el("div", { class: "opcoes-reporte", role: "radiogroup", "aria-label": "Tipo de problema" },
    Object.entries(TIPOS_REPORTE).map(([chave, texto]) => {
      const radio = el("input", { type: "radio", name: "tipo-reporte", value: chave, checked: chave === tipoInicial,
        onchange: () => { tipo = chave; dicaLink.hidden = chave !== "contestacao_loja"; } });
      return el("label", { class: "opcao" }, radio, el("span", {}, texto));
    }));
  const descricao = el("textarea", { class: "campo-texto", rows: 3, maxlength: 1000, placeholder: "O que está errado? Ex.: na loja o preço é R$ 23,90.", "aria-label": "Descrição do problema" });
  const link = el("input", { class: "campo-texto", type: "url", placeholder: "Link que comprove (opcional)", "aria-label": "Link que comprove" });
  const dicaLink = el("p", { class: "minusculo", hidden: tipoInicial !== "contestacao_loja" }, "Para contestar, inclua um link ou documento público que sustente a correção.");
  const email = el("input", { class: "campo-texto", type: "email", placeholder: "Seu e-mail, se quiser resposta (opcional)", "aria-label": "E-mail para resposta", autocomplete: "email" });
  const fechar = abrirFolha("Reportar um problema",
    opcoes, descricao, link, dicaLink, email,
    el("p", { class: "minusculo" }, "Não é preciso ter conta. O e-mail é opcional, serve só para responder e é apagado quando o caso for resolvido (no máximo em 12 meses)."),
    el("button", { class: "botao-principal", type: "button", onclick: async () => {
      try {
        await (await comunidade()).reportar({ ean, tipo, descricao: descricao.value, link: link.value.trim() || null, contato: email.value });
        fechar();
        avisar("Recebemos. Obrigado por ajudar a corrigir.");
      } catch (e) { avisar(e instanceof ErroComunidade ? e.message : "Não deu certo agora."); }
    } }, "Enviar"),
    contato ? el("p", { class: "minusculo", style: "text-align:center" }, "Ou escreva para ", el("a", { href: `mailto:${contato}` }, contato)) : null);
}

async function telaNaoAcompanhado(ean, aberto, tabela) {
  const nome = aberto?.nome;
  const subtitulo = [aberto?.marca, aberto?.quantidade].filter(Boolean).join(" · ");
  conteudo.replaceChildren(
    el("header", { class: "hero" },
      el("div", { class: "hero-barra" },
        el("button", { class: "botao-redondo", type: "button", "aria-label": "Voltar", onclick: voltar }, icone("voltar"))),
      el("div", { class: "produto-topo entrar" },
        aberto?.foto ? el("img", { class: "foto-produto", src: aberto.foto, alt: "" }) : null,
        el("h1", { class: "produto-nome" }, nome || "Produto não identificado", el("small", {}, subtitulo || `Código ${ean}`),
          aberto?.foto || aberto?.nome ? creditoFoto(ean) : null)),
      el("p", { class: "rotulo entrar" }, "Ainda não acompanhamos o preço deste produto"),
      el("p", { class: "onde entrar" }, "A lista de produtos cresce a cada coleta.")),
    el("div", { class: "folha" },
      nome ? cartaoImpostos(tabela, [nome], null) : el("section", { class: "cartao entrar" },
        el("h2", {}, "Não reconhecemos este código"),
        el("p", { class: "sub", style: "margin:0" }, "Ele não está na nossa lista nem na base aberta de produtos. Confira se o código foi lido certo.")),
      el("section", { class: "cartao entrar entrar-2" },
        el("button", { class: "botao-escanear-grande botao-marca", type: "button", onclick: abrirLeitor }, icone("escanear"), "Escanear outro produto"))));
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

function heroProduto(p, foto) {
  const melhor = p.ofertas[0];
  const subtitulo = [p.marca, p.quantidade].filter(Boolean).join(" · ");
  const economia = p.ofertas.length > 1 ? p.ofertas[p.ofertas.length - 1].preco - melhor.preco : 0;
  const tend = tendencia(p);
  return el("header", { class: "hero" },
    el("div", { class: "hero-barra" },
      el("button", { class: "botao-redondo", type: "button", "aria-label": "Voltar", onclick: voltar }, icone("voltar")),
      el("span", { class: "acoes-hero" },
        botaoFavorito(p),
        el("button", { class: "botao-redondo", type: "button", "aria-label": "Compartilhar", onclick: () => compartilhar(p) }, icone("compartilhar")))),
    el("div", { class: "produto-topo entrar" },
      foto ? el("img", { class: "foto-produto", src: foto, alt: "" }) : null,
      el("h1", { class: "produto-nome" }, p.nome || "Produto sem nome", subtitulo ? el("small", {}, subtitulo) : null,
        foto ? creditoFoto(p.ean) : null)),
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

// licença das fotos e dados do Open Food Facts: CC BY-SA (fotos) e ODbL (dados), com crédito obrigatório
function creditoFoto(ean) {
  return el("a", { class: "credito", href: `https://world.openfoodfacts.org/product/${ean}`, target: "_blank", rel: "noopener" },
    "Foto e dados: Open Food Facts (CC BY-SA / ODbL)");
}

function botaoFavorito(p) {
  const botao = el("button", { class: "botao-redondo", type: "button" });
  const desenhar = () => {
    const ativo = favoritos.tem(p.ean);
    botao.setAttribute("aria-pressed", String(ativo));
    botao.setAttribute("aria-label", ativo ? "Deixar de acompanhar" : "Acompanhar este produto");
    botao.replaceChildren(icone(ativo ? "marcadorCheio" : "marcador"));
  };
  botao.addEventListener("click", () => {
    const ativo = favoritos.alternar(p);
    desenhar();
    avisar(ativo ? "Pronto! Vamos avisar na tela inicial quando o preço mudar." : "Você deixou de acompanhar este produto.");
  });
  desenhar();
  return botao;
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

function linhaConfianca(p, o, votos, atualizar) {
  const meus = votos.filter((v) => v.alvo === "preco" && v.chave === chavePreco(o));
  const c = confiancaPreco({ fonte: o.fonte, data: o.data }, meus);
  const sugerido = precoSugerido(meus);
  const partes = [c.rotulo];
  if (c.confirmacoes) partes.push(c.confirmacoes === 1 ? "1 pessoa confirmou" : `${c.confirmacoes} confirmaram`);
  if (c.contestacoes) partes.push(c.contestacoes === 1 ? "1 pessoa contestou" : `${c.contestacoes} contestaram`);
  return el("div", { class: "confianca" },
    el("div", { class: "confianca-linha" },
      estrelas(c.estrelas, `Confiança da comunidade: ${String(c.estrelas).replace(".", ",")} de 5`),
      el("span", {}, partes.join(" · "))),
    sugerido ? el("div", { class: "sugerido" }, `${sugerido.informantes} pessoas informaram ${brl.format(sugerido.preco)}`) : null,
    el("button", { class: "botao-pilula", type: "button", onclick: () => confirmarPreco(p, o, atualizar) }, "Está certo?"));
}

function confirmarPreco(p, o, atualizar) {
  const chave = chavePreco(o);
  const enviar = async (valor, preco = null) => {
    fechar();
    if (await contribuir((com) => com.votar({ ean: p.ean, alvo: "preco", chave, valor, preco_informado: preco }))) await atualizar();
  };
  const entrada = el("input", { inputmode: "decimal", placeholder: "0,00", "aria-label": "Preço que você viu, em reais" });
  const correcao = el("div", { class: "correcao", hidden: true },
    el("label", { class: "campo-preco" }, el("span", {}, "Qual preço você viu?"), el("span", { class: "entrada" }, "R$ ", entrada)),
    el("button", { class: "botao-principal", type: "button", onclick: () => {
      const n = parseFloat(entrada.value.replace(/\./g, "").replace(",", "."));
      enviar(false, Number.isFinite(n) ? n : null);
    } }, "Enviar correção"),
    el("button", { class: "botao-texto", type: "button", onclick: () => enviar(false) }, "Está diferente, mas não sei o valor"));
  const fechar = abrirFolha("Confirme o preço",
    el("p", { class: "texto-folha" }, `${p.nome || "Este produto"} em ${o.loja} está custando `, el("strong", {}, brl.format(o.preco)), "?"),
    el("p", { class: "minusculo" }, "Responda só se você viu o preço hoje, na loja ou no site."),
    el("div", { class: "botoes-lado" },
      el("button", { class: "botao-principal", type: "button", onclick: () => enviar(true) }, icone("polegarCima"), "Sim, está certo"),
      el("button", { class: "botao-secundario-neutro", type: "button", onclick: () => { correcao.hidden = false; entrada.focus(); } },
        icone("polegarBaixo"), "Não, está diferente")),
    correcao);
}

function cartaoOndeComprar({ p, votos, atualizar }) {
  const cartao = el("section", { class: "cartao", "data-cartao": "onde" }, el("h2", {}, "Onde comprar"));
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
          : `+${brl.format(o.diferenca_rs)}`))),
    linhaConfianca(p, o, votos, atualizar)))));
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
  if (p.qualidade?.ocultos) {
    cartao.append(el("p", { class: "minusculo", style: "margin:8px 0 0" },
      `${p.qualidade.ocultos} preço${p.qualidade.ocultos > 1 ? "s" : ""} com sinal de erro (valor absurdo ou pico que voltou logo) ${p.qualidade.ocultos > 1 ? "foram ocultados" : "foi ocultado"} pela checagem de qualidade.`));
  }

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

// ---------- preço de compra no DF (NF-e entre empresas, Mapa de Preços do DF) ----------

const UNIDADE_SIMPLES = /^(un|und|unid|unidade|pc|pç|peça|peca)\b/i;

function cartaoCompraDF(p) {
  const c = p.compra_df;
  if (!c || !c.serie?.length) return null;
  const cartao = el("section", { class: "cartao entrar entrar-3" }, el("h2", {}, "Preço de compra no DF"));
  const ultimo = c.serie[c.serie.length - 1];
  const t = c.tendencia || {};
  cartao.append(el("p", { class: "sub" }, `Quanto o comércio pagou, por ${c.unidade.toLowerCase()}: mediana das notas fiscais entre empresas.`));
  cartao.append(el("div", { class: "loja-linha" },
    el("div", { class: "meio" },
      el("div", { class: "nome" }, "Último dia com notas"),
      el("div", { class: "detalhe" }, `${dataBR(ultimo.data)} · ${ultimo.itens} ${ultimo.itens === 1 ? "item de nota" : "itens de notas"}`)),
    el("div", { class: "direita" }, el("div", { class: "valor" }, brl.format(ultimo.mediana)))));

  if (t.variacao_pct != null) {
    const sobe = t.variacao_pct >= 2, cai = t.variacao_pct <= -2;
    const v = `${t.variacao_pct > 0 ? "+" : ""}${String(t.variacao_pct).replace(".", ",")}%`;
    cartao.append(el("p", { class: "texto-folha", style: "margin:12px 0 0" },
      el("strong", {}, sobe ? `Custo subindo: ${v} em 7 dias.` : cai ? `Custo caindo: ${v} em 7 dias.` : `Custo estável (${v} em 7 dias).`),
      sobe ? " Quando o custo de compra sobe, a prateleira costuma subir depois. Não é certeza." :
      cai ? " Se a queda se mantiver, pode abrir espaço para o preço da prateleira cair. Não é certeza." : ""));
  } else if (t.nota) {
    cartao.append(el("p", { class: "minusculo", style: "margin:12px 0 0" }, `Tendência de 7 dias: ${t.nota}.`));
  }

  const prateleira = p.ofertas[0];
  if (prateleira && UNIDADE_SIMPLES.test(c.unidade) && ultimo.mediana > 0) {
    const dif = (prateleira.preco / ultimo.mediana - 1) * 100;
    cartao.append(el("p", { class: "minusculo", style: "margin:8px 0 0" },
      `Na prateleira hoje: ${brl.format(prateleira.preco)} em ${prateleira.loja} (${dif >= 0 ? "+" : ""}${dif.toFixed(0).replace(".", ",")}% sobre a mediana de compra). ` +
      "A diferença inclui frete, perdas, impostos e margem; não é só lucro."));
  }

  if (c.serie.length >= 2) {
    const caixa = el("div", { class: "grafico" });
    const pts = c.serie.filter((d) => d.mediana > 0).map((d) => ({ data: d.data, preco: d.mediana, t: dia(d.data).getTime() }));
    const serie = [{ loja: "Mediana de compra", cor: "var(--serie-2)", pts }];
    cartao.append(caixa);
    let largura = 0;
    new ResizeObserver(([e]) => {
      const w = Math.floor(e.contentRect.width);
      if (w > 0 && w !== largura) { largura = w; grafico(caixa, serie, pts[0].t, pts[pts.length - 1].t); }
    }).observe(caixa);
  }
  cartao.append(el("p", { class: "minusculo", style: "margin:10px 0 0" }, c.aviso, " ",
    el("a", { href: c.evidencia, target: "_blank", rel: "noopener" }, "Ver o painel oficial")));
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
      if (h.ancora || serie.pts.length > 40) continue; // série diária longa: só a linha
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

function cartaoCausas({ p, votos, evidencias = [], atualizar }, chaveAberta = null) {
  const cartao = el("section", { class: "cartao", "data-cartao": "causas" }, el("h2", {}, "Por que o preço mudou"));
  if (!p.mudancas.length) {
    cartao.append(el("div", { class: "vazio-curto" }, "Nenhuma mudança de preço registrada ainda."));
    return cartao;
  }
  cartao.append(el("p", { class: "sub" }, "Toque numa mudança para ver as provas."));
  // evidências enviadas pela comunidade e aceitas pela moderação entram junto, sempre com o nível dado na moderação
  const daComunidade = (m) => evidencias.filter((e) => e.chave === chaveCausa(m)).map((e) => ({
    nivel: e.nivel, tipo: "comunidade", descricao: e.descricao || "Evidência enviada pela comunidade.", fontes: [e.url], comunidade: true,
  }));
  const comEvidencias = p.mudancas.map((m) => ({ ...m, evidencias: [...m.evidencias, ...daComunidade(m)] }));
  const aberta = comEvidencias.slice(0, 8).findIndex((m) => m.evidencias.length);
  comEvidencias.slice(0, 8).forEach((m, i) => {
    const sobe = m.variacao_pct > 0;
    const provas = m.evidencias.map((e) => {
      const fontes = e.fontes.slice(0, 2);
      const mesmoSite = fontes.length === 2 && host(fontes[0]) === host(fontes[1]);
      return el("li", { class: "prova" },
        seloNivel(e.nivel),
        e.comunidade ? el("span", { class: "selo-comunidade" }, "enviada pela comunidade e conferida") : null,
        el("div", {}, e.descricao),
        fontes.length ? el("div", { class: "fontes" }, fontes.map((f, j) => f.startsWith("http")
          ? el("a", { href: f, target: "_blank", rel: "noopener" }, icone("fonte"), mesmoSite ? ["Fonte antes", "Fonte depois"][j] : host(f))
          : el("span", { class: "minusculo" }, f))) : null);
    });
    const chave = chaveCausa(m);
    cartao.append(el("details", { class: "mudanca", open: chaveAberta ? chave === chaveAberta : i === aberta },
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
        : null,
      blocoComunidadeCausa(p, chave, votos.filter((v) => v.alvo === "causa" && v.chave === chave), atualizar)));
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

function blocoComunidadeCausa(p, chave, votosCausa, atualizar) {
  const u = utilidade(votosCausa);
  const avaliar = async (valor) => {
    if (await contribuir((com) => com.votar({ ean: p.ean, alvo: "causa", chave, valor }))) await atualizar(chave);
  };
  return el("div", { class: "comunidade-causa" },
    el("div", { class: "pergunta" },
      el("span", {}, "Essa explicação ajudou?"),
      el("span", { class: "botoes-voto" },
        el("button", { class: "voto", type: "button", "aria-label": "Sim, ajudou", onclick: () => avaliar(true) }, icone("polegarCima")),
        el("button", { class: "voto", type: "button", "aria-label": "Não ajudou", onclick: () => avaliar(false) }, icone("polegarBaixo")))),
    u.total ? el("p", { class: "minusculo", style: "margin:4px 0 0" },
      `${u.total === 1 ? (u.uteis ? "1 pessoa achou útil" : "1 pessoa não achou útil") : `${u.uteis} de ${u.total} pessoas acharam útil`}. Opinião não muda o nível de prova.`)
      : el("p", { class: "minusculo", style: "margin:4px 0 0" }, "A opinião da comunidade não muda o nível de prova."),
    el("button", { class: "botao-texto alinhado", type: "button", onclick: () => sugerirEvidencia(p, chave) }, icone("documento"), "Tenho uma evidência"));
}

function sugerirEvidencia(p, chave) {
  const url = el("input", { type: "url", placeholder: "https://", "aria-label": "Link da evidência", class: "campo-texto" });
  const descricao = el("textarea", { rows: 3, maxlength: 500, placeholder: "O que esse link mostra? (opcional)", "aria-label": "Descrição", class: "campo-texto" });
  const fechar = abrirFolha("Enviar uma evidência",
    el("p", { class: "texto-folha" }, "Uma notícia, um comunicado do fabricante, uma lei ou um dado oficial que ajude a explicar esta mudança de preço."),
    url, descricao,
    el("p", { class: "minusculo" }, "Vamos conferir antes de publicar. Não envie dados pessoais nem acusações sem fonte."),
    el("button", { class: "botao-principal", type: "button", onclick: async () => {
      if (await contribuir((com) => com.sugerirEvidencia({ ean: p.ean, chave, url: url.value.trim(), descricao: descricao.value.trim() }))) fechar();
    } }, "Enviar para conferência"));
}

function cartaoImpostos(tabela, nomes, precoInicial) {
  const cartao = el("section", { class: "cartao entrar entrar-4" });
  const cabecalho = el("div", { class: "cabecalho-impostos" },
    el("h2", {}, "Impostos no preço"), el("span", { class: "selo-breve" }, "ESTIMATIVA"));
  const seloConferido = (cat) => {
    if (!cat.conferencia?.conferido_em) return;
    cabecalho.querySelector(".selo-breve").replaceWith(el("span", { class: "selo-breve conferido" }, "LEI CONFERIDA"));
  };
  if (!tabela) {
    cartao.append(cabecalho, el("p", { class: "sub", style: "margin:0" }, "Não foi possível carregar a tabela de impostos agora."));
    return cartao;
  }
  const cat = categoria(tabela, ...nomes);
  if (!cat) {
    cartao.append(cabecalho, el("p", { class: "sub", style: "margin:0" },
      "Ainda não sabemos classificar este produto para estimar os impostos. Por enquanto cobrimos itens da cesta básica e de higiene."));
    return cartao;
  }

  seloConferido(cat);
  const resultado = el("div");
  const desenhar = (preco) => {
    if (!(preco > 0)) {
      resultado.replaceChildren(el("p", { class: "sub", style: "margin:0" }, "Informe o preço para ver quanto dele é imposto."));
      return;
    }
    const r = calcular(tabela, cat, preco);
    const fatia = (v) => `${Math.max(0, Math.min(100, (v / preco) * 100))}%`;
    const reformaTexto = r.reforma.regime === "zero"
      ? "Cesta básica nacional: IBS e CBS com alíquota zero."
      : `${r.reforma.regime === "reduzida_60" ? "Redução de 60%: " : ""}IBS + CBS de ${pct(r.reforma.aliquota, false)} sobre o preço sem imposto.`;
    resultado.replaceChildren(
      el("div", { class: "imposto-total" },
        el("span", { class: "valor" }, `≈ ${brl.format(r.total)}`),
        el("span", { class: "sub", style: "margin:0" }, `${pct(r.percentual, false)} de ${brl.format(preco)} são impostos na venda`)),
      el("div", { class: "barra-imposto", role: "img", "aria-label": `ICMS ${brl.format(r.icms.valor)}, PIS/Cofins ${brl.format(r.pisCofins.valor)}` },
        el("span", { class: "fatia icms", style: `width:${fatia(r.icms.valor)}` }),
        el("span", { class: "fatia pis", style: `width:${fatia(r.pisCofins.valor)}` })),
      el("ul", { class: "linhas-imposto" },
        el("li", {}, el("span", { class: "amostra icms" }),
          el("span", { class: "meio" }, el("strong", {}, "ICMS (DF)"),
            el("span", { class: "detalhe" }, r.icms.regra === "cesta" ? `carga de ${pct(r.icms.carga, false)} (cesta básica)` : `alíquota geral de ${pct(r.icms.carga, false)}`)),
          el("span", { class: "valor" }, brl.format(r.icms.valor))),
        el("li", {}, el("span", { class: "amostra pis" }),
          el("span", { class: "meio" }, el("strong", {}, "PIS/Cofins (federal)"),
            el("span", { class: "detalhe" }, r.pisCofins.aliquota === 0 ? "zerado por lei para este produto" : `${pct(r.pisCofins.aliquota, false)} sobre o preço sem ICMS`)),
          el("span", { class: "valor" }, brl.format(r.pisCofins.valor)))),
      el("div", { class: "reforma" },
        el("strong", {}, `Com a Reforma Tributária (${r.reforma.ano})`),
        el("p", {}, reformaTexto, " ",
          r.reforma.valor > 0.004
            ? `No mesmo preço final, seriam ≈ ${brl.format(r.reforma.valor)} (${pct(r.reforma.percentual, false)}).`
            : "O imposto na venda cairia para zero."),
        el("p", { class: "minusculo", style: "margin:4px 0 0" }, "A alíquota oficial da Reforma ainda não foi definida; usamos 26,5%, a estimativa da regulamentação.")));
  };

  let preco = precoInicial;
  const entradaPreco = precoInicial == null ? el("label", { class: "campo-preco" },
    el("span", {}, "Quanto custa aí?"),
    el("span", { class: "entrada" }, "R$ ",
      el("input", { inputmode: "decimal", placeholder: "0,00", "aria-label": "Preço do produto em reais",
        oninput: (ev) => { preco = parseFloat(ev.target.value.replace(/\./g, "").replace(",", ".")); desenhar(preco); } }))) : null;

  cartao.append(...[cabecalho,
    el("p", { class: "sub" }, `Categoria: ${cat.nome}. ${precoInicial != null ? "Calculado sobre o menor preço de hoje." : ""}`),
    entradaPreco, resultado,
    cat.pendente ? el("p", { class: "pendente" }, icone("duvida"), el("span", {}, `A confirmar: ${cat.pendente}`)) : null,
    cat.conferencia?.conferido_em
      ? el("p", { class: "conferida" }, icone("escudo"), el("span", {}, `Leis desta categoria conferidas no texto oficial em ${dataBR(cat.conferencia.conferido_em)}.`))
      : null,
    el("details", { class: "expansivel" },
      el("summary", {}, "Leis usadas no cálculo", icone("seta")),
      el("ul", { class: "fontes-lei" }, calcularFontes(tabela, cat).map((id) => {
        const f = tabela.fontes[id];
        return el("li", {}, f.url ? el("a", { href: f.url, target: "_blank", rel: "noopener" }, f.titulo) : f.titulo);
      })),
      el("p", { class: "minusculo" }, tabela.aviso))].filter(Boolean));
  desenhar(preco);
  return cartao;
}

function calcularFontes(tabela, cat) {
  return calcular(tabela, cat, 1).fontes;
}

// ---------- sobre e privacidade ----------

function telaSobre() {
  const apagar = async () => {
    try { localStorage.removeItem("recentes"); localStorage.removeItem("favoritos"); } catch { /* nada salvo */ }
    try { await (await comunidade()).apagarTudo(); } catch { /* sem conexão: tente de novo */ }
    avisar("Pronto. Apagamos seus dados e suas contribuições.");
  };
  const bloco = (nomeIcone, titulo, ...texto) => el("section", { class: "cartao entrar" },
    el("div", { class: "passo" }, el("span", { class: "icone-passo" }, icone(nomeIcone)),
      el("div", {}, el("strong", { style: "font-size:17px" }, titulo), ...texto.map((t) => el("p", { class: "texto-sobre" }, t)))));
  conteudo.replaceChildren(
    el("header", { class: "hero" },
      el("div", { class: "hero-barra" },
        el("button", { class: "botao-redondo", type: "button", "aria-label": "Voltar", onclick: voltar }, icone("voltar"))),
      el("h1", {}, "Sobre o Preço com Prova"),
      el("p", {}, "Preços com fonte, histórico real e causas separadas por nível de prova.")),
    el("div", { class: "folha" },
      bloco("fonte", "De onde vêm os preços",
        "De páginas públicas de supermercados, de cópias antigas guardadas pelo Internet Archive e de bases abertas como o Open Prices. Cada preço tem o link de onde veio.",
        "Preços online podem ser diferentes dos da loja física."),
      bloco("escudo", "Como lemos as causas",
        "Só chamamos de comprovado o que é fato documentado e com efeito calculável, como uma lei de imposto ou uma embalagem que encolheu. O resto aparece como contexto, sem afirmar a causa, e nunca acusamos nenhuma loja."),
      bloco("cadeado", "Sua privacidade",
        "Não há cadastro nem conta. A câmera funciona só no seu aparelho: nenhuma imagem é enviada.",
        "Os produtos que você viu e os que acompanha ficam guardados só neste aparelho.",
        "Para mostrar nome e foto, o aparelho consulta o código do produto na base aberta Open Food Facts. No iPhone, o leitor de código é baixado do serviço jsDelivr."),
      bloco("documento", "Licenças e créditos",
        "Nomes e fotos de produtos: Open Food Facts (dados ODbL, fotos CC BY-SA). Preços colaborativos: Open Prices (ODbL). Cópias antigas de páginas: Internet Archive. Índices: IBGE e Banco Central. Notícias: GDELT. Marcas pertencem aos seus titulares."),
      el("section", { class: "cartao entrar lista-links" },
        el("a", { href: "#/termos" }, icone("documento"), "Termos de uso", icone("seta")),
        el("a", { href: "#/privacidade" }, icone("cadeado"), "Política de privacidade", icone("seta")),
        el("a", { href: "#/", onclick: (ev) => { ev.preventDefault(); abrirReporte(); } }, icone("bandeira"), "Reportar um problema ou contestar", icone("seta"))),
      el("section", { class: "cartao entrar" },
        el("button", { class: "botao-secundario", type: "button", onclick: apagar }, icone("lixeira"), "Apagar meus dados e contribuições")),
      el("p", { class: "rodape-nota" }, "Projeto em teste. Os números são estimativas com fonte; confira sempre o link.")));
}

// ---------- perfil e ranking ----------

async function telaPerfil() {
  const com = await comunidade();
  const perfil = await com.perfil().catch(() => ({ apelido: null, pontos: 0 }));
  const n = nivelPorPontos(perfil.pontos);
  const ranking = await com.ranking().catch(() => null);

  const apelido = el("input", { class: "campo-texto", value: perfil.apelido || "", maxlength: 24, placeholder: "Ex.: Maria do Guará", "aria-label": "Apelido" });
  const salvarApelido = async () => {
    if (!(await garantirConsentimento())) return;
    try { await com.definirApelido(apelido.value); avisar("Apelido salvo."); }
    catch (e) { avisar(e instanceof ErroComunidade ? e.message : "Não deu certo agora."); }
  };
  const apagar = async () => {
    await com.apagarTudo().catch(() => {});
    avisar("Pronto. Suas contribuições e seus pontos foram apagados.");
    telaPerfil();
  };

  conteudo.replaceChildren(
    el("header", { class: "hero" },
      el("div", { class: "hero-barra" },
        el("button", { class: "botao-redondo", type: "button", "aria-label": "Voltar", onclick: voltar }, icone("voltar"))),
      el("p", { class: "rotulo" }, perfil.apelido || "Seu perfil"),
      el("h1", {}, n.nome),
      el("div", { class: "nivel-estrelas" }, estrelas(n.nivel, `Nível ${n.nivel} de 5`), el("span", {}, `${perfil.pontos} pontos`)),
      el("div", { class: "progresso", role: "progressbar", "aria-label": "Progresso até o próximo nível", "aria-valuemin": 0, "aria-valuemax": 100, "aria-valuenow": Math.round(n.progresso * 100) },
        el("span", { style: `width:${n.progresso * 100}%` })),
      el("p", {}, n.proximo ? `Faltam ${n.proximo.min - perfil.pontos} pontos para ${n.proximo.nome}.` : "Você chegou ao nível mais alto.")),
    el("div", { class: "folha" },
      com.modo === "teste" ? el("p", { class: "faixa-teste cartao" }, "Modo de teste: a comunidade ainda não está ligada. Seus pontos e contribuições ficam só neste aparelho.") : null,
      el("section", { class: "cartao entrar" },
        el("h2", {}, "Como ganhar pontos"),
        el("ul", { class: "lista-pontos" },
          el("li", {}, el("span", {}, "Confirmar um preço que você viu"), el("strong", {}, `+${PONTOS.confirmar}`)),
          el("li", {}, el("span", {}, "Corrigir um preço informando o valor"), el("strong", {}, `+${PONTOS.corrigir}`)),
          el("li", {}, el("span", {}, "Dizer se uma explicação ajudou"), el("strong", {}, `+${PONTOS.avaliar_causa}`)),
          el("li", {}, el("span", {}, "Evidência aceita depois da conferência"), el("strong", {}, `+${PONTOS.evidencia}`))),
        el("p", { class: "minusculo" }, "Quanto maior o nível, mais o seu voto pesa. Pontos não valem dinheiro, prêmios nem descontos.")),
      el("section", { class: "cartao entrar entrar-2" },
        el("h2", {}, "Níveis"),
        el("ul", { class: "lista-pontos" }, NIVEIS_COMUNIDADE.map((x) => el("li", { class: x.nivel === n.nivel ? "atual" : null },
          el("span", {}, estrelas(x.nivel, `Nível ${x.nivel}`), ` ${x.nome}`), el("strong", {}, `${x.min}+`))))),
      el("section", { class: "cartao entrar entrar-3" },
        el("h2", {}, "Ranking"),
        ranking && ranking.length
          ? el("ol", { class: "ranking" }, ranking.map((r) => el("li", {}, el("span", {}, r.apelido), el("strong", {}, `${r.pontos} pts`))))
          : el("p", { class: "sub", style: "margin:0" }, com.modo === "teste" ? "O ranking aparece quando a comunidade estiver ligada." : "Ainda não há ninguém no ranking."),
        el("label", { class: "rotulo-campo" }, "Seu apelido no ranking (opcional)"),
        el("div", { class: "linha-campo" }, apelido, el("button", { class: "botao-principal compacto", type: "button", onclick: salvarApelido }, "Salvar")),
        el("p", { class: "minusculo" }, "Sem apelido, você não aparece no ranking.")),
      el("section", { class: "cartao entrar entrar-4" },
        el("button", { class: "botao-secundario", type: "button", onclick: apagar }, icone("lixeira"), "Apagar minhas contribuições e pontos")),
      el("p", { class: "rodape-nota" }, el("a", { href: "#/moderar", class: "link-discreto" }, "Área de moderação"))));
}

// ---------- moderação ----------

// "Loja B|2023-05-20|2024-04-11" -> "mudança na Loja B de mai/23 a abr/24"
function descreverChave(chave) {
  const [loja, de, ate] = chave.split("|");
  return de && ate ? `mudança em ${loja}, de ${mesAno(de)} a ${mesAno(ate)}` : chave.replaceAll("|", " · ");
}

async function telaModeracao() {
  const com = await comunidade();
  const [moderador, meuId] = await Promise.all([com.souModerador().catch(() => false), com.meuId().catch(() => null)]);
  const corpo = el("div", { class: "folha" });
  conteudo.replaceChildren(
    el("header", { class: "hero" },
      el("div", { class: "hero-barra" },
        el("button", { class: "botao-redondo", type: "button", "aria-label": "Voltar", onclick: voltar }, icone("voltar"))),
      el("h1", {}, "Moderação"),
      el("p", {}, "Confira evidências e reportes antes que apareçam no app.")),
    corpo);

  if (!moderador) {
    corpo.append(el("section", { class: "cartao" },
      el("h2", {}, "Acesso restrito"),
      el("p", { class: "sub" }, "Esta área é só para quem modera. Para liberar este aparelho, quem administra o banco de dados roda:"),
      el("pre", { class: "codigo" }, `insert into public.moderadores (id) values ('${meuId || "faça uma contribuição primeiro para gerar seu id"}');`)));
    return;
  }
  if (com.modo === "teste") corpo.append(el("p", { class: "faixa-teste cartao" }, "Modo de teste: a fila mostra só o que foi enviado deste aparelho."));

  const desenhar = async () => {
    const fila = await com.filaModeracao().catch(() => ({ evidencias: [], reportes: [] }));
    const decidir = async (fn) => {
      try { await fn(); avisar("Decisão salva."); desenhar(); }
      catch (e) { avisar(e instanceof ErroComunidade ? e.message : "Não deu certo agora."); }
    };
    const blocoEvidencias = el("section", { class: "cartao" }, el("h2", {}, `Evidências (${fila.evidencias.length})`),
      fila.evidencias.length ? null : el("p", { class: "sub", style: "margin:0" }, "Nada pendente."),
      fila.evidencias.map((e) => {
        const motivo = el("input", { class: "campo-texto", placeholder: "Motivo (opcional, ajuda na recusa)", "aria-label": "Motivo" });
        return el("div", { class: "item-moderacao" },
          el("div", { class: "minusculo" }, `Produto ${e.ean} · ${descreverChave(e.chave)} · enviada em ${dataBR(e.criado_em)}`),
          el("a", { href: e.url, target: "_blank", rel: "noopener", class: "link-moderacao" }, icone("fonte"), host(e.url)),
          e.descricao ? el("p", { class: "texto-folha" }, e.descricao) : null,
          el("p", { class: "minusculo" }, "Abra o link e confira. Aceite só se a fonte for pública e sustentar o que diz; nunca aceite acusação sem prova."),
          motivo,
          el("div", { class: "botoes-moderacao" },
            el("button", { class: "botao-principal compacto", type: "button",
              onclick: () => decidir(() => com.moderarEvidencia(e.id, { status: "aceita", nivel: "DECLARADO", motivo: motivo.value })) }, "Aceitar: declarado"),
            el("button", { class: "botao-secundario-neutro compacto", type: "button",
              onclick: () => decidir(() => com.moderarEvidencia(e.id, { status: "aceita", nivel: "ASSOCIADO", motivo: motivo.value })) }, "Aceitar: associado"),
            el("button", { class: "botao-texto", type: "button",
              onclick: () => decidir(() => com.moderarEvidencia(e.id, { status: "recusada", motivo: motivo.value })) }, "Recusar")));
      }));
    const blocoReportes = el("section", { class: "cartao" }, el("h2", {}, `Reportes (${fila.reportes.length})`),
      fila.reportes.length ? null : el("p", { class: "sub", style: "margin:0" }, "Nada em aberto."),
      fila.reportes.map((r) => {
        const resposta = el("textarea", { class: "campo-texto", rows: 2, placeholder: "Resposta ou anotação (opcional)", "aria-label": "Resposta" });
        return el("div", { class: "item-moderacao" },
          el("div", { class: "minusculo" }, `${TIPOS_REPORTE[r.tipo] || r.tipo}${r.ean ? ` · produto ${r.ean}` : ""} · ${dataBR(r.criado_em)}`),
          el("p", { class: "texto-folha" }, r.descricao),
          r.link ? el("a", { href: r.link, target: "_blank", rel: "noopener", class: "link-moderacao" }, icone("fonte"), host(r.link)) : null,
          r.contato ? el("p", { class: "minusculo" }, `Responder para: ${r.contato}`) : null,
          resposta,
          el("div", { class: "botoes-moderacao" },
            el("button", { class: "botao-principal compacto", type: "button",
              onclick: () => decidir(() => com.responderReporte(r.id, { status: "resolvido", resposta: resposta.value })) }, "Resolvido"),
            el("button", { class: "botao-texto", type: "button",
              onclick: () => decidir(() => com.responderReporte(r.id, { status: "descartado", resposta: resposta.value })) }, "Descartar")));
      }));
    corpo.querySelectorAll(".cartao:not(.faixa-teste)").forEach((n) => n.remove());
    corpo.append(blocoEvidencias, blocoReportes);
  };
  await desenhar();
}

async function telaLegal(arquivo, titulo) {
  const corpo = el("div", { class: "texto-legal" }, el("p", { class: "carregando" }, "Carregando…"));
  conteudo.replaceChildren(
    el("header", { class: "hero" },
      el("div", { class: "hero-barra" },
        el("button", { class: "botao-redondo", type: "button", "aria-label": "Voltar", onclick: voltar }, icone("voltar"))),
      el("h1", {}, titulo)),
    el("div", { class: "folha" }, el("section", { class: "cartao" }, corpo)));
  try {
    const r = await fetch(`legal/${arquivo}.html`, { cache: "no-cache" });
    if (!r.ok) throw new Error();
    corpo.innerHTML = await r.text(); // arquivo estático do próprio app
  } catch {
    corpo.replaceChildren(el("p", {}, "Não foi possível carregar agora."));
  }
}

// ---------- rotas ----------

async function rotear() {
  fecharLeitor();
  fecharFolhas();
  document.getElementById("aviso-rapido").classList.remove("visivel");
  const hash = location.hash || "#/";
  const produto = hash.match(/^#\/p\/(\d{8,14})$/);
  const lista = hash.match(/^#\/produtos(?:\?q=(.*))?$/);
  document.querySelectorAll(".abas a").forEach((a) =>
    a.classList.toggle("ativa", (a.dataset.aba === "produtos" && !!lista) || (a.dataset.aba === "inicio" && hash === "#/")));
  document.title = "Preço com Prova";
  if (produto) await telaProduto(produto[1]);
  else if (lista) await telaProdutos(decodeURIComponent(lista[1] || ""));
  else if (hash === "#/sobre") telaSobre();
  else if (hash === "#/perfil") await telaPerfil();
  else if (hash === "#/moderar") await telaModeracao();
  else if (hash === "#/termos") await telaLegal("termos", "Termos de uso");
  else if (hash === "#/privacidade") await telaLegal("privacidade", "Política de privacidade");
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
