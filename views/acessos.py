"""Acessos do campus (gestor): lista de matrículas autorizadas e contas da Psicopedagogia."""
from __future__ import annotations

import streamlit as st

from views import pessoas, ui


def pagina() -> None:
    c = ui.ctx()
    ui.cabecalho("Acessos", f"Quem pode usar o AutoPEI no campus {c.campus_nome}")
    aba1, aba2, aba3 = st.tabs(["Auxiliares e ETEP (SUAP)", "Psicopedagogia (conta local)", "Gestores e docentes"])
    with aba1:
        st.caption("Auxiliares e ETEP entram **somente pelo SUAP**. Inclua a matrícula SUAP de cada pessoa: "
                   "só quem estiver nesta lista recebe o perfil.")
        pessoas.autorizar_matricula(c.campus_id, ["auxiliar", "etep"], "aux_etep")
        pessoas.lista_acessos(c.campus_id, ["auxiliar", "etep"], "aux_etep")
    with aba2:
        st.caption("A Psicopedagogia entra com **usuário e senha** criados aqui e pode trocar a senha depois.")
        pessoas.psicopedagogas(c.campus_id)
    with aba3:
        st.markdown("**Gestores** — cadastrados pelo administrador do sistema.")
        if c.is_admin:
            pessoas.lista_acessos(c.campus_id, ["gestor"], "gestores_adm")
        else:
            _gestores_ro(c.campus_id)
        st.markdown("**Docentes** — não precisam de cadastro: qualquer pessoa que entra pelo SUAP pode ser "
                    "docente. Os PEIs chegam a cada um pela associação feita em **Disciplinas e docentes**.")


def _gestores_ro(campus_id: int) -> None:
    from sqlalchemy import select

    from core import db
    from core.models import Acesso

    for a in db.s().scalars(select(Acesso).where(Acesso.campus_id == campus_id, Acesso.perfil == "gestor")):
        st.markdown(f"- {a.nome or a.matricula} (`{a.matricula}`){'' if a.ativo else ' — desativado'}")
