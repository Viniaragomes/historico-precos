# Redes médias/grandes de supermercado no DF: fontes públicas de preço

> **Limitação de método (importante):** neste ambiente, o acesso direto aos sites das redes foi **bloqueado**. `curl` via Bash recebeu `403` do proxy no CONNECT (ex.: martminas.com.br, paodeacucar.com), e o WebFetch devolveu `ENOTFOUND` para www.paguepouco.com.br e ofertas.comper.com.br. Por isso **nenhum robots.txt, sitemap, JSON-LD ou fingerprint de plataforma foi verificado diretamente**. Tudo abaixo vem de resultados de busca (WebSearch), mais o contexto já conhecido que veio na tarefa (marcado "contexto, não reverificado"). Os campos robots.txt, sitemap e GTIN estão marcados como **NÃO VERIFICADO** em quase todas as redes. Para fechar essas lacunas, os domínios listados precisam ser liberados nas configurações de rede da sessão, ou o teste tem que rodar em outra máquina.

## 1. Quais redes têm fonte pública de preço ainda não conhecida, e em que plataforma?

### Takeaway
O achado novo mais forte é o **Super Veneza** (Guará II e Cruzeiro 811), que vende online pela **Instabuy**, a mesma plataforma do Big Box. Também apareceram três candidatos a testar: o subdomínio de ofertas do **Comper** por cidade (ofertas.comper.com.br/cidade/distrito-federal/), o site oficial do **Tatico** (taticobaratotododia.com.br) e o do **Mega Box** (megaboxatacado.com.br). Várias redes da lista não têm loja online identificável ou são casos de nome trocado: Pague Pouco, Leve Mais, Hiper Bom, Coma Bem e Super Vizinho.

### Cited Findings

