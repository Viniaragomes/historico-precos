// Confiança da comunidade, no estilo do Waze: quem está na loja confirma ou contesta, e a reputação pesa.
// Isto NÃO é nível de prova: votos confirmam o que se vê (preço, promoção), nunca provam uma causa.

// quanto cada fonte já merece de confiança antes de qualquer voto (0 a 1)
export const CONFIANCA_DA_FONTE = { vtex: 0.6, wayback: 0.7, open_prices: 0.5, usuario: 0.35 };
const FORCA_DA_FONTE = 2; // a fonte vale como 2 votos
const MEIA_VIDA_FONTE_DIAS = 14; // preço sem confirmação vai ficando incerto
const MEIA_VIDA_VOTO_DIAS = 7; // voto antigo pesa menos: preço muda

export const NIVEIS = [
  { nivel: 1, nome: "Iniciante", min: 0 },
  { nivel: 2, nome: "Colaborador", min: 20 },
  { nivel: 3, nome: "Fiscal de preços", min: 100 },
  { nivel: 4, nome: "Especialista", min: 300 },
  { nivel: 5, nome: "Guardião do preço", min: 1000 },
];

export const PONTOS = { confirmar: 1, corrigir: 3, evidencia: 5, avaliar_causa: 1 };
export const LIMITE_VOTOS_POR_HORA = 60;

const DIA = 864e5;

export function nivelPorPontos(pontos = 0) {
  const atual = [...NIVEIS].reverse().find((n) => pontos >= n.min);
  const proximo = NIVEIS.find((n) => n.min > pontos) || null;
  const progresso = proximo ? (pontos - atual.min) / (proximo.min - atual.min) : 1;
  return { ...atual, pontos, proximo, progresso };
}

// voto de quem tem mais reputação pesa mais: de 1 (iniciante) a 3 (guardião)
export function pesoDoVoto(pontosDoAutor = 0) {
  return 1 + (nivelPorPontos(pontosDoAutor).nivel - 1) * 0.5;
}

function decaimento(idadeDias, meiaVida) {
  return 0.5 ** (Math.max(0, idadeDias) / meiaVida);
}

/**
 * ponto: { fonte, data: "AAAA-MM-DD" }
 * votos: [{ valor: true|false, pontos_autor, criado_em: ISO }]
 * Média de uma distribuição Beta: a fonte entra como votos iniciais, que perdem força com o tempo.
 */
export function confiancaPreco(ponto, votos = [], agora = Date.now()) {
  const base = CONFIANCA_DA_FONTE[ponto.fonte] ?? 0.5;
  const idadePreco = (agora - new Date(ponto.data + "T12:00:00").getTime()) / DIA;
  const forca = FORCA_DA_FONTE * decaimento(idadePreco, MEIA_VIDA_FONTE_DIAS);
  // o que a fonte perde de força vira "não sei" (meio a meio)
  let sim = base * forca + 0.5 * (FORCA_DA_FONTE - forca);
  let nao = (1 - base) * forca + 0.5 * (FORCA_DA_FONTE - forca);

  let confirmacoes = 0, contestacoes = 0, volume = 0;
  for (const v of votos) {
    const idade = (agora - new Date(v.criado_em).getTime()) / DIA;
    const peso = pesoDoVoto(v.pontos_autor) * decaimento(idade, MEIA_VIDA_VOTO_DIAS);
    volume += peso;
    if (v.valor) { sim += peso; confirmacoes++; } else { nao += peso; contestacoes++; }
  }
  const score = sim / (sim + nao);
  return {
    score,
    estrelas: Math.round(score * 10) / 2, // de meia em meia estrela
    rotulo: rotulo(score, confirmacoes + contestacoes),
    confirmacoes,
    contestacoes,
    volume,
  };
}

function rotulo(score, votos) {
  if (!votos) return "Ainda sem confirmações";
  if (score >= 0.8) return "Muito confiável";
  if (score >= 0.6) return "Confiável";
  if (score >= 0.4) return "Incerto";
  return "Contestado";
}

// preço que a comunidade informa quando contesta: a mediana resiste a valores absurdos
export function precoSugerido(votos = []) {
  const valores = votos.filter((v) => !v.valor && v.preco_informado > 0).map((v) => Number(v.preco_informado)).sort((a, b) => a - b);
  if (valores.length < 2) return null;
  const meio = Math.floor(valores.length / 2);
  return { preco: valores.length % 2 ? valores[meio] : (valores[meio - 1] + valores[meio]) / 2, informantes: valores.length };
}

// "essa explicação ajudou?": opinião, não prova
export function utilidade(votos = []) {
  const uteis = votos.filter((v) => v.valor).length;
  return { uteis, total: votos.length, percentual: votos.length ? (uteis / votos.length) * 100 : null };
}

export const chavePreco = (oferta) => `${oferta.loja}|${oferta.data}`;
export const chaveCausa = (m) => `${m.loja}|${m.data_anterior}|${m.data_nova}`;
