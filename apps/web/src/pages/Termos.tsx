import { PageShell, Prose } from '@/components/layout/PageShell';
import { Alert } from '@/components/ui/Alert';
import { usePageMeta } from '@/hooks/usePageMeta';
import { SITE } from '@/lib/config';

export default function Termos() {
  usePageMeta('Termos de uso', 'Termos de uso da BrooStore: compras, entregas, direitos do consumidor e responsabilidades.');
  return (
    <PageShell title="Termos de uso" intro="Regras gerais para usar a loja e comprar produtos na BrooStore.">
      <Alert tone="warning" title="Texto modelo" className="mb-6">
        Este é um texto genérico de referência e deve ser revisado por um profissional jurídico antes de ser tratado como definitivo.
      </Alert>
      <Prose>
        <h2>1. Sobre a BrooStore</h2>
        <p>
          A BrooStore é uma plataforma que reúne ebooks, produtos físicos, games, aplicativos e assinaturas de autores e criadores
          independentes. Ao navegar ou comprar, você concorda com estes termos.
        </p>

        <h2>2. Cadastro e informações</h2>
        <p>
          Para comprar, você informa nome, e-mail, telefone e, em produtos físicos, o endereço de entrega. Você é responsável pela
          veracidade dos dados. O e-mail informado é o canal de entrega dos produtos digitais e das licenças.
        </p>

        <h2>3. Preços e pagamento</h2>
        <ul>
          <li>Os preços são exibidos em reais (R$) e podem ser alterados sem aviso prévio; vale o valor confirmado no checkout.</li>
          <li>O pagamento é processado pelo Mercado Pago, por PIX ou cartão de crédito.</li>
          <li>O valor final (produto, desconto de cupom e frete) é calculado pelo servidor no momento da compra.</li>
          <li>A BrooStore não armazena número, validade ou código de segurança do seu cartão.</li>
        </ul>

        <h2>4. Entrega</h2>
        <ul>
          <li>Produtos digitais: link de acesso enviado por e-mail após a confirmação do pagamento.</li>
          <li>Aplicativos, games e assinaturas: licença ou chave enviada por e-mail após a confirmação do pagamento.</li>
          <li>Produtos físicos: frete calculado pelo CEP no checkout; prazos informados são estimativas das transportadoras.</li>
        </ul>

        <h2>5. Direito de arrependimento e trocas</h2>
        <p>
          Nos termos do Código de Defesa do Consumidor, compras feitas à distância podem ser desfeitas em até 7 dias corridos após o
          recebimento do produto ou a contratação do serviço. Em produtos digitais já entregues, aplicam-se as condições legais
          cabíveis. Para solicitar, entre em contato pelo e-mail abaixo informando os dados da compra.
        </p>

        <h2>6. Conteúdo e propriedade intelectual</h2>
        <p>
          Os produtos pertencem aos seus respectivos autores. É proibido copiar, revender ou redistribuir o conteúdo adquirido sem
          autorização. Licenças são pessoais e vinculadas ao e-mail da compra.
        </p>

        <h2>7. Classificação indicativa</h2>
        <p>
          Cada produto exibe sua classificação indicativa. Conteúdos para maiores de 18 anos ficam ocultos por padrão e exigem
          confirmação de idade.
        </p>

        <h2>8. Responsabilidades</h2>
        <p>
          Nos esforçamos para manter a loja disponível e as informações corretas, mas não garantimos funcionamento ininterrupto. A
          responsabilidade pelo conteúdo de cada produto é do respectivo autor.
        </p>

        <h2>9. Alterações</h2>
        <p>Estes termos podem ser atualizados. A versão vigente é sempre a publicada nesta página.</p>

        <h2>10. Contato</h2>
        <p>
          Dúvidas: <a href={`mailto:${SITE.supportEmail}`}>{SITE.supportEmail}</a>.
        </p>
      </Prose>
    </PageShell>
  );
}
