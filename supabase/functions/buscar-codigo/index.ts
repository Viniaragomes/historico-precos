// Busca na hora: quando alguém escaneia um código, procura o preço nas lojas com catálogo público (VTEX),
// a partir do servidor do Supabase (região São Paulo). Guarda o resultado por 6 horas para não repetir consultas.
// Regras do projeto: robô identificado, só endereços que o robots.txt libera (a API de catálogo das lojas abaixo foi
// verificada em 21/10/2026), poucas consultas e respeito a "vá mais devagar" (HTTP 429).
//
// Como publicar (sem instalar nada): Supabase > Edge Functions > Deploy a new function > Via Editor,
// nome "buscar-codigo", cole este arquivo e clique em Deploy. Desligue "Verify JWT" (o app chama com a chave pública).

import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.4";

const UA = "HistoricoPrecosBot/0.1 (pesquisa de precos ao consumidor; respeita robots.txt)";
const LOJAS = [
  { nome: "Atacadão", dominio: "www.atacadao.com.br" },
  { nome: "Oba Hortifruti", dominio: "www.obahortifruti.com.br" },
];
const VALIDADE_MS = 6 * 3600 * 1000;
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, apikey, content-type" };

function eanValido(c: string): boolean {
  if (!/^(\d{8}|\d{12,14})$/.test(c)) return false;
  const corpo = c.slice(0, -1).split("").reverse().map(Number);
  const soma = corpo.reduce((s, d, i) => s + d * (i % 2 === 0 ? 3 : 1), 0);
  return (10 - (soma % 10)) % 10 === Number(c.at(-1));
}

async function buscarLoja(loja: { nome: string; dominio: string }, ean: string) {
  const url = `https://${loja.dominio}/api/catalog_system/pub/products/search?fq=alternateIds_Ean:${ean}`;
  const resp = await fetch(url, { headers: { "User-Agent": UA, Accept: "application/json" } });
  if (resp.status === 429) return { loja: loja.nome, erro: "a loja pediu para ir mais devagar" };
  if (!resp.ok) return { loja: loja.nome, erro: `HTTP ${resp.status}` };
  const produtos = await resp.json();
  for (const p of produtos ?? []) {
    for (const item of p.items ?? []) {
      if (String(item.ean ?? "").replace(/^0+/, "") !== ean.replace(/^0+/, "")) continue;
      for (const v of item.sellers ?? []) {
        const o = v.commertialOffer ?? {};
        if (o.IsAvailable && o.Price) {
          return { loja: loja.nome, preco: o.Price, preco_de: o.ListPrice > o.Price ? o.ListPrice : null, nome: p.productName,
                   marca: p.brand, evidencia: url, link: p.link ?? `https://${loja.dominio}/${p.linkText}/p` };
        }
      }
    }
  }
  return { loja: loja.nome, encontrado: false };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  const ean = new URL(req.url).searchParams.get("ean") ?? "";
  if (!eanValido(ean)) return Response.json({ erro: "código inválido" }, { status: 400, headers: CORS });

  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const { data: guardado } = await db.from("busca_cache").select("resultado, buscado_em").eq("ean", ean).maybeSingle();
  if (guardado && Date.now() - new Date(guardado.buscado_em).getTime() < VALIDADE_MS) {
    return Response.json({ ...guardado.resultado, do_cache: true }, { headers: CORS });
  }
  const resultados = [];
  for (const loja of LOJAS) {  // uma loja por vez: menos carga nos sites
    try { resultados.push(await buscarLoja(loja, ean)); } catch (e) { resultados.push({ loja: loja.nome, erro: String(e) }); }
  }
  const resultado = { ean, buscado_em: new Date().toISOString(), ofertas: resultados.filter((r) => "preco" in r), detalhes: resultados };
  await db.from("busca_cache").upsert({ ean, resultado, buscado_em: resultado.buscado_em });
  await db.rpc("pedir_codigo", { codigo: ean });  // e entra na coleta diária
  return Response.json(resultado, { headers: CORS });
});
