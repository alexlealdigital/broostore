-- =============================================================================
-- 01_diagnostico_broostore.sql  (somente LEITURA - pode rodar sem medo)
-- Projeto Supabase da BrooStore (gyepvrzkwesohbagpgfa) -> SQL Editor.
-- Rode cada consulta e me mande o resultado (print ou copiar/colar).
-- =============================================================================

-- 1) Colunas da tabela products (quero ver se existe alguma que eu nao conheco)
select column_name, data_type, is_nullable, column_default
from information_schema.columns
where table_schema = 'public' and table_name = 'products'
order by ordinal_position;

-- 2) RLS ligado? Quais policies existem em products, reviews e contatos?
select c.relname as tabela, c.relrowsecurity as rls_ligado
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relname in ('products','reviews','contatos');

select tablename, policyname, cmd, roles, qual, with_check
from pg_policies
where schemaname = 'public' and tablename in ('products','reviews','contatos')
order by tablename, policyname;

-- 3) O que o anonimo (chave publica) consegue fazer nessas tabelas?
select table_name, privilege_type
from information_schema.role_table_grants
where table_schema = 'public' and grantee = 'anon'
  and table_name in ('products','reviews','contatos')
order by table_name, privilege_type;

-- 4) Produtos: quantos por tipo e quais ids estao em uso (para o produto de teste)
select tipo, count(*) as qtd, min(id) as menor_id, max(id) as maior_id
from public.products group by tipo order by qtd desc;

select id, title, price, tipo, active from public.products where id in (98, 99);

-- 5) A coluna que o worker novo precisa existe em chaves_licenca? (banco do Render,
--    NAO do Supabase, se o DATABASE_URL apontar para outro Postgres - veja CUTOVER.md)
select column_name from information_schema.columns
where table_name = 'chaves_licenca' and column_name = 'ativa_no_app';
