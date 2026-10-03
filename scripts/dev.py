"""Modo de desenvolvimento do AutoPEI: banco populado com dados fictícios, ou banco zerado.

    uv run python scripts/dev.py iniciar           # popula o banco de DESENVOLVIMENTO e abre o AutoPEI em modo dev
    uv run python scripts/dev.py iniciar --manter  # abre em modo dev sem repopular (mantém o que você fez)
    uv run python scripts/dev.py popular           # só (re)popula o banco de desenvolvimento
    uv run python scripts/dev.py zerar             # APAGA TUDO do banco principal (.env) e deixa pronto para começar
    uv run python scripts/dev.py zerar --dev       # o mesmo, no banco de desenvolvimento

Bancos:
* principal → DATABASE_URL (do .env), o banco "de verdade".
* desenvolvimento → AUTOPEI_DEV_DATABASE_URL ou, se não definido, o mesmo servidor de DATABASE_URL
  com o nome do banco + "_dev" (ex.: autopei_dev). É criado automaticamente se não existir.
  Assim, popular e testar nunca mexem nos dados reais.

Os dados vêm dos arquivos CSV da pasta dev/ (pessoas e senhas em dev/logins.csv) e as respostas
de scripts/dev_conteudo.py. TODOS OS DADOS SÃO FICTÍCIOS.
"""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DEV_DIR = RAIZ / "dev"
SAIDA = DEV_DIR / "saida"
URL_PADRAO = "postgresql+psycopg://autopei:autopei@localhost:5432/autopei"

sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from dotenv import load_dotenv

    load_dotenv(RAIZ / ".env")
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Bancos
# ---------------------------------------------------------------------------
def url_principal() -> str:
    return os.getenv("DATABASE_URL", URL_PADRAO)


def url_dev() -> str:
    if os.getenv("AUTOPEI_DEV_DATABASE_URL"):
        return os.environ["AUTOPEI_DEV_DATABASE_URL"]
    from sqlalchemy.engine import make_url

    u = make_url(url_principal())
    return u.set(database=f"{u.database or 'autopei'}_dev").render_as_string(hide_password=False)


def _mostrar(url: str) -> str:
    from sqlalchemy.engine import make_url

    return make_url(url).render_as_string(hide_password=True)


