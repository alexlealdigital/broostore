import { render, screen } from '@testing-library/react';
import { Router } from 'wouter';
import { memoryLocation } from 'wouter/memory-location';
import { describe, expect, it } from 'vitest';
import { makeProduct } from '@/test/fixtures';
import { ProductCard } from './ProductCard';

function renderCard(ui: React.ReactElement) {
  const { hook } = memoryLocation({ path: '/' });
  return render(<Router hook={hook}>{ui}</Router>);
}

describe('ProductCard', () => {
  it('mostra titulo, autor, preco, preco original riscado, desconto, classificacao, tipo e estrelas', () => {
    renderCard(
      <ProductCard
        product={makeProduct({ id: 7, title: 'Guia Completo', price: 29.9, original_price: 49.9, classificacao: '12', tipo: 'fisico' })}
        rating={{ average: 4.5, count: 10 }}
      />,
    );
    expect(screen.getByRole('link', { name: 'Guia Completo' })).toHaveAttribute('href', '/produto/7');
    expect(screen.getByText('Por Ana Souza')).toBeInTheDocument();
    expect(screen.getByText('R$ 29,90')).toBeInTheDocument();
    expect(screen.getByText('R$ 49,90')).toBeInTheDocument();
    expect(screen.getAllByText('-40%').length).toBeGreaterThan(0);
    expect(screen.getByLabelText('Classificação indicativa: 12 anos')).toHaveTextContent('12+');
    expect(screen.getByText('Físico')).toBeInTheDocument();
    expect(screen.getByLabelText('Nota 4,5 de 5, 10 avaliações')).toBeInTheDocument();
  });

  it('sem desconto nem avaliacoes nao mostra selo e informa "Sem avaliações"', () => {
    renderCard(<ProductCard product={makeProduct({ id: 1, price: 10, classificacao: 'L' })} />);
    expect(screen.queryByText(/^-\d+%$/)).not.toBeInTheDocument();
    expect(screen.getByText('Sem avaliações')).toBeInTheDocument();
    expect(screen.getByLabelText('Classificação indicativa: livre para todos os públicos')).toHaveTextContent('L');
  });

  it('imagem ausente usa fallback acessivel', () => {
    renderCard(<ProductCard product={makeProduct({ id: 1, image_url: null, title: 'Sem Capa' })} />);
    expect(screen.getByRole('img', { name: /Sem Capa.*sem imagem/ })).toBeInTheDocument();
  });
});
