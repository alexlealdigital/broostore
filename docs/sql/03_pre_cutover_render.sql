-- =============================================================================
-- 03_pre_cutover_render.sql  -  rode ANTES de trocar o Render para o repo novo
-- Banco: o Postgres que o DATABASE_URL do Render usa (veja docs/CUTOVER.md).
-- Seguro e idempotente: nao faz nada se a coluna ja existir.
-- =============================================================================
ALTER TABLE chaves_licenca
  ADD COLUMN IF NOT EXISTS ativa_no_app BOOLEAN NOT NULL DEFAULT FALSE;

-- Conferencia: deve devolver 1 linha
select column_name from information_schema.columns
where table_name = 'chaves_licenca' and column_name = 'ativa_no_app';
