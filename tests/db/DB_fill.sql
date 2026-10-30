SET client_min_messages = warning;

TRUNCATE usuario, produto, insumo, fornecedor, receita, compra_insumo RESTART IDENTITY CASCADE;

-- ---------- Usuários ----------
INSERT INTO usuario (id_usuario, nome, email, telefone, senha_hash, perfil, ativo, cpf, data_nascimento) VALUES
  (1, 'Rosangela Almeida Crespo', 'rosangela@confeitaria.local', '22999990001', 'scrypt:32768:8:1$KNHQ2UIqfEyRYZta$f2a4c47b27836331c8107debda39bd434b9240f7b44d37fc7ef158a66464ad8f5c4fa9f6ffd2cdb0ec07fd0bf87b1e5b0afbaf856fa69e743f9145d4ed6020ac', 'administrador', true, '15881399803', '1966-03-14'),
  (2, 'Joao Pedro Viana', 'joao@confeitaria.local', '22999990002', 'scrypt:32768:8:1$KNHQ2UIqfEyRYZta$f2a4c47b27836331c8107debda39bd434b9240f7b44d37fc7ef158a66464ad8f5c4fa9f6ffd2cdb0ec07fd0bf87b1e5b0afbaf856fa69e743f9145d4ed6020ac', 'funcionario', true, '87973091173', '1999-07-02'),
  (3, 'Larissa Nunes Rangel', 'larissa@confeitaria.local', '22999990003', 'scrypt:32768:8:1$KNHQ2UIqfEyRYZta$f2a4c47b27836331c8107debda39bd434b9240f7b44d37fc7ef158a66464ad8f5c4fa9f6ffd2cdb0ec07fd0bf87b1e5b0afbaf856fa69e743f9145d4ed6020ac', 'funcionario', true, '70753645530', '2002-11-19'),
  -- Ana faz aniversário daqui a 3 dias (aparece em "Aniversários da semana")
  (10, 'Ana Souza', 'ana@exemplo.com', '22999990010', 'scrypt:32768:8:1$KNHQ2UIqfEyRYZta$f2a4c47b27836331c8107debda39bd434b9240f7b44d37fc7ef158a66464ad8f5c4fa9f6ffd2cdb0ec07fd0bf87b1e5b0afbaf856fa69e743f9145d4ed6020ac', 'cliente', true, '52998224725', (current_date + 3 - interval '34 years')::date),
  (11, 'Bruno Carvalho', 'bruno@exemplo.com', '22999990011', 'scrypt:32768:8:1$KNHQ2UIqfEyRYZta$f2a4c47b27836331c8107debda39bd434b9240f7b44d37fc7ef158a66464ad8f5c4fa9f6ffd2cdb0ec07fd0bf87b1e5b0afbaf856fa69e743f9145d4ed6020ac', 'cliente', true, '89768469749', '1988-02-10'),
  (12, 'Carla Nunes', 'carla@exemplo.com', '22999990012', 'scrypt:32768:8:1$KNHQ2UIqfEyRYZta$f2a4c47b27836331c8107debda39bd434b9240f7b44d37fc7ef158a66464ad8f5c4fa9f6ffd2cdb0ec07fd0bf87b1e5b0afbaf856fa69e743f9145d4ed6020ac', 'cliente', true, NULL, '1990-05-20'),
  (13, 'Antonio Peixoto', NULL, '22999990013', NULL, 'cliente', true, NULL, NULL),
  (14, 'Daniela Moreira', 'dani@exemplo.com', '22999990014', 'scrypt:32768:8:1$KNHQ2UIqfEyRYZta$f2a4c47b27836331c8107debda39bd434b9240f7b44d37fc7ef158a66464ad8f5c4fa9f6ffd2cdb0ec07fd0bf87b1e5b0afbaf856fa69e743f9145d4ed6020ac', 'cliente', true, '30411895508', '1995-09-01'),
  (15, 'Eduardo Lima', 'edu@exemplo.com', '22999990015', 'scrypt:32768:8:1$KNHQ2UIqfEyRYZta$f2a4c47b27836331c8107debda39bd434b9240f7b44d37fc7ef158a66464ad8f5c4fa9f6ffd2cdb0ec07fd0bf87b1e5b0afbaf856fa69e743f9145d4ed6020ac', 'cliente', false, '04876452946', '1985-12-03');

