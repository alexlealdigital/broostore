import { describe, expect, it } from 'vitest';
import { MENSAGEM_RECUSA_PADRAO, mensagemRecusaCartao } from './cardErrors';

describe('mensagemRecusaCartao', () => {
  it('orienta ligar ao banco quando precisa de autorizacao', () => {
    expect(mensagemRecusaCartao('cc_rejected_call_for_authorize')).toMatch(/banco precisa autorizar/);
  });
  it('trata saldo insuficiente', () => {
    expect(mensagemRecusaCartao('cc_rejected_insufficient_amount')).toMatch(/limite insuficiente/);
  });
  it('ignora caixa e espacos', () => {
    expect(mensagemRecusaCartao('  CC_REJECTED_BAD_FILLED_DATE ')).toMatch(/validade/);
  });
  it('codigo desconhecido ou vazio usa a mensagem padrao', () => {
    expect(mensagemRecusaCartao('algo_novo')).toBe(MENSAGEM_RECUSA_PADRAO);
    expect(mensagemRecusaCartao(undefined)).toBe(MENSAGEM_RECUSA_PADRAO);
    expect(mensagemRecusaCartao(null)).toBe(MENSAGEM_RECUSA_PADRAO);
  });
  it('nunca expoe o codigo tecnico', () => {
    for (const c of ['cc_rejected_other_reason', 'cc_rejected_high_risk', 'xyz']) {
      expect(mensagemRecusaCartao(c)).not.toMatch(/cc_rejected/);
    }
  });
});
