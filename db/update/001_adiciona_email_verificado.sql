-- db/update/001_adiciona_email_verificado.sql
-- Verificação de e-mail: guarda se a pessoa já confirmou o endereço pelo link recebido.
-- Contas que já existem ficam como NÃO verificadas (false): ninguém confirmou ainda.
-- Aplicar UMA vez em cada banco:
--   docker compose exec -T db psql -U app -d appdb -v ON_ERROR_STOP=1 --single-transaction < db/update/001_adiciona_email_verificado.sql
ALTER TABLE usuario ADD COLUMN email_verificado bool DEFAULT false NOT NULL;