INSERT INTO administrador (id_usuario, nivel_privilegio, acesso_financeiro) VALUES
  (1, 'total', true);

INSERT INTO funcionario (id_usuario, cargo, data_contratacao) VALUES
  (2, 'Auxiliar de cozinha', '2025-12-01'),
  (3, 'Atendente e embalagem', '2026-06-08');

INSERT INTO cliente (id_usuario, apelido, cliente_vip, instagram, restricoes_alimentares, observacoes, preferencias) VALUES
  (10, 'Aninha', false, '@anasouza', NULL, NULL, 'Bolo de chocolate'),
  (11, 'Bruno', true, '@brunoc', 'Sem lactose', 'Cliente fiel: pede docinhos todo mês', 'Brigadeiro'),
  (12, 'Carlinha', false, NULL, NULL, NULL, 'Chocolate meio amargo'),
  (13, 'Seu Antonio', false, NULL, 'Diabético: pouco doce', 'Pede pelo WhatsApp', NULL),
  (14, 'Dani', false, '@danimoreira', NULL, NULL, NULL),
  (15, 'Edu', false, NULL, NULL, 'Conta desativada a pedido do cliente', NULL);

INSERT INTO endereco (id_endereco, id_cliente, apelido, logradouro, numero, complemento, bairro, cidade, cep) VALUES
  (1, 10, 'Casa', 'Rua Ouvidor', '889', NULL, 'Jockey Club', 'Campos dos Goytacazes', '28020493'),
  (2, 10, 'Trabalho', 'Rua Santa Rosa', '1473', 'Sala 659', 'Pelinca', 'Campos dos Goytacazes', '28035573'),
  (3, 11, 'Casa', 'Rua Doutor Siqueira', '1421', 'Apto 628', 'Pelinca', 'Campos dos Goytacazes', '28035463'),
  (4, 12, 'Casa', 'Avenida Pelinca', '200', NULL, 'Pelinca', 'Campos dos Goytacazes', '28035053'),
  (5, 13, 'Casa', 'Rua Treze de Maio', '52', NULL, 'Centro', 'Campos dos Goytacazes', '28010260'),
  (6, 14, 'Casa', 'Rua Barao de Miracema', '100', 'Apto 2', 'Centro', 'Campos dos Goytacazes', '28035000');

-- ---------- Fornecedores e insumos ----------
INSERT INTO fornecedor (id_fornecedor, nome, email, telefone, endereco, cnpj, contato_principal, ativo) VALUES
  (1, 'Atacadao Campos', 'compras@atacadaocampos.local', '2227330000', 'BR-101, Km 64, Parque Rodoviario', '12345678000190', 'Carlos', true),
  (2, 'Casa do Confeiteiro', 'vendas@casadoconfeiteiro.local', '2227331111', 'Rua Formosa, 300, Centro', '23456789000101', 'Ana', true),
  (3, 'Hortifruti Pelinca', NULL, '22998761234', 'Avenida Pelinca, 85, Pelinca', NULL, 'Seu Jorge', true),
  (4, 'Embala Campos', 'pedidos@embalacampos.local', '2227332222', 'Rua Treze de Maio, 410, Centro', '34567890000112', 'Patricia', false);

