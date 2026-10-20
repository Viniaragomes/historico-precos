// Guarda o app para abrir sem internet. Dados: tenta a rede primeiro e usa a cópia salva se estiver offline.
const VERSAO = "v7";
const APP = ["./", "index.html", "app.css", "app.js", "impostos.js", "impostos.json", "confianca.js", "comunidade.js", "legal/termos.html", "legal/privacidade.html", "manifest.webmanifest", "icone.svg", "icone-192.png", "icone-512.png"];

self.addEventListener("install", (ev) => {
  ev.waitUntil(caches.open(`app-${VERSAO}`).then((c) => c.addAll(APP)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (ev) => {
  ev.waitUntil(caches.keys()
    .then((nomes) => Promise.all(nomes.filter((n) => !n.endsWith(VERSAO)).map((n) => caches.delete(n))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (ev) => {
  const url = new URL(ev.request.url);
  if (ev.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.includes("/dados/") || url.pathname.endsWith("impostos.json") || url.pathname.endsWith("config.json")) {
    ev.respondWith(fetch(ev.request).then((resp) => {
      if (resp.ok) {
        const copia = resp.clone();
        caches.open(`dados-${VERSAO}`).then((c) => c.put(ev.request, copia));
      }
      return resp;
    }).catch(() => caches.match(ev.request).then((r) => r || new Response("", { status: 503 }))));
    return;
  }
  ev.respondWith(caches.match(ev.request).then((r) => r || fetch(ev.request)));
});
