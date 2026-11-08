# Revisão geral do Prova Preço (08/11/2026)

Base: app publicado (v29), banco do ramo `dados`, últimas coletas e as medições de hoje com os encartes reais.

## Onde estamos

| Indicador | Valor |
|---|---|
| Produtos com preço no app | **5.299** (de 5.477 no índice) |
| Produtos com preço em **2 ou mais mercados** (30 dias) | **810** |
| Preços no banco | 8.564; 3.461 dos últimos 7 dias |
| Fontes que mais trazem preço | Fort 2.156 produtos · Big Box 1.928 · Oba 1.787 · Carrefour 294 · Atacadão 37 |
| Catálogos lidos pelo nome | Big Box 13.613 páginas lidas, 3.045 ligadas a código (22%) · Fort 12.837 lidas, 2.144 ligadas (17%) |
| Encartes (medição de hoje) | 249 preços lidos de 12 mercados; 25 anúncios ligados a código |
| Dicionário de códigos do DF | 141.468 códigos |
| Comunidade, cupom, busca na hora | desligados (falta o Supabase) |

---

## Parte 1. O que melhorar no que já temos (por prioridade)

### 1. Banco crescendo sem limite no GitHub — URGENTE
O ramo `dados` guarda uma cópia nova do banco a cada coleta: **25 cópias, 228 MB**, e cresce uns 15 MB por dia. Em 2 a 3 meses o repositório fica pesado demais (o GitHub recomenda até 1 GB) e a coleta fica mais lenta para baixar.
**Proposta:** manter só a versão mais recente no ramo (o histórico de preços continua dentro do próprio banco). Isso apaga as cópias antigas do banco no GitHub, então **preciso do seu ok**.

### 2. Preços errados lidos nos encartes
Ainda passam preços pequenos que não são o preço de oferta ("Amaciante Ypê R$ 0,98", "Ovos 30 unidades R$ 2,98", "Heineken R$ 0,99"): são "preço por unidade", "o quilo sai por" ou leitura errada.
**Proposta (eu faço):**
- descartar trechos com "sai por", "valor unitário", "a unidade", "o quilo";
- quando o anúncio estiver ligado a um código que já tem preço em loja, descartar preço abaixo de 40% ou acima de 250% do preço das lojas.

### 3. Comparação de produtos vendidos por quilo e por unidade
O comparativo põe lado a lado "R$ 5,99 o kg" e "R$ 3,99 a unidade" como se fossem a mesma coisa. Acontece em hortifrúti e carnes.
**Proposta (eu faço):** separar a unidade (kg, unidade, bandeja) e só comparar iguais, mostrando o preço por kg ou litro quando der.

### 4. Impostos só para poucos produtos
A estimativa de impostos só cobre cesta básica e higiene ("Ainda não sabemos classificar este produto"). O dicionário do DF traz o **NCM** (classificação fiscal) de 141 mil códigos, que é exatamente o que define o imposto.
**Proposta (eu faço):** classificar pelo NCM, o que cobre quase todo produto escaneado.

### 5. Coleta longa e perto do limite
A coleta diária leva de 3h30 a 4h, e o GitHub corta em 5h30. Cada loja nova aumenta o tempo. Além disso, o GitHub dispara o horário agendado com até 6h de atraso: a coleta marcada para 06h17 de Brasília tem começado por volta de 13h, e o app atualiza à noite.
**Proposta (eu faço):**
- dividir a coleta em partes que rodam em paralelo (lojas, encartes, Mapa de Preços) e juntam os bancos no fim;
- adiantar o horário agendado para compensar o atraso do GitHub.

### 6. Textos legais incompletos
A Política de Privacidade e os Termos de Uso ainda têm **"[NOME DO RESPONSÁVEL]" e "[E-MAIL DE CONTATO]"**. A LGPD exige identificar o responsável e um canal de contato.
**Precisa de você:** nome (ou razão social) e um e-mail de contato.

### 7. Menores
- Nomes de loja com sufixo técnico no app ("Carrefour Mercado (site)").
- A "Big Box" sem loja no nome é a 402/403 Norte.
- Na triangulação, anúncios vagos ligam a muitos códigos (um "Óleo de Soja 900ml" ligou a 21): mostrar menos destaque quando são mais de 5.
- O arquivo `__main__.py` concentra mais de 1.000 linhas de comandos: separar facilita manter. Sem pressa.

---

## Parte 2. O que impede ter 100% dos dados

| Dado que falta | Por quê | O que resolve | Quem age |
|---|---|---|---|
| **Preço de prateleira de todos os mercados, com código de barras** | Só existe nas notas fiscais de consumidor (NFC-e) da Secretaria de Economia; o pedido pela LAI foi negado | Recurso no Participa DF (texto pronto, com o argumento de Alagoas) | **Você** (protocolar) e o governo |
| **Catálogo do Atacadão** (37 produtos) | A plataforma VTEX recusa os servidores do GitHub (excesso de acessos) | Coleta pelo seu computador, ou busca na hora pelo Supabase | **Você** (rodar o script / chaves do Supabase); eu preparo |
| **Comper, Assaí (catálogo), Super Adega, Superbom, Pão de Açúcar** | Bloqueio a robôs, captcha ou preço só carregado por JavaScript | Sem caminho legítimo hoje; só os encartes deles (encartesdf, Portafolhetos) | — |
| **Código de barras nas lojas sem código** (Big Box, Fort, Super Veneza, Bellavia) | O site não mostra o código; ligamos pelo nome (17% a 22% ligados) | Melhorar o vínculo com mais nomes de referência (o dicionário já entrou); nunca chega a 100% | Eu (melhoria contínua) |
| **Preço de encarte lido com precisão** | A leitura gratuita de imagem (Tesseract) erra preço estilizado | Filtros da Parte 1, item 2; leitura por IA de visão seria bem mais precisa, mas tem custo por imagem (você recusou antes) | Eu (filtros); **você** (se quiser reavaliar IA paga) |
| **Redes de bairro** (União, Bistecão, Mineirão e outras ~35) | Só publicam no WhatsApp/Instagram ou no encartesdf; o Instagram proíbe coleta | Seguir pelo encartesdf; preços informados pela comunidade | Comunidade (precisa do Supabase) |
| **Preços informados por pessoas e cupons fiscais** | Comunidade desligada | Ligar o Supabase (URL e chave pública) | **Você** |
| **Leitura do cupom fiscal confirmada** | Nunca testada com cupom real | Um link ou print de cupom com o CPF coberto | **Você** |
| **Preço do mesmo dia em todas as lojas** | Coleta atrasa (horário do GitHub) e lojas grandes levam dias para serem relidas | Item 5 da Parte 1 + releitura diária dos produtos ligados (já feito hoje) | Eu |
| **Impostos para qualquer produto** | Classificação só por categorias manuais | NCM do dicionário (Parte 1, item 4) | Eu |
| **Histórico longo de preços** | A coleta começou em outubro/2026; o histórico só cresce com o tempo | Tempo (e o arquivo da web, onde houver) | — |
| **Textos legais completos (LGPD)** | Faltam responsável e contato | Informar nome e e-mail | **Você** |

## Ordem sugerida

1. **Você:** ok para enxugar o histórico do banco no GitHub (item 1); nome e e-mail para os textos legais; recurso da LAI se ainda no prazo; chaves do Supabase.
2. **Eu, em seguida:** filtros de preço dos encartes (item 2), comparação por unidade (item 3), impostos pelo NCM (item 4), coleta em paralelo e horário (item 5).
