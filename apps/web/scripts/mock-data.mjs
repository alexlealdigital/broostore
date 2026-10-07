// Dados ficticios usados SOMENTE para testes visuais (scripts/screenshots.mjs).
// Nada aqui toca o Supabase nem a API reais.

const palette = [
  ['#1E40AF', '#60A5FA'],
  ['#7C2D12', '#FDBA74'],
  ['#14532D', '#86EFAC'],
  ['#581C87', '#D8B4FE'],
  ['#0F172A', '#38BDF8'],
  ['#831843', '#F9A8D4'],
  ['#78350F', '#FCD34D'],
  ['#134E4A', '#5EEAD4'],
];

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
}

/** Capa ficticia em SVG (data URI), proporcao 4:5. */
export function cover(title, i, tag = '') {
  const [a, b] = palette[i % palette.length];
  const words = title.split(' ');
  const lines = [];
  let cur = '';
  for (const w of words) {
    if ((cur + ' ' + w).trim().length > 14) {
      lines.push(cur.trim());
      cur = w;
    } else cur += ' ' + w;
  }
  if (cur.trim()) lines.push(cur.trim());
  const text = lines
    .slice(0, 4)
    .map((l, k) => `<text x="40" y="${150 + k * 44}" font-family="Arial, sans-serif" font-size="34" font-weight="700" fill="#fff">${esc(l)}</text>`)
    .join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="480" height="600" viewBox="0 0 480 600">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/></linearGradient></defs>
<rect width="480" height="600" fill="url(#g)"/><circle cx="400" cy="90" r="120" fill="#fff" opacity=".12"/><circle cx="60" cy="560" r="150" fill="#000" opacity=".12"/>
${text}<text x="40" y="560" font-family="Arial, sans-serif" font-size="20" fill="#fff" opacity=".85">${esc(tag)}</text></svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

const d = (n) => new Date(Date.UTC(2026, 8, 30 - n)).toISOString();

const base = [
  [1, 'Guia Prático da Eleição 2026', 'Alex Leal', 29.9, 49.9, 'Política', 'ebook', 'L', 'Um guia direto ao ponto para entender como funcionam campanhas, pesquisas e estratégias na eleição brasileira de 2026.\n\nInclui checklists, exemplos reais e um glossário completo.'],
  [2, 'Marketing Político na Era Digital', 'Marina Duarte', 39.9, null, 'Política', 'ebook', '14', 'Como planejar, medir e ajustar campanhas nas redes sociais respeitando a legislação eleitoral.'],
  [3, 'Receitas Rápidas para a Semana', 'Carla Nunes', 19.9, 29.9, 'Culinária', 'ebook', 'L', '60 receitas para o dia a dia com lista de compras semanal.'],
  [4, 'Finanças Pessoais Sem Complicação', 'Rafael Prado', 24.9, null, 'Finanças', 'ebook', 'L', 'Orçamento, reserva de emergência e primeiros investimentos em linguagem simples.'],
  [5, 'Contos Sombrios, Volume 1', 'Helena Braga', 14.9, null, 'Ficção', 'ebook', '16', 'Doze contos de suspense e terror urbano brasileiro.'],
  [6, 'Obra Exemplo +18 (oculta por padrão)', 'Autor Anônimo', 12.9, null, 'Ficção', 'ebook', '18', 'Conteúdo restrito a maiores de 18 anos.'],
  [7, 'Estratégia e Poder: Edição Impressa', 'Marina Duarte', 79.9, 99.9, 'Política', 'fisico', '12', 'Edição de colecionador, capa dura, 320 páginas. Enviado pelos Correios ou transportadora.'],
  [8, 'Caderno de Campanha Eleitoral', 'Equipe BrooStore', 34.9, null, 'Papelaria', 'fisico', 'L', 'Caderno com 120 folhas pautadas e planner de metas.'],
  [9, 'Camiseta Lizards Games', 'Lizards Games', 59.9, 69.9, 'Vestuário', 'fisico', 'L', 'Camiseta 100% algodão, estampa exclusiva do estúdio.'],
  [10, 'Na Trilha do Risco', 'Lizards Games', 19.9, null, 'Games', 'game', '12', 'Aventura de sobrevivência em terceira pessoa pelas cinco regiões do Brasil.'],
  [11, 'Fighter 3D', 'Lizards Games', 9.9, 14.9, 'Games', 'game', '10', 'Jogo de luta 3D com controles touch para celular.'],
  [12, 'BrooStock Pro (assinatura mensal)', 'Broo Technology', 59, null, 'Aplicativos', 'assinatura', 'L', 'Controle de estoque completo para pequenos negócios. Licença enviada por e-mail.'],
  [13, 'BrooFlow5', 'Broo Technology', 39.9, null, 'Aplicativos', 'app', 'L', 'Fluxos e tarefas em um app leve que funciona offline.'],
  [14, 'Mini Game da Eleição (sem capa)', 'Lizards Games', 4.9, null, 'Games', 'game', 'L', 'Partidas curtíssimas para a eleição de 2026.'],
];

export const products = base.map(([id, title, author, price, original, category, tipo, classificacao, descricao], i) => ({
  id,
  title,
  author,
  price,
  original_price: original,
  image_url: id === 14 ? null : cover(title, i, category.toUpperCase()),
  category,
  link: null,
  descricao,
  active: true,
  classificacao,
  tipo,
  frete: tipo === 'fisico' ? 18 : 0,
  created_at: d(i),
  peso_kg: tipo === 'fisico' ? 0.45 : null,
  altura_cm: tipo === 'fisico' ? 3 : null,
  largura_cm: tipo === 'fisico' ? 16 : null,
  comprimento_cm: tipo === 'fisico' ? 23 : null,
  paginas: tipo === 'ebook' ? 80 + i * 12 : null,
  sobre_autor: id === 1 ? 'Alex Leal é desenvolvedor e criador de jogos políticos desde 2010.' : null,
}));

function rv(productId, ratings) {
  return ratings.map((rating) => ({ product_id: productId, rating }));
}

export const reviews = [
  ...rv(1, [5, 5, 4, 5, 4, 5, 3, 5]),
  ...rv(2, [4, 4, 5]),
  ...rv(3, [5, 4]),
  ...rv(7, [5, 5, 5, 4]),
  ...rv(10, [4, 5, 5, 4, 3, 5, 5]),
  ...rv(11, [3, 4]),
  ...rv(12, [5, 5, 4, 5]),
];

export const freteOptions = [
  { id: 1, empresa: 'Correios', nome: 'PAC', preco: 21.9, prazo: 8, destaque: 'Mais barato' },
  { id: 2, empresa: 'Jadlog', nome: '.Package', preco: 27.5, prazo: 5, destaque: 'Custo-beneficio' },
  { id: 3, empresa: 'Correios', nome: 'SEDEX', preco: 42.8, prazo: 2, destaque: 'Mais rapido' },
];
