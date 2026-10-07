import { useEffect } from 'react';

const SUFFIX = 'BrooStore';
const DEFAULT_DESCRIPTION =
  'BrooStore: ebooks, produtos físicos e aplicativos. Pagamento seguro com Mercado Pago, PIX e cartão, e entrega imediata por e-mail.';

/** Atualiza <title> e meta description por pagina (SPA). */
export function usePageMeta(title?: string, description?: string) {
  useEffect(() => {
    document.title = title ? `${title} | ${SUFFIX}` : `${SUFFIX} | Ebooks, produtos físicos e aplicativos`;
    const meta = document.querySelector<HTMLMetaElement>('meta[name="description"]');
    if (meta) meta.content = description ?? DEFAULT_DESCRIPTION;
  }, [title, description]);
}
