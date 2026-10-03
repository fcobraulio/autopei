# Pasta de desenvolvimento

Dados **fictícios** para testar o AutoPEI com um sistema completo: um campus, dois semestres, pessoas de todos os perfis, PEIs em todas as etapas e DOCX prontos para baixar.

> Nada aqui é de estudantes reais. Nunca use o modo de desenvolvimento em produção.

## Como usar

```bash
uv run python scripts/dev.py iniciar           # recria o banco de desenvolvimento com estes dados e abre o AutoPEI em modo dev
uv run python scripts/dev.py iniciar --manter  # abre em modo dev mantendo o que você já fez no banco de desenvolvimento
uv run python scripts/dev.py popular           # só recria os dados (sem abrir o AutoPEI)
uv run python scripts/dev.py zerar --dev       # deixa o banco de desenvolvimento vazio (só campus, perguntas e admin)
uv run python scripts/dev.py zerar             # APAGA TUDO do banco principal (.env) e deixa pronto para começar do zero
```

O modo de desenvolvimento usa um **banco separado**: o mesmo servidor do `DATABASE_URL`, com o nome terminado em `_dev` (por exemplo, `autopei_dev`). Ele é criado sozinho. Para usar outro banco, defina `AUTOPEI_DEV_DATABASE_URL` no `.env`.

Se o seu usuário do PostgreSQL não puder criar bancos (erro *permission denied to create database*), crie o banco uma vez como administrador e rode de novo:

```bash
sudo -u postgres createdb -O autopei autopei_dev
# com Docker: docker compose exec db createdb -U autopei autopei_dev
``` Assim, popular e testar **não mexem nos dados reais**.

Abra http://localhost:8501. Na tela de login há o seletor **Entrar rapidamente como…** (escolha a pessoa e clique em Entrar) e o formulário de usuário e senha.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `logins.csv` | as 22 pessoas, com login, senha e perfil (senha de todos: `autopei`; administrador: `admin` / `admin`) |
| `turmas.csv` | 3 turmas: INFO1V (Informática integrado), ALI2M (Alimentos integrado) e TSI3N (Sistemas para Internet) |
| `disciplinas.csv` | 15 disciplinas (5 por turma), com código, docente(s), objetivos e conteúdos |
| `estudantes.csv` | 10 estudantes com PEI em 2026.2, a NEE e a etapa em que cada PEI deve ficar |
| `estudos_individualizados.csv` | horários de estudo individualizado cadastrados pelos docentes |
| `saida/` | cópia dos DOCX prontos (gerada ao popular; fora do git) |

Os CSV usam `;` e abrem direto no Excel/LibreOffice. Você pode editá-los e rodar `popular` de novo. As respostas dos formulários ficam em `scripts/dev_conteudo.py`, uma por perfil de NEE (`tea`, `tea_ah`, `tdah`, `tag_tdah`, `dislexia`, `baixa_visao`, `auditiva`, `di`, `discalculia`).

## O que fica pronto

**Semestre 2026.1 (encerrado):** PEIs registrados de Bruno, Elisa e João, que servem de base para o pré-preenchimento em 2026.2.

**Semestre 2026.2 (aberto):**

| Estudante | Turma | Situação | Quem tem pendência |
|---|---|---|---|
| Ana Clara Bezerra | INFO1V | Aguardando Psicopedagogia | psico1, psico2, psico3 |
| Bruno Medeiros Dantas | INFO1V | Aguardando Psicopedagogia (**pré-preenchido** de 2026.1) | psico1, psico2, psico3 |
| Camila Faria Souto | ALI2M | Aguardando ETEP | etep1, etep2 |
| Fábio Nóbrega Lins | ALI2M | Aguardando ETEP (**correção** pedida pela gestora) | etep1, etep2 |
| Davi Lucena Araújo | TSI3N | Docentes: 2 de 5 concluídos (rascunho salvo em Eng. de Software) | prof10, prof11, prof12 |
| Elisa Morais Galvão | INFO1V | Docentes: 4 de 5 concluídos, com estudos individualizados | prof04 |
| Gabriela Azevedo Cunha | TSI3N | Em revisão (NAPNE) | gestora, auxiliares |
| Heitor Silveira Maia | ALI2M | Aprovado, **DOCX pronto**, aguardando registro no SUAP | gestora |
| Isabela Pinheiro Rocha | TSI3N | Registrado (**DOCX** disponível) | — |
| João Victor Tavares | INFO1V | Registrado (**DOCX** disponível, pré-preenchido de 2026.1) | — |

Também há laudos fictícios em PDF anexados pela Psicopedagogia, um modelo de prova ampliada anexado por um docente e uma disciplina com dois docentes (TSI.0302 – Banco de Dados: prof08 e prof09).

## Roteiro rápido de teste

1. **gestora** → Painel: veja onde está cada PEI. Abra **Gabriela** (revisão): escreva o parecer e aprove ou devolva. Abra **Heitor** (aprovado): baixe o DOCX e marque como registrado.
2. **psico1** → Preencha o PEI de **Ana** (em branco) e o de **Bruno** (pré-preenchido).
3. **etep1** → Corrija o PEI de **Fábio** (volta direto para a revisão) e preencha o de **Camila**.
4. **prof04** → Conclua Física I da **Elisa**: o PEI vai para a revisão.
5. **prof10** → Continue o rascunho de Engenharia de Software do **Davi** e cadastre um estudo individualizado.
6. **admin** → Administração: campi, perguntas, usuários.
