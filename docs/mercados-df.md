# Supermercados do DF: situação de cada fonte (08/11/2026)

Levantamento a partir de fontes públicas: encartesdf.com.br (60 nomes de mercados com encarte no último ano),
busca dos sites oficiais e teste direto de cada site a partir do GitHub (robots.txt lido e respeitado, sem login,
sem burlar bloqueio). Detalhes: `reports/Fontes de preços do DF.md` e `research_notes/Fontes de preços do DF/`.

## 1. Preço lido direto do site da loja (catálogo)

| Mercado | Como | Código de barras |
|---|---|---|
| Atacadão | API pública VTEX (o GitHub é limitado por excesso de acessos) | sim |
| Oba Hortifruti | API pública VTEX (idem) | sim |
| Carrefour | sitemap + JSON-LD | sim |
| Big Box 402/403 Norte ("Big Box"), Lago Sul QI 23, 105 Sudoeste, Lago Sul QI 11 | Instabuy, um site por loja | não: vínculo pelo nome |
| Fort Atacadista | osuper, sitemap + JSON-LD | não: vínculo pelo nome |
| Super Veneza Guará II e Cruzeiro | Instabuy | não: vínculo pelo nome |
| Bellavia Jardim Botânico | Instabuy | não: vínculo pelo nome |

## 2. Encarte lido no site do próprio mercado

| Mercado | Formato |
|---|---|
| Atacadão Dia a Dia | PDF com texto (leitura exata), por região DF |
| Dona | PDF do folheto |
| Ultrabox | imagens das páginas (mídia pública do WordPress) |
| Costa Atacadão | imagens dos tabloides "DF" (os de Goiás ficam de fora) |
| Primor | imagens das ofertas do dia |
| Assaí Atacadista | capa do folheto "ofertas DF" via Portafolhetos (site do Assaí recusa robôs; paginação proibida no robots.txt de lá) |

## 3. Só pelo encartesdf.com.br (imagens republicadas)

União, Supercei, Atacadista Super Adega, Superbom, Bevia, Bellavia (demais lojas), Bistecão (e 421), Ideal, Mineirão,
Varejão da Fartura, Mais Econômico, Tatico, Brandão, Comper, Super Frota, Mega Box, SuperGiro, Então, Caprichoso,
Planeta, Via Norte, Favorito, Serve Mais, Vivendas Atacadão, Melhor Atacadista, Atacarejo Bonamix, G&L Atacarejo,
Espírito Santo, Indaiá, Barbosa, Ponto Alto, Tend Tudo, Ki Preço, Bom Preço, Mix, Rei Arthur, Guarapari.

Motivo de não haver fonte própria: site sem preço ou sem encarte (Tatico, Caprichoso, Varejão da Fartura), plataforma
sem lista de produtos (União e Bistecão: osuper sem sitemap), encarte desatualizado (Melhor Atacadista: abril/2026),
site com certificado inválido (Supercei, Mineirão), ofertas só por WhatsApp, Instagram ou Telegram (a maioria das
redes de bairro; Instagram e Facebook proíbem coleta automática), bloqueio a robôs (Comper: 403 até no robots.txt;
Super Adega e Superbom: captcha).

## 4. Fora do DF (Goiás, Entorno)

Cristal (Cidade Ocidental), Super Big e Atacadão Premium (Santo Antônio do Descoberto), Vizinhança e Tio Max
(Valparaíso e Luziânia), Super Marques (Planaltina-GO). Continuam aparecendo se o encartesdf publicar, mas não são DF.

## 5. Sem acesso legítimo hoje

Pão de Açúcar e Extra (preço só carregado por JavaScript, sem sitemap), iFood (403), apps de dark store (preço
próprio), Menor Preço Brasil (exige login gov.br). Dados de notas fiscais de consumidor do DF: pedido pela LAI
negado; cabe recurso (ver relatório).
