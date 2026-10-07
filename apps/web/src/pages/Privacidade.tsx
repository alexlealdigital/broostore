import { PageShell, Prose } from '@/components/layout/PageShell';
import { Alert } from '@/components/ui/Alert';
import { usePageMeta } from '@/hooks/usePageMeta';
import { SITE } from '@/lib/config';

export default function Privacidade() {
  usePageMeta('Política de privacidade', 'Como a BrooStore trata dados pessoais, em linha com a LGPD (Lei 13.709/2018).');
  return (
    <PageShell title="Política de privacidade" intro="Como tratamos seus dados pessoais, em linha com a Lei Geral de Proteção de Dados (LGPD).">
      <Alert tone="warning" title="Texto modelo" className="mb-6">
        Este é um texto genérico de referência e deve ser revisado por um profissional jurídico antes de ser tratado como definitivo.
      </Alert>
      <Prose>
        <h2>1. Quem somos</h2>
        <p>
          A BrooStore é a controladora dos dados pessoais tratados nesta loja. Contato do responsável pelo tratamento:{' '}
          <a href={`mailto:${SITE.supportEmail}`}>{SITE.supportEmail}</a>.
        </p>

        <h2>2. Quais dados coletamos</h2>
        <ul>
          <li>Dados de compra: nome, e-mail, telefone e, em produtos físicos, endereço de entrega.</li>
          <li>Dados de contato: nome, e-mail, assunto e mensagem enviados pelo formulário.</li>
          <li>Avaliações: a nota que você atribui a um produto (sem identificação pessoal).</li>
          <li>
            Dados de pagamento: número do cartão, validade e CVV são informados diretamente ao Mercado Pago e não passam por
            nossos servidores. Recebemos apenas o resultado do pagamento.
          </li>
        </ul>

        <h2>3. Para que usamos</h2>
        <ul>
          <li>Processar o pedido, confirmar o pagamento e entregar o produto, a licença ou o envio físico (execução de contrato).</li>
          <li>Calcular frete e emitir comunicações sobre a compra.</li>
          <li>Responder mensagens e prestar suporte.</li>
          <li>Cumprir obrigações legais e prevenir fraudes.</li>
        </ul>

        <h2>4. Com quem compartilhamos</h2>
        <p>Compartilhamos apenas o necessário com operadores que nos ajudam a prestar o serviço, como:</p>
        <ul>
          <li>Mercado Pago (pagamentos);</li>
          <li>transportadoras e serviço de cotação de frete (produtos físicos);</li>
          <li>provedores de infraestrutura, banco de dados e envio de e-mail.</li>
        </ul>
        <p>Não vendemos seus dados pessoais.</p>

        <h2>5. Cookies e armazenamento no navegador</h2>
        <p>
          A loja não usa cookies de rastreamento publicitário. Podemos guardar no seu navegador, de forma local, apenas preferências
          simples (por exemplo, a confirmação de maioridade da sessão e se você já avaliou um produto).
        </p>

        <h2>6. Por quanto tempo guardamos</h2>
        <p>
          Mantemos os dados pelo tempo necessário para cumprir as finalidades acima e as obrigações legais e fiscais aplicáveis.
        </p>

        <h2>7. Seus direitos</h2>
        <p>
          Conforme o art. 18 da LGPD, você pode solicitar confirmação de tratamento, acesso, correção, anonimização, portabilidade,
          eliminação de dados tratados com consentimento, informações sobre compartilhamento e revogação de consentimento. Envie sua
          solicitação para <a href={`mailto:${SITE.supportEmail}`}>{SITE.supportEmail}</a>.
        </p>

        <h2>8. Segurança</h2>
        <p>Adotamos medidas técnicas e administrativas razoáveis para proteger seus dados, como conexão criptografada (HTTPS).</p>

        <h2>9. Alterações</h2>
        <p>Esta política pode ser atualizada. A versão vigente é sempre a publicada nesta página.</p>
      </Prose>
    </PageShell>
  );
}