-- fator_conversao = unidades da receita por unidade de compra (1 kg = 1000 g; 1 dúzia = 12 un)
-- Açúcar (2) e leite condensado (4) estão abaixo do mínimo: aparecem na lista de compras
INSERT INTO insumo (id_insumo, nome, tipo, unidade_medida, unidade_receita, fator_conversao, quantidade_atual, estoque_minimo, custo_por_unidade, ativo) VALUES
  (1, 'Farinha de trigo', 'ingrediente', 'kg', 'g', 1000, 11268.19, 10000, 5.13, true),
  (2, 'Acucar refinado', 'ingrediente', 'kg', 'g', 1000, 8731.04, 10000, 4.69, true),
  (3, 'Ovo', 'ingrediente', 'duzia', 'un', 12, 72, 60, 13.43, true),
  (4, 'Leite condensado (395g)', 'ingrediente', 'lata', 'un', 1, 24, 40, 7.03, true),
  (5, 'Creme de leite (200g)', 'ingrediente', 'caixa', 'un', 1, 44, 40, 3.48, true),
  (6, 'Chocolate meio amargo', 'ingrediente', 'kg', 'g', 1000, 3383.4, 3000, 44.94, true),
  (8, 'Cacau em po 50%', 'ingrediente', 'kg', 'g', 1000, 1239.06, 500, 38.82, true),
  (9, 'Manteiga sem sal', 'ingrediente', 'kg', 'g', 1000, 3060.52, 2000, 47.74, true),
  (10, 'Leite integral', 'ingrediente', 'litro', 'ml', 1000, 7360.7, 6000, 5.16, true),
  (11, 'Oleo de soja', 'ingrediente', 'litro', 'ml', 1000, 2759.16, 2000, 7.60, true),
  (12, 'Fermento quimico', 'ingrediente', 'pote 100g', 'g', 100, 382.8, 300, 4.68, true),
  (13, 'Cenoura', 'ingrediente', 'kg', 'g', 1000, 2700, 2000, 4.27, true),
  (15, 'Coco ralado', 'ingrediente', 'kg', 'g', 1000, 1699, 500, 32.26, true),
  (19, 'Granulado de chocolate', 'decoracao', 'kg', 'g', 1000, 1803, 500, 23.01, true),
  (21, 'Forminha de papel n.4', 'embalagem', 'pacote 100un', 'un', 100, 763, 500, 6.25, true),
  (22, 'Caixa para bolo 25cm', 'embalagem', 'un', 'un', 1, 17, 15, 3.36, true),
  (26, 'Fita de cetim', 'decoracao', 'rolo 10m', 'm', 10, 26.2, 20, 7.87, false);

-- ---------- Receitas ----------
-- A tabela receita ainda não tem coluna de nome: o nome vai no início do modo de preparo.
INSERT INTO receita (id_receita, modo_preparo, tempo_preparo, rendimento_qtd, rendimento_un, complexidade, ativa) VALUES
  (1, 'Massa branca: Bater ovos e acucar, juntar leite e oleo, incorporar farinha e fermento. Assar 40 min a 180C.', 50, 1, 'bolo 25cm', 'baixa', true),
  (2, 'Massa de chocolate: Misturar secos com cacau, juntar ovos, leite e oleo. Assar 40 min a 180C.', 50, 1, 'bolo 25cm', 'baixa', true),
  (3, 'Massa de cenoura: Bater cenoura, ovos e oleo no liquidificador; misturar farinha, acucar e fermento. Assar 40 min.', 50, 1, 'bolo 25cm', 'baixa', true),
  (5, 'Brigadeiro: Cozinhar leite condensado, manteiga e chocolate ate desgrudar. Enrolar e passar no granulado.', 60, 50, 'unidades', 'baixa', true),
  (6, 'Beijinho: Cozinhar leite condensado com manteiga e coco. Enrolar e passar no coco.', 60, 50, 'unidades', 'baixa', true),
  (7, 'Ganache de chocolate: Derreter chocolate meio amargo com creme de leite.', 15, 1, 'cobertura de bolo', 'baixa', true),
  (8, 'Recheio de brigadeiro de colher: Cozinhar leite condensado, creme de leite, cacau e manteiga ate ponto cremoso.', 25, 1, 'recheio de bolo', 'baixa', true),
  (12, 'Brownie: Derreter chocolate com manteiga, juntar acucar, ovos, cacau e farinha. Assar 25 min.', 45, 16, 'pedacos', 'baixa', false);

INSERT INTO item_receita (id_receita, id_insumo, quantidade_necessaria) VALUES
  (1, 1, 300), (1, 2, 250), (1, 3, 4), (1, 10, 240), (1, 11, 120), (1, 12, 15),
  (2, 1, 280), (2, 2, 280), (2, 3, 4), (2, 8, 60), (2, 10, 240), (2, 11, 120), (2, 12, 15),
  (3, 13, 300), (3, 3, 3), (3, 11, 200), (3, 1, 240), (3, 2, 240), (3, 12, 15),
  (5, 4, 2), (5, 9, 30), (5, 6, 50), (5, 19, 150), (5, 21, 50),
  (6, 4, 2), (6, 9, 30), (6, 15, 150), (6, 21, 50),
  (7, 6, 300), (7, 5, 2),
  (8, 4, 2), (8, 5, 1), (8, 8, 40), (8, 9, 20),
  (12, 6, 300), (12, 9, 200), (12, 2, 300), (12, 3, 4), (12, 1, 150), (12, 8, 30);

