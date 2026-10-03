"""Tarefas administrativas por linha de comando.

Exemplos:
    python scripts/gerenciar.py init
    python scripts/gerenciar.py criar-admin --usuario admin --nome "Fulano" --senha "Troque123"
    python scripts/gerenciar.py admin-suap 1234567          # dá perfil de admin a uma matrícula SUAP
    python scripts/gerenciar.py criar-campus "Natal-Central" --sigla CNAT
    python scripts/gerenciar.py autorizar 1234567 "Currais Novos" gestor   # gestor/auxiliar/etep por matrícula SUAP
    python scripts/gerenciar.py psicopedagoga ana.souza "Ana Souza" "Currais Novos" --senha "Troque123"
    python scripts/gerenciar.py listar
    python scripts/gerenciar.py restaurar-perguntas          # recria as perguntas padrão (apaga as atuais!)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select  # noqa: E402

from core.db import SessionLocal, init_db  # noqa: E402
from core.models import PERFIS, Acesso, Campus, Pergunta, Resposta, Usuario  # noqa: E402
from core.security import hash_senha, senha_forte  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Gerenciamento do AutoPEI")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="cria as tabelas e os dados iniciais")
    a = sub.add_parser("criar-admin", help="cria (ou redefine) um administrador local")
    a.add_argument("--usuario", required=True)
    a.add_argument("--nome", default="Administrador(a)")
    a.add_argument("--senha", required=True)
    a = sub.add_parser("admin-suap", help="marca uma matrícula SUAP como administradora")
    a.add_argument("matricula")
    a.add_argument("--nome", default="")
    a = sub.add_parser("criar-campus")
    a.add_argument("nome")
    a.add_argument("--sigla", default="")
    a.add_argument("--cidade", default="")
    a = sub.add_parser("autorizar", help="autoriza uma matrícula SUAP como gestor, auxiliar ou etep em um campus")
    a.add_argument("matricula")
    a.add_argument("campus")
    a.add_argument("perfil", choices=["gestor", "auxiliar", "etep"])
    a.add_argument("--nome", default="")
    a = sub.add_parser("psicopedagoga", help="cria a conta local de uma psicopedagoga")
    a.add_argument("usuario")
    a.add_argument("nome")
    a.add_argument("campus")
    a.add_argument("--senha", required=True)
    sub.add_parser("listar", help="lista campi e usuários")
    sub.add_parser("restaurar-perguntas", help="APAGA perguntas e respostas e recria as perguntas padrão")
    args = ap.parse_args()

    init_db()
    with SessionLocal() as s:
        if args.cmd == "init":
            print("Banco inicializado.")
        elif args.cmd == "criar-admin":
            if erro := senha_forte(args.senha):
                sys.exit(erro)
            u = s.scalar(select(Usuario).where(Usuario.username == args.usuario.lower()))
            if u is None:
                u = Usuario(username=args.usuario.lower(), nome=args.nome, ativo=True)
                s.add(u)
            u.auth, u.senha_hash, u.is_admin, u.ativo = "local", hash_senha(args.senha), True, True
            print(f"Administrador local '{u.username}' pronto.")
        elif args.cmd == "admin-suap":
            m = args.matricula.lower()
            u = s.scalar(select(Usuario).where(Usuario.username == m))
            if u is None:
                u = Usuario(username=m, nome=args.nome or f"Usuário SUAP {m}", auth="suap", ativo=True)
                s.add(u)
            u.is_admin, u.ativo = True, True
            print(f"Matrícula {m} agora é administradora (entra pelo SUAP).")
        elif args.cmd == "criar-campus":
            s.add(Campus(nome=args.nome, sigla=args.sigla.upper(), cidade=args.cidade or args.nome, ativo=True))
            print("Campus criado.")
        elif args.cmd == "autorizar":
            c = s.scalar(select(Campus).where(Campus.nome == args.campus))
            if not c:
                sys.exit("Campus não encontrado.")
            s.add(Acesso(campus_id=c.id, matricula=args.matricula.lower(), perfil=args.perfil,
                         nome=args.nome, ativo=True))
            print(f"Matrícula {args.matricula} autorizada como {PERFIS[args.perfil]} em {c.nome}.")
        elif args.cmd == "psicopedagoga":
            c = s.scalar(select(Campus).where(Campus.nome == args.campus))
            if not c:
                sys.exit("Campus não encontrado.")
            if erro := senha_forte(args.senha):
                sys.exit(erro)
            un = args.usuario.lower()
            if not s.scalar(select(Usuario).where(Usuario.username == un)):
                s.add(Usuario(username=un, nome=args.nome, auth="local", senha_hash=hash_senha(args.senha),
                              ativo=True, is_admin=False))
            s.add(Acesso(campus_id=c.id, matricula=un, perfil="psicopedagogia", nome=args.nome, ativo=True))
            print(f"Conta local '{un}' criada como Psicopedagogia em {c.nome}.")
        elif args.cmd == "listar":
            for c in s.scalars(select(Campus)):
                print(f"[campus] {c.id} {c.nome} ({c.sigla}) {'ativo' if c.ativo else 'inativo'}")
            for a in s.scalars(select(Acesso).order_by(Acesso.campus_id, Acesso.perfil)):
                print(f"[acesso]  {a.matricula:15} {a.perfil:15} {a.campus.nome} {'' if a.ativo else '(desativado)'}")
            for u in s.scalars(select(Usuario).order_by(Usuario.nome)):
                print(f"[usuário] {u.username:15} {u.nome:35} {u.auth:5} {'ADMIN ' if u.is_admin else ''}{u.suap_tipo}")
        elif args.cmd == "restaurar-perguntas":
            if input("Isto apaga TODAS as perguntas e respostas. Digite SIM: ") != "SIM":
                sys.exit("Cancelado.")
            s.execute(delete(Resposta))
            s.execute(delete(Pergunta))
            s.flush()
            from core.seed import seed

            seed(s)
            print("Perguntas padrão restauradas.")
        s.commit()


if __name__ == "__main__":
    main()
