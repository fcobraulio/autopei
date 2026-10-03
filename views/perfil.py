"""Meu perfil: dados e troca de senha (contas locais)."""
from __future__ import annotations

import streamlit as st

from core import auth, db
from core.models import PERFIS, Usuario
from core.security import hash_senha, senha_forte, verificar_senha
from views import ui


def pagina() -> None:
    c = ui.ctx()
    s = db.s()
    u = s.get(Usuario, c.usuario_id)
    ui.cabecalho("Meu perfil")
    st.markdown(f"**{u.nome}** · `{u.username}`  \nAcesso: {'SUAP' if u.auth == 'suap' else 'conta local'}"
                + (" · Administrador(a)" if u.is_admin else ""))
    for a in auth.acessos(s, u.username):
        st.markdown(f"- {a.campus.nome}: {PERFIS[a.perfil]}")
    if c.docente:
        st.markdown("- Docente (via SUAP): PEIs das disciplinas associadas à sua matrícula")
    if u.suap_tipo:
        st.caption(f"Tipo de usuário no SUAP: {u.suap_tipo}")

    email = st.text_input("E-mail", u.email)
    if st.button("Salvar e-mail"):
        u.email = email.strip()
        s.commit()
        st.toast("Salvo.")

    if u.auth == "local":
        st.markdown("#### Trocar senha")
        with st.form("troca_senha", clear_on_submit=True):
            atual = st.text_input("Senha atual", type="password")
            nova = st.text_input("Nova senha", type="password")
            conf = st.text_input("Confirme a nova senha", type="password")
            if st.form_submit_button("Trocar senha", type="primary"):
                if not verificar_senha(atual, u.senha_hash):
                    st.error("Senha atual incorreta.")
                elif nova != conf:
                    st.error("As senhas não conferem.")
                elif erro := senha_forte(nova):
                    st.error(erro)
                else:
                    u.senha_hash = hash_senha(nova)
                    s.commit()
                    st.success("Senha alterada.")
    else:
        st.caption("Sua senha é a mesma do SUAP e deve ser alterada no próprio SUAP.")