-- ---------- Produtos ----------
INSERT INTO produto (id_produto, nome, descricao, disponibilidade, preco_base, custo_mao_de_obra, margem_lucro, tamanho, caminho_foto, ativo, antecedencia_horas, custo_embalagem, custo_indireto, percentual_perda) VALUES
  (1, 'Bolo de chocolate com brigadeiro', 'Massa de chocolate com recheio e cobertura de brigadeiro de colher', 'encomenda', 98.00, 25.00, 2.50, '25 cm', 'fotos/produto_01.jpg', true, 48, 3.10, 0.00, 3.00),
  (2, 'Bolo de cenoura com chocolate', 'Bolo caseiro de cenoura com cobertura de ganache', 'encomenda', 78.00, 20.00, 2.50, '25 cm', 'fotos/produto_02.jpg', true, 48, 3.10, 0.00, 3.00),
  (6, 'Cento de brigadeiro', '100 brigadeiros tradicionais', 'encomenda', 135.00, 30.00, 2.50, '100 unidades', 'fotos/produto_06.jpg', true, 24, 4.30, 0.00, 3.00),
  (7, 'Cento de beijinho', '100 beijinhos de coco', 'encomenda', 135.00, 30.00, 2.50, '100 unidades', 'fotos/produto_07.jpg', true, 24, 4.30, 0.00, 3.00),
  (8, 'Cento de docinhos sortidos', '50 brigadeiros e 50 beijinhos', 'encomenda', 140.00, 30.00, 2.50, '100 unidades', 'fotos/produto_08.jpg', true, 24, 4.30, 0.00, 3.00),
  (13, 'Kit festa', 'Bolo de chocolate com brigadeiro 25cm e 50 brigadeiros', 'encomenda', 195.00, 45.00, 2.50, 'bolo 25cm + 50 doces', 'fotos/produto_13.jpg', true, 72, 7.40, 0.00, 3.00),
  (17, 'Bolo red velvet', 'Massa vermelha com recheio de ganache (saiu do cardapio)', 'encomenda', 110.00, 28.00, 2.50, '25 cm', 'fotos/produto_17.jpg', false, 48, 3.10, 0.00, 3.00),
  (18, 'Brigadeiro', 'Brigadeiro tradicional, unidade', 'pronta_entrega', 3.50, 0.50, 2.50, 'unidade', 'fotos/produto_18.jpg', true, 0, 0.00, 0.00, 3.00),
  (19, 'Beijinho', 'Beijinho de coco, unidade', 'pronta_entrega', 3.50, 0.50, 2.50, 'unidade', 'fotos/produto_19.jpg', true, 0, 0.00, 0.00, 3.00),
  (20, 'Fatia de bolo de chocolate', 'Fatia do bolo de chocolate com brigadeiro', 'pronta_entrega', 12.00, 1.50, 2.50, 'fatia', 'fotos/produto_20.jpg', true, 0, 0.00, 0.00, 3.00),
  (21, 'Brownie', 'Pedaco de brownie de chocolate meio amargo', 'pronta_entrega', 10.00, 1.00, 2.50, 'pedaco', 'fotos/produto_21.jpg', false, 0, 0.00, 0.00, 3.00);

-- quantidade = fração da receita usada em uma unidade do produto
INSERT INTO produto_receita (id_produto, id_receita, quantidade) VALUES
  (1, 2, 1), (1, 8, 1.5),
  (2, 3, 1), (2, 7, 0.6),
  (6, 5, 2),
  (7, 6, 2),
  (8, 5, 1), (8, 6, 1),
  (13, 2, 1), (13, 8, 1.5), (13, 5, 1),
  (17, 1, 1), (17, 7, 1),
  (18, 5, 0.02),
  (19, 6, 0.02),
  (20, 2, 0.083), (20, 8, 0.125),
  (21, 12, 0.063);

