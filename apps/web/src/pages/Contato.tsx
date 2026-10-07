import { CheckCircle2, Mail, Send } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { PageShell } from '@/components/layout/PageShell';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { InputField, TextareaField } from '@/components/ui/Field';
import { usePageMeta } from '@/hooks/usePageMeta';
import { SITE } from '@/lib/config';
import { submitContato } from '@/lib/products';
import { isEmail, isFullName } from '@/lib/validators';

interface Errors {
  nome?: string;
  email?: string;
  assunto?: string;
  mensagem?: string;
}

export default function Contato() {
  usePageMeta('Contato', 'Fale com a BrooStore: dúvidas sobre compras, entregas, parcerias e publicação de produtos.');
  const [errors, setErrors] = useState<Errors>({});
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    // Campo-isca contra robos: usuarios reais nunca o preenchem.
    if (String(data.get('website') ?? '').trim()) return;

    const nome = String(data.get('nome') ?? '').trim();
    const email = String(data.get('email') ?? '').trim();
    const assunto = String(data.get('assunto') ?? '').trim();
    const mensagem = String(data.get('mensagem') ?? '').trim();

    const next: Errors = {};
    if (!isFullName(nome)) next.nome = 'Informe seu nome.';
    if (!isEmail(email)) next.email = 'Informe um e-mail válido.';
    if (assunto.length < 3) next.assunto = 'Informe o assunto.';
    if (mensagem.length < 10) next.mensagem = 'Escreva uma mensagem com pelo menos 10 caracteres.';
    setErrors(next);
    if (Object.keys(next).length > 0) return;

    setStatus('sending');
    try {
      await submitContato({ nome, email, assunto, mensagem });
      setStatus('sent');
      form.reset();
    } catch {
      setStatus('error');
    }
  };

  return (
    <PageShell title="Fale com a BrooStore" intro="Dúvidas sobre uma compra, entrega, parceria ou publicação? Escreva para nós.">
      <div className="grid gap-8 lg:grid-cols-[1fr_280px]">
        <div className="rounded-2xl border border-surface-line bg-white p-5 shadow-card sm:p-7">
          {status === 'sent' ? (
            <div className="py-6 text-center" role="status">
              <CheckCircle2 aria-hidden="true" className="mx-auto h-12 w-12 text-emerald-600" />
              <h2 className="mt-3 text-xl font-bold text-ink">Mensagem enviada!</h2>
              <p className="mt-1.5 text-sm text-ink-muted">Recebemos seu contato e retornaremos em breve pelo e-mail informado.</p>
              <Button className="mt-5" variant="secondary" onClick={() => setStatus('idle')}>
                Enviar outra mensagem
              </Button>
            </div>
          ) : (
            <form onSubmit={onSubmit} noValidate className="grid gap-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <InputField label="Nome" name="nome" autoComplete="name" required error={errors.nome} maxLength={120} />
                <InputField label="E-mail" name="email" type="email" autoComplete="email" required error={errors.email} maxLength={160} />
              </div>
              <InputField label="Assunto" name="assunto" required error={errors.assunto} maxLength={140} />
              <TextareaField label="Mensagem" name="mensagem" required error={errors.mensagem} maxLength={4000} />
              {/* isca anti-robo, invisivel para pessoas e leitores de tela */}
              <div aria-hidden="true" className="absolute -left-[9999px] h-0 w-0 overflow-hidden">
                <label>
                  Não preencha este campo
                  <input type="text" name="website" tabIndex={-1} autoComplete="off" />
                </label>
              </div>
              {status === 'error' && (
                <Alert tone="error" title="Não foi possível enviar">
                  Tente novamente em instantes ou escreva para {SITE.supportEmail}.
                </Alert>
              )}
              <Button type="submit" size="lg" loading={status === 'sending'} className="sm:w-fit">
                <Send aria-hidden="true" className="h-4 w-4" />
                {status === 'sending' ? 'Enviando...' : 'Enviar mensagem'}
              </Button>
            </form>
          )}
        </div>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-surface-line bg-white p-5 shadow-card">
            <Mail aria-hidden="true" className="h-5 w-5 text-brand-600" />
            <h2 className="mt-2 text-sm font-bold text-ink">E-mail</h2>
            <a href={`mailto:${SITE.supportEmail}`} className="mt-1 block break-all text-sm font-medium text-brand-700 hover:underline">
              {SITE.supportEmail}
            </a>
          </div>
          <div className="rounded-2xl border border-surface-line bg-white p-5 text-sm leading-6 text-ink-muted shadow-card">
            <h2 className="text-sm font-bold text-ink">Sobre sua compra</h2>
            <p className="mt-1">Informe o e-mail usado na compra para agilizarmos o atendimento.</p>
          </div>
        </aside>
      </div>
    </PageShell>
  );
}
