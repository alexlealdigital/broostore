-- =============================================================================
-- 02_produto_teste_1_real.sql   (v2 - corrige o erro products_tipo_check)
-- Cria o produto de TESTE de R$ 1,00 (id 98) para validar PIX e cartao em producao.
-- Rode no SQL Editor do Supabase da BrooStore. Nao sobrescreve nada: se o id 98
-- ja existir, nao insere.
-- O bloco abaixo tenta os valores de "tipo" que o painel de autores usa e,
-- se nenhum passar, mostra a regra real da tabela para eu ajustar.
-- Para testar: https://SEU-SITE/comprar/98
-- =============================================================================

do $$
declare
  v_tipo text;
  v_ok   boolean := false;
begin
  if exists (select 1 from public.products where id = 98) then
    raise notice 'Produto 98 ja existe: nada foi inserido.';
    return;
  end if;

  foreach v_tipo in array array['digital', 'ebook', 'pdf'] loop
    begin
      insert into public.products
        (id, title, author, price, image_url, category, link,
         descricao, active, classificacao, tipo)
      values
        (98, 'TESTE - Pagamento R$ 1,00', 'BrooStore', 1.00, '', 'teste', '',
         'Produto interno para validar o checkout. Nao e uma venda real.',
         true, 'L', v_tipo);
      raise notice 'Produto 98 criado com tipo = %', v_tipo;
      v_ok := true;
      exit;
    exception when check_violation then
      raise notice 'tipo % recusado pela regra da tabela, tentando o proximo...', v_tipo;
    end;
  end loop;

  if not v_ok then
    raise exception 'Nenhum tipo aceito. Rode a consulta abaixo e me envie o resultado.';
  end if;
end $$;

-- Conferir:
select id, title, price, tipo, active from public.products where id = 98;

-- Se deu erro "Nenhum tipo aceito", rode e me envie:
-- select conname, pg_get_constraintdef(oid) from pg_constraint
-- where conrelid = 'public.products'::regclass and contype = 'c';

-- ---------- DESATIVAR depois dos testes ----------
-- update public.products set active = false where id = 98;