-- A opção 10 está desligada: não aparece para o cliente
INSERT INTO opcao_personalizacao (id_opcao, id_produto, nome, descricao, custo_adicional, ativo) VALUES
  (1, 1, 'Brigadeiros em cima', 'Por unidade (entrevista 5.4)', 3.00, true),
  (2, 1, 'Nozes no recheio', 'Acrescimo por bolo', 15.00, true),
  (3, 1, 'Morangos frescos', 'Acrescimo por bolo', 18.00, true),
  (4, 1, 'Escrita personalizada', 'Nome ou frase na cobertura', 10.00, true),
  (5, 1, 'Topo de bolo de papel', 'Tema escolhido pelo cliente', 15.00, true),
  (6, 2, 'Brigadeiros em cima', 'Por unidade (entrevista 5.4)', 3.00, true),
  (7, 2, 'Nozes no recheio', 'Acrescimo por bolo', 15.00, true),
  (8, 2, 'Morangos frescos', 'Acrescimo por bolo', 18.00, true),
  (9, 2, 'Escrita personalizada', 'Nome ou frase na cobertura', 10.00, true),
  (10, 2, 'Topo de bolo de papel', 'Tema escolhido pelo cliente', 15.00, false),
  (26, 13, 'Brigadeiros em cima', 'Por unidade (entrevista 5.4)', 3.00, true),
  (27, 13, 'Nozes no recheio', 'Acrescimo por bolo', 15.00, true),
  (28, 13, 'Morangos frescos', 'Acrescimo por bolo', 18.00, true),
  (29, 13, 'Escrita personalizada', 'Nome ou frase na cobertura', 10.00, true),
  (30, 13, 'Topo de bolo de papel', 'Tema escolhido pelo cliente', 15.00, true),
  (31, 17, 'Brigadeiros em cima', 'Por unidade (entrevista 5.4)', 3.00, true),
  (32, 17, 'Escrita personalizada', 'Nome ou frase na cobertura', 10.00, true),
  (39, 6, 'Forminhas coloridas', 'Cor escolhida pelo cliente', 8.00, true),
  (40, 6, 'Granulado colorido', 'Troca o granulado de chocolate', 5.00, true),
  (41, 7, 'Forminhas coloridas', 'Cor escolhida pelo cliente', 8.00, true),
  (42, 7, 'Granulado colorido', 'Troca o granulado de chocolate', 5.00, true),
  (43, 8, 'Forminhas coloridas', 'Cor escolhida pelo cliente', 8.00, true),
  (44, 8, 'Granulado colorido', 'Troca o granulado de chocolate', 5.00, true);

-- ---------- Pedidos ----------
-- Um pedido em cada status. valor_total = soma(preco_unitario * quantidade + custo_personalizacao) + taxa_entrega
INSERT INTO pedido (id_pedido, id_cliente, id_endereco_entrega, data_criacao, data_entrega_ou_retirada, valor_total, taxa_entrega, status, status_pagamento, tipo_entrega, motivo_cancelamento, observacoes, forma_pagamento_sinal, forma_pagamento_restante, nome_recebedor) VALUES
  (1, 10, 1, date_trunc('hour', now()) - interval '12 days', date_trunc('day', now()) - interval '10 days' + interval '15 hours', 116.00, 8.00, 'finalizado', 'pago', 'entrega', NULL, NULL, 'pix', 'pix', 'Ana Souza'),
  (2, 11, NULL, date_trunc('hour', now()) - interval '4 days', date_trunc('day', now()) - interval '2 days' + interval '10 hours', 135.00, 0.00, 'entregue', 'pago', 'retirada', NULL, NULL, 'pix', 'dinheiro', 'Bruno'),
  (3, 12, 4, date_trunc('hour', now()) - interval '3 days', date_trunc('hour', now()) + interval '3 hours', 118.00, 10.00, 'pronto', 'sinal_pago', 'entrega', NULL, 'Interfone com defeito, ligar ao chegar', 'pix', NULL, 'Carla Nunes'),
  (4, 13, NULL, date_trunc('hour', now()) - interval '2 days', date_trunc('day', now()) + interval '1 day 14 hours', 140.00, 0.00, 'em_producao', 'sinal_pago', 'retirada', NULL, NULL, 'dinheiro', NULL, 'Seu Antonio'),
  (5, 10, 2, date_trunc('hour', now()) - interval '1 day', date_trunc('day', now()) + interval '3 days 16 hours', 213.00, 8.00, 'confirmado', 'sinal_pago', 'entrega', NULL, NULL, 'cartao', NULL, 'Ana Souza'),
  (6, 14, 6, date_trunc('hour', now()) - interval '1 day', date_trunc('day', now()) + interval '4 days 18 hours', 110.00, 12.00, 'orcamento', 'aguardando_sinal', 'entrega', NULL, NULL, 'pix', NULL, 'Dani'),
  (7, 12, NULL, date_trunc('hour', now()) - interval '2 hours', date_trunc('day', now()) + interval '5 days 11 hours', 170.00, 0.00, 'solicitado', 'aguardando_sinal', 'retirada', NULL, NULL, 'pix', NULL, 'Carlinha'),
  (8, 11, NULL, date_trunc('hour', now()) - interval '8 days', date_trunc('day', now()) - interval '5 days' + interval '10 hours', 78.00, 0.00, 'cancelado', 'sinal_pago', 'retirada', 'Cliente viajou; o sinal nao e devolvido (regra da confeitaria)', NULL, 'pix', NULL, 'Bruno');

