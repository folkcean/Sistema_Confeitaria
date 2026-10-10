CREATE TABLE USUARIO (
  ID_usuario      SERIAL NOT NULL,
  nome            varchar(255) NOT NULL,
  email           varchar(255) UNIQUE,
  telefone        varchar(11) NOT NULL UNIQUE,
  senha           varchar(255),
  data_cadastro   timestamp(10) NOT NULL,
  ativo           bool DEFAULT 'true' NOT NULL,
  cpf             char(11) UNIQUE,
  data_nascimento date);
CREATE TABLE CLIENTE (
  ID_usuario             int4 NOT NULL,
  apelido                varchar(255) NOT NULL,
  cliente_vip            bool DEFAULT 'false' NOT NULL,
  instagram              varchar(255),
  restricoes_alimentares varchar(255),
  observacoes            text,
  preferencias           text);
CREATE TABLE FUNCIONARIO (
  ID_usuario       int4 NOT NULL,
  cargo            varchar(255) NOT NULL,
  data_contratacao date NOT NULL);
CREATE TABLE ADMINISTRADOR (
  ID_usuario        int4 NOT NULL,
  nivel_privilegio  varchar(255) NOT NULL,
  acesso_financeiro bool DEFAULT 'false' NOT NULL);
CREATE TABLE ENDERECO (
  ID_endereco SERIAL NOT NULL,
  ID_cliente  int4 NOT NULL,
  apelido     varchar(255),
  logradouro  varchar(255) NOT NULL,
  numero      varchar(255) NOT NULL,
  complemento varchar(255),
  bairro      varchar(255) NOT NULL,
  cidade      varchar(255) NOT NULL,
  cep         char(8) NOT NULL);
CREATE TABLE PEDIDO (
  ID_pedido                SERIAL NOT NULL,
  ID_endereco_entrega      int4,
  ID_cliente               int4 NOT NULL,
  data_criacao             timestamp(10) NOT NULL,
  data_entrega_ou_retirada timestamp(10) NOT NULL,
  valor_total              numeric(10, 2) NOT NULL,
  taxa_entrega             numeric(10, 2) DEFAULT 0 NOT NULL,
  status                   varchar(255) DEFAULT 'solicitado' NOT NULL CHECK(status IN ('solicitado', 'orcamento', 'confirmado', 'em_producao', 'pronto', 'entregue', 'finalizado', 'cancelado')),
  status_pagamento         varchar(255) DEFAULT 'aguardando_sinal' NOT NULL CHECK(status_pagamento IN ('aguardando_sinal', 'sinal_pago', 'pago')),
  tipo_entrega             varchar(255) NOT NULL CHECK(tipo_entrega IN ('entrega', 'retirada')),
  motivo_cancelamento      varchar(255),
  rastreamento             varchar(255),
  observacoes              varchar(255),
  forma_pagamento_sinal    varchar(20) CHECK(forma_pagamento_sinal IN ('pix', 'dinheiro', 'cartao')),
  forma_pagamento_restante varchar(20) CHECK(forma_pagamento_restante IN ('pix', 'dinheiro', 'cartao')),
  nome_recebedor           varchar(255));
CREATE TABLE ITEM_PEDIDO (
  ID_item_pedido       SERIAL NOT NULL,
  ID_produto           int4 NOT NULL,
  ID_pedido            int4 NOT NULL,
  quantidade           int4 NOT NULL,
  preco_unitario       numeric(10, 2) NOT NULL,
  personalizacao       varchar(255),
  custo_personalizacao numeric(10, 2) DEFAULT 0 NOT NULL,
  desconto             numeric(10, 2) DEFAULT 0 NOT NULL,
  observacoes          varchar(255),
  custo_unitario       numeric(10, 2) NOT NULL CHECK(custo_unitario >= 0));
CREATE TABLE OPCAO_PERSONALIZACAO (
  ID_opcao        SERIAL NOT NULL,
  ID_produto      int4 NOT NULL,
  nome            varchar(255) NOT NULL,
  descricao       varchar(255),
  custo_adicional numeric(10, 2) NOT NULL,
  ativo           bool DEFAULT 'true' NOT NULL);
