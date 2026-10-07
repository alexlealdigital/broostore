import { CheckCircle2, Clock, KeyRound, Mail, Truck } from 'lucide-react';
import { Link } from 'wouter';
import { ButtonLink } from '@/components/ui/Button';
import { entregaDaArea, type Entrega } from '@/lib/categorias';
import { formatBRL } from '@/lib/format';
import type { Area } from '@/types';

const NEXT: Record<Entrega, { icon: typeof Mail; title: string; text: (email: string) => string }> = {
  'email-link': {
    icon: Mail,
    title: 'Seu produto está a caminho do e-mail',
    text: (email) => `Enviamos o link de download para ${email}. Se não encontrar, confira a caixa de spam e a aba Promoções.`,
  },
  'email-licenca': {
    icon: KeyRound,
    title: 'Sua licença chega por e-mail',
    text: (email) => `A licença/chave de acesso será enviada para ${email}. Ela fica vinculada a esse e-mail.`,
  },
  frete: {
    icon: Truck,
    title: 'Enviaremos um e-mail de confirmação',
    text: (email) => `Você receberá a confirmação do pedido em ${email} e entraremos em contato sobre o envio e o rastreio.`,
  },
};

interface Props {
  area: Area;
  email: string;
  productTitle: string;
  total: number | null;
  message?: string;
  returnUrl: string | null;
}

export function PaymentSuccess({ area, email, productTitle, total, message, returnUrl }: Props) {
  const next = NEXT[entregaDaArea(area)];
  const Icon = next.icon;
  return (
    <div className="rounded-2xl border border-emerald-200 bg-white p-6 text-center shadow-card sm:p-10" role="status" aria-live="polite">
      <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
        <CheckCircle2 aria-hidden="true" className="h-9 w-9" />
      </span>
      <h2 className="mt-4 text-2xl font-extrabold text-ink sm:text-3xl">Pagamento confirmado</h2>
      <p className="mt-1.5 text-sm text-ink-muted">
        {productTitle}
        {total !== null ? ` · ${formatBRL(total)}` : ''}
      </p>

      <div className="mx-auto mt-6 max-w-md rounded-xl bg-emerald-50/70 p-4 text-left">
        <p className="flex items-center gap-2 text-sm font-bold text-emerald-900">
          <Icon aria-hidden="true" className="h-4 w-4" />
          {next.title}
        </p>
        <p className="mt-1.5 text-sm leading-6 text-emerald-900/90">{next.text(email)}</p>
        {message && <p className="mt-2 text-sm text-emerald-900/80">{message}</p>}
      </div>

      <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
        {returnUrl && (
          <ButtonLink href={returnUrl} external sameTab variant="primary" size="lg">
            Voltar ao aplicativo
          </ButtonLink>
        )}
        <ButtonLink href="/loja" variant={returnUrl ? 'secondary' : 'primary'} size="lg">
          Continuar comprando
        </ButtonLink>
      </div>
      <p className="mt-5 text-xs text-ink-muted">
        Algo errado? <Link href="/contato" className="font-semibold text-brand-700 hover:underline">
          Fale com a gente
        </Link> informando o e-mail da compra.
      </p>
    </div>
  );
}

export function PaymentReview({ message, returnUrl }: { message: string; returnUrl: string | null }) {
  return (
    <div className="rounded-2xl border border-amber-200 bg-white p-6 text-center shadow-card sm:p-10" role="status" aria-live="polite">
      <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-amber-50 text-amber-600">
        <Clock aria-hidden="true" className="h-9 w-9" />
      </span>
      <h2 className="mt-4 text-2xl font-extrabold text-ink">Pagamento em análise</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink-muted">{message}</p>
      <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
        {returnUrl && (
          <ButtonLink href={returnUrl} external sameTab variant="primary" size="lg">
            Voltar ao aplicativo
          </ButtonLink>
        )}
        <ButtonLink href="/loja" variant={returnUrl ? 'secondary' : 'primary'} size="lg">
          Voltar para a loja
        </ButtonLink>
      </div>
    </div>
  );
}
