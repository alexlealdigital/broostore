import { useState } from 'react';
import { tipoInfo } from '@/lib/categorias';
import { cn } from '@/lib/cn';

interface Props {
  src: string | null;
  alt: string;
  tipo?: string;
  className?: string;
  /** "eager" para imagem principal da pagina de produto. */
  loading?: 'lazy' | 'eager';
}

/** Capa do produto com fallback elegante (sem imagem ou imagem quebrada). */
export function ProductImage({ src, alt, tipo, className, loading = 'lazy' }: Props) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const broken = !src || failedSrc === src;
  const { icon: Icon } = tipoInfo(tipo);

  if (broken) {
    return (
      <div
        role="img"
        aria-label={`${alt} (sem imagem)`}
        className={cn('flex items-center justify-center bg-gradient-to-br from-brand-100 via-brand-50 to-white text-brand-400', className)}
      >
        <Icon aria-hidden="true" className="h-1/4 w-1/4 min-h-8 min-w-8" strokeWidth={1.5} />
      </div>
    );
  }
  return (
    <img
      src={src}
      alt={alt}
      loading={loading}
      decoding="async"
      onError={() => setFailedSrc(src)}
      className={cn('object-cover', className)}
    />
  );
}
