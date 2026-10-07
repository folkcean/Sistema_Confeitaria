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
