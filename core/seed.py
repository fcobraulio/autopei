"""Dados iniciais: campus Currais Novos, perguntas padrão e administrador local."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .models import Campus, Pergunta, Usuario
from .perguntas_padrao import PERGUNTAS
from .security import hash_senha


def seed(s: Session) -> None:
    if not s.scalar(select(Campus.id).limit(1)):
        s.add(Campus(nome=config.CAMPUS_INICIAL, sigla=config.CAMPUS_INICIAL_SIGLA,
                     cidade=config.CAMPUS_INICIAL))

    if not s.scalar(select(Pergunta.id).limit(1)):
        ordem: dict[str, int] = {}
        for p in PERGUNTAS:
            ordem[p["etapa"]] = ordem.get(p["etapa"], 0) + 10
            s.add(Pergunta(
                etapa=p["etapa"], secao=p.get("secao", ""), ordem=ordem[p["etapa"]],
                enunciado=p["enunciado"], ajuda=p.get("ajuda", ""), tipo=p["tipo"],
                opcoes=p.get("opcoes", []), obrigatoria=p.get("obrigatoria", True),
                texto_nada=p.get("texto_nada", ""),
            ))

    if config.ADMIN_PASSWORD:
        username = config.ADMIN_USERNAME.lower()
        if not s.scalar(select(Usuario.id).where(Usuario.username == username)):
            s.add(Usuario(nome=config.ADMIN_NOME, username=username, auth="local",
                          senha_hash=hash_senha(config.ADMIN_PASSWORD), is_admin=True))
