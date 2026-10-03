"""Equipe do campus (gestor): pessoas, perfis e liberação de acesso."""
from __future__ import annotations

import streamlit as st
from sqlalchemy import select

from core import db
from core.models import Usuario, Vinculo
from views import pessoas, ui


def pagina() -> None:
    c = ui.ctx()
    s = db.s()
    ui.cabecalho("Equipe", f"Pessoas com acesso ao AutoPEI no campus {c.campus_nome}")

    membros = list(s.scalars(select(Usuario).join(Vinculo).where(Vinculo.campus_id == c.campus_id)
                             .distinct().order_by(Usuario.nome)))
    sem_perfil = list(s.scalars(select(Usuario).where(~Usuario.vinculos.any(), ~Usuario.is_admin)
                                .order_by(Usuario.criado_em.desc())))

    aba1, aba2, aba3 = st.tabs([f"Equipe ({len(membros)})", "Adicionar pessoa",
                                f"Aguardando liberação ({len(sem_perfil)})"])
    with aba1:
        if not membros:
            st.info("Ninguém cadastrado ainda.")
        else:
            st.dataframe(pessoas.tabela_pessoas(membros, c.campus_id), hide_index=True,
                         use_container_width=True)
            u = st.selectbox("Editar pessoa", membros, index=None, placeholder="Selecione…",
                             format_func=lambda x: f"{x.nome} ({x.username})")
            if u:
                with st.container(border=True):
                    pessoas.editar_pessoa(u, c.campus_id, f"eq_{u.id}_")
    with aba2:
        st.caption("Docentes: informe a matrícula SUAP. Eles entram com o login do SUAP e já "
                   "encontram suas pendências. Psicopedagogia, ETEP e auxiliares podem usar SUAP "
                   "ou conta local.")
        pessoas.form_nova_pessoa(c.campus_id, "eq_")
    with aba3:
        st.caption("Pessoas que entraram pelo SUAP mas ainda não têm perfil em nenhum campus.")
        if not sem_perfil:
            st.success("Nenhuma pessoa aguardando.")
        for u in sem_perfil:
            with st.container(border=True):
                st.markdown(f"**{u.nome}** · `{u.username}` · campus SUAP: {u.suap_campus or '—'} · "
                            f"primeiro acesso em {ui.data(u.criado_em, True)}")
                pessoas.editar_pessoa(u, c.campus_id, f"lib_{u.id}_")
