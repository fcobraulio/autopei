<p align="center"><img src="assets/logo.svg" alt="AutoPEI" width="220"></p>

# AutoPEI

**Plano Educacional Individualizado (PEI) com fluxo de preenchimento condicionado, para os NAPNEs do IFRN.**

O NAPNE cadastra o estudante com Necessidades Educacionais Específicas (NEE) e os **códigos das disciplinas** que ele cursa. O PEI passa pela **Psicopedagogia**, depois pela **ETEP** e então segue **ao mesmo tempo (em paralelo) para todos os docentes** dessas disciplinas. Quando todos concluem, volta ao NAPNE para revisão, correção ou aprovação. Ao aprovar, o sistema gera um **DOCX só com texto e tabelas**, pronto para colar no SUAP. Depois das assinaturas no SUAP, o(a) gestor(a) marca o PEI como **registrado**.

Feito com **Streamlit (Python)** e **PostgreSQL**, com dependências gerenciadas pelo **[uv](https://docs.astral.sh/uv/)**. Login pelo **SUAP via OAuth**: o botão “Entrar com SUAP” leva à página de login do próprio SUAP e volta para o sistema, como no IFKey e no site da ASIFRN.

---

## Sumário

1. [Funcionalidades](#funcionalidades)
2. [Perfis, login e permissões](#perfis-login-e-permissões)
3. [Fluxo do PEI](#fluxo-do-pei)
4. [Instalação com uv](#instalação-com-uv)
5. [Configuração (.env)](#configuração-env)
6. [Login pelo SUAP (OAuth)](#login-pelo-suap-oauth)
7. [Primeiro acesso](#primeiro-acesso)
8. [Administração por código](#administração-por-código)
9. [Perguntas dos formulários](#perguntas-dos-formulários)
10. [O documento DOCX](#o-documento-docx)
11. [Estrutura do projeto](#estrutura-do-projeto)
12. [Testes](#testes)
13. [Segurança e LGPD](#segurança-e-lgpd)
14. [Limitações conhecidas](#limitações-conhecidas)

---

## Funcionalidades

- **Login só pelo SUAP** para gestores, auxiliares, ETEP e docentes (redirecionamento OAuth: a senha do SUAP nunca passa pelo AutoPEI). Login com usuário e senha apenas para a Psicopedagogia e administradores.
- **Lista de matrículas autorizadas**: o(a) gestor(a) define quais matrículas SUAP são auxiliares e ETEP. **Docente pode ser qualquer pessoa** que entra pelo SUAP.
- **Disciplinas por código**: o NAPNE associa os **códigos das disciplinas** aos estudantes com NEE e aos docentes. Um estudante com os códigos 123, 456 e 789, depois da Psicopedagogia e da ETEP, **cai automaticamente e ao mesmo tempo** na caixa dos docentes desses três códigos.
- **Caixas de pendências**: Psicopedagogia, ETEP e docentes entram e já veem o que precisam preencher.
- **Painel da gestão**: PEIs por etapa, com quem estão, há quantos dias, quantos docentes já concluíram e quais disciplinas ainda estão sem docente.
- **Correção só para quem recebeu**: na revisão, o NAPNE devolve para a Psicopedagogia, a ETEP ou um docente específico. O PEI volta **só para essa pessoa** e depois **direto para o NAPNE**, sem refazer a cadeia. A cadeia só é refeita se o(a) gestor(a) marcar isso explicitamente.
- **Pré-preenchimento com o semestre anterior**: no novo PEI de um estudante que já teve PEI, Psicopedagogia, ETEP e docentes das **mesmas disciplinas** recebem os campos preenchidos e só ajustam o que mudou. Disciplinas novas começam em branco.
- **Estudos individualizados cadastrados pelos docentes**: cada docente, no seu componente, cadastra os horários de estudo individualizado que achar necessários (horas fechadas, ex.: 13h–14h), com frequência **semanal, quinzenal ou mensal** e quantos horários quiser (ex.: dois por semana). O DOCX traz uma tabela com todos os horários ou, se nenhum docente cadastrar, informa que o(a) estudante não tem estudo individualizado. A gestão não faz esse cadastro.
- **Anexos internos**: os **laudos são anexados pela Psicopedagogia**; ETEP e docentes podem anexar outros documentos de apoio (notificação escolar, prova…). Gestão e auxiliares só cadastram os dados do estudante e consultam os anexos, que **não entram no DOCX**.
- **“Nada a declarar”** em toda pergunta de resposta longa, com texto automático adequado à pergunta.
- **Perguntas configuráveis** pelo administrador: resposta longa, escolha única, múltipla escolha e menu de seleção.
- **DOCX** sem imagens (negrito, itálico, sublinhado, cores, maiúsculas/minúsculas e tabelas).
- **Campus e semestre**: o sistema começa com **Currais Novos**; o administrador cadastra novos campi e seus gestores. O(a) gestor(a) encerra o semestre quando tudo estiver registrado.

## Perfis, login e permissões

| Perfil | Como entra | Quem cadastra |
|---|---|---|
| **Administrador(a)** | conta local inicial ou SUAP | `.env` / outro administrador |
| **Gestor(a)** | **somente SUAP** | administrador (Administração → Campi e gestores) |
| **Auxiliar** | **somente SUAP** | gestor(a) (Acessos → lista de matrículas autorizadas) |
| **ETEP** | **somente SUAP** | gestor(a) (Acessos → lista de matrículas autorizadas) |
| **Psicopedagogia** | usuário e senha (pode trocar a senha) | gestor(a) (Acessos → Psicopedagogia) |
| **Docente** | **somente SUAP** | ninguém: qualquer pessoa do SUAP pode ser docente; os PEIs chegam pela associação disciplina ↔ docente |

O SUAP informa o **tipo de usuário** (ex.: “Servidor (Docente)”), que aparece no perfil e serve de sugestão ao associar docentes. Os perfis que dão poder no sistema (gestor, auxiliar, ETEP) dependem da lista do campus, não só do tipo informado pelo SUAP.

| Ação | Admin | Gestor(a) | Auxiliar | Psicoped. | ETEP | Docente |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Painel, lista de PEIs, cadastrar PEI | ✅ | ✅ | ✅ | | | |
| Associar disciplinas (códigos) a estudantes e docentes | ✅ | ✅ | ✅ | | | |
| Devolver para correção, parecer da equipe | ✅ | ✅ | ✅ | | | |
| **Aprovar, registrar, cancelar** | ✅ | ✅ | | | | |
| **Criar e encerrar semestre** | ✅ | ✅ | | | | |
| **Acessos** (auxiliares, ETEP, psicopedagogas) | ✅ | ✅ | | | | |
| Campi, gestores, perguntas, administradores | ✅ | | | | | |
| Cadastrar os dados do estudante | ✅ | ✅ | ✅ | | | |
| Preencher a sua etapa | | | | ✅ | ✅ | ✅ |
| Anexar laudos | | | | ✅ | | |
| Anexar outros documentos de apoio | | | | ✅ | ✅ | ✅ |
| Cadastrar estudos individualizados | | | | | | ✅ |

## Fluxo do PEI

```mermaid
flowchart LR
    A["NAPNE cadastra estudante<br/>+ códigos das disciplinas"] --> B["Psicopedagogia<br/>(uma por estudante)"]
    B --> C["ETEP<br/>(uma por estudante)"]
    C --> D1["Docente da disciplina 123"]
    C --> D2["Docente da disciplina 456"]
    C --> D3["Docente da disciplina 789"]
    D1 --> R["Revisão NAPNE<br/>(quando TODOS concluírem)"]
    D2 --> R
    D3 --> R
    R --> Q{"Está tudo certo?"}
    Q -.->|"Não: volta só para quem<br/>precisa corrigir"| C
    Q -->|Sim| AP["Gestor(a) aprova<br/>DOCX gerado"]
    AP --> SU["Cola no SUAP e<br/>coleta assinaturas"]
    SU --> RG["Registrado"]
```

- **Psicopedagogia e ETEP**: cada estudante tem **uma** etapa de cada, sempre nessa ordem.
- **Docentes, em paralelo**: depois da ETEP, o PEI aparece **ao mesmo tempo** na caixa de **todos** os docentes das disciplinas do estudante. Cada docente preenche só o seu componente. O PEI segue para a revisão **quando todos terminarem**. Uma disciplina com mais de um docente pode ser preenchida por qualquer um deles.
- **Disciplina sem docente**: o painel avisa. Quando a gestão fizer a associação, o PEI aparece na caixa do docente sem nenhum outro passo.
- **Correções**: o PEI volta **apenas para a etapa escolhida** (ou para um docente específico) e, ao ser reenviado, retorna **direto para a revisão**. Exemplo: devolver para a ETEP **não** faz o PEI passar de novo pelos docentes. Para refazer as etapas seguintes, a gestão marca isso explicitamente ao devolver.

| Estado | Com quem está |
|---|---|
| Aguardando Psicopedagogia | Psicopedagogia do campus |
| Aguardando ETEP | ETEP do campus |
| Com os docentes (em paralelo) | todos os docentes com componente pendente |
| Em revisão (NAPNE) | gestor(a) e auxiliar |
| Aprovado · aguardando registro | gestor(a), que sobe o documento no SUAP |
| Registrado / Cancelado | concluído |

O desenho do processo está em [`docs/fluxo_autopei.drawio`](docs/fluxo_autopei.drawio). Ele abre gratuitamente em **[app.diagrams.net](https://app.diagrams.net)**. Há também a versão em imagem ([PNG](docs/fluxo_autopei.png)) e em Mermaid ([`.mmd`](docs/fluxo_autopei.mmd), abre em **[mermaid.live](https://mermaid.live)**).

## Instalação com uv

As dependências e suas versões ficam em `pyproject.toml` e são travadas em `uv.lock`. Não há `requirements.txt`.

### Opção A — Ubuntu, sem Docker

```bash
# 1. uv (uma vez)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. PostgreSQL
sudo apt install postgresql
sudo -u postgres psql -c "CREATE USER autopei WITH PASSWORD 'autopei';"
sudo -u postgres psql -c "CREATE DATABASE autopei OWNER autopei;"

# 3. Dependências (cria .venv com as versões exatas do uv.lock)
uv sync

# 4. Configuração
cp .env.example .env          # preencha SUAP_CLIENT_ID/SECRET e a senha do admin

# 5. Executar
uv run streamlit run app.py
```

Comandos úteis do uv:

| Tarefa | Comando |
|---|---|
| Instalar exatamente o que está no lock | `uv sync --frozen` |
| Adicionar uma biblioteca | `uv add nome-da-biblioteca` |
| Atualizar as versões travadas | `uv lock --upgrade` e depois `uv sync` |
| Rodar os testes | `uv run pytest` |

### Opção B — Docker

```bash
cp .env.example .env
docker compose up -d --build
```

A imagem usa o `uv` e instala exatamente o que está no `uv.lock`. O PostgreSQL fica no volume `dados_autopei`. Acesse `http://localhost:8501`.

> **Produção:** use HTTPS (Nginx, Caddy ou o proxy do campus) e cadastre no SUAP o endereço público como Redirect URI.

> **Atualizando da versão 1.0:** o modelo de dados mudou (acessos por matrícula e disciplinas por código). Se você tinha um banco de testes da versão anterior, apague e recrie o banco antes de iniciar.

## Configuração (.env)

| Variável | Para que serve | Padrão |
|---|---|---|
| `DATABASE_URL` | conexão com o PostgreSQL | `postgresql+psycopg://autopei:autopei@localhost:5432/autopei` |
| `AUTOPEI_ADMIN_USERNAME` / `AUTOPEI_ADMIN_PASSWORD` | administrador local criado na 1ª execução | `admin` / — |
| `AUTOPEI_ADMINS_SUAP` | matrículas SUAP que viram administradoras ao entrar | — |
| `SUAP_URL` | endereço do SUAP | `https://suap.ifrn.edu.br` |
| `SUAP_CLIENT_ID` / `SUAP_CLIENT_SECRET` | credenciais da aplicação OAuth cadastrada no SUAP | — |
| `SUAP_REDIRECT_URI` | endereço do AutoPEI para onde o SUAP volta (igual ao cadastrado no SUAP) | `http://localhost:8501/` |
| `SUAP_ME_ENDPOINTS` | rotas com os dados da pessoa logada | `/api/rh/eu/,/api/eu/` |
| `AUTOPEI_SECRET_KEY` | chave para assinar o `state` do login | derivada das credenciais |
| `AUTOPEI_ANEXO_MAX_MB` | tamanho máximo de cada anexo | `10` |
| `AUTOPEI_SUAP_FAKE` | **somente desenvolvimento**: simulador do retorno do SUAP | `0` |

## Login pelo SUAP (OAuth)

O fluxo é o mesmo do IFKey e do site da ASIFRN:

1. A tela de entrada mostra **um botão “Entrar com SUAP”**, que leva a `https://suap.ifrn.edu.br/o/authorize/?client_id=…&response_type=code&redirect_uri=…&state=…`.
2. A pessoa faz login **na página do SUAP**.
3. O SUAP volta para o AutoPEI com `?code=…`.
4. O AutoPEI troca o `code` por um token em `/o/token/`, usando `client_id` e `client_secret`.
5. Com o token, lê `/api/rh/eu/`: matrícula (`identificacao`), nome, e-mail, campus e **tipo de usuário** (`tipo_usuario`).

Logo abaixo do botão há o link **“Deseja entrar com login e senha?”**, para a Psicopedagogia e os administradores.

**Cadastro da aplicação no SUAP** (uma vez):

1. Acesse **https://suap.ifrn.edu.br/api/** → *Aplicações OAuth2* → *Adicionar*.
2. *Client type*: **Confidential**. *Authorization grant type*: **Authorization code**.
3. *Redirect URIs*: o endereço exato do AutoPEI, por exemplo `https://autopei.cn.ifrn.edu.br/` ou `http://localhost:8501/` para testes.
4. Copie o *Client ID* e o *Client secret* para o `.env`.

**Desenvolvimento sem SUAP:** com `AUTOPEI_SUAP_FAKE=1`, a tela de entrada mostra um simulador que substitui a página do SUAP. Ele permite informar a matrícula e o tipo de usuário. Nunca ative isso em produção.

## Primeiro acesso

1. Defina `AUTOPEI_ADMIN_PASSWORD`, `SUAP_CLIENT_ID` e `SUAP_CLIENT_SECRET` no `.env` e inicie o sistema.
2. Entre em **“Deseja entrar com login e senha?”** com o usuário `admin`.
3. Em **Administração → Campi e gestores**, autorize a matrícula SUAP do(a) gestor(a) do NAPNE de Currais Novos.
4. O(a) gestor(a) entra com **Entrar com SUAP** e:
   - cria o semestre em **Semestres** (ex.: `2026.2`);
   - em **Acessos**, autoriza as matrículas das **auxiliares** e da **ETEP** e cria a conta da **Psicopedagogia**;
   - em **Disciplinas e docentes**, associa cada **código de disciplina** ao docente (pode colar uma lista);
   - em **PEIs → Novo PEI**, cadastra o estudante com os códigos das disciplinas.

## Administração por código

```bash
uv run python scripts/gerenciar.py init
uv run python scripts/gerenciar.py criar-admin --usuario admin --nome "Fulano" --senha "Troque123"
uv run python scripts/gerenciar.py admin-suap 1234567
uv run python scripts/gerenciar.py criar-campus "Natal-Central" --sigla CNAT
uv run python scripts/gerenciar.py autorizar 1234567 "Currais Novos" gestor --nome "Maria"
uv run python scripts/gerenciar.py psicopedagoga ana.souza "Ana Souza" "Currais Novos" --senha "Troque123"
uv run python scripts/gerenciar.py listar
```

## Perguntas dos formulários

- **Psicopedagogia**: NEE identificadas, laudo, CID e profissionais, acompanhamentos externos, aspectos cognitivos, emocionais, de comunicação, sensoriais e motores, recomendações.
- **ETEP**: histórico, habilidades e interesses, dificuldades, apoios e recursos, família, estratégias recomendadas, observações.
- **Docente (por componente)**: objetivos, conteúdos, metodologias, recursos, avaliações (e adaptações), comportamento em sala, parecer e situação. Além das perguntas, o docente pode cadastrar **estudos individualizados** (dia, horário em hora fechada, frequência semanal/quinzenal/mensal e local/observação).
- **Gestão NAPNE**: registro do acompanhamento e parecer da equipe multiprofissional.

Em **Administração → Perguntas** dá para editar o texto, o tipo, as opções, a seção, a ordem, a obrigatoriedade, quem responde e o texto automático do “Nada a declarar”. Perguntas já respondidas não são apagadas, apenas desativadas.

## O documento DOCX

Feito para ser **copiado e colado no editor do SUAP**: sem imagens, cabeçalhos/rodapés de página ou caixas de texto, só parágrafos formatados e tabelas. Respostas “Nada a declarar” aparecem em itálico. **Os anexos não entram no documento.** A seção **Estudos individualizados** traz uma tabela (componente, docente, dia, horário, frequência e local/observação) com todos os horários cadastrados pelos docentes ou, se não houver nenhum, a frase “Este(a) estudante não tem nenhum estudo individualizado cadastrado pelos docentes neste período”. Cada componente aparece como **“código — disciplina”**, com os docentes. O DOCX aprovado fica guardado no banco. Veja o exemplo fictício em [`docs/exemplo_PEI_ficticio.docx`](docs/exemplo_PEI_ficticio.docx).

## Estrutura do projeto

```
autopei/
├── app.py                  # entrada: login (callback do SUAP), campus, menu por perfil
├── pyproject.toml, uv.lock # dependências (uv)
├── core/
│   ├── config.py  models.py  db.py  seed.py  perguntas_padrao.py  security.py
│   ├── suap.py             # OAuth do SUAP (authorize → token → /api/rh/eu/)
│   ├── auth.py             # regras de login e perfis por campus
│   ├── fluxo.py            # máquina de estados, distribuição paralela, correções, pré-preenchimento, anexos
│   └── docx_pei.py         # geração do DOCX
├── views/
│   ├── login.py  inicio.py  peis.py  disciplinas.py  semestres.py  acessos.py
│   ├── admin.py  perfil.py  pessoas.py  formulario.py  anexos.py  estudos.py  ui.py  nav.py
├── scripts/gerenciar.py    # administração por linha de comando
├── tests/test_fluxo.py
├── docs/                   # manual, fluxo (draw.io, PNG, Mermaid), exemplo de PEI
└── Dockerfile  docker-compose.yml  .env.example
```

## Testes

```bash
createdb autopei_teste      # banco separado: os testes apagam e recriam as tabelas
DATABASE_URL=postgresql+psycopg://autopei:autopei@localhost:5432/autopei_teste uv run pytest
```

Os testes verificam:
- a distribuição paralela pelos códigos de disciplina (inclusive uma disciplina com dois docentes);
- que um docente não preenche a disciplina de outro;
- a correção pontual na ETEP, que **não** volta aos docentes;
- a correção em cascata explícita e a correção de um único docente;
- que os anexos ficam fora do DOCX e que só as etapas de preenchimento anexam (laudos pela Psicopedagogia; a gestão não anexa);
- os estudos individualizados dos docentes (vários por semana, quinzenal, horas fechadas, sem duplicar horário) e a tabela ou o aviso no DOCX;
- o pré-preenchimento a partir do semestre anterior;
- as regras de login (psicopedagogia local, ETEP só com SUAP, qualquer pessoa do SUAP como docente).

## Segurança e LGPD

O PEI contém **dados sensíveis de saúde de estudantes**, em geral menores de idade, e os anexos podem incluir laudos.
- Use HTTPS.
- Restrinja o acesso ao servidor e ao banco e faça backup cifrado (`pg_dump`).
- Revise a cada semestre a lista de matrículas autorizadas.
- **Nunca** ligue `AUTOPEI_SUAP_FAKE=1` em produção.

## Limitações conhecidas

- O login SUAP segue o mesmo fluxo OAuth do IFKey. Ele deve ser validado com a aplicação cadastrada no SUAP do IFRN.
- A sessão do Streamlit não sobrevive a um F5. Com o SUAP isso é rápido: o botão leva ao SUAP, que devolve a pessoa já autenticada.
- Não há notificações por e-mail; as pendências aparecem ao entrar.
- Os estudos individualizados **não** são pré-preenchidos com o semestre anterior, porque os horários mudam a cada semestre.
