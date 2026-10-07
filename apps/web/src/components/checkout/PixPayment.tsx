import { Check, Clock, Copy, Loader2, RefreshCw } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { usePixStatus } from '@/hooks/usePixStatus';
import { copyText } from '@/lib/clipboard';
import { formatBRL } from '@/lib/format';
import type { PixResponse } from '@/types';

interface Props {
  pix: PixResponse;
  externalReference: string | null;
  total: number | null;
  email: string;
  onPaid: () => void;
  onNewCode: () => void;
}

const STEPS = [
  'Abra o aplicativo do seu banco e escolha pagar com Pix.',
  'Escaneie o QR Code ou use a opção "Pix Copia e Cola".',
  'Confira o valor e confirme o pagamento.',
];

export function PixPayment({ pix, externalReference, total, email, onPaid, onNewCode }: Props) {
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { state, checkNow } = usePixStatus(externalReference, onPaid);
  const [checking, setChecking] = useState(false);

  useEffect(() => () => void (timer.current && clearTimeout(timer.current)), []);

  const copy = async () => {
    const ok = await copyText(pix.qr_code_text);
    setCopied(ok);
    setCopyFailed(!ok);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      setCopied(false);
      setCopyFailed(false);
    }, 3000);
  };

  const verify = async () => {
    setChecking(true);
    try {
      await checkNow();
    } finally {
      setChecking(false);
    }
  };

  const shownTotal = total ?? pix.total_cobrado ?? null;

  return (
    <div className="rounded-2xl border border-surface-line bg-white p-5 shadow-card sm:p-7" aria-labelledby="pix-title">
      <div className="text-center">
        <h2 id="pix-title" className="text-xl font-extrabold text-ink sm:text-2xl">
          Pague com PIX
        </h2>
        {shownTotal !== null && (
          <p className="mt-1 text-sm text-ink-muted">
            Valor a pagar: <strong className="text-ink">{formatBRL(shownTotal)}</strong>
          </p>
        )}
        {pix.desconto_aplicado && (
          <p className="mt-1 text-sm font-medium text-emerald-700">
            Cupom {pix.desconto_aplicado.cupom_codigo} aplicado: você economizou {formatBRL(pix.desconto_aplicado.valor_desconto)}.
          </p>
        )}
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-[auto_1fr] md:items-start">
        {pix.qr_code_base64 ? (
          <div className="mx-auto rounded-2xl border border-surface-line bg-white p-3 shadow-sm">
            <img
              src={`data:image/jpeg;base64,${pix.qr_code_base64}`}
              alt="QR Code PIX para pagamento"
              width={224}
              height={224}
              className="h-56 w-56 max-w-full"
            />
          </div>
        ) : null}

        <div className="min-w-0">
          <label htmlFor="pix-code" className="text-sm font-semibold text-ink">
            PIX Copia e Cola
          </label>
          <div className="mt-1.5 flex gap-2">
            <input
              id="pix-code"
              readOnly
              value={pix.qr_code_text}
              onFocus={(e) => e.currentTarget.select()}
              className="h-11 min-w-0 flex-1 truncate rounded-lg border border-surface-line bg-surface px-3 font-mono text-xs text-ink-soft focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/40"
            />
            <Button onClick={copy} variant={copied ? 'success' : 'primary'} className="shrink-0">
              {copied ? <Check aria-hidden="true" className="h-4 w-4" /> : <Copy aria-hidden="true" className="h-4 w-4" />}
              {copied ? 'Copiado!' : 'Copiar código'}
            </Button>
          </div>
          <p aria-live="polite" className="mt-1.5 min-h-[1.25rem] text-xs">
            {copied && <span className="text-emerald-700">Código copiado. Cole no app do seu banco.</span>}
            {copyFailed && <span className="text-red-600">Não foi possível copiar. Selecione o código e copie manualmente.</span>}
          </p>

          <ol className="mt-3 space-y-2">
            {STEPS.map((s, i) => (
              <li key={s} className="flex gap-3 text-sm text-ink-soft">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-50 text-xs font-bold text-brand-700">{i + 1}</span>
                <span className="pt-0.5">{s}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>

      <div className="mt-6" aria-live="polite">
        {state === 'checking' && (
          <div className="flex flex-col items-center gap-3 rounded-xl bg-brand-50 p-4 text-center sm:flex-row sm:justify-between sm:text-left">
            <p className="flex items-center gap-2.5 text-sm font-medium text-brand-900">
              <Loader2 aria-hidden="true" className="h-4 w-4 shrink-0 animate-spin text-brand-600" />
              Aguardando a confirmação do pagamento. Esta tela atualiza sozinha.
            </p>
            <Button size="sm" variant="secondary" onClick={verify} loading={checking}>
              Já paguei
            </Button>
          </div>
        )}
        {state === 'timeout' && (
          <Alert tone="info" title="Ainda não identificamos o pagamento">
            <p>
              Se você já pagou, fique tranquilo: assim que for confirmado enviaremos o e-mail para <strong>{email}</strong>. Você também pode
              verificar de novo agora.
            </p>
            <Button size="sm" variant="secondary" className="mt-2" onClick={verify} loading={checking}>
              <RefreshCw aria-hidden="true" className="h-4 w-4" /> Verificar novamente
            </Button>
          </Alert>
        )}
        {state === 'unsupported' && (
          <Alert tone="info" title="Depois de pagar, é só aguardar o e-mail">
            Assim que o pagamento for confirmado, enviamos a confirmação para <strong>{email}</strong>. Pode levar alguns instantes.
          </Alert>
        )}
      </div>

      <div className="mt-5 flex flex-col items-center justify-between gap-3 border-t border-surface-line pt-4 text-xs text-ink-muted sm:flex-row">
        <p className="flex items-center gap-1.5">
          <Clock aria-hidden="true" className="h-3.5 w-3.5" />O código PIX tem validade limitada. Se o banco recusar, gere um novo.
        </p>
        <button
          type="button"
          onClick={onNewCode}
          className="rounded font-semibold text-brand-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        >
          Gerar novo código
        </button>
      </div>
    </div>
  );
}
