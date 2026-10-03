"""Conexão com o PostgreSQL e sessão do banco por execução do Streamlit."""
from __future__ import annotations

import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from . import config
from .models import Base

engine = create_engine(config.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

_local = threading.local()
_inicializado = False


def set_current(sessao: Session | None) -> None:
    _local.sessao = sessao


def s() -> Session:
    """Sessão do banco da execução atual da página."""
    sessao = getattr(_local, "sessao", None)
    if sessao is None:
        sessao = SessionLocal()
        _local.sessao = sessao
    return sessao


def init_db() -> None:
    """Cria as tabelas (se não existirem) e popula os dados iniciais. Idempotente."""
    global _inicializado
    if _inicializado:
        return
    from .seed import seed

    Base.metadata.create_all(engine)
    with SessionLocal() as sessao:
        seed(sessao)
        sessao.commit()
    _inicializado = True
