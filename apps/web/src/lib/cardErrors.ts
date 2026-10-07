/**
 * Traduz o `status_detail` do Mercado Pago (recusa de cartao) para uma mensagem clara em portugues.
 * Nunca mostra o codigo tecnico ao cliente. Codigo desconhecido cai numa mensagem generica segura.
 */
const MENSAGENS: Record<string, string> = {
  cc_rejected_call_for_authorize:
    'O banco precisa autorizar esta compra. Ligue para o número no verso do cartão, autorize e tente de novo, ou use outro cartão ou o PIX.',
  cc_rejected_insufficient_amount: 'Saldo ou limite insuficiente no cartão. Tente outro cartão ou pague com PIX.',
  cc_rejected_bad_filled_card_number: 'O número do cartão parece incorreto. Confira e tente de novo.',
  cc_rejected_bad_filled_date: 'A validade do cartão parece incorreta. Confira e tente de novo.',
  cc_rejected_bad_filled_security_code: 'O código de segurança (CVV) parece incorreto. Confira e tente de novo.',
  cc_rejected_bad_filled_other: 'Algum dado do cartão parece incorreto. Confira e tente de novo.',
  cc_rejected_form_error: 'Algum dado do cartão parece incorreto. Confira e tente de novo.',
  cc_rejected_card_disabled: 'Este cartão está desabilitado. Ative-o no app do banco ou use outro cartão.',
  cc_rejected_card_error: 'Não foi possível processar este cartão. Tente outro cartão ou pague com PIX.',
  cc_rejected_duplicated_payment: 'Você já fez um pagamento igual a este há pouco. Confira seu e-mail antes de tentar de novo.',
  cc_rejected_high_risk: 'Por segurança, este pagamento não foi aprovado. Tente outro cartão ou pague com PIX.',
  cc_rejected_blacklist: 'Este pagamento não pôde ser aprovado. Tente outro cartão ou pague com PIX.',
  cc_rejected_invalid_installments: 'Este cartão não aceita o parcelamento escolhido. Escolha outro número de parcelas.',
  cc_rejected_max_attempts: 'Muitas tentativas com este cartão. Aguarde um pouco ou use outro cartão ou o PIX.',
  cc_rejected_other_reason: 'O banco não aprovou este pagamento. Tente outro cartão ou pague com PIX.',
};

export const MENSAGEM_RECUSA_PADRAO =
  'Pagamento não aprovado. Confira os dados do cartão, tente outro cartão ou pague com PIX.';

export function mensagemRecusaCartao(statusDetail?: string | null): string {
  const chave = (statusDetail ?? '').trim().toLowerCase();
  return MENSAGENS[chave] ?? MENSAGEM_RECUSA_PADRAO;
}