**Super Veneza (Supermercado Veneza)**
- Lojas online na Instabuy: `superveneza.instabuy.com.br` (Guará II) e `supervenezacruzeiro811.instabuy.com.br` (Cruzeiro 811), com entrega e retirada na loja e pagamento online por Pix ou cartão — [Super Veneza Guará II (Instabuy)](https://www.superveneza.instabuy.com.br/); [Sobre nós Guará II](https://superveneza.instabuy.com.br/sobre); [Cruzeiro 811 (Instabuy)](https://www.supervenezacruzeiro811.instabuy.com.br/)
- Domínio white-label `cruzeiro811.appsuperveneza.com`, também com páginas "Sobre" no padrão Instabuy — [Cruzeiro 811 appsuperveneza](https://cruzeiro811.appsuperveneza.com/)
- Outros domínios: `supervenezadf.com.br/app/` (página do app) e `superveneza.com` (o site institucional manda pedir por telefone e anuncia frete grátis acima de R$ 150) — [App Super Veneza](https://supervenezadf.com.br/app/); [superveneza.com](https://superveneza.com/)
- App Android `br.com.superveneza` — [Google Play](https://play.google.com/store/apps/details?id=br.com.superveneza&hl=en_US)
- Ressalva: os dois sites não usam os mesmos telefones (3025-7200 e 3360-4061 nas páginas Instabuy, 3305-3801 em superveneza.com). Podem ser operadores ou franquias distintos sob a mesma marca (inferência a partir dos resultados acima).

**Comper (Grupo Pereira)**
- `comper.com.br` tem loja online (site e app Clube Mais) com entrega ou retirada, e Brasília está entre as cidades atendidas — [Comper Supermercado Online](https://www.comper.com.br/)
- Existe uma página de ofertas por cidade em `ofertas.comper.com.br/cidade/distrito-federal/`. O snippet da busca citava pedido mínimo de R$ 50 no Comper.com.br e mostrava "Nenhuma oferta ainda" no momento do índice — [Brasília/DF ofertas Comper](https://ofertas.comper.com.br/cidade/distrito-federal/)
- Contexto (não reverificado): o site do Comper devolve 403 a bots.

**Supermercados Tatico**
- Site oficial: `taticobaratotododia.com.br` — [Supermercados Tatico](https://taticobaratotododia.com.br/)
- Atua em Brasília e Goiânia — [Tiendeo Tatico Taguatinga](https://www.tiendeo.com.br/Lojas/taguatinga/tatico)
- Há registro de entrega a partir da loja do Recanto das Emas (reclamação antiga), mas não se confirmou loja online com preços — [Reclame Aqui Tatico](https://www.reclameaqui.com.br/supermercados-tatico/entrega_sHA1BmhUzeDng95r/)
- Encartes republicados por terceiros — [Encartes DF Tatico (vencido, 23-08-2026)](https://encartesdf.com.br/supermercado-tatico-ate-23-08-2026/); [SuperDF Tatico](https://www.superdf.com.br/tatico/)

**Ultrabox**
- Segundo o LinkedIn, é uma rede de atacado e varejo com cerca de 20 lojas no DF e faz parte do grupo **Big Box**. O site informado é `www.ultraboxatacado.com.br` — [LinkedIn Ultrabox](https://br.linkedin.com/company/ultrabox-atacado-e-varejo)
- Folhetos aparecem na Tiendeo (mais recente indexado: 29/07/2026) — [Tiendeo Ultrabox Brasília](https://www.tiendeo.com.br/brasilia/ultrabox)
- Cuidado com homônimos: ultrabox.com (logística, Colômbia) e ultraboxembalagens.com.br (embalagens) não têm relação com a rede — [ultrabox.com](https://www.ultrabox.com/principal/quienes-somos/); [ultraboxembalagens](https://ultraboxembalagens.com.br/)

**Supermaia**
- Site oficial: `supermaia.com.br` (institucional; os resultados não indicam loja online) — [Supermaia](https://www.supermaia.com.br/)
- 15 lojas, 14 no DF e 1 em Valparaíso (GO); primeira loja no Cruzeiro, em 1992 — [LinkedIn Super Maia](https://br.linkedin.com/company/supermercado-supermaia)

**Super Cei (Supercei)**
- Lojas no DF (Brazlândia, Ceilândia, Gama, Taguatinga), e-mail contato@supercei.com.br. Os resultados não indicam e-commerce. Encartes republicados pelo Encartes DF — [Encartes DF Supercei até 10-09-2026](https://encartesdf.com.br/supercei-supermercado-ate-10-09-2026/); [Encartes DF Supercei até 25-08-2026](https://encartesdf.com.br/supercei-supermercado-ate-25-08-2026/)

**Costa Atacadão**
- Aparece no ranking ABRAS 2026 como atacarejo de Goiás ligado ao Grupo JC. Nenhuma loja online encontrada — [Ranking ABRAS 2026 (PDF)](https://static.abras.com.br/pdf/ranking/ranking-abras-2026.pdf)

**Pão de Açúcar / GPA (Brasília)**
- `paodeacucar.com` vende online. O FAQ cita Brasília entre os centros de distribuição com entrega "Agendada" — [Pão de Açúcar como comprar](https://www.paodeacucar.com/supermercado-online-como-comprar)
- Nenhuma documentação pública de API ou EAN encontrada. A plataforma também não foi confirmada.

**Assaí**
- Folhetos regionais online, inclusive do DF, republicados por agregadores (ex.: encarte de 05/11/2026). Nenhum delivery próprio identificado — [Portafolhetos Assaí](https://www.portafolhetos.com.br/assai-atacadista/)
- Contexto (não reverificado): o site devolve 403 a bots.

**Mart Minas**
- Nenhuma loja no DF confirmada. As fontes listam apenas cidades de MG e MT (Contagem, Uberlândia, Sinop etc.) — [Kimbino Mart Minas](https://www.kimbino.com.br/mart-minas/); [Tiendeo Comper/Brasília lista Mart Minas como "outro negócio"](https://www.tiendeo.com.br/Lojas/brasilia/comper)

**Outras redes do DF encontradas**
- **Mega Box Atacadista**: site oficial `megaboxatacado.com.br`. A Tiendeo descreve a rede como fundada em 2010 no Rio de Janeiro, mas o Encartes DF publica encartes de um "Supermercado Mega Box" (vencido em 19-08-2026). A presença no DF e a identidade da rede são ambíguas (pode haver homônimos) — [Mega Box Atacadista](https://www.megaboxatacado.com.br/); [Tiendeo Mega Box](https://www.tiendeo.com.br/Encartes-Catalogos/mega-box); [Encartes DF Mega Box](https://encartesdf.com.br/supermercado-mega-box-ate-19-08-2026/)
- **Bevia Atacadista**: lojas em Paranoá, Ceilândia e Itapoã. Divulga encarte e ofertas diárias pelo Instagram e por canal de WhatsApp; nenhum site com preços encontrado — [Instagram Bevia](https://www.instagram.com/beviaatacadista/); [Encartes DF Bevia (vencido 26-08-2026)](https://encartesdf.com.br/bevia-atacadista-ate-26-08-2026/)
- **Atacarejo Bonamix**: lojas sobretudo no Entorno (Valparaíso, Águas Lindas, Luziânia, Novo Gama) e uma em Samambaia (DF) — [Encartes DF Bonamix](https://encartesdf.com.br/mercado/atacarejo-bonamix/); [Encartes DF Bonamix 2022](https://encartesdf.com.br/atacarejo-bonamix-ate-14-11-2022/)

**Redes da lista sem presença no DF confirmada ou com nome trocado**
- **Pague Pouco**: a rede encontrada é do Acre (Rio Branco, Grupo Recol, app "PaguePouco Supermercado Online"). Nada indica lojas no DF — [App Store PaguePouco](https://apps.apple.com/us/app/id1509498866)
- **Leve Mais**: nos resultados, é marca própria do Super Pague Menos ou um supermercado de Jaboatão (PE). Nenhuma rede no DF confirmada — [Super Pague Menos / Leve Mais](https://www.superpaguemenos.com.br/leve-mais/); [Supermercado Leve Mais (PE)](http://supermercadolevemais.com.br/)
- **Hiper Bom**: hiperbom.com diz "O Hiper Bom agora é Hiper Select", e o delivery é em Florianópolis (SC), não no DF — [hiperbom.com](https://www.hiperbom.com/); [Hiper Select](https://www.hiperselectsupermercados.com.br/)
- **Coma Bem**: em Brasília só aparecem restaurantes. O "Coma Bem Supermercados" encontrado fica em Viamão (RS) — [Waze Coma Bem Viamão](https://www.waze.com/live-map/directions/coma-bem-supermercados-av.-liberdade-1825-viamao?to=place.w.202442203.2024356497.1942562); [Restaurante Coma Bem Brasília](https://restaurantguru.com.br/Restaurante-Coma-Bem-Brasilia-4)
- **Super Vizinho**: a rede "Super Vizinho" é de São Paulo. No DF existe a "Super Vizinha" (Comércio de Alimentos Supervizinhança S.A., CNPJ 51.406.453/0002-34, Paranoá) — [Econodata Super Vizinha](https://www.econodata.com.br/consulta-empresa/51406453000234-comercio-de-alimentos-supervizinhanca-sa); [Empregos.com.br Super Vizinho](https://www.empregos.com.br/empresa/super-vizinho/e-61989)

### Inferences
- O Super Veneza na Instabuy deve se comportar como o Big Box (contexto conhecido): preço público sem login, mas sem código de barras. Se for isso mesmo, dá para reaproveitar o mesmo coletor Instabuy usado no Big Box.
- Como a Ultrabox pertence ao grupo Big Box, é possível que use a mesma Instabuy (bigboxdelivery.com.br) ou nem tenha loja online própria. Não foi verificado.
- O subdomínio `ofertas.comper.com.br/cidade/...` parece um portal de ofertas por cidade, talvez um WordPress separado do e-commerce. Pode estar fora do bloqueio 403 do domínio principal. Não foi verificado.

### Gaps
- Plataforma (VTEX, VipCommerce etc.) de comper.com.br, paodeacucar.com, taticobaratotododia.com.br, ultraboxatacado.com.br, supermaia.com.br e megaboxatacado.com.br: não confirmada, porque o acesso direto foi bloqueado.
- Não se confirmou se o Tatico, a Supermaia, o Super Cei ou o Costa Atacadão vendem online.
- O próprio pedido de pesquisa pode ter nomes errados para o DF (Pague Pouco, Leve Mais, Hiper Bom, Coma Bem, Super Vizinho). Vale confirmar com o usuário os nomes das redes locais.

## 2. Quais expõem GTIN/EAN publicamente?

### Takeaway
Não foi possível verificar o GTIN de nenhuma rede nova. Pelo contexto já conhecido, as lojas Instabuy (Big Box) e osuper (Fort) **não** mostram código de barras, e as plataformas VTEX (Atacadão) e o sitemap com JSON-LD do Carrefour seguem como as fontes mais prováveis de EAN.

### Cited Findings
- A busca não achou nenhuma documentação pública de API, catálogo ou EAN do Pão de Açúcar — [Pão de Açúcar FAQ](https://www.paodeacucar.com/duvidas-frequentes)
- O Super Veneza está na Instabuy, mesma plataforma do Big Box — [Super Veneza Instabuy](https://www.superveneza.instabuy.com.br/)

### Inferences
- O Super Veneza provavelmente não traz EAN, por analogia com o Big Box na Instabuy (contexto da tarefa). Isso ainda precisa de teste.
- Se o Comper ou o Pão de Açúcar rodarem em VTEX, o endpoint `/api/catalog_system/pub/products/search` costuma devolver `items[].ean`. É só hipótese; vale testar com rate limit baixo.

### Gaps
- JSON-LD (`gtin13`) de comper.com.br, paodeacucar.com e da Instabuy do Super Veneza não foi verificado, por bloqueio de rede.

## 3. Quais publicam encartes semanais no próprio site de forma legível por máquina?

### Takeaway
Entre as redes novas, nenhuma publica encarte em PDF com camada de texto ou em JSON no próprio site, pelo que se pôde confirmar. Supercei, Tatico, Bevia, Mega Box e Bonamix aparecem principalmente no **encartesdf.com.br** (agregador) e na Tiendeo, Kimbino e Portafolhetos. A Bevia distribui ofertas por Instagram e WhatsApp, canais que não servem para leitura automática legítima. O único candidato oficial é o portal `ofertas.comper.com.br/cidade/distrito-federal/`.

### Cited Findings
- O Encartes DF publica encartes de Supercei, Tatico, Bevia, Mega Box e Bonamix (vários vencidos em ago/set de 2026, o que indica que o índice da busca está desatualizado) — [Encartes DF Supercei](https://encartesdf.com.br/supercei-supermercado-ate-10-09-2026/); [Encartes DF Tatico](https://encartesdf.com.br/supermercado-tatico-ate-23-08-2026/); [Encartes DF Bevia](https://encartesdf.com.br/bevia-atacadista-ate-26-08-2026/); [Encartes DF Mega Box](https://encartesdf.com.br/supermercado-mega-box-ate-19-08-2026/); [Encartes DF Bonamix](https://encartesdf.com.br/mercado/atacarejo-bonamix/)
- O SuperDF também republica encartes do Tatico — [SuperDF Tatico](https://www.superdf.com.br/tatico/)
- O Assaí tem folhetos por região e data (agregador: encarte de 05/11/2026) — [Portafolhetos Assaí](https://www.portafolhetos.com.br/assai-atacadista/)
- A Bevia divulga encarte e ofertas diárias pelo link do Instagram e por canal de WhatsApp — [Instagram Bevia](https://www.instagram.com/beviaatacadista/)
- O Comper tem página de ofertas por cidade no DF (estava vazia no momento do índice) — [ofertas.comper.com.br DF](https://ofertas.comper.com.br/cidade/distrito-federal/)

### Inferences
- Para redes sem e-commerce (Supercei, Tatico, Bevia, Bonamix, Supermaia), a fonte de encartes mais prática seria o Encartes DF. É um agregador que republica material de terceiros, então antes de usar é preciso checar os termos e o robots.txt dele e de onde vêm as imagens. Os encartes costumam ser imagens, o que exige OCR.

### Gaps
- Não se confirmou se taticobaratotododia.com.br, supermaia.com.br ou megaboxatacado.com.br têm página própria de encarte, em PDF ou imagem.

## 4. Termos de uso que proíbem acesso automatizado? / Recomendação por rede

### Takeaway
Nenhum termo de uso ou robots.txt pôde ser lido: o acesso foi bloqueado e a busca não trouxe cláusulas específicas. Isso fica como lacuna para todas as redes. As recomendações abaixo valem só como direção e precisam passar por um teste de robots.txt antes de qualquer coleta.

### Cited Findings
- Nenhuma cláusula de termos de uso contra robôs ou raspagem apareceu nos resultados de busca de nenhuma rede (ausência de evidência, não evidência de permissão).
- Contexto da tarefa (não reverificado): Comper e Assaí devolvem 403 a bots; Super Adega e Superbom usam captcha.

### Inferences — tabela de recomendação

| Rede | Domínio(s) | Plataforma | Preço público sem login | GTIN | Encarte | robots.txt / sitemap | Recomendação |
|---|---|---|---|---|---|---|---|
| Super Veneza | superveneza.instabuy.com.br, supervenezacruzeiro811.instabuy.com.br, cruzeiro811.appsuperveneza.com, superveneza.com, supervenezadf.com.br | **Instabuy** (confirmado pela busca) | Provável (Instabuy) | Provavelmente não | Não encontrado | NÃO VERIFICADO | **Testar já**: reaproveitar o coletor Instabuy do Big Box |
| Comper | comper.com.br, ofertas.comper.com.br | Desconhecida (e-commerce próprio + portal de ofertas) | Desconhecido; 403 a bots (contexto) | ? | Portal por cidade (DF) | NÃO VERIFICADO | **Testar** só ofertas.comper.com.br; descartar o e-commerce se o 403 continuar |
| Pão de Açúcar (GPA) | paodeacucar.com | Desconhecida | Provável (vende online em BSB) | ? | ? | NÃO VERIFICADO (proxy bloqueou) | **Testar** robots, sitemap e JSON-LD |
| Tatico | taticobaratotododia.com.br | Desconhecida | Não confirmado | ? | Via Encartes DF/SuperDF | NÃO VERIFICADO | **Testar** se o site tem encarte |
| Ultrabox (grupo Big Box) | ultraboxatacado.com.br (segundo o LinkedIn) | Desconhecida; talvez Instabuy do Big Box | ? | ? | Tiendeo | NÃO VERIFICADO | **Testar** |
| Supermaia | supermaia.com.br | Site institucional | Não indicado | ? | Não encontrado | NÃO VERIFICADO | **Testar** (baixa expectativa) |
| Super Cei | (contato@supercei.com.br; supercei.com.br provável, não confirmado) | ? | Não | ? | Via Encartes DF | NÃO VERIFICADO | Usar encarte via agregador / descartar fonte própria |
| Costa Atacadão | ? | ? | Não encontrado | ? | ? | — | **Descartar** por ora |
| Assaí | assai.com.br | ? | 403 a bots (contexto) | ? | Folhetos regionais (agregadores) | — | **Descartar** o site; considerar encarte via agregador |
| Mart Minas | martminas.com.br | ? | — | — | — | — | **Descartar** (sem loja no DF confirmada) |
| Mega Box | megaboxatacado.com.br | ? | ? | ? | Encartes DF | NÃO VERIFICADO | **Testar** (confirmar presença no DF) |
| Bevia Atacadista | (Instagram/WhatsApp) | — | Não | — | Instagram/WhatsApp, Encartes DF | — | Descartar fonte própria; só agregador |
| Atacarejo Bonamix | ? | — | Não | — | Encartes DF | — | Descartar fonte própria; só agregador |
| Pague Pouco, Leve Mais, Hiper Bom, Coma Bem, Super Vizinho | — | — | — | — | — | — | **Descartar**: sem rede correspondente no DF encontrada (provável erro de nome) |
| Atacadão, Oba, Carrefour, Big Box, Fort, Dia a Dia, Dona, Super Adega, Superbom | (contexto da tarefa) | VTEX / sitemap+JSON-LD / Instabuy / osuper / WordPress / PDF / captcha | — | — | — | Não reverificado | Manter a avaliação já conhecida |

### Gaps
- robots.txt, sitemap.xml e termos de uso de todas as redes acima: não lidos, por bloqueio de rede (proxy 403 / ENOTFOUND). Domínios a liberar para o teste: superveneza.instabuy.com.br, comper.com.br, ofertas.comper.com.br, paodeacucar.com, taticobaratotododia.com.br, ultraboxatacado.com.br, supermaia.com.br, megaboxatacado.com.br, encartesdf.com.br.
- Presença no DF, em fins de 2026, de Mart Minas, Mega Box (Rio de Janeiro ou outra rede homônima), Pague Pouco e Leve Mais: não confirmada.
