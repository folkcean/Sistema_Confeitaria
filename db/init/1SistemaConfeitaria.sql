CREATE TABLE USUARIO (
  ID_usuario      SERIAL NOT NULL, 
  nome            varchar(255) NOT NULL, 
  email           varchar(255) UNIQUE, 
  telefone        varchar(11) NOT NULL UNIQUE, 
  senha_hash      varchar(255), 
  data_cadastro   timestamp(6) DEFAULT now() NOT NULL, 
  ativo           bool DEFAULT 'true' NOT NULL, 
  cpf             char(11) UNIQUE, 
  data_nascimento date, 
  perfil          varchar(20) NOT NULL CHECK(perfil IN ('cliente', 'funcionario', 'administrador')), 
  PRIMARY KEY (ID_usuario));
CREATE TABLE CLIENTE (
  ID_usuario             int4 NOT NULL, 
  apelido                varchar(255) NOT NULL, 
  cliente_vip            bool DEFAULT 'false' NOT NULL, 
  instagram              varchar(255), 
  restricoes_alimentares varchar(255), 
  observacoes            text, 
  preferencias           text, 
  PRIMARY KEY (ID_usuario));
CREATE TABLE FUNCIONARIO (
  ID_usuario       int4 NOT NULL, 
  cargo            varchar(255) NOT NULL, 
  data_contratacao date NOT NULL, 
  PRIMARY KEY (ID_usuario));
CREATE TABLE ADMINISTRADOR (
  ID_usuario        int4 NOT NULL, 
  nivel_privilegio  varchar(255) NOT NULL, 
  acesso_financeiro bool DEFAULT 'false' NOT NULL, 
  PRIMARY KEY (ID_usuario));
CREATE TABLE ENDERECO (
  ID_endereco SERIAL NOT NULL, 
  ID_cliente  int4 NOT NULL, 
  apelido     varchar(255), 
  logradouro  varchar(255) NOT NULL, 
  numero      varchar(255) NOT NULL, 
  complemento varchar(255), 
  bairro      varchar(255) NOT NULL, 
  cidade      varchar(255) NOT NULL, 
  cep         char(8) NOT NULL, 
  PRIMARY KEY (ID_endereco));
CREATE TABLE PEDIDO (
  ID_pedido                SERIAL NOT NULL, 
  ID_endereco_entrega      int4, 
  ID_cliente               int4 NOT NULL, 
  data_criacao             timestamp(6) DEFAULT now() NOT NULL, 
  data_entrega_ou_retirada timestamp(6) NOT NULL, 
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
  nome_recebedor           varchar(255), 
  PRIMARY KEY (ID_pedido));
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
  custo_unitario       numeric(10, 2) NOT NULL CHECK(custo_unitario >= 0), 
  PRIMARY KEY (ID_item_pedido));
CREATE TABLE OPCAO_PERSONALIZACAO (
  ID_opcao        SERIAL NOT NULL, 
  ID_produto      int4 NOT NULL, 
  nome            varchar(255) NOT NULL, 
  descricao       varchar(255), 
  custo_adicional numeric(10, 2) NOT NULL, 
  ativo           bool DEFAULT 'true' NOT NULL, 
  PRIMARY KEY (ID_opcao));
CREATE TABLE PRODUTO (
  ID_produto         SERIAL NOT NULL, 
  nome               varchar(255) NOT NULL, 
  descricao          varchar(255) NOT NULL, 
  disponibilidade    varchar(255) NOT NULL CHECK(disponibilidade IN ('pronta_entrega', 'encomenda')), 
  preco_base         numeric(10, 2) NOT NULL, 
  custo_mao_de_obra  numeric(10, 2) NOT NULL, 
  margem_lucro       numeric(10, 2) NOT NULL, 
  tamanho            varchar(255), 
  caminho_foto       varchar(255), 
  ativo              bool DEFAULT 'true' NOT NULL, 
  antecedencia_horas int4 DEFAULT 48 NOT NULL CHECK(antecedencia_horas >= 0), 
  custo_embalagem    numeric(10, 2) DEFAULT 0 NOT NULL CHECK(custo_embalagem>= 0), 
  custo_indireto     numeric(10, 2) DEFAULT 0 NOT NULL CHECK(custo_indireto >= 0), 
  percentual_perda   numeric(5, 2) DEFAULT 0 NOT NULL CHECK(percentual_perda BETWEEN 0 AND 100), 
  PRIMARY KEY (ID_produto));
