# Sistema de Gestão de Confeitaria

Repositório oficial do projeto da disciplina de Paradigma Orientado a Objetos para Desenvolvimento de Software (INF01210) da Universidade Estadual do Norte Fluminense Darcy Ribeiro (UENF).

## Sobre o Projeto

O Sistema de Gestão de Confeitaria foi pensado para apoiar a futura operação de uma confeitaria afetiva com abertura planejada para os próximos anos. 

Atualmente, o negócio funciona de forma artesanal e sob encomenda para pessoas próximas, com controle de pedidos e estoque feitos manualmente.

O objetivo deste software é organizar e automatizar a operação da confeitaria antes de sua formalização, focando em três grandes necessidades da proprietária:
1. Organizar o estoque de ingredientes e embalagens.
2. Automatizar a precificação dos produtos com base nos custos e personalizações.
3. Gerenciar os pedidos de forma centralizada e sem confusões.

A aplicação está dividida em duas grandes frentes que compartilham a mesma inteligência e o mesmo banco de dados:

- Área do Cliente (no celular)
- Área Interna (no computador)

## Tecnologias Utilizadas

- Linguagem: Python
- Backend: Flask (microframework)
- Banco de Dados: PostgreSQL
- Interface (Frontend): HTML e CSS
- Testes: pytest
- Organização e Versão: Git, GitHub e Docker para rodar o banco de dados

## Estrutura do Projeto

```
sistema-confeitaria/
├── app/
│   ├── controllers/                 # (a criar) rotas Flask, sem regra de negócio
│   ├── models/                      # entidades e regras do negócio; sem Flask e sem SQL
│   │   ├── __init__.py              # índice dos models
│   │   ├── administrador.py
│   │   ├── base.py                  # Entidade (classe mãe de tudo que tem id)
│   │   ├── cliente.py
│   │   ├── contratos.py             # Protocols de Pedido, Estoque e Recomendador
│   │   ├── endereco.py
│   │   ├── enums.py                 # Perfil, StatusPedido, StatusPagamento...
│   │   ├── funcionario.py
│   │   ├── opcao_personalizacao.py
│   │   ├── produto.py
│   │   ├── senha.py                 # Senha (hash) e SenhaAusente
│   │   └── usuario.py               # Usuario (classe abstrata)
│   ├── services/                    # casos de uso
│   │   ├── __init__.py
│   │   ├── autenticacao.py          # login e tokens
│   │   └── controle_login.py        # bloqueio por tentativas
│   ├── templates/
│   ├── validators/                  # validação de dados; não conhece nenhuma entidade
│   │   ├── __init__.py
│   │   ├── campos.py                # garantir() e Validador
│   │   └── senha.py                 # regras de força da senha
│   ├── __init__.py
│   └── exceptions.py                # ValidacaoError, AcessoNegadoError...
├── tests/
├── .env                             # local, não vai para o GitHub
├── .gitignore
├── README.md
├── requirements.txt
└── run.py
```

## Convenções de código

**Nomes**
- Classes: `PascalCase` (`OpcaoPersonalizacao`)
- Métodos e funções: `camelCase` (`adicionarEndereco`)
- Variáveis, atributos e propriedades: `snake_case` (`custo_adicional`)
- Constantes: `MAIUSCULAS` (`TAMANHO_MINIMO`)
- Arquivos e pastas: `snake_case` (`opcao_personalizacao.py`)
- Nome começando com `_` = uso interno da classe; não acessar de fora.

**Orientação a objetos**
- Não usamos `if/elif/else`. No lugar, usamos polimorfismo (cada classe responde do seu jeito),
  tabelas (`dict`/`Enum`) e a função `garantir(condicao, erro)` para validações.
  Única exceção: `if TYPE_CHECKING:` (recurso de tipagem, não é regra de negócio).
- Entidades ficam em `app/models`, um arquivo por tabela do DER. Partes que só existem dentro de outra entidade também têm arquivo próprio e se referenciam por dicas de tipo.
- Importações sempre absolutas: `from app.models import Cliente`.

**Regras que não podem ser quebradas**
- Todo dado que entra passa por `Validador` (`app/validators/campos.py`).
  Erros usam as exceções de `app.exceptions`.
- Dinheiro é `Decimal` (via `Validador.dinheiro`), **nunca `float`**.
- A senha nunca é guardada em texto: use `Senha.criar(...)`. Só o hash vai para o banco.
- O CPF só é lido por `obterCpf(solicitante)`, que confere a permissão.
- Regra de negócio não fica em controller nem em repository.

**Comentários**
- Toda classe e função tem docstring (`"""..."""`) dizendo o que faz e por quê.
- Uso de `#` para explicar sintaxe ou lógica que não é óbvia, escrito em português.

## Versionamento

### Novo ciclo de desenovolvimento:

- `git switch nome-da-branch` Para trocar de branch.
- `git pull` Para puxar a ultima atualização da branch.
- `git switch -c funcionalidade/nome-da-funcionalidade-nova` Cria uma nova banch e troca automatico pra ela.
- `git push -u origin funcionalidade/nome-da-funcionalidade-nova` Manda para o github sua nova branch.

### Dia a dia depois de iniciar o novo ciclo:
- `git add .` Para adicionar todos os arquivos (menos do .gitignore) para serem comitados.
- `git commit -m "Escreve o que foi feito"` Comita as ultimas modificações.
- `git push` Posta as atualizações online no github. O git add e git commit estavam apenas locais na maquina.

### Fim do desenvolvimento da funcionalidade
- `git status` Para conferir se não ficou nada sem commit.
  -  Se tiver, faz `git add .` depois `git commit` e por fim `git push`.

No site:
- No GitHub, abrir um **Pull Request** da `funcionalidade/nome-da-funcionalidade-nova` para a `main` e pedir revisão.

  - Terminal:
    - Se pedirem ajustes: fazer as alterações e repetir `git add .` depois `git commit -m "Escreve o que mudou"` e `git push`. O Pull Request atualiza sozinho.
  
    - Se a `main` mudou enquanto o PR estava aberto(tentar não fazer isso):
      - `git fetch origin` Baixa as atualizações do GitHub sem mexer nos seus arquivos.
      - `git merge origin/main` Traz a `main` atualizada para dentro da sua branch (resolver conflitos, se tiver).
      - `git push` Manda a branch atualizada para o PR.
  
- Depois de aprovado, fazer o merge no GitHub usando **"Create a merge commit"** (não usar squash!!!, manter visivel os comits).
- Clicar em **"Delete branch"** no próprio PR para apagar a branch no GitHub.

Por fim, de volta ao terminal:
- `git switch main` Volta para a `main`.
- `git pull` Puxa a `main` já com a funcionalidade nova.
- `git branch -d funcionalidade/nome-da-funcionalidade-nova` Apaga a branch local (só apaga se já tiver sido mergeada).
- `git fetch --prune` Limpa as referências de branches que já foram apagadas no GitHub.
- Volta para o **Novo ciclo de desenvolvimento**.

## Equipe

- Anna Cecília Garcia
- Iarlo Henrique Drumond Pires Pascoal
