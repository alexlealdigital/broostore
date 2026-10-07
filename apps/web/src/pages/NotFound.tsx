import { Compass } from 'lucide-react';
import { ButtonLink } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { usePageMeta } from '@/hooks/usePageMeta';

export default function NotFound() {
  usePageMeta('Página não encontrada');
  return (
    <Container className="py-20 text-center">
      <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-brand-50 text-brand-600">
        <Compass aria-hidden="true" className="h-8 w-8" />
      </span>
      <p className="mt-5 text-sm font-semibold text-brand-700">Erro 404</p>
      <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-ink">Página não encontrada</h1>
      <p className="mx-auto mt-3 max-w-md text-ink-muted">O endereço pode ter mudado ou não existe mais. Volte para a página inicial ou continue explorando a loja.</p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <ButtonLink href="/" size="lg">
          Ir para o início
        </ButtonLink>
        <ButtonLink href="/loja" variant="secondary" size="lg">
          Ver a loja
        </ButtonLink>
      </div>
    </Container>
  );
}