CREATE TABLE RECEITA (
  ID_receita     SERIAL NOT NULL, 
  modo_preparo   text, 
  tempo_preparo  int4 NOT NULL, 
  rendimento_qtd numeric(10, 3) NOT NULL, 
  rendimento_un  varchar(100) NOT NULL, 
  complexidade   varchar(255), 
  data_criacao   timestamp(6) DEFAULT now() NOT NULL, 
  ativa          bool DEFAULT 'true' NOT NULL, 
  nome           varchar(255), 
  PRIMARY KEY (ID_receita));
CREATE TABLE ITEM_RECEITA (
  ID_item_receita       SERIAL NOT NULL, 
  ID_insumo             int4 NOT NULL, 
  ID_receita            int4 NOT NULL, 
  quantidade_necessaria numeric(10, 3) NOT NULL, 
  observacoes           varchar(255), 
  PRIMARY KEY (ID_item_receita), 
  CONSTRAINT uq_receita_insumo 
    UNIQUE (ID_receita, ID_insumo));
CREATE TABLE INSUMO (
  ID_insumo         SERIAL NOT NULL, 
  nome              varchar(255) NOT NULL UNIQUE, 
  unidade_medida    varchar(255) NOT NULL, 
  quantidade_atual  numeric(10, 3) DEFAULT 0 NOT NULL, 
  estoque_minimo    numeric(10, 3) DEFAULT 0 NOT NULL, 
  custo_por_unidade numeric(10, 4), 
  data_atualizacao  timestamp(6) DEFAULT now() NOT NULL, 
  unidade_receita   varchar(20) NOT NULL, 
  fator_conversao   numeric(10, 3) DEFAULT 1 NOT NULL, 
  tipo              varchar(20) DEFAULT 'ingrediente' NOT NULL CHECK(tipo IN ('ingrediente', 'embalagem', 'decoracao')), 
  ativo             bool DEFAULT 'true' NOT NULL, 
  PRIMARY KEY (ID_insumo));
CREATE TABLE FORNECEDOR (
  ID_fornecedor     SERIAL NOT NULL, 
  email             varchar(255), 
  nome              varchar(255) NOT NULL, 
  telefone          varchar(20) NOT NULL, 
  endereco          varchar(255) NOT NULL, 
  cnpj              varchar(14) UNIQUE, 
  contato_principal varchar(255), 
  ativo             bool DEFAULT 'true' NOT NULL, 
  PRIMARY KEY (ID_fornecedor));
CREATE TABLE COMPRA_INSUMO (
  ID_compra_insumo SERIAL NOT NULL, 
  ID_fornecedor    int4 NOT NULL, 
  data_compra      timestamp(6) DEFAULT now() NOT NULL, 
  data_entrega     timestamp(6), 
  valor_total      numeric(10, 2) NOT NULL, 
  status           varchar(255) NOT NULL CHECK(status IN ('pendente', 'recebida', 'cancelada')), 
  nota_fiscal      varchar(255), 
  PRIMARY KEY (ID_compra_insumo));
CREATE TABLE ITEM_COMPRA_INSUMO (
  ID_item_compra   SERIAL NOT NULL, 
  ID_insumo        int4 NOT NULL, 
  ID_compra_insumo int4 NOT NULL, 
  quantidade       numeric(10, 3) NOT NULL, 
  custo_unitario   numeric(10, 4) NOT NULL, 
  PRIMARY KEY (ID_item_compra));
CREATE TABLE PRODUTO_RECEITA (
  quantidade numeric(10, 3) DEFAULT 1 NOT NULL CHECK(quantidade > 0), 
  ID_produto int4 NOT NULL, 
  ID_receita int4 NOT NULL, 
  PRIMARY KEY (ID_produto, 
  ID_receita));
CREATE TABLE MOVIMENTACAO_ESTOQUE (
  ID_movimentacao_estoque SERIAL NOT NULL, 
  ID_insumo               int4 NOT NULL, 
  tipo                    varchar(20) NOT NULL CHECK(tipo IN ('entrada', 'consumo', 'perda', 'ajuste')), 
  quantidade              numeric(10, 3) NOT NULL, 
  data                    timestamp DEFAULT now() NOT NULL, 
  motivo                  varchar(255), 
  ID_pedido               int4, 
  ID_compra_insumo        int4, 
  PRIMARY KEY (ID_movimentacao_estoque));
CREATE TABLE OPCAO_ESCOLHIDA (
  ID_item_pedido int4 NOT NULL, 
  ID_opcao       int4 NOT NULL, 
  quantidade     int4 DEFAULT 1 NOT NULL CHECK(quantidade > 0), 
  custo_cobrado  numeric(10, 2) NOT NULL, 
  PRIMARY KEY (ID_item_pedido, 
  ID_opcao));
