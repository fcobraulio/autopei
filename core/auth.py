"""Login (SUAP ou conta local), contexto da sessão e permissões.

Regras de acesso:
* Gestor(a), auxiliar, ETEP e docente entram **somente pelo SUAP**.
* Gestor(a): cadastrado(a) pelo administrador (matrícula SUAP) em um campus.
* Auxiliar e ETEP: matrícula precisa estar na lista de autorizados do gestor.
* Docente: qualquer pessoa que entra pelo SUAP; vê os PEIs das disciplinas que leciona.
* Psicopedagogia: conta local (usuário e senha) criada pelo gestor.
* Administrador: conta local inicial ou matrícula SUAP marcada como administradora.

Modo de desenvolvimento (AUTOPEI_DEV=1): qualquer pessoa com senha cadastrada entra com
usuário e senha e recebe todos os seus perfis, como se tivesse entrado pelo SUAP.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .models import PERFIS_SUAP, Acesso, Campus, Usuario
from .security import verificar_senha
from .suap import DadosSuap


class LoginError(Exception):
    pass


def acessos(s: Session, username: str, campus_id: int | None = None) -> list[Acesso]:
    q = select(Acesso).join(Campus).where(Acesso.matricula == username, Acesso.ativo, Campus.ativo)
    if campus_id is not None:
        q = q.where(Acesso.campus_id == campus_id)
    return list(s.scalars(q))


def via_completa(via: str) -> bool:
    """True quando a sessão vale como login SUAP (todos os perfis valem)."""
    return via == "suap" or config.DEV


def login_local(s: Session, username: str, senha: str) -> Usuario:
    u = s.scalar(select(Usuario).where(Usuario.username == username.strip().lower()))
    conta_ok = u is not None and (u.auth == "local" or (config.DEV and u.senha_hash))
    if not u or not u.ativo or not conta_ok or not verificar_senha(senha, u.senha_hash):
        raise LoginError("Usuário ou senha inválidos.")
    perfis = {a.perfil for a in acessos(s, u.username)}
    if not config.DEV and not u.is_admin and "psicopedagogia" not in perfis:
        raise LoginError("O login com usuário e senha é exclusivo da Psicopedagogia e de "
                         "administradores. Use o botão “Entrar com SUAP”.")
    u.ultimo_login = datetime.now()
    return u


def login_suap(s: Session, dados: DadosSuap) -> Usuario:
    u = s.scalar(select(Usuario).where(Usuario.username == dados.username))
    if u is None:
        u = Usuario(nome=dados.nome, username=dados.username, email=dados.email, auth="suap",
                    ativo=True, is_admin=False)
        s.add(u)
    if not u.ativo:
        raise LoginError("Seu acesso ao AutoPEI está desativado. Procure o NAPNE do seu campus.")
    if u.auth == "local" and not config.DEV:
        raise LoginError("Esta matrícula pertence a uma conta local. Use “Deseja entrar com login e senha?”.")
    u.nome = dados.nome or u.nome
    u.email = dados.email or u.email
    u.suap_tipo = dados.tipo[:80]
    u.suap_campus = dados.campus[:80]
    if dados.username in config.ADMINS_SUAP:
        u.is_admin = True
    u.ultimo_login = datetime.now()
    s.flush()
    return u


# ---------------------------------------------------------------------------
@dataclass
class Contexto:
    usuario_id: int
    username: str
    nome: str
    is_admin: bool
    via: str  # "suap" | "local"
    campus_id: int | None
    campus_nome: str
    perfis: set[str] = field(default_factory=set)  # perfis no campus atual

    def tem(self, *perfis: str) -> bool:
        return bool(self.perfis.intersection(perfis))

    @property
    def docente(self) -> bool:
        return via_completa(self.via)

    @property
    def gestao(self) -> bool:  # painel, cadastro de PEI, disciplinas, devolver para correção
        return self.is_admin or self.tem("gestor", "auxiliar")

    @property
    def critico(self) -> bool:  # aprovar, registrar, cancelar, semestres, acessos
        return self.is_admin or self.tem("gestor")


def campi_do_usuario(s: Session, u: Usuario, via: str) -> list[Campus]:
    if u.is_admin:
        return list(s.scalars(select(Campus).where(Campus.ativo).order_by(Campus.nome)))
    ids = {a.campus_id for a in acessos(s, u.username) if via_completa(via) or a.perfil not in PERFIS_SUAP}
    if not ids:
        return []
    return list(s.scalars(select(Campus).where(Campus.id.in_(ids)).order_by(Campus.nome)))


def montar_contexto(s: Session, usuario_id: int, via: str, campus_id: int | None) -> Contexto | None:
    u = s.get(Usuario, usuario_id)
    if not u or not u.ativo:
        return None
    campi = campi_do_usuario(s, u, via)
    if campus_id not in {c.id for c in campi}:
        campus_id = campi[0].id if campi else None
    campus = s.get(Campus, campus_id) if campus_id else None
    perfis = set()
    if campus_id:
        perfis = {a.perfil for a in acessos(s, u.username, campus_id)}
        if not via_completa(via):  # gestor, auxiliar e ETEP só valem com login SUAP
            perfis -= PERFIS_SUAP
    return Contexto(u.id, u.username, u.nome, u.is_admin, via, campus_id,
                    campus.nome if campus else "", perfis)
