import { Instagram, Lock, Mail } from 'lucide-react';
import { Link } from 'wouter';
import { Container } from '@/components/ui/Container';
import { AREAS, AREA_INFO } from '@/lib/categorias';
import { SITE } from '@/lib/config';
import { Logo } from './Logo';

const col = 'text-sm font-semibold text-white';
const link =
  'rounded text-sm text-brand-100/80 transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white';

export function Footer() {
  return (
    <footer className="mt-16 bg-brand-900 text-brand-100">
      <Container className="py-12">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.6fr_1fr_1fr_1fr]">
          <div>
            <Logo onDark />
            <p className="mt-4 max-w-xs text-sm leading-6 text-brand-100/80">
              Ebooks, produtos físicos e aplicativos de autores e estúdios brasileiros, com pagamento seguro e entrega rápida.
            </p>
            <div className="mt-5 flex gap-2">
              <a
                href={SITE.instagram}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Instagram da Lizards Games (abre em nova aba)"
                className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10 text-white transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
              >
                <Instagram aria-hidden="true" className="h-5 w-5" />
              </a>
              <a
                href={`mailto:${SITE.supportEmail}`}
                aria-label="Enviar e-mail para o suporte"
                className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10 text-white transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
              >
                <Mail aria-hidden="true" className="h-5 w-5" />
              </a>
            </div>
          </div>

          <nav aria-label="Loja">
            <h2 className={col}>Loja</h2>
            <ul className="mt-4 space-y-2.5">
              <li>
                <Link href="/loja" className={link}>
                  Todos os produtos
                </Link>
              </li>
              {AREAS.map((a) => (
                <li key={a}>
                  <Link href={`/loja?area=${a}`} className={link}>
                    {AREA_INFO[a].label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          <nav aria-label="Institucional">
            <h2 className={col}>BrooStore</h2>
            <ul className="mt-4 space-y-2.5">
              <li>
                <Link href="/sobre" className={link}>
                  Sobre nós
                </Link>
              </li>
              <li>
                <Link href="/autores" className={link}>
                  Venda na BrooStore
                </Link>
              </li>
              <li>
                <Link href="/contato" className={link}>
                  Fale conosco
                </Link>
              </li>
            </ul>
          </nav>

          <nav aria-label="Legal">
            <h2 className={col}>Legal</h2>
            <ul className="mt-4 space-y-2.5">
              <li>
                <Link href="/termos" className={link}>
                  Termos de uso
                </Link>
              </li>
              <li>
                <Link href="/privacidade" className={link}>
                  Política de privacidade
                </Link>
              </li>
            </ul>
          </nav>
        </div>

        <div className="mt-10 flex flex-col gap-3 border-t border-white/10 pt-6 text-xs text-brand-100/70 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} BrooStore. Todos os direitos reservados.</p>
          <p className="inline-flex items-center gap-1.5">
            <Lock aria-hidden="true" className="h-3.5 w-3.5" />
            Pagamentos processados com segurança pelo Mercado Pago
          </p>
        </div>
      </Container>
    </footer>
  );
}
