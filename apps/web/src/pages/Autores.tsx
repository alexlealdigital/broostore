import { BookOpen, ExternalLink, Mail, Percent, Upload, Wallet } from 'lucide-react';
import { PageShell } from '@/components/layout/PageShell';
import { ButtonLink } from '@/components/ui/Button';
import { usePageMeta } from '@/hooks/usePageMeta';
import { AUTHOR_PANEL_URL } from '@/lib/config';

const STEPS = [
  { icon: Upload, title: 'Cadastre seu produto', text: 'Envie capa, descrição, preço e o arquivo (ou os dados do produto físico) pelo painel do autor.' },
  { icon: BookOpen, title: 'Apareça na vitrine', text: 'Seu produto entra na BrooStore com página própria, avaliações e busca.' },
  { icon: Mail, title: 'Entrega automática', text: 'Ebooks e licenças vão para o e-mail do cliente assim que o pagamento é confirmado.' },
  { icon: Wallet, title: 'Receba pelas vendas', text: 'Pagamentos via Mercado Pago, com PIX e cartão, direto na plataforma.' },
];

export default function Autores() {
  usePageMeta('Venda na BrooStore', 'Publique ebooks, produtos físicos, games e aplicativos na BrooStore e receba pelas suas vendas.');
  return (
    <PageShell
      title="Publique seu trabalho na BrooStore"
      intro="Você cria, a BrooStore cuida da vitrine, do pagamento seguro e da entrega para o seu cliente."
    >
      <ol className="grid gap-4 sm:grid-cols-2">
        {STEPS.map(({ icon: Icon, title, text }, i) => (
          <li key={title} className="flex gap-4 rounded-2xl border border-surface-line bg-white p-5 shadow-card">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
              <Icon aria-hidden="true" className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-base font-bold text-ink">
                {i + 1}. {title}
              </h2>
              <p className="mt-1 text-sm leading-6 text-ink-muted">{text}</p>
            </div>
          </li>
        ))}
      </ol>

      <div className="mt-8 flex items-start gap-3 rounded-2xl border border-brand-100 bg-brand-50/70 p-5 text-sm text-brand-900">
        <Percent aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
        <p>
          Tem dúvidas sobre condições comerciais, tipos de produto aceitos ou como começar? Escreva pela página de contato e respondemos
          por e-mail.
        </p>
      </div>

      <div className="mt-8 flex flex-wrap gap-3">
        <ButtonLink href={AUTHOR_PANEL_URL} external variant="accent" size="lg">
          Acessar o painel do autor
          <ExternalLink aria-hidden="true" className="h-4 w-4" />
          <span className="sr-only">(abre em nova aba)</span>
        </ButtonLink>
        <ButtonLink href="/contato" variant="secondary" size="lg">
          Tirar dúvidas
        </ButtonLink>
      </div>
    </PageShell>
  );
}