INSERT INTO item_pedido (id_item_pedido, id_pedido, id_produto, quantidade, preco_unitario, personalizacao, custo_personalizacao, custo_unitario, observacoes) VALUES
  (1, 1, 1, 1, 98.00, 'Escrita personalizada', 10.00, 71.85, 'Feliz aniversario, Ana'),
  (2, 2, 6, 1, 135.00, NULL, 0.00, 72.00, NULL),
  (3, 3, 2, 1, 78.00, 'Brigadeiros em cima x10', 30.00, 55.00, NULL),
  (4, 4, 8, 1, 140.00, NULL, 0.00, 73.00, 'Pouco doce'),
  (5, 5, 13, 1, 195.00, 'Escrita personalizada', 10.00, 140.00, 'Parabens, Joao'),
  (6, 6, 1, 1, 98.00, NULL, 0.00, 71.85, NULL),
  (7, 7, 7, 1, 135.00, NULL, 0.00, 70.00, NULL),
  (8, 7, 18, 10, 3.50, NULL, 0.00, 1.60, NULL),
  (9, 8, 2, 1, 78.00, NULL, 0.00, 55.00, NULL);

-- custo_cobrado = custo da opção x quantidade
INSERT INTO opcao_escolhida (id_item_pedido, id_opcao, quantidade, custo_cobrado) VALUES
  (1, 4, 1, 10.00),
  (3, 6, 10, 30.00),
  (5, 29, 1, 10.00);

-- ---------- Compras ----------
-- valor_total = soma(quantidade * custo_unitario), na unidade de compra
INSERT INTO compra_insumo (id_compra_insumo, id_fornecedor, data_compra, data_entrega, valor_total, status, nota_fiscal) VALUES
  (1, 1, date_trunc('hour', now()) - interval '6 days', date_trunc('day', now()) - interval '5 days', 118.45, 'recebida', 'NF 000123'),
  (2, 2, date_trunc('hour', now()) - interval '1 day', date_trunc('day', now()) + interval '2 days', 258.60, 'pendente', NULL),
  (3, 1, date_trunc('hour', now()) - interval '3 days', NULL, 46.90, 'cancelada', NULL);

INSERT INTO item_compra_insumo (id_item_compra, id_compra_insumo, id_insumo, quantidade, custo_unitario) VALUES
  (1, 1, 1, 10, 5.13),
  (2, 1, 3, 5, 13.43),
  (3, 2, 4, 24, 7.03),
  (4, 2, 6, 2, 44.94),
  (5, 3, 2, 10, 4.69);

