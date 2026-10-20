# Rodar a partir do Brasil

Alguns sites públicos recusam conexões vindas de fora do país. Em 20/10/2026, a partir dos servidores do GitHub (EUA):

| Site | Resposta | O que significa |
|---|---|---|
| CEASA-DF, IPE-DF, dados.df.gov.br | "Página bloqueada ... política de segurança" (firewall do GDF) | bloqueio por endereço, não por robô |
| Conab (Portal de Informações) | "403 - Acesso proibido" | idem |
| Diário Oficial da União | conexão encerrada | idem |
| Confaz | sem resposta | provável idem |

Do seu computador, no Brasil, o acesso é o mesmo de qualquer pessoa. As regras do projeto continuam valendo.

## Passo a passo (uma vez)

1. Instale o Python 3.10 ou mais novo (python.org) e o Git (git-scm.com).
2. Clone o repositório: `git clone https://github.com/Viniaragomes/historico-precos.git`
3. Entre na pasta: `cd historico-precos`
4. Rode: `python ferramentas/coleta_brasil.py --publicar`

O relatório vai para `relatorios/brasil/` no GitHub, e eu leio de lá para escrever os coletores desses sites.

## Por que não ligar seu computador ao GitHub Actions

O GitHub permite usar o seu computador como "runner", mas desaconselha isso em repositórios públicos:
qualquer pessoa pode abrir um pull request que rodaria código na sua máquina. Por isso o caminho é o script acima,
que você roda quando quiser (ou agenda no Agendador de Tarefas do Windows / cron no Linux e Mac).
