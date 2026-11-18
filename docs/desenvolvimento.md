# Guia de desenvolvimento

Convenções e processos internos da equipe. Para instalar e executar o sistema, consulte o [README](../README.md).

## Convenções de código

### Nomes

| Elemento | Padrão | Exemplo |
|---|---|---|
| Classes | `PascalCase` | `OpcaoPersonalizacao` |
| Métodos e funções | `camelCase` | `adicionarEndereco` |
| Variáveis, atributos e propriedades | `snake_case` | `custo_adicional` |
| Constantes | `MAIUSCULAS` | `TAMANHO_MINIMO` |
| Arquivos e pastas | `snake_case` | `opcao_personalizacao.py` |

Um nome iniciado por `_` indica uso interno da classe e não deve ser acessado de fora.

### Orientação a objetos

- O código não usa `if/elif/else`. No lugar, usa polimorfismo (cada classe responde à sua maneira), tabelas
  (`dict`/`Enum`) e a função `garantir(condicao, erro)` para validações. Única exceção: `if TYPE_CHECKING:`
  (recurso de tipagem, sem regra de negócio).
- As entidades ficam em `app/models`, um arquivo por tabela do DER. Partes que só existem dentro de outra entidade
  também têm arquivo próprio e se referenciam por dicas de tipo.
- As importações são sempre absolutas: `from app.models import Cliente`.

### Regras obrigatórias

- Todo dado de entrada passa pelo `Validador` (`app/validators/campos.py`), e os erros usam as exceções de
  `app.exceptions`.
- Valores monetários são `Decimal` (via `Validador.dinheiro`), **nunca `float`**.
- A senha nunca é armazenada em texto: use `Senha.criar(...)`; só o hash vai para o banco.
- O CPF só é lido por `obterCpf(solicitante)`, que verifica a permissão.
- Regras de negócio não ficam em controllers nem em repositories.
- Toda rota nova entra na matriz de acesso (`tests/rotas/test_matriz_de_acesso.py`); caso contrário, a suíte falha.

### Comentários

- Toda classe e função tem docstring dizendo o que faz e por quê.
- Comentários com `#` explicam sintaxe ou lógica não óbvia, em português.

## Testes

```bash
pytest -q                                           # completo (banco ligado)
pytest tests/models tests/services tests/validators # sem banco
pytest tests/models/test_pedido.py -v               # um arquivo, listando cada teste
pytest tests/models/test_pedido.py -x --tb=short    # para no primeiro erro, com mensagem curta
```

- Serviços externos (Pix, e-mail, IA) nunca são chamados nos testes: use os dublês de `tests/falsos.py`.
- A configuração de teste (`ConfigTeste`) zera as chaves de SMTP e de IA, mesmo que estejam no `.env`.
- Os testes de banco carregam `tests/db/DB_fill.sql` dentro de uma transação desfeita ao final.

## Alterações no banco de dados

O DER no Visual Paradigm (`docs/Sistema Confeitaria.vpp`) é a fonte da verdade do banco. Toda alteração começa
nele, nunca direto no SQL.

- `db/init/`: estrutura inicial, gerada a partir do DER. Roda apenas na criação do banco e **não deve mais ser
  editada**.
- `db/update/`: alterações posteriores, numeradas em ordem (`001_...sql`, `002_...sql`).

### Como fazer uma alteração

1. Altere o DER no Visual Paradigm.
2. Gere o script com a opção **Update**, exportando para arquivo em vez de executar direto no banco.
3. Salve como `db/update/<próximo número>_<descricao_curta>.sql`.
4. **Revise o script antes de executar.** Ao renomear uma coluna, o Visual Paradigm pode gerar `DROP COLUMN` +
   `ADD COLUMN`, o que apaga os dados; nesse caso, substitua por `ALTER TABLE ... RENAME COLUMN ...`.
5. Aplique no banco local:
   ```bash
   docker compose exec -T db psql -U app -d appdb -v ON_ERROR_STOP=1 --single-transaction < db/update/<arquivo>.sql
   ```
6. Faça o commit do DER e do script juntos e avise a equipe sobre a nova migração.

### Regras

- Nunca edite um arquivo de `db/update/` já commitado; para corrigir algo, crie um novo.
- Depois de um `git pull` que trouxe arquivos novos em `db/update/`, aplique cada um, em ordem.
- Cada migração é aplicada **uma única vez** em cada banco. O GitHub Actions aplica todas, em ordem, num banco novo.
- Para recriar o banco do zero (**apaga todos os dados**): `docker compose down -v` e depois `docker compose up -d`.

## Versionamento

### Branches e mensagens

- Cada funcionalidade é desenvolvida numa branch própria, criada a partir da `main` atualizada
  (ex.: `incremento/assistente-ia`).
- Mensagens de commit seguem o formato `tipo(escopo): descrição`, em português. Tipos usados: `feat`, `fix`,
  `test`, `docs`, `chore`.

### Ciclo de uma funcionalidade

```bash
git switch main
git pull
git switch -c incremento/nome-da-funcionalidade
# ... desenvolvimento, com commits pequenos ...
git add <arquivos>
git commit -m "feat(escopo): o que foi feito"
git push -u origin incremento/nome-da-funcionalidade
```

1. Abra um **Pull Request** para a `main` e peça a revisão da dupla. O GitHub Actions executa a suíte no PR.
2. Ajustes pedidos na revisão: novos commits na mesma branch atualizam o PR.
3. Se a `main` mudou enquanto o PR estava aberto: `git fetch origin`, `git merge origin/main`, resolver
   conflitos, rodar os testes e `git push`.
4. Após a aprovação, faça o merge com **"Create a merge commit"** (sem squash, para preservar o histórico) e apague
   a branch no próprio PR.

### Depois do merge

```bash
git switch main
git pull
git branch -d incremento/nome-da-funcionalidade
git fetch --prune
```