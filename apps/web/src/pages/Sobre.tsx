import { HeartHandshake, ShieldCheck, Sparkles } from 'lucide-react';
import { PageShell } from '@/components/layout/PageShell';
import { ButtonLink } from '@/components/ui/Button';
import { usePageMeta } from '@/hooks/usePageMeta';

const VALUES = [
  { icon: Sparkles, title: 'Curadoria independente', text: 'Valorizamos autores, estúdios e desenvolvedores brasileiros que criam com cuidado.' },
  { icon: ShieldCheck, title: 'Compra segura', text: 'Pagamentos processados pelo Mercado Pago, com PIX ou cartão. Não guardamos dados do seu cartão.' },
  { icon: HeartHandshake, title: 'Suporte de verdade', text: 'Algum problema com a compra ou a entrega? Fale com a gente e resolvemos.' },
];

export default function Sobre() {
  usePageMeta('Sobre', 'Conheça a BrooStore, a loja de ebooks, produtos físicos e aplicativos de autores brasileiros.');
  return (
    <PageShell
      title="Sobre a BrooStore"
      intro="Uma loja brasileira para quem cria e para quem consome ebooks, produtos físicos, games, aplicativos e assinaturas."
    >
      <div className="space-y-4 text-[15px] leading-7 text-ink-soft">
        <p>
          A BrooStore nasceu para aproximar autores e criadores independentes do público, com uma experiência de compra simples:
          você escolhe, paga com PIX ou cartão e recebe por e-mail, ou em casa quando o produto é físico.
        </p>
        <p>
          Para o criador, a BrooStore cuida da vitrine, do pagamento e da entrega automática. Para o cliente, é uma loja confiável
          com avaliações reais e informações claras antes da compra.
        </p>
      </div>

      <ul className="mt-10 grid gap-4 md:grid-cols-3">
        {VALUES.map(({ icon: Icon, title, text }) => (
          <li key={title} className="rounded-2xl border border-surface-line bg-white p-5 shadow-card">
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
              <Icon aria-hidden="true" className="h-5 w-5" />
            </span>
            <h2 className="mt-4 text-base font-bold text-ink">{title}</h2>
            <p className="mt-1.5 text-sm leading-6 text-ink-muted">{text}</p>
          </li>
        ))}
      </ul>

      <div className="mt-10 flex flex-wrap gap-3">
        <ButtonLink href="/loja" size="lg">
          Explorar a loja
        </ButtonLink>
        <ButtonLink href="/contato" variant="secondary" size="lg">
          Falar com a gente
        </ButtonLink>
      </div>
    </PageShell>
  );
}
