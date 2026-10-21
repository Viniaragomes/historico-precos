// Guarda o app para abrir sem internet. Com internet, sempre busca a versão mais nova (rede primeiro);
// a cópia salva só é usada quando a rede falha ou demora demais.
const VERSAO = "v26";
const APP = ["./", "index.html", "app.css", "app.js", "impostos.js", "impostos.json", "cepea.json", "confianca.js", "comunidade.js", "legal/termos.html", "legal/privacidade.html", "manifest.webmanifest", "icone.svg", "icone-192.png", "icone-512.png"];

self.addEventListener("install", (ev) => {
  // cache: "reload" ignora a cópia do navegador: assim a versão nova nunca guarda um arquivo antigo
  ev.waitUntil(caches.open(`app-${VERSAO}`)
    .then((c) => c.addAll(APP.map((u) => new Request(u, { cache: "reload" }))))
    .then(() => self.skipWaiting()));
});

self.addEventListener("activate", (ev) => {
  ev.waitUntil(caches.keys()
    .then((nomes) => Promise.all(nomes.filter((n) => !n.endsWith(VERSAO)).map((n) => caches.delete(n))))
    .then(() => self.clients.claim()));
});

function redePrimeiro(req, nomeCache, prazoMs) {
  const daRede = fetch(req, { cache: "no-cache" }).then((resp) => {
    if (resp.ok) {
      const copia = resp.clone();
      caches.open(nomeCache).then((c) => c.put(req, copia));
    }
    return resp;
  });
  const reserva = () => caches.match(req).then((r) => r || daRede);
  if (!prazoMs) return daRede.catch(() => caches.match(req).then((r) => r || new Response("", { status: 503 })));
  // rede lenta: depois do prazo, abre a cópia salva (se houver) para não travar
  return Promise.race([daRede, new Promise((ok) => setTimeout(ok, prazoMs)).then(reserva)]).catch(reserva);
}

self.addEventListener("fetch", (ev) => {
  const url = new URL(ev.request.url);
  if (ev.request.method !== "GET" || url.origin !== location.origin) return;
  const dados = url.pathname.includes("/dados/") || url.pathname.endsWith("impostos.json") || url.pathname.endsWith("config.json");
  ev.respondWith(redePrimeiro(ev.request, dados ? `dados-${VERSAO}` : `app-${VERSAO}`, dados ? 0 : 4000));
});
