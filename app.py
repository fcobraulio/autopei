"""AutoPEI — Plano Educacional Individualizado (NAPNE / IFRN).

Execute com:  uv run streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from core import config, db
from core.auth import campi_do_usuario, montar_contexto
from core.models import PERFIS, Usuario
from views import acessos, admin, disciplinas, inicio, login, nav, peis, perfil, semestres

st.set_page_config(page_title="AutoPEI", page_icon=str(config.ASSETS_DIR / "icone.svg"),
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
  .block-container {padding-top: 2rem; max-width: 1100px;}
  [data-testid="stMetricValue"] {font-size: 1.8rem;}
</style>
""", unsafe_allow_html=True)

if config.DEV:
    st.markdown("""<div style="position:fixed;top:0;left:0;right:0;z-index:999999;background:#B45309;
        color:#fff;text-align:center;font-size:.8rem;font-weight:600;padding:2px 0;letter-spacing:.03em">
        MODO DE DESENVOLVIMENTO — login sem SUAP liberado para todos os perfis</div>""",
                unsafe_allow_html=True)

db.init_db()
sessao = db.SessionLocal()
db.set_current(sessao)

try:
    st.logo(str(config.ASSETS_DIR / "logo.svg"), size="large",
            icon_image=str(config.ASSETS_DIR / "icone.svg"))

    if "uid" not in st.session_state:
        login.callback_oauth()  # retorno do SUAP (?code=...)

    contexto = None
    if "uid" in st.session_state:
        contexto = montar_contexto(sessao, st.session_state["uid"], st.session_state.get("via", "local"),
                                   st.session_state.get("campus_id"))
        if contexto is None:  # usuário removido ou desativado
            st.session_state.clear()

    if contexto is None:
        st.navigation([st.Page(login.pagina, title="Entrar", icon=":material/login:")],
                      position="hidden").run()
        st.stop()

    usuario = sessao.get(Usuario, contexto.usuario_id)

    with st.sidebar:
        campi = campi_do_usuario(sessao, usuario, contexto.via)
        if len(campi) > 1:
            ids = [cp.id for cp in campi]
            escolhido = st.selectbox("Campus", campi, index=ids.index(contexto.campus_id),
                                     format_func=lambda cp: cp.nome)
            if escolhido.id != contexto.campus_id:
                st.session_state["campus_id"] = escolhido.id
                for k in ("pei_sel", "abrir", "peis_modo"):
                    st.session_state.pop(k, None)
                st.rerun()
        elif campi:
            st.caption(f"Campus {campi[0].nome}")
        st.session_state["campus_id"] = contexto.campus_id
        st.session_state["ctx"] = contexto

    nav.PAGINAS["inicio"] = st.Page(inicio.pagina, title="Início", icon=":material/home:",
                                    url_path="inicio", default=True)
    paginas: dict[str, list] = {"": [nav.PAGINAS["inicio"]]}
    if contexto.campus_id and contexto.gestao:
        nav.PAGINAS["peis"] = st.Page(peis.pagina, title="PEIs", icon=":material/description:", url_path="peis")
        paginas["NAPNE"] = [
            nav.PAGINAS["peis"],
            st.Page(disciplinas.pagina, title="Disciplinas e docentes", icon=":material/school:",
                    url_path="disciplinas"),
            st.Page(semestres.pagina, title="Semestres", icon=":material/calendar_month:", url_path="semestres"),
        ]
        if contexto.critico:
            paginas["NAPNE"].append(st.Page(acessos.pagina, title="Acessos", icon=":material/group:",
                                            url_path="acessos"))
    if contexto.is_admin:
        paginas["Sistema"] = [st.Page(admin.pagina, title="Administração", icon=":material/settings:",
                                      url_path="admin")]
    paginas["Conta"] = [st.Page(perfil.pagina, title="Meu perfil", icon=":material/person:", url_path="perfil")]

    pg = st.navigation(paginas)

    with st.sidebar:
        st.divider()
        papeis = sorted(PERFIS[p] for p in contexto.perfis)
        if contexto.docente:
            papeis.append("Docente")
        if contexto.is_admin:
            papeis.insert(0, "Administrador(a)")
        via = "SUAP" if contexto.via == "suap" else "login local"
        if config.DEV:
            via += " (modo de desenvolvimento)"
        st.markdown(f"**{contexto.nome}**  \n<small>{' · '.join(papeis) or 'sem perfil'}<br>"
                    f"entrou via {via}</small>", unsafe_allow_html=True)
        if st.button("Sair", icon=":material/logout:", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    pg.run()
finally:
    sessao.close()
    db.set_current(None)
