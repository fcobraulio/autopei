"""Tela de entrada: um botão "Entrar com SUAP" (redireciona ao SUAP e volta) e,
discretamente, o acesso com usuário e senha (psicopedagogia e administradores)."""
from __future__ import annotations

import html

import streamlit as st

from core import config, db, suap
from core.auth import LoginError, login_local, login_suap
from views import ui


def entrar(usuario_id: int, via: str) -> None:
    st.session_state.clear()
    st.session_state["uid"] = usuario_id
    st.session_state["via"] = via
    st.rerun()


def callback_oauth() -> None:
    """Retorno do SUAP: ?code=...&state=... → troca pelo token e entra."""
    params = st.query_params
    if "code" not in params and "error" not in params:
        return
    code, state = params.get("code", ""), params.get("state", "")
    erro_suap = params.get("error", "")
    st.query_params.clear()
    if erro_suap:
        st.session_state["erro_login"] = "O acesso pelo SUAP foi cancelado."
        return
    if not suap.state_valido(state):
        st.session_state["erro_login"] = "A tentativa de login expirou. Clique em “Entrar com SUAP” novamente."
        return
    s = db.s()
    try:
        u = login_suap(s, suap.trocar_codigo(code))
        s.commit()
    except (suap.SuapError, LoginError) as exc:
        s.rollback()
        st.session_state["erro_login"] = str(exc)
        return
    entrar(u.id, "suap")


def _botao_suap() -> None:
    url = html.escape(suap.url_autorizacao(), quote=True)
    st.markdown(
        f"""<a href="{url}" target="_self" class="botao-suap">Entrar com SUAP</a>""",
        unsafe_allow_html=True,
    )


def _simulador_suap() -> None:
    """Somente com AUTOPEI_SUAP_FAKE=1: simula o retorno do SUAP para testes locais."""
    with st.expander("Simular login SUAP (modo de desenvolvimento)"):
        st.caption("Substitui a página do SUAP. Nunca ative em produção.")
        mat = st.text_input("Matrícula SUAP", key="fake_mat")
        nome = st.text_input("Nome", key="fake_nome")
        tipo = st.selectbox("Tipo de usuário", ["Servidor (Docente)", "Servidor (Técnico-Administrativo)",
                                                "Prestador de Serviço"], key="fake_tipo")
        if st.button("Simular retorno do SUAP", key="fake_btn") and mat.strip():
            st.query_params.update({"code": f"fake:{mat.strip()}:{tipo}:{nome.strip()}",
                                    "state": suap.gerar_state()})
            st.rerun()


def pagina() -> None:
    st.markdown("""
    <style>
      .botao-suap {display:block; text-align:center; background:#1c1c1c; color:#fff !important;
                   font-weight:700; font-size:1.15rem; padding:.8rem 1rem; border-radius:6px;
                   text-decoration:none !important; margin: 1.2rem 0 .6rem 0;}
      .botao-suap:hover {background:#2E7D32;}
    </style>""", unsafe_allow_html=True)

    _, centro, _ = st.columns([1, 1.2, 1])
    with centro:
        st.write("")
        st.write("")
        st.markdown(f"<div style='text-align:center'>{ui.logo_svg(210)}</div>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#5f6b66;margin-top:.3rem'>"
                    "Plano Educacional Individualizado · NAPNE / IFRN</p>", unsafe_allow_html=True)
        if erro := st.session_state.pop("erro_login", None):
            st.error(erro)

        if suap.configurado():
            if config.SUAP_CLIENT_ID:
                _botao_suap()
            if config.SUAP_FAKE:
                _simulador_suap()
        else:
            st.warning("O login pelo SUAP ainda não foi configurado (SUAP_CLIENT_ID e "
                       "SUAP_CLIENT_SECRET no arquivo .env).")

        mostrar = st.session_state.get("mostrar_local", False)
        _, meio, _ = st.columns([1, 3, 1])
        if meio.button("Deseja entrar com login e senha?", type="tertiary", use_container_width=True):
            st.session_state["mostrar_local"] = not mostrar
            st.rerun()
        if mostrar:
            with st.form("login_local"):
                st.caption("Exclusivo para a Psicopedagogia e administradores.")
                usuario = st.text_input("Usuário")
                senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", use_container_width=True):
                    s = db.s()
                    try:
                        u = login_local(s, usuario, senha)
                        s.commit()
                    except LoginError as exc:
                        s.rollback()
                        st.error(str(exc))
                    else:
                        entrar(u.id, "local")