-- ---------- Movimentações de estoque ----------
-- Quantidades na unidade da receita (entrada da compra = quantidade comprada x fator)
INSERT INTO movimentacao_estoque (id_insumo, tipo, quantidade, data, motivo, id_pedido, id_compra_insumo) VALUES
  -- compra 1 recebida: 10 kg de farinha e 5 dúzias de ovos
  (1, 'entrada', 10000, date_trunc('day', now()) - interval '5 days' + interval '9 hours', NULL, NULL, 1),
  (3, 'entrada', 60, date_trunc('day', now()) - interval '5 days' + interval '9 hours', NULL, NULL, 1),
  -- pedido 1 confirmado: massa de chocolate x1 + recheio de brigadeiro x1,5
  (1, 'consumo', 280, date_trunc('day', now()) - interval '11 days' + interval '10 hours', NULL, 1, NULL),
  (2, 'consumo', 280, date_trunc('day', now()) - interval '11 days' + interval '10 hours', NULL, 1, NULL),
  (3, 'consumo', 4, date_trunc('day', now()) - interval '11 days' + interval '10 hours', NULL, 1, NULL),
  (8, 'consumo', 120, date_trunc('day', now()) - interval '11 days' + interval '10 hours', NULL, 1, NULL),
  (10, 'consumo', 240, date_trunc('day', now()) - interval '11 days' + interval '10 hours', NULL, 1, NULL),
  (11, 'consumo', 120, date_trunc('day', now()) - interval '11 days' + interval '10 hours', NULL, 1, NULL),
  (12, 'consumo', 15, date_trunc('day', now()) - interval '11 days' + interval '10 hours', NULL, 1, NULL),
  (4, 'consumo', 3, date_trunc('day', now()) - interval '11 days' + interval '10 hours', NULL, 1, NULL),
  (5, 'consumo', 1.5, date_trunc('day', now()) - interval '11 days' + interval '10 hours', NULL, 1, NULL),
  (9, 'consumo', 30, date_trunc('day', now()) - interval '11 days' + interval '10 hours', NULL, 1, NULL),
  -- pedido 2 confirmado: brigadeiro x2
  (4, 'consumo', 4, date_trunc('day', now()) - interval '3 days' + interval '10 hours', NULL, 2, NULL),
  (9, 'consumo', 60, date_trunc('day', now()) - interval '3 days' + interval '10 hours', NULL, 2, NULL),
  (6, 'consumo', 100, date_trunc('day', now()) - interval '3 days' + interval '10 hours', NULL, 2, NULL),
  (19, 'consumo', 300, date_trunc('day', now()) - interval '3 days' + interval '10 hours', NULL, 2, NULL),
  (21, 'consumo', 100, date_trunc('day', now()) - interval '3 days' + interval '10 hours', NULL, 2, NULL),
  -- ajuste manual (pode ser desfeito pela tela)
  (22, 'ajuste', -2, date_trunc('day', now()) - interval '1 day' + interval '17 hours', 'Caixas amassadas na contagem', NULL, NULL);

-- ---------- Sequências ----------
-- Os INSERTs acima usaram ids fixos: as sequências continuam do maior id, senão o próximo INSERT da aplicação repete um id
SELECT setval(pg_get_serial_sequence('usuario', 'id_usuario'), (SELECT max(id_usuario) FROM usuario));
SELECT setval(pg_get_serial_sequence('endereco', 'id_endereco'), (SELECT max(id_endereco) FROM endereco));
SELECT setval(pg_get_serial_sequence('fornecedor', 'id_fornecedor'), (SELECT max(id_fornecedor) FROM fornecedor));
SELECT setval(pg_get_serial_sequence('insumo', 'id_insumo'), (SELECT max(id_insumo) FROM insumo));
SELECT setval(pg_get_serial_sequence('receita', 'id_receita'), (SELECT max(id_receita) FROM receita));
SELECT setval(pg_get_serial_sequence('produto', 'id_produto'), (SELECT max(id_produto) FROM produto));
SELECT setval(pg_get_serial_sequence('opcao_personalizacao', 'id_opcao'), (SELECT max(id_opcao) FROM opcao_personalizacao));
SELECT setval(pg_get_serial_sequence('pedido', 'id_pedido'), (SELECT max(id_pedido) FROM pedido));
SELECT setval(pg_get_serial_sequence('item_pedido', 'id_item_pedido'), (SELECT max(id_item_pedido) FROM item_pedido));
SELECT setval(pg_get_serial_sequence('compra_insumo', 'id_compra_insumo'), (SELECT max(id_compra_insumo) FROM compra_insumo));
SELECT setval(pg_get_serial_sequence('item_compra_insumo', 'id_item_compra'), (SELECT max(id_item_compra) FROM item_compra_insumo));