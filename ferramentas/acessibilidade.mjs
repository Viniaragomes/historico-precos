// Auditoria de acessibilidade (WCAG 2.1 AA) de todas as telas, nos temas claro e escuro.
// Uso: npm i -D playwright axe-core && python -m historico_precos servir --porta 8765 (com dados exportados)
//      node ferramentas/acessibilidade.mjs [http://localhost:8765/]
import { createRequire } from "module";
import { readFileSync } from "fs";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const B = process.argv[2] || "http://localhost:8765/";
const axe = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
const browser = await chromium.launch();
const telas = [
  ["início", "#/", null], ["produtos", "#/produtos", null], ["produto", "#/p/7896005800027", null],
  ["não acompanhado", "#/p/7891234567895", null], ["sobre", "#/sobre", null], ["perfil", "#/perfil", null],
  ["termos", "#/termos", null], ["moderação", "#/moderar", null],
  ["leitor", "#/", async (p) => { await p.click("#aba-escanear"); }],
  ["confirmar preço", "#/p/7896005800027", async (p) => { await p.click(".botao-pilula >> nth=0"); }],
  ["reportar", "#/p/7896005800027", async (p) => { await p.click("text=Reportar um problema"); }],
];
const resumo = {};
for (const tema of ["light", "dark"]) {
  for (const [nome, rota, acao] of telas) {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, colorScheme: tema, reducedMotion: "reduce" });
    const page = await ctx.newPage();
    await page.route("https://world.openfoodfacts.org/**", (r) => r.fulfill({ contentType: "application/json",
      body: JSON.stringify({ status: 1, product: { product_name: "Arroz Branco Tipo 1 Exemplo 5kg" } }) }));
    await page.goto(B + rota); await page.waitForTimeout(800);
    if (acao) { await acao(page); await page.waitForTimeout(500); }
    await page.addScriptTag({ content: axe });
    const r = await page.evaluate(async () => (await axe.run(document, { runOnly: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"] })).violations);
    for (const v of r) {
      const k = `${v.id} [${v.impact}] ${v.help}`;
      resumo[k] = resumo[k] || { telas: new Set(), exemplos: new Set() };
      resumo[k].telas.add(`${nome}/${tema}`);
      v.nodes.slice(0, 2).forEach((n) => resumo[k].exemplos.add(n.target.join(" ") + (n.any[0]?.message ? " → " + n.any[0].message.slice(0, 140) : "")));
    }
    await ctx.close();
  }
}
await browser.close();
const chaves = Object.keys(resumo);
console.log(chaves.length ? "" : "Nenhuma violação.");
process.exitCode = chaves.length ? 1 : 0;
for (const k of chaves) {
  console.log(`\n${k}\n  telas: ${[...resumo[k].telas].join(", ")}`);
  [...resumo[k].exemplos].slice(0, 3).forEach((e) => console.log(`  - ${e}`));
}
