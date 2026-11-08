# Apps de delivery e marketplaces com preços de supermercado no DF

> Escopo: iFood (Mercado), Rappi (Turbo), Daki, James Delivery, Shopper, Cornershop/Uber, Mercado Livre Supermercado, Amazon, Magalu, Carrefour/Atacadão, diretórios Instabuy e VipCommerce, sites próprios de redes do DF, catálogos de WhatsApp. Data da pesquisa: 2026-11-08.
>
> **Limite de método:** nesta sessão não foi possível abrir nenhum site das plataformas. O `curl` recebeu "CONNECT tunnel failed, 403" do proxy e o WebFetch devolveu ENOTFOUND para ifood.com.br, rappi.com.br, mercadolivre.com.br, mercado.carrefour.com.br e soudaki.com. Por isso **nenhum robots.txt e nenhum termo de uso foi lido em primeira mão**. Tudo o que vem de robots.txt, termos e JSON-LD está marcado como NÃO VERIFICADO. Para checar, é preciso liberar esses domínios na rede da sessão e repetir a coleta.

## 1. Quais plataformas mostram preços de supermercados do DF sem login?

### Takeaway
As plataformas com presença confirmada no DF são o iFood Mercado (com o Assaí e outras redes), a Shopper (CD e dark stores em Brasília desde setembro de 2026), a Uber/Cornershop (Atacadão, Carrefour Hiper e Extra em Brasília), a Rappi (Carrefour em Brasília, em 2019) e os sites próprios de redes como Comper e Pão de Açúcar. Daki e Rappi Turbo **não** aparecem como ativos no DF. Não consegui verificar se cada uma mostra preços sem login, nem se exige CEP.

