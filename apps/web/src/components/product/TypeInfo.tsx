import { KeyRound, Mail, PackageCheck, Truck, type LucideIcon } from 'lucide-react';
import { entregaDoTipo, type Entrega } from '@/lib/categorias';

interface Item {
  icon: LucideIcon;
  title: string;
  text: string;
}

const CONTENT: Record<Entrega, { heading: string; items: Item[] }> = {
  'email-link': {
    heading: 'Produto digital',
    items: [
      { icon: Mail, title: 'Entrega imediata por e-mail', text: 'Assim que o pagamento é confirmado, enviamos o link para download no e-mail informado na compra.' },
      { icon: PackageCheck, title: 'Sem frete', text: 'Você recebe o arquivo na hora, sem esperar transportadora.' },
    ],
  },
  'email-licenca': {
    heading: 'Aplicativo, game ou assinatura',
    items: [
      { icon: KeyRound, title: 'Licença ou chave por e-mail', text: 'Depois da confirmação do pagamento, enviamos a licença/chave de acesso para o e-mail da compra.' },
      { icon: Mail, title: 'Use o mesmo e-mail', text: 'A licença fica vinculada ao e-mail informado no checkout. Confira se está correto.' },
    ],
  },
  frete: {
    heading: 'Produto físico',
    items: [
      { icon: Truck, title: 'Frete calculado no checkout', text: 'Informe o seu CEP na etapa de compra para ver as opções de transportadora, prazo e valor.' },
      { icon: Mail, title: 'Confirmação por e-mail', text: 'Após o pagamento você recebe um e-mail de confirmação e entramos em contato sobre o envio.' },
    ],
  },
};

export function TypeInfo({ tipo }: { tipo: string }) {
  const { heading, items } = CONTENT[entregaDoTipo(tipo)];
  return (
    <section aria-label={heading} className="rounded-xl border border-brand-100 bg-brand-50/60 p-4">
      <h2 className="text-sm font-bold text-brand-800">{heading}</h2>
      <ul className="mt-3 grid gap-3">
        {items.map(({ icon: Icon, title, text }) => (
          <li key={title} className="flex gap-3">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white text-brand-600 shadow-sm">
              <Icon aria-hidden="true" className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-ink">{title}</p>
              <p className="text-sm leading-5 text-ink-muted">{text}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