CREATE TABLE PRODUTO (
  ID_produto         SERIAL NOT NULL,
  nome               varchar(255) NOT NULL,
  descricao          varchar(255) NOT NULL,
  disponibilidade    varchar(255) NOT NULL,
  preco_base         numeric(10, 2) NOT NULL,
  custo_mao_de_obra  numeric(10, 2) NOT NULL,
  margem_lucro       numeric(10, 2) NOT NULL,
  tamanho            varchar(255),
  caminho_foto       varchar(255),
  ativo              bool DEFAULT 'true' NOT NULL,
  antecedencia_horas int4 DEFAULT 48 NOT NULL CHECK(antecedencia_horas >= 0),
  custo_embalagem    numeric(10, 2) DEFAULT 0 NOT NULL CHECK(custo_embalagem>= 0),
  custo_indireto     numeric(10, 2) DEFAULT 0 NOT NULL CHECK(custo_indireto >= 0),
  percentual_perda   numeric(5, 2) DEFAULT 0 NOT NULL CHECK(percentual_perda BETWEEN 0 AND 100));
CREATE TABLE RECEITA (
  ID_receita     SERIAL NOT NULL,
  modo_preparo   text,
  tempo_preparo  int4 NOT NULL,
  rendimento_qtd numeric(10, 3) NOT NULL,
  rendimento_un  varchar(100) NOT NULL,
  complexidade   varchar(255),
  data_criacao   timestamp(10) NOT NULL,
  ativa          bool DEFAULT 'true' NOT NULL);
CREATE TABLE ITEM_RECEITA (
  ID_item_receita       SERIAL NOT NULL,
  ID_insumo             int4 NOT NULL,
  ID_receita            int4 NOT NULL,
  quantidade_necessaria numeric(10, 3) NOT NULL,
  observacoes           varchar(255),
  CONSTRAINT uq_receita_insumo
    UNIQUE (ID_receita, ID_insumo));
CREATE TABLE INSUMO (
  ID_insumo         SERIAL NOT NULL,
  nome              varchar(255) NOT NULL UNIQUE,
  unidade_medida    varchar(255) NOT NULL,
  quantidade_atual  numeric(10, 3) DEFAULT 0 NOT NULL,
  estoque_minimo    numeric(10, 3) DEFAULT 0 NOT NULL,
  custo_por_unidade numeric(10, 4),
  data_atualizacao  timestamp(10) NOT NULL,
  unidade_receita   varchar(20) NOT NULL,
  fator_conversao   numeric(10, 3) DEFAULT 1 NOT NULL,
  tipo              varchar(20) DEFAULT 'ingrediente' NOT NULL CHECK(tipo IN ('ingrediente', 'embalagem', 'decoracao')),
  ativo             bool DEFAULT 'true' NOT NULL);
CREATE TABLE FORNECEDOR (
  ID_fornecedor     SERIAL NOT NULL,
  email             varchar(255),
  nome              varchar(255) NOT NULL,
  telefone          varchar(20) NOT NULL,
  endereco          varchar(255) NOT NULL,
  cnpj              varchar(14) UNIQUE,
  contato_principal varchar(255),
  ativo             bool DEFAULT 'true' NOT NULL);
CREATE TABLE COMPRA_INSUMO (
  ID_compra_insumo SERIAL NOT NULL,
  ID_fornecedor    int4 NOT NULL,
  data_compra      timestamp(10) NOT NULL,
  data_entrega     timestamp(10),
  valor_total      numeric(10, 2) NOT NULL,
  status           varchar(255) NOT NULL CHECK(status IN ('pendente', 'recebida', 'cancelada')),
  nota_fiscal      varchar(255));
CREATE TABLE ITEM_COMPRA_INSUMO (
  ID_item_compra   SERIAL NOT NULL,
  ID_insumo        int4 NOT NULL,
  ID_compra_insumo int4 NOT NULL,
  quantidade       numeric(10, 3) NOT NULL,
  custo_unitario   numeric(10, 4) NOT NULL);
CREATE TABLE PRODUTO_RECEITA (
  quantidade numeric(10, 3) DEFAULT 1 NOT NULL CHECK(quantidade > 0),
  ID_produto int4 NOT NULL,
  ID_receita int4 NOT NULL);
CREATE TABLE MOVIMENTACAO_ESTOQUE (
  ID_movimentacao_estoque SERIAL NOT NULL,
  ID_insumo               int4 NOT NULL,
  tipo                    varchar(20) NOT NULL CHECK(tipo IN ('entrada', 'consumo', 'perda', 'ajuste')),
  quantidade              numeric(10, 3) NOT NULL,
  data                    timestamp NOT NULL,
  motivo                  varchar(255),
  ID_pedido               int4,
  ID_compra_insumo        int4);
CREATE TABLE OPCAO_ESCOLHIDA (
  ID_item_pedido int4 NOT NULL,
  ID_opcao       int4 NOT NULL,
  quantidade     int4 DEFAULT 1 NOT NULL CHECK(quantidade > 0),
  custo_cobrado  numeric(10, 2) NOT NULL);