def garantir_banco(url: str) -> None:
    """Cria o banco se ainda não existir (precisa de permissão CREATEDB)."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    from sqlalchemy.exc import OperationalError

    u = make_url(url)
    admin = create_engine(u.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        con = admin.connect()
    except OperationalError as exc:
        sys.exit(f"Não consegui conectar ao PostgreSQL em {u.host}:{u.port or 5432} ({exc.orig}).\n"
                 "Ele está rodando? Com Docker:  docker compose up -d db")
    with con:
        if not con.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": u.database}):
            con.execute(text(f'CREATE DATABASE "{u.database}"'))
            print(f"Banco {u.database} criado.")
    admin.dispose()


def usar_banco(url: str, dev: bool) -> None:
    """Aponta o AutoPEI para o banco escolhido (antes de importar core.*)."""
    if "core.db" in sys.modules:
        raise RuntimeError("usar_banco() deve ser chamado antes de importar core.db")
    os.environ["DATABASE_URL"] = url
    if dev:
        os.environ["AUTOPEI_DEV"] = "1"
        os.environ["AUTOPEI_ADMIN_USERNAME"] = "admin"
        os.environ["AUTOPEI_ADMIN_PASSWORD"] = "admin"
        os.environ["AUTOPEI_ADMIN_NOME"] = "Administrador(a) AutoPEI"


def recriar_tabelas() -> None:
    """Apaga TODAS as tabelas do banco atual e cria tudo de novo (campus, perguntas e admin)."""
    from sqlalchemy import MetaData

    from core import db

    md = MetaData()
    md.reflect(db.engine)
    md.drop_all(db.engine)
    db.init_db()


def confirmar(msg: str, sim: bool) -> bool:
    if sim:
        return True
    print(msg)
    return input('Digite ZERAR para confirmar: ').strip().upper() == "ZERAR"


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------
def ler(nome: str) -> list[dict]:
    with open(DEV_DIR / nome, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def pdf_ficticio(titulo: str, linhas: list[str]) -> bytes:
    """PDF simples de uma página (para os anexos de exemplo)."""
    def esc(t: str) -> str:
        return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    texto = ["BT /F1 16 Tf 60 780 Td (" + esc(titulo) + ") Tj ET"]
    y = 750
    for linha in linhas:
        texto.append(f"BT /F1 11 Tf 60 {y} Td ({esc(linha)}) Tj ET")
        y -= 18
    stream = "\n".join(texto).encode("latin-1", "replace")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    out = bytearray(b"%PDF-1.4\n")
    pos = []
    for i, o in enumerate(objs, start=1):
        pos.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for p in pos:
        out += b"%010d 00000 n \n" % p
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


def popular() -> None:
    import dev_conteudo as C
    from sqlalchemy import func, select

    from core import fluxo
    from core.db import SessionLocal
    from core.docx_pei import gerar_docx, nome_arquivo
    from core.models import (
        Acesso,
        Campus,
        Componente,
        Estudante,
        EstudoIndividualizado,
        Historico,
        Pei,
        Usuario,
    )
    from core.security import hash_senha

    hoje = datetime.now().replace(second=0, microsecond=0)
    s = SessionLocal()
    campus = s.scalar(select(Campus))
    campus.cidade = "Currais Novos"

    # --- pessoas -----------------------------------------------------------------
    perfil_por_rotulo = {"Gestor(a) NAPNE": "gestor", "Auxiliar (bolsista)": "auxiliar",
                         "Psicopedagogia": "psicopedagogia", "ETEP": "etep"}
    tipo_suap = {"gestor": "Servidor (Técnico-Administrativo)", "auxiliar": "Aluno",
                 "etep": "Servidor (Técnico-Administrativo)"}
    u: dict[str, Usuario] = {}
    for p in ler("logins.csv"):
        login = p["login"].strip().lower()
        perfil = perfil_por_rotulo.get(p["perfil"])
        x = s.scalar(select(Usuario).where(Usuario.username == login))
        if x is None:
            x = Usuario(username=login)
            s.add(x)
        x.nome, x.ativo, x.senha_hash = p["nome"], True, hash_senha(p["senha"])
        x.email = f"{login}@ficticio.ifrn.edu.br"
        if login == "admin":
            x.auth, x.is_admin = "local", True
        elif perfil == "psicopedagogia":
            x.auth = "local"
        else:  # em produção estas pessoas entram pelo SUAP
            x.auth = "suap"
            x.suap_tipo = tipo_suap.get(perfil, "Servidor (Docente)")
            x.suap_campus = "CN"
        if perfil:
            s.add(Acesso(campus_id=campus.id, matricula=login, perfil=perfil, nome=p["nome"], ativo=True))
        u[login] = x
    s.flush()
    gestora = u["gestora"]
    psicos = [u[k] for k in ("psico1", "psico2", "psico3")]
    eteps = [u["etep1"], u["etep2"]]

    turmas = {t["turma"]: t for t in ler("turmas.csv")}
    disciplinas = ler("disciplinas.csv")
    disc_por_cod = {d["codigo"]: d for d in disciplinas}
    lista_ofertas = "\n".join(f"{d['codigo']}; {d['disciplina']}; {m}; {u[m.strip()].nome}"
                              for d in disciplinas for m in d["docentes"].split(","))
    estudos = ler("estudos_individualizados.csv")

    # --- helpers de preenchimento -----------------------------------------------------
    def responder(pei, etapa, quem, est_csv, comp=None):
        nome = est_csv["nome"].split()[0]
        for perg in fluxo.perguntas(s, etapa):
            if etapa == "docente":
                d = disc_por_cod[comp.codigo]
                v = C.valor_docente(est_csv["perfil_nee"], perg.enunciado, nome, d["disciplina"],
                                    d["objetivos"], d["conteudos"])
            elif etapa == "gestao":
                v = C.REGISTRO_GESTAO if perg.enunciado.startswith("Registro") else C.PARECER_GESTAO
            else:
                v = C.valor_psico_etep(est_csv["perfil_nee"], etapa, perg.enunciado, nome)
            nada = v is C.NADA
            if nada and perg.tipo != "longa":
                v = perg.opcoes[:1] if perg.tipo == "checkbox" else perg.opcoes[0]
                nada = False
            fluxo.salvar_resposta(s, pei, perg, comp.id if comp else None, "" if nada else v, nada, quem.id)
        s.flush()

    def docente_de(comp):
        return u[disc_por_cod[comp.codigo]["docentes"].split(",")[0].strip()]

    def cadastrar_estudos(pei, est_csv, comp):
        for e in estudos:
            if e["estudante"] == est_csv["nome"] and e["codigo"] == comp.codigo:
                fluxo.adicionar_estudo(s, pei, comp, docente_de(comp).id, e["dia"], int(e["hora_inicio"]),
                                       e["frequencia"], e["local"])

    def anexar_laudo(pei, est_csv, psico):
        if C.PERFIS[est_csv["perfil_nee"]]["psico"]["Situação da documentação"] != "Possui laudo":
            return
        laudo = C.PERFIS[est_csv["perfil_nee"]]["psico"]["Laudos, CID"]
        pdf = pdf_ficticio("LAUDO FICTICIO - USO EM DESENVOLVIMENTO",
                           [f"Paciente: {est_csv['nome']}", laudo[:90], laudo[90:180],
                            "Documento gerado automaticamente pelo AutoPEI (modo dev)."])
        fluxo.anexar(s, pei, "psicopedagogia", psico.id, f"laudo_{est_csv['matricula']}.pdf", "application/pdf",
                     pdf, "Laudo (fictício)")

    def ate(pei, est_csv, alvo: str, psico, etep):
        """Leva o PEI até a situação desejada usando as regras reais do fluxo."""
        if alvo == "psicopedagogia":
            return
        anexar_laudo(pei, est_csv, psico)
        responder(pei, "psicopedagogia", psico, est_csv)
        fluxo.enviar(s, pei, "psicopedagogia", psico)
        if alvo == "etep":
            return
        responder(pei, "etep", etep, est_csv)
        fluxo.enviar(s, pei, "etep", etep)
        n = int(alvo.split(":")[1]) if alvo.startswith("docente:") else len(pei.componentes)
        for i, comp in enumerate(pei.componentes):
            doc = docente_de(comp)
            if i < n:
                cadastrar_estudos(pei, est_csv, comp)
                responder(pei, "docente", doc, est_csv, comp)
                fluxo.enviar(s, pei, "docente", doc, comp)
            elif i == n:  # o próximo docente já começou: rascunho salvo
                cadastrar_estudos(pei, est_csv, comp)
                d = disc_por_cod[comp.codigo]
                perg = fluxo.perguntas(s, "docente")[0]
                fluxo.salvar_resposta(s, pei, perg, comp.id, d["objetivos"], False, doc.id)
        if alvo.startswith("docente:") or alvo == "revisao":
            return
        if alvo == "correcao_etep":
            fluxo.devolver(s, pei, gestora.id, "etep",
                           "Detalhar as estratégias pedagógicas para as aulas de laboratório "
                           "(uso do AASI com equipamentos ruidosos).")
            return
        responder(pei, "gestao", gestora, est_csv)
        fluxo.aprovar(s, pei, gestora.id)
        if alvo == "registrado":
            fluxo.registrar(s, pei, gestora.id, f"Documento SUAP nº {pei.id:03d}/2026 – NAPNE/CN")

    def estudante(e):
        t = turmas[e["turma"]]
        x = Estudante(campus_id=campus.id, nome=e["nome"], matricula=e["matricula"],
                      data_nascimento=date.fromisoformat(e["data_nascimento"]), curso=t["curso"],
                      nivel_forma=t["nivel_forma"], periodo=t["periodo"], turno=t["turno"],
                      nee=e["nee_resumo"], responsavel=e["responsavel"])
        s.add(x)
        s.flush()
        return x

    def codigos(turma):
        return [(d["codigo"], "") for d in disciplinas if d["turma"] == turma]

    alunos = ler("estudantes.csv")

    # --- 2026.1 (encerrado): PEIs registrados que servem de base para o pré-preenchimento ----
    s1 = fluxo.criar_semestre(s, campus.id, "2026.1")
    fluxo.importar_ofertas(s, s1.id, lista_ofertas)
    estudantes: dict[str, Estudante] = {}
    for i, e in enumerate(a for a in alunos if a["pei_2026_1"] == "sim"):
        estudantes[e["nome"]] = estudante(e)
        pei = fluxo.criar_pei(s, estudantes[e["nome"]], s1, gestora.id, codigos(e["turma"]))
        ate(pei, e, "registrado", psicos[i % 3], eteps[i % 2])
    fluxo.encerrar_semestre(s, s1, gestora.id)

    # --- 2026.2 (aberto) -----------------------------------------------------------------
    s2 = fluxo.criar_semestre(s, campus.id, "2026.2")
    fluxo.importar_ofertas(s, s2.id, lista_ofertas)
    for i, e in enumerate(alunos):
        est = estudantes.get(e["nome"]) or estudante(e)
        pei = fluxo.criar_pei(s, est, s2, u[e["cadastrado_por"]].id, codigos(e["turma"]))
        ate(pei, e, e["situacao_2026_2"], psicos[i % 3], eteps[i % 2])
    # um docente anexa um documento de apoio
    davi = s.scalar(select(Pei).join(Estudante).where(Estudante.nome == "Davi Lucena Araújo", Pei.semestre_id == s2.id))
    if davi:
        comp = davi.componentes[0]
        fluxo.anexar(s, davi, "docente", docente_de(comp).id, "prova_ampliada_exemplo.pdf", "application/pdf",
                     pdf_ficticio("PROVA AMPLIADA (EXEMPLO)", ["Fonte 24, alto contraste.", "Questao 1 ..."]),
                     "Modelo de prova ampliada", comp.id)
    s.flush()

    # --- datas plausíveis (o fluxo acima aconteceu "agora") ---------------------------------
    dias = {a["nome"]: int(a["dias_na_etapa"] or 1) for a in alunos}
    for pei in s.scalars(select(Pei)):
        hist = list(s.scalars(select(Historico).where(Historico.pei_id == pei.id).order_by(Historico.id)))
        if pei.semestre.codigo == "2026.1":
            inicio, fim = datetime(2026, 3, 2, 9, 0), datetime(2026, 7, 10, 16, 0)
        else:
            fim = hoje - timedelta(days=dias.get(pei.estudante.nome, 1))
            inicio = min(datetime(2026, 8, 17, 9, 0) + timedelta(days=pei.id % 7), fim)
        passo = (fim - inicio) / max(1, len(hist) - 1)
        for k, h in enumerate(hist):
            h.criado_em = inicio + passo * k
            if h.para_status == "aprovado":
                pei.aprovado_em = h.criado_em
            if h.para_status == "registrado":
                pei.registrado_em = h.criado_em
        pei.criado_em = inicio
        pei.atualizado_em = max((h.criado_em for h in hist if h.para_status), default=inicio)
        for comp in pei.componentes:
            if comp.concluido_em:
                comp.concluido_em = pei.atualizado_em
        for e in s.scalars(select(EstudoIndividualizado).where(EstudoIndividualizado.pei_id == pei.id)):
            e.criado_em = pei.atualizado_em
        if pei.docx:
            pei.docx = gerar_docx(s, pei)
            pei.docx_nome = nome_arquivo(pei)
    s1.encerrado_em = datetime(2026, 7, 31, 17, 0)
    for k, x in enumerate(u.values()):
        x.ultimo_login = hoje - timedelta(hours=3 * k)
    s.commit()

    # --- cópia dos DOCX prontos em dev/saida (fora do git) ---------------------------------
    SAIDA.mkdir(exist_ok=True)
    for velho in SAIDA.glob("*.docx"):
        velho.unlink()
    for pei in s.scalars(select(Pei).where(Pei.docx.is_not(None))):
        (SAIDA / (pei.docx_nome or nome_arquivo(pei))).write_bytes(pei.docx)

    # --- resumo ------------------------------------------------------------------------
    print("\nBanco de desenvolvimento populado:")
    from core.models import STATUS
    for sem in (s1, s2):
        print(f"  Semestre {sem.codigo} ({sem.status}):")
        for p in s.scalars(select(Pei).join(Estudante).where(Pei.semestre_id == sem.id).order_by(Estudante.nome)):
            extra = " · em correção" if p.em_correcao else ""
            if p.status == "docente":
                extra = f" · {sum(c.status == 'concluido' for c in p.componentes)}/{len(p.componentes)} docentes"
            print(f"    - {p.estudante.nome:<26} {STATUS[p.status]}{extra}")
    n_comp = s.scalar(select(func.count(Componente.id)))
    print(f"  {len(u)} pessoas · {len(disciplinas)} disciplinas · {len(turmas)} turmas · {n_comp} componentes")
    print(f"  DOCX prontos copiados para {SAIDA.relative_to(RAIZ)}/")
    print(f"  Logins e senhas: {(DEV_DIR / 'logins.csv').relative_to(RAIZ)} (senha de todos: autopei; admin: admin)")
    s.close()


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="Modo de desenvolvimento do AutoPEI",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("iniciar", help="popula o banco de desenvolvimento e abre o AutoPEI em modo dev")
    a.add_argument("--manter", action="store_true", help="não repopula: mantém os dados atuais do banco dev")
    a.add_argument("--porta", default="8501")
    sub.add_parser("popular", help="apaga e popula o banco de desenvolvimento com dados fictícios")
    a = sub.add_parser("zerar", help="APAGA TODOS OS DADOS e deixa o banco pronto para começar do zero")
    a.add_argument("--dev", action="store_true", help="zera o banco de desenvolvimento em vez do principal")
    a.add_argument("--sim", action="store_true", help="não pede confirmação")
    args = ap.parse_args()

    if args.cmd in ("popular", "iniciar"):
        url = url_dev()
        if url == url_principal() and not os.getenv("AUTOPEI_DEV_DATABASE_URL"):
            sys.exit("O banco de desenvolvimento não pode ser o mesmo do DATABASE_URL.")
        garantir_banco(url)
        if args.cmd == "popular" or not args.manter:
            print(f"Populando {_mostrar(url)} …")
            usar_banco(url, dev=True)
            recriar_tabelas()
            popular()
        if args.cmd == "iniciar":
            env = dict(os.environ, DATABASE_URL=url, AUTOPEI_DEV="1")
            print(f"\nAbrindo o AutoPEI em MODO DE DESENVOLVIMENTO em http://localhost:{args.porta}  (Ctrl+C para sair)")
            subprocess.run([sys.executable, "-m", "streamlit", "run", str(RAIZ / "app.py"),
                            "--server.port", str(args.porta)], env=env, cwd=RAIZ)

    elif args.cmd == "zerar":
        url = url_dev() if args.dev else url_principal()
        qual = "de DESENVOLVIMENTO" if args.dev else "PRINCIPAL"
        if not confirmar(f"Isto APAGA TODOS OS DADOS do banco {qual}: {_mostrar(url)}", args.sim):
            sys.exit("Nada foi apagado.")
        if args.dev:
            garantir_banco(url)
        usar_banco(url, dev=args.dev)
        recriar_tabelas()
        from core import config

        print(f"Banco {qual} zerado: tabelas recriadas com o campus {config.CAMPUS_INICIAL} e as perguntas padrão.")
        if args.dev:
            print("Administrador: admin / admin.")
        elif config.ADMIN_PASSWORD:
            print(f"Administrador local: {config.ADMIN_USERNAME} (senha de AUTOPEI_ADMIN_PASSWORD no .env).")
        else:
            print("Atenção: AUTOPEI_ADMIN_PASSWORD está vazio no .env, então nenhum administrador foi criado. "
                  "Crie um com:  uv run python scripts/gerenciar.py criar-admin --usuario admin --senha ...")


if __name__ == "__main__":
    main()
