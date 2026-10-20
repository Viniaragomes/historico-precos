# Teste com usuários: Preço com Prova

**Objetivo:** ver pessoas reais usando o app e descobrir onde elas travam, o que não entendem e se confiam no que veem. Com 5 pessoas já aparecem cerca de 80% dos problemas de uso.

**Duração:** 20 a 25 minutos por pessoa.

## 1. Quem chamar (5 pessoas no DF)

Varie o perfil, porque não pode ser só gente parecida com você:

| # | Perfil sugerido |
|---|---|
| 1 | Quem faz as compras da casa, 30 a 50 anos, Android |
| 2 | Pessoa com mais de 60 anos |
| 3 | Jovem, 18 a 25 anos, iPhone |
| 4 | Pessoa que compra em atacarejo e compara preço (bem econômica) |
| 5 | Pessoa com pouca familiaridade com aplicativos |

Não chame quem ajudou a construir o app nem quem já viu as telas.

## 2. Antes de começar

- Use o **celular da própria pessoa** e o link do app publicado.
- Tenha em mãos **2 ou 3 produtos reais** que o app acompanha (ou faça o teste no mercado).
- Prepare a planilha `teste-com-usuarios-planilha.csv` e um cronômetro.
- **Não grave** voz ou tela sem permissão expressa. Na planilha, identifique a pessoa só por número (P1, P2…), sem nome. Isso também atende à LGPD.

**O que dizer (leia em voz alta):**

> "Obrigado por ajudar. Estamos testando o **aplicativo**, não você: não existe resposta errada. Se algo for difícil, a culpa é do app, e é exatamente isso que queremos descobrir. Vou pedir algumas tarefas. Fale em voz alta o que está pensando enquanto usa. Eu não vou ajudar durante as tarefas, mas no fim tiro todas as dúvidas. Posso anotar o que você disser, sem seu nome?"

## 3. Tarefas

Leia **uma tarefa por vez**, exatamente como está. Não diga onde clicar. Se a pessoa travar por mais de 2 minutos, anote "falha" e passe para a próxima.

Depois de cada tarefa, pergunte: **"De 1 (muito difícil) a 7 (muito fácil), quão fácil foi?"** e anote na coluna `facilidade_1a7`.

| # | Tarefa (leia assim) | Sucesso quando a pessoa… | Observe |
|---|---|---|---|
| T1 | "Você está no mercado com este café na mão. Descubra em qual loja ele está mais barato." | escaneia (ou digita) e aponta a loja certa | achou o botão de escanear? entendeu o número grande? |
| T2 | "Quanto esse café custava mais ou menos um ano atrás?" | lê o gráfico ou a tabela e dá um valor próximo | usou o gráfico? tocou nele? achou a tabela? |
| T3 | "O preço subiu. O app sabe dizer por quê?" | abre uma mudança e lê as provas | entendeu que nem toda causa é comprovada? |
| T4 | "Quanto do preço desse produto é imposto?" | encontra o cartão de impostos e diz o valor | achou o cartão? entendeu "estimativa"? |
| T5 | "Imagine que na prateleira o preço está diferente do app. Avise isso no aplicativo." | usa "Está certo?" → "Não, está diferente" e informa o valor | entendeu o pedido de consentimento? leu? desistiu? |
| T6 | "Você quer ficar de olho no preço deste produto. Como faria?" | marca o produto e o encontra na tela inicial | achou o marcador no topo? |
| T7 | "A foto deste produto parece errada. Como você avisaria?" | encontra "Reportar um problema" | procurou onde? |

## 4. Perguntas de entendimento (logo depois das tarefas)

Anote as respostas com as palavras da pessoa:

1. "Com suas palavras, o que significa quando aparece **COMPROVADO**? E **ASSOCIADO**?"
   - Se a pessoa achar que ASSOCIADO também é prova, os selos precisam mudar. É o ponto mais importante do teste.
2. "Você confiaria nesse preço para decidir onde comprar? Por quê?"
3. "O que as **estrelas** ao lado do preço querem dizer?"
4. "O que mais te incomodou?"
5. "O que faria você usar isso toda semana? E o que faria você desinstalar?"

## 5. Questionário final (SUS)

Peça para responder de 1 (discordo totalmente) a 5 (concordo totalmente) e anote na planilha de SUS:

1. Eu acho que gostaria de usar este aplicativo com frequência.
2. Eu achei o aplicativo desnecessariamente complexo.
3. Eu achei o aplicativo fácil de usar.
4. Eu acho que precisaria de ajuda de uma pessoa com conhecimentos técnicos para usar o aplicativo.
5. Eu acho que as várias funções do aplicativo estão muito bem integradas.
6. Eu acho que o aplicativo apresenta muita inconsistência.
7. Eu imagino que as pessoas aprenderão como usar este aplicativo rapidamente.
8. Eu achei o aplicativo atrapalhado de usar.
9. Eu me senti confiante ao usar o aplicativo.
10. Eu precisei aprender várias coisas novas antes de conseguir usar o aplicativo.

## 6. Depois dos 5 testes

Rode:

```bash
python ferramentas/resumo_teste.py docs/teste-com-usuarios-planilha.csv docs/teste-com-usuarios-sus.csv
```

O script mostra a taxa de sucesso e a facilidade por tarefa, a nota SUS e onde as pessoas travaram.

**Metas para considerar o app pronto para abrir ao público:**

| Métrica | Meta |
|---|---|
| Sucesso em cada tarefa | 4 de 5 pessoas (80%) |
| Facilidade média por tarefa | 5 ou mais (de 7) |
| Nota SUS média | 68 ou mais (média de mercado); 80 ou mais é excelente |
| Pergunta 1 de entendimento (COMPROVADO x ASSOCIADO) | 4 de 5 pessoas entendem a diferença |

Me mande as duas planilhas preenchidas e as citações mais marcantes, e eu ajusto o app com base nelas.
