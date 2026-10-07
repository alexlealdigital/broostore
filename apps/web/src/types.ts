/** Tipos compartilhados da loja. Colunas desconhecidas do Supabase sao sempre opcionais. */

export type Area = 'digitais' | 'fisicos' | 'aplicativos';

/** Linha da tabela `products` como vem do Supabase (tudo que nao e garantido e opcional). */
export interface ProductRow {
  id: number | string;
  title?: string | null;
  author?: string | null;
  price?: number | string | null;
  original_price?: number | string | null;
  image_url?: string | null;
  category?: string | null;
  link?: string | null;
  descricao?: string | null;
  active?: boolean | null;
  classificacao?: string | null;
  tipo?: string | null;
  frete?: number | string | null;
  created_at?: string | null;
  // Fisicos
  peso_kg?: number | string | null;
  altura_cm?: number | string | null;
  largura_cm?: number | string | null;
  comprimento_cm?: number | string | null;
  // Colunas extras que o site antigo ja lia (todas opcionais)
  paginas?: number | string | null;
  intro?: string | null;
  sobre_autor?: string | null;
  peso?: string | null;
  dimensoes?: string | null;
  prazo_prod?: string | null;
  specs?: string | null;
  estoque?: number | string | null;
}

/** Produto normalizado para a UI. */
export interface Product {
  id: number;
  title: string;
  author: string;
  price: number;
  originalPrice: number | null;
  imageUrl: string | null;
  category: string;
  descricao: string;
  classificacao: string;
  /** tipo normalizado (trim + lowercase). Vazio vira "ebook". */
  tipo: string;
  area: Area;
  /** frete fixo cadastrado (referencia); o valor real vem da cotacao por CEP. */
  frete: number;
  createdAt: string | null;
  link: string | null;
  // fisicos (cadastro de frete)
  pesoKg: number | null;
  alturaCm: number | null;
  larguraCm: number | null;
  comprimentoCm: number | null;
  // extras opcionais
  paginas: string | null;
  intro: string | null;
  sobreAutor: string | null;
  peso: string | null;
  dimensoes: string | null;
  prazoProducao: string | null;
  specs: string | null;
  estoque: number | null;
}

export interface RatingSummary {
  average: number;
  count: number;
}

export type RatingsMap = Record<string, RatingSummary>;

export interface ReviewRow {
  product_id: number | string;
  rating: number | string;
}

export interface Distribution {
  /** indice 0 = 1 estrela ... indice 4 = 5 estrelas */
  counts: [number, number, number, number, number];
  total: number;
  average: number;
}

export type LoadStatus = 'idle' | 'loading' | 'success' | 'error';

/* ---------- API de pagamentos ---------- */

export interface ApiProdutoResponse {
  status?: string;
  id: number;
  nome: string;
  preco: number;
  tipo?: string | null;
}

export interface CupomInfo {
  id: number;
  codigo: string;
  tipo?: string;
  valor?: number;
  descricao?: string;
}

export interface CupomCalculo {
  valor_original: number;
  desconto: number;
  valor_final: number;
  percentual_aplicado?: number;
}

export interface ValidarCupomResponse {
  status: string;
  cupom: CupomInfo;
  calculo: CupomCalculo;
}

export interface FreteOption {
  id: string;
  empresa: string;
  nome: string;
  preco: number;
  prazo: number | null;
  destaque: string;
}

export interface Endereco {
  cep: string;
  rua: string;
  numero: string;
  complemento: string;
  bairro: string;
  cidade: string;
  estado: string;
}

export interface PixPayload {
  email: string;
  nome: string;
  telefone: string;
  product_id: number;
  cupom_id: number | null;
  endereco?: Endereco;
  frete?: number;
  frete_servico_id?: string | null;
  cep_destino?: string;
}

export interface CobrancaInfo {
  external_reference?: string;
  [key: string]: unknown;
}

export interface PixResponse {
  status?: string;
  message?: string;
  qr_code_base64: string;
  qr_code_text: string;
  payment_id?: number | string;
  cobranca?: CobrancaInfo;
  frete_aplicado?: number;
  subtotal_produto?: number;
  total_cobrado?: number;
  desconto_aplicado?: {
    cupom_codigo: string;
    valor_desconto: number;
    valor_final?: number;
  };
}

/** Corpo enviado ao nosso backend para pagamento com cartao: SOMENTE token, nunca dados do cartao. */
export interface CardPayload {
  token: string;
  payment_method_id: string;
  issuer_id: string | number | null;
  installments: number;
  email: string;
  nome: string;
  telefone: string;
  cpf: string;
  product_id: number;
  cupom_id: number | null;
  endereco?: Endereco;
  frete?: number;
  frete_servico_id?: string | null;
  cep_destino?: string;
}

export interface CardResponse {
  status: string;
  status_detail?: string;
  payment_id?: number | string;
  mensagem?: string;
  frete_aplicado?: number;
  subtotal_produto?: number;
  total_cobrado?: number;
}

export interface CobrancaStatusResponse {
  status: string;
  pago: boolean;
}

/* ---------- Mercado Pago SDK (subconjunto usado) ---------- */

export interface MpPayerCost {
  installments: number;
  installment_amount: number;
  recommended_message?: string;
}

export interface MpInstance {
  getPaymentMethods(args: { bin: string }): Promise<{
    results?: Array<{ id: string; thumbnail?: string; name?: string }>;
  }>;
  getIssuers(args: { paymentMethodId: string; bin: string }): Promise<Array<{ id: string | number }> | undefined>;
  getInstallments(args: { amount: string; bin: string; paymentMethodId: string }): Promise<
    Array<{ payer_costs?: MpPayerCost[] }> | undefined
  >;
  createCardToken(args: {
    cardNumber: string;
    cardholderName: string;
    cardExpirationMonth: string;
    cardExpirationYear: string;
    securityCode: string;
    identificationType: string;
    identificationNumber: string;
  }): Promise<{ id?: string } | undefined>;
}

export type MpConstructor = new (publicKey: string, options?: { locale?: string }) => MpInstance;

declare global {
  interface Window {
    MercadoPago?: MpConstructor;
  }
}