### Cited Findings
- **iFood Mercado.** O piloto com o Assaí começou com 15 lojas em São Paulo, BH, **Brasília** e Goiânia e depois foi ampliado — [Mercado&Consumo, 08/11/2024](https://mercadoeconsumo.com.br/08/11/2024/destaque-do-dia/assai-e-ifood-iniciam-parceria-visando-ampliar-opcoes-para-os-consumidores-do-atacadista/); [Mercado&Consumo, 09/01/2025](https://mercadoeconsumo.com.br/09/01/2025/supermercados/assai-triplica-numero-de-lojas-atendidas-pelo-ifood/)
- **iFood Mercado.** 46 dos 50 maiores grupos de supermercados do país estão no iFood. O GMV da vertical Mercado cresceu 60% entre março de 2025 e março de 2026 — [InfoMoney](https://www.infomoney.com.br/?p=3432370)
- **iFood Mercado.** Em buscas por delivery de mercado, São Paulo e DF lideram, segundo levantamento do iFood com dados do Google — [Consumidor Moderno](https://consumidormoderno.com.br/delivery-de-mercado-e-a-descentralizacao-que-move-o-cx/)
- **iFood Mercado.** O iFood anunciou R$ 24 bi em investimentos (abril de 2026 a março de 2027), com foco em mercados, farmácias e pet shops — [Mercado&Consumo, 16/09/2026](https://mercadoeconsumo.com.br/16/09/2026/noticias/ifood-anuncia-investimento-recorde-de-r-24-bi-em-meio-a-disputas-na-justica-e-no-cade/)
- **Daki.** Vende dentro do app do iFood por parceria — [Bloomberg Línea](https://www.bloomberglinea.com.br/negocios/na-batalha-do-delivery-de-supermercado-ifood-muda-plano-e-faz-parceria-com-daki/). Em maio de 2026 operava 40 dark stores, apenas em SP e MG — [Mercado&Consumo, 07/05/2026](https://mercadoeconsumo.com.br/07/05/2026/supermercados/daki-aposta-em-verticalizacao-e-tecnologia-propria-para-avancar-no-quick-commerce/). Brasília aparecia só como possível praça futura — [NeoFeed](https://neofeed.com.br/startups/a-daki-perdeu-o-status-de-unicornio-agora-corre-atras-de-outra-marca-bilionaria/en/)
- **Shopper.** Abriu em Brasília, por volta de 01/09/2026, seu primeiro CD fora de SP (R$ 25 mi, mais de 7.000 m²), que atende Brasília e Goiânia. São 6 dark stores (4 em Brasília), cada uma com cerca de 3.000 produtos, e entrega em até 20 minutos, 24h, pelo "Shopper Now" — [Mercado&Consumo, 31/08/2026](https://mercadoeconsumo.com.br/31/08/2026/logistica/shopper-inicia-operacao-no-centro-oeste-com-cd-de-r-25-milhoes/); [GiroNews](https://gironews.com/varejo-digital/shopper-investe-r-25-milhoes-e-chega-ao-centro-oeste/); [Boca](https://boca.com.br/negocios/shopper-inaugura-centro-de-distribuicao-em-brasilia-e-abre-260-vagas). Os números de vagas divergem entre as fontes: 600+ em uma, 840 até o fim do ano em outra.
- **Rappi Turbo.** Uma lista de cidades (sem data) inclui SP, Campinas, Barueri, Curitiba, POA, RJ, BH, Recife e Fortaleza, **sem Brasília**. As dark stores do Turbo atendem só o app — [Startups.com.br](https://startups.com.br/negocios/food-delivery/rappi-aposta-no-turbo-first-para-se-afastar-do-ifood/)
- **Rappi + Carrefour.** Em 2019 a entrega do Carrefour via Rappi já funcionava em Brasília — [Forbes Brasil, 2019](https://forbes.com.br/last/2019/03/carrefour-brasil-expande-parceria-com-rappi/). Em 2021 o GPA (Extra, Pão de Açúcar, Minuto) voltou à Rappi — [GiroNews](https://gironews.com/supermercado/gpa-retorna-ao-rappi-62792/)
- **Uber Eats/Cornershop.** O delivery de restaurantes do Uber Eats acabou no Brasil em 07/03/2022. Supermercados e atacadistas continuaram no app — [InfoMoney](https://www.infomoney.com.br/?p=1759675); [TecMundo](https://www.tecmundo.com.br/mercado/234986-fim-uber-eats-brasil-o-que-muda-agora.htm). A página pública atual "Brasília" do Uber Eats lista Atacadão (Asa Norte), Carrefour Hiper Asa Norte e Extra — [Uber Eats Brasília](https://www.ubereats.com/br-en/city/bras%C3%ADlia-df) (segundo snippet de busca; não abri a página)
- **James Delivery.** Comprado pelo GPA em 2018. Em novembro de 2022 o GPA anunciou a intenção de incorporá-lo — [Money Times](https://www.moneytimes.com.br/gpa-quer-incorporar-james-delivery-para-elevar-vendas-e-cortar-custos/); [Suno](https://www.suno.com.br/noticias/?p=132720). Não encontrei sinal de operação atual no DF.
- **Comper (Grupo Pereira).** Tem compra pelo site com "Clique & Retire" (Sobradinho e Águas Claras), entrega agendada e Entrega Expressa em até 3h. O delivery cresceu 104% no DF — [Correio Braziliense, 2022](https://edicao.correiobraziliense.com.br/correiobraziliense/2022/05/14/143176/pdf/A18-CID-1405-DIG.pdf); [Super Varejo](https://supervarejo.com.br/varejo/comper-tem-crescimento-em-suas-vendas-de-delivery). App "Comper Delivery" — [App Store](https://apps.apple.com/br/app/comper-delivery/id6451009498)
- **Pão de Açúcar.** Entrega agendada a partir de CDs em SP, Rio, **Brasília** e Recife — [paodeacucar.com](https://www.paodeacucar.com/supermercado-online-como-comprar)
- **Carrefour.** Passou a vender na Amazon Brasil (agosto de 2026) — [TI Inside](https://tiinside.com.br/en/04/08/2026/carrefour-passa-a-vender-na-amazon-brasil/). Também tem operação fulfillment no Mercado Livre (2023) — [Mercado&Consumo](https://mercadoeconsumo.com.br/27/01/2023/ecommerce/carrefour-chega-com-operacao-fulfillment-ao-mercado-livre/amp)
- **VipCommerce.** Plataforma white label de BH, comprada pelo Magalu em 2021. Em 2022 atendia mais de 120 redes em 300+ cidades de 21 estados — [Mercado&Consumo](https://mercadoeconsumo.com.br/2021/03/03/magazine-luiza-compra-vipcommerce-plataforma-de-e-commerce-de-supermercados/); [Mercado&Consumo 2022](https://mercadoeconsumo.com.br/28/06/2022/inovacao/vipcommerce-lanca-aplicativo-omnichannel-para-supermercados/). Não achei nenhum cliente do DF.
- **Instabuy.** Desenvolve apps de supermercado com a marca de cada loja (ex.: "Bem Vindo Supermercado") — [App Store](https://apps.apple.com/br/app/1615430208). Não achei nenhum cliente do DF.
- **Keeta.** Não há fonte que confirme supermercado no DF. A cobertura trata de restaurantes e da disputa no Cade — [GiroNews](https://gironews.com/food-service/keeta-retoma-expansao-no-brasil-com-entrada-em-21-novas-cidades-e-acirra-disputa-no-delivery/)

### Inferences
- Para o DF, as fontes mais promissoras são **iFood Mercado**, **Shopper**, **Uber (Atacadão/Carrefour/Extra)**, **Pão de Açúcar/GPA** e **Comper**. Daki, Rappi Turbo e James Delivery parecem ausentes ou extintos no DF.
- NÃO VERIFICADO (conhecimento prévio, não confirmado nesta sessão): iFood e Rappi costumam exigir endereço para mostrar o catálogo de cada loja, porque o catálogo depende da área de entrega. A Shopper historicamente pedia CEP ou cadastro antes de mostrar o sortimento completo. Os sites próprios em VTEX (Carrefour Mercado, Pão de Açúcar) pedem CEP ou loja para regionalizar preço. A página de cidade do Uber Eats é pública, mas os preços por item em geral dependem de endereço.

### Gaps
- Se cada plataforma mostra preço sem login e sem CEP: não deu para testar, porque a rede estava bloqueada.
- Lista completa das redes do DF (Dona de Casa, Big Box, Tatico, Super Adega, Superbom, Atacadão Dia a Dia, Veneza etc.) em cada app: não encontrei fonte.
- Mercado Livre Supermercado, Amazon Supermercado e Magalu Mercado: não achei nada sobre cobertura de entrega de mercearia no DF, nem se os preços são de redes locais. Muito provavelmente são preços nacionais de seller ou fulfillment, não preço de gôndola do DF (inferência).
- Catálogos de WhatsApp: nenhuma fonte encontrada. Além disso, catálogos de WhatsApp Business não ficam numa página web pública rastreável (inferência).

## 2. O que robots.txt e termos permitem?

### Takeaway
Não consegui ler nenhum robots.txt nem nenhum termo de uso das plataformas, porque a rede bloqueou o acesso. A única fonte secundária encontrada diz que todas as grandes plataformas de entrega restringem acesso automatizado nos termos, mas não cita o texto. Mercado Livre e Amazon oferecem APIs oficiais, que são o caminho legítimo para essas duas.

### Cited Findings
- Um guia de coleta de preços afirma que os termos das principais plataformas de entrega restringem acesso automatizado. É fonte secundária e não cita o texto do iFood — [DataImpulse](https://dataimpulse.com/pt/blog/dados-de-precos-de-mercados-e-entregas-por-endereco/)
- Existe um scraper público do iFood que usa a "API móvel interna". Isso mostra que a técnica existe, **não** que é permitida, e não é um caminho legítimo para o projeto — [Apify](https://apify.com/gio21/ifood-scraper.md)
- **Mercado Livre.** Tem API oficial documentada. Os itens têm o atributo `GTIN` (GTIN-13/8, ITF-14), consultável via `GET /items/{id}?include_attributes=all`. Há `EMPTY_GTIN_REASON` quando não existe código. Documento atualizado em 29/12/2025 — [ML Developers – Identificadores de produtos](https://developers.mercadolivre.com.br/pt-br/identificadores-de-produtos)
- **Mercado Pago/ML Developers.** Os termos dão uma licença limitada e revogável, permitem limitar chamadas e só aceitam cópias intermediárias "estritamente necessárias" — [Termos Mercado Pago Developers](https://www.mercadopago.com.br/developers/pt/docs/resources/legal/terms-and-conditions)
- **Amazon.** A PA-API 5.0 está sendo descontinuada em favor da Creators API (OAuth 2.0, credenciais em Associates Central). O uso é restrito ao marketplace em que o afiliado se registrou. As fontes divergem sobre a data: 31/01, 30/04 ou 15/05/2026 — [Amazon Creators API – deprecation](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/paapiv5-deprecation); [Affiliate Toolkit](https://www.affiliate-toolkit.com/affiliate-toolkit-3-8-5-amazon-creators-api-support-why-you-need-to-migrate-before-may-15-2026/)

### Inferences
- NÃO VERIFICADO (conhecimento prévio, a confirmar quando a rede for liberada):
  - O robots.txt do iFood bloqueia caminhos dinâmicos e de busca, e os termos do iFood proíbem robôs e extração de dados.
  - O robots.txt do Mercado Livre libera produtos `/p/MLB...` para crawlers gerais, mas bloqueia `/jm/`, `/gz/` e buscas com filtros. Os termos do ML vedam "robôs, spiders ou qualquer dispositivo automático" para coletar dados.
  - O robots.txt da Amazon BR tem muitos `Disallow` em `/gp/`, `/s?` etc., e as Conditions of Use proíbem "data mining, robots".
  - Sites VTEX (Carrefour, Pão de Açúcar) costumam ter robots.txt permissivo para produtos, bloqueando `/checkout`, `/account` e buscas.
  - Nada disso foi lido nesta sessão. As linhas exatas precisam ser coletadas antes de qualquer decisão.
- Para Mercado Livre e Amazon, a rota legítima é a API oficial, não o scraping. Mas essas plataformas não refletem preço de gôndola do DF.

### Gaps
- Linhas exatas de robots.txt de: ifood.com.br, rappi.com.br, shopper.com.br, ubereats.com, mercadolivre.com.br, amazon.com.br, magazineluiza.com.br, mercado.carrefour.com.br, atacadao.com.br, paodeacucar.com, comper.com.br, instabuy.com.br, vipcommerce.com.br.
- Cláusulas de scraping nos termos de iFood, Rappi, Shopper, Uber, Magalu, Carrefour, GPA e Comper.
- iFood, Rappi e Shopper não têm API pública para consumidores. As APIs de parceiro do iFood (Merchant API) servem lojistas, não leitura de catálogo por terceiros (conhecimento prévio, não verificado). Pela regra do projeto ("sem parcerias"), estão fora de qualquer forma.

## 3. As páginas expõem código de barras (GTIN)?

### Takeaway
O único GTIN confirmado é o da API oficial do Mercado Livre. Para as demais plataformas, não consegui verificar JSON-LD.

### Cited Findings
- O Mercado Livre expõe GTIN como atributo de item pela API oficial — [ML Developers](https://developers.mercadolivre.com.br/pt-br/identificadores-de-produtos)

### Inferences
- NÃO VERIFICADO: lojas VTEX (Carrefour Mercado, Pão de Açúcar e possivelmente Comper) costumam publicar JSON-LD `Product` com `gtin13` e o `ean` no estado da página. Lojas VipCommerce e Instabuy em geral usam SPAs com API interna. O iFood não expõe EAN publicamente no front-end. Tudo isso precisa ser testado abrindo uma página de produto.

### Gaps
- Não encontrei nenhuma fonte sobre JSON-LD ou GTIN em iFood, Rappi, Shopper, Uber, Magalu, Amazon, Carrefour, Comper, VipCommerce ou Instabuy.

## 4. O preço no app é igual ao da loja?

### Takeaway
Não encontrei estudo de Procon ou Idec que compare o preço do app com o da gôndola para supermercados. Há só declarações de empresas e relatos sem método. A Rappi afirma que os preços são "parecidos" com os da loja física. Logo, preço de app **não deve ser tratado como preço de loja** sem validação local.

### Cited Findings
- Segundo a InfoMoney, o diretor da Rappi afirmou que os preços são parecidos com os dos supermercados offline. É uma declaração da empresa, sem dados que a sustentem — [InfoMoney](https://www.infomoney.com.br/?p=1777068)
- Um texto opinativo diz que o mesmo item aparece mais caro no digital por repasse de comissão e que nem todo o sortimento é listado. Não descreve método nem amostra — [Oficina da Net](https://www.oficinadanet.com.br/tecnologia/32454-ifood-ou-rappi-supermercado)
- Em 2020, reportagem sobre a pandemia relatou que o consumidor chegava a gastar até 30% a mais em mercados. É dado pontual, não comparação app x loja — [Correio 24 Horas](https://www.correio24horas.com.br/noticia/nid/quem-ganha-na-pandemia-consumidor-chega-a-gastar-ate-30-a-mais-nos-mercados)
- O Procon-SP encontrou variações de até 200% entre supermercados online para o mesmo produto. Compara lojas entre si, não app x loja — [Procon-SP](https://www.procon.sp.gov.br/?p=65245)
- A Senacon passou a exigir que apps de transporte e delivery detalhem quanto do valor vai para entregador, plataforma e loja — [Tecnoblog](https://tecnoblog.net/noticias/senacon-exige-transparencia-nos-precos-de-uber-99-e-outros-apps/)
- Um supermercado foi multado por cobrar no caixa preço diferente do anunciado para quem não tinha o app da loja, prática considerada abusiva. Isso mostra que preços "de app" podem diferir do preço geral — [Metrópoles](https://www.metropoles.com/colunas/grande-angular/destacar-valor-menor-de-combustivel-em-pagamento-por-app-e-publicidade-enganosa) (contexto: combustível e app de pagamento; relação indireta)
- Procon de Juiz de Fora, pesquisa de delivery de 2023 (PDF). O conteúdo exato não foi lido — [PJF Procon](https://www.pjf.mg.gov.br/administracao_indireta/procon/pesquisas/arquivos/pesq_delivery_2023.pdf)

### Inferences
- Dark stores (Shopper, Daki, Rappi Turbo) têm preço **próprio**: não são preço de loja física de nenhuma rede do DF. Servem como referência de mercado, mas não como "preço no supermercado X".
- Marketplaces de terceiros (iFood e Rappi com lojas parceiras, Uber) podem aplicar preço diferente da gôndola por comissão, conforme o texto opinativo acima e o que se sabe do setor. O app deveria rotular essas entradas como "preço no app de delivery".
- Sites próprios das redes (Comper, Pão de Açúcar, Carrefour) tendem a ser os mais próximos do preço da loja, mas também podem ter preço "online" diferente.

### Gaps
- Nenhum estudo de Procon-DF, Idec ou outro órgão com cesta coletada no mesmo dia em app e loja. Não achei nenhum para o DF.

## Recomendação por plataforma (síntese para o redator)

| Plataforma | Presença DF | Recomendação | Justificativa |
|---|---|---|---|
| iFood Mercado | Sim (Assaí e outras) | **Descartar para coleta automática** | Provável exigência de endereço, termos restritivos (não verificado) e preço com possível markup. Só via parceria, que está vetada. |
| Rappi (Turbo/super) | Turbo não; Carrefour/GPA via marketplace | **Descartar** | Turbo ausente no DF. Mesmas restrições de termos (não verificado). |
| Daki | Não (só SP/MG em maio de 2026) | **Descartar** | Fora do DF. |
| James Delivery | Incorporado pelo GPA (2022) | **Descartar** | Sem operação aparente. |
| Shopper | Sim (desde set/2026) | **Testar** | Novo no DF. Verificar se o catálogo é público sem login/CEP, o robots.txt e os termos. Preço próprio de dark store. |
| Uber (Cornershop) | Sim (Atacadão, Carrefour Hiper, Extra) | **Testar com cautela / provável descarte** | A página de cidade é pública, mas o catálogo de itens provavelmente depende de endereço. Termos da Uber a ler. |
| Mercado Livre Supermercado | Nacional | **Usar a API oficial só como referência nacional** | Tem API oficial com GTIN, mas o preço não é de gôndola do DF. |
| Amazon Supermercado | Nacional (Carrefour vende lá desde ago/2026) | **Descartar ou usar só como referência** | A Creators API exige ser afiliado (o que se aproxima de "parceria"), e o preço é nacional. |
| Magalu Mercado | Nacional | **Descartar** | Sem evidência de preço local do DF. |
| Carrefour Mercado / Atacadão | Sim (lojas em Brasília) | **Testar** | Site próprio provavelmente em VTEX, com possível JSON-LD com GTIN e preço por loja via CEP (não verificado). Ler robots.txt e termos. |
| Pão de Açúcar / Extra (GPA) | Sim (CD Brasília) | **Testar** | Mesmo racional do Carrefour. |
| Comper | Sim (site + app, Sobradinho/Águas Claras) | **Testar** | Site próprio de rede do DF. Verificar plataforma, robots.txt e GTIN. |
| Diretório Instabuy | Nenhum cliente do DF achado | **Testar (baixa prioridade)** | Verificar se há clientes do DF e se as lojas são públicas. |
| Diretório VipCommerce | Nenhum cliente do DF achado | **Testar (baixa prioridade)** | Mesmo racional. |
| Catálogos de WhatsApp | Sem fonte | **Descartar** | Não é página web pública rastreável. A coleta exigiria automação do WhatsApp, o que viola os termos (inferência). |

Próximo passo indispensável: liberar na rede da sessão os domínios ifood.com.br, rappi.com.br, shopper.com.br, ubereats.com, mercadolivre.com.br, amazon.com.br, magazineluiza.com.br, mercado.carrefour.com.br, atacadao.com.br, paodeacucar.com, comper.com.br, instabuy.com.br e vipcommerce.com.br. Depois, coletar robots.txt, termos e uma página de produto de cada um para confirmar os itens marcados como NÃO VERIFICADO.