ALTER TABLE ENDERECO ADD CONSTRAINT FKENDERECO612842 FOREIGN KEY (ID_cliente) REFERENCES CLIENTE (ID_usuario) ON DELETE Cascade;
ALTER TABLE PEDIDO ADD CONSTRAINT FKPEDIDO797951 FOREIGN KEY (ID_endereco_entrega) REFERENCES ENDERECO (ID_endereco);
ALTER TABLE ITEM_PEDIDO ADD CONSTRAINT FKITEM_PEDID563675 FOREIGN KEY (ID_pedido) REFERENCES PEDIDO (ID_pedido) ON DELETE Cascade;
ALTER TABLE PEDIDO ADD CONSTRAINT FKPEDIDO110089 FOREIGN KEY (ID_cliente) REFERENCES CLIENTE (ID_usuario) ON DELETE Restrict;
ALTER TABLE ITEM_PEDIDO ADD CONSTRAINT FKITEM_PEDID237378 FOREIGN KEY (ID_produto) REFERENCES PRODUTO (ID_produto);
ALTER TABLE OPCAO_PERSONALIZACAO ADD CONSTRAINT FKOPCAO_PERS993737 FOREIGN KEY (ID_produto) REFERENCES PRODUTO (ID_produto) ON DELETE Cascade;
ALTER TABLE ITEM_RECEITA ADD CONSTRAINT FKITEM_RECEI498044 FOREIGN KEY (ID_receita) REFERENCES RECEITA (ID_receita) ON DELETE Cascade;
ALTER TABLE ITEM_RECEITA ADD CONSTRAINT FKITEM_RECEI572432 FOREIGN KEY (ID_insumo) REFERENCES INSUMO (ID_insumo);
ALTER TABLE COMPRA_INSUMO ADD CONSTRAINT FKCOMPRA_INS990379 FOREIGN KEY (ID_fornecedor) REFERENCES FORNECEDOR (ID_fornecedor);
ALTER TABLE ITEM_COMPRA_INSUMO ADD CONSTRAINT FKITEM_COMPR310217 FOREIGN KEY (ID_compra_insumo) REFERENCES COMPRA_INSUMO (ID_compra_insumo) ON DELETE Cascade;
ALTER TABLE ITEM_COMPRA_INSUMO ADD CONSTRAINT FKITEM_COMPR571174 FOREIGN KEY (ID_insumo) REFERENCES INSUMO (ID_insumo);
ALTER TABLE ADMINISTRADOR ADD CONSTRAINT FKADMINISTRA911885 FOREIGN KEY (ID_usuario) REFERENCES USUARIO (ID_usuario) ON DELETE Cascade;
ALTER TABLE FUNCIONARIO ADD CONSTRAINT FKFUNCIONARI431771 FOREIGN KEY (ID_usuario) REFERENCES USUARIO (ID_usuario) ON DELETE Cascade;
ALTER TABLE CLIENTE ADD CONSTRAINT FKCLIENTE340166 FOREIGN KEY (ID_usuario) REFERENCES USUARIO (ID_usuario) ON DELETE Cascade;
ALTER TABLE MOVIMENTACAO_ESTOQUE ADD CONSTRAINT FKMOVIMENTAC131374 FOREIGN KEY (ID_insumo) REFERENCES INSUMO (ID_insumo);
ALTER TABLE MOVIMENTACAO_ESTOQUE ADD CONSTRAINT FKMOVIMENTAC33025 FOREIGN KEY (ID_pedido) REFERENCES PEDIDO (ID_pedido) ON DELETE Set null;
ALTER TABLE MOVIMENTACAO_ESTOQUE ADD CONSTRAINT FKMOVIMENTAC101174 FOREIGN KEY (ID_compra_insumo) REFERENCES COMPRA_INSUMO (ID_compra_insumo) ON DELETE Set null;
ALTER TABLE PRODUTO_RECEITA ADD CONSTRAINT FKPRODUTO_RE940878 FOREIGN KEY (ID_produto) REFERENCES PRODUTO (ID_produto) ON DELETE Cascade;
ALTER TABLE PRODUTO_RECEITA ADD CONSTRAINT FKPRODUTO_RE356472 FOREIGN KEY (ID_receita) REFERENCES RECEITA (ID_receita);
ALTER TABLE OPCAO_ESCOLHIDA ADD CONSTRAINT FKOPCAO_ESCO235516 FOREIGN KEY (ID_item_pedido) REFERENCES ITEM_PEDIDO (ID_item_pedido) ON DELETE Cascade;
ALTER TABLE OPCAO_ESCOLHIDA ADD CONSTRAINT FKOPCAO_ESCO949281 FOREIGN KEY (ID_opcao) REFERENCES OPCAO_PERSONALIZACAO (ID_opcao);
