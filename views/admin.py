"""Administração: campi, usuários, perguntas e informações do sistema."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import func, select

from core import config, db
from core.models import ETAPAS, TIPOS_PERGUNTA, Acesso, Campus, Pei, Pergunta, Resposta, Usuario
from core.security import hash_senha, senha_forte
from views import pessoas, ui


# ---------------------------------------------------------------------------
def _campi() -> None:
    s = db.s()
    campi = list(s.scalars(select(Campus).order_by(Campus.nome)))
    gestores = {cp.id: [a for a in s.scalars(select(Acesso).where(Acesso.campus_id == cp.id,
                                                                  Acesso.perfil == "gestor"))] for cp in campi}
    st.dataframe(pd.DataFrame([{"Campus": x.nome, "Sigla": x.sigla, "Cidade": x.cidade,
                                "Gestores": ", ".join(a.nome or a.matricula for a in gestores[x.id]) or "—",
                                "Ativo": "sim" if x.ativo else "não"} for x in campi]),
                 hide_index=True, use_container_width=True)
    with st.expander("➕ Novo campus"):
        with st.form("novo_campus", clear_on_submit=True):
            col1, col2, col3 = st.columns([3, 1, 2])
            nome = col1.text_input("Nome *", placeholder="ex.: Natal-Central")
            sigla = col2.text_input("Sigla", placeholder="CNAT")
            cidade = col3.text_input("Cidade")
            if st.form_submit_button("Incluir campus", type="primary"):
                if not nome.strip():
                    st.error("Informe o nome.")
                elif s.scalar(select(Campus.id).where(func.lower(Campus.nome) == nome.strip().lower())):
                    st.error("Já existe um campus com esse nome.")
                else:
                    s.add(Campus(nome=nome.strip(), sigla=sigla.strip().upper(),
                                 cidade=cidade.strip() or nome.strip(), ativo=True))
                    s.commit()
                    st.rerun()

    cp = ui.escolher("Campus", campi, lambda x: x.nome, key="adm_campus")
    if cp:
        with st.container(border=True):
            st.markdown(f"**Gestores de {cp.nome}** (entram pelo SUAP)")
            pessoas.autorizar_matricula(cp.id, ["gestor"], f"gest_{cp.id}")
            pessoas.lista_acessos(cp.id, ["gestor"], f"gest_{cp.id}")
        with st.expander(f"Editar dados de {cp.nome}"):
            nome = st.text_input("Nome", cp.nome, key=f"cn_{cp.id}")
            sigla = st.text_input("Sigla", cp.sigla, key=f"cs_{cp.id}")
            cidade = st.text_input("Cidade", cp.cidade, key=f"cc_{cp.id}")
            ativo = st.checkbox("Ativo", cp.ativo, key=f"ca_{cp.id}")
            if st.button("Salvar campus"):
                cp.nome, cp.sigla, cp.cidade, cp.ativo = nome.strip(), sigla.strip().upper(), cidade.strip(), ativo
                s.commit()
                st.rerun()


# ---------------------------------------------------------------------------
def _usuarios() -> None:
    s = db.s()
    st.caption("Pessoas que já entraram no AutoPEI e contas locais. Perfis por campus são dados em "
               "**Campi** (gestores) e pelo gestor em **Acessos** (auxiliares, ETEP e psicopedagogas).")
    busca = st.text_input("Buscar", placeholder="nome ou matrícula")
    q = select(Usuario).order_by(Usuario.nome)
    if busca:
        q = q.where(Usuario.nome.ilike(f"%{busca}%") | Usuario.username.ilike(f"%{busca}%"))
    usuarios = list(s.scalars(q))
    st.dataframe(pd.DataFrame([{
        "Nome": u.nome, "Matrícula/usuário": u.username, "Acesso": "SUAP" if u.auth == "suap" else "local",
        "Tipo no SUAP": u.suap_tipo, "Admin": "sim" if u.is_admin else "", "Ativo": "sim" if u.ativo else "não",
        "Último acesso": ui.data(u.ultimo_login, True)} for u in usuarios]), hide_index=True, use_container_width=True)
    u = ui.escolher("Editar", usuarios, lambda x: f"{x.nome} ({x.username})", index=None,
                    placeholder="Selecione…")
    if u:
        with st.container(border=True):
            ativo = st.checkbox("Ativo", u.ativo, key=f"u_at_{u.id}")
            adm = st.checkbox("Administrador(a) do sistema", u.is_admin, key=f"u_ad_{u.id}")
            if st.button("Salvar", key=f"u_sv_{u.id}"):
                if u.id == ui.ctx().usuario_id and (not ativo or not adm):
                    st.error("Você não pode remover o seu próprio acesso de administrador.")
                else:
                    u.ativo, u.is_admin = ativo, adm
                    s.commit()
                    st.rerun()
            if u.auth == "local":
                nova = st.text_input("Nova senha", type="password", key=f"u_pw_{u.id}")
                if st.button("Redefinir senha", key=f"u_pwb_{u.id}"):
                    if erro := senha_forte(nova):
                        st.error(erro)
                    else:
                        u.senha_hash = hash_senha(nova)
                        s.commit()
                        st.success("Senha redefinida.")
    with st.expander("➕ Novo administrador"):
        st.caption("Pela matrícula SUAP (recomendado) ou com uma conta local.")
        with st.form("novo_admin", clear_on_submit=True):
            col1, col2 = st.columns([1, 2])
            usuario = col1.text_input("Matrícula SUAP ou usuário *")
            nome = col2.text_input("Nome *")
            senha = st.text_input("Senha (só para conta local; deixe vazio para SUAP)", type="password")
            if st.form_submit_button("Salvar", type="primary"):
                usuario = usuario.strip().lower()
                if not usuario or not nome.strip():
                    st.error("Informe matrícula/usuário e nome.")
                elif senha and (erro := senha_forte(senha)):
                    st.error(erro)
                else:
                    x = s.scalar(select(Usuario).where(Usuario.username == usuario))
                    if x is None:
                        x = Usuario(username=usuario, nome=nome.strip(), ativo=True,
                                    auth="local" if senha else "suap")
                        s.add(x)
                    if senha:
                        x.auth, x.senha_hash = "local", hash_senha(senha)
                    x.is_admin = True
                    s.commit()
                    st.success(f"{nome} agora é administrador(a).")


# ---------------------------------------------------------------------------
def _form_pergunta(p: Pergunta | None, etapa: str, chave: str) -> None:
    s = db.s()
    novo = p is None
    p = p or Pergunta(etapa=etapa, secao="", enunciado="", tipo="longa", opcoes=[], obrigatoria=True,
                      texto_nada="", ajuda="", ordem=0, ativo=True)
    with st.form(chave):
        enunciado = st.text_area("Pergunta *", p.enunciado, height=70)
        col1, col2, col3 = st.columns([2, 2, 1])
        tipo = col1.selectbox("Tipo de resposta", list(TIPOS_PERGUNTA),
                              index=list(TIPOS_PERGUNTA).index(p.tipo), format_func=TIPOS_PERGUNTA.get)
        responsavel = col2.selectbox("Quem responde", list(ETAPAS), index=list(ETAPAS).index(p.etapa),
                                     format_func=ETAPAS.get)
        ordem = col3.number_input("Ordem", value=int(p.ordem or 0), step=10)
        secao = st.text_input("Seção (título do grupo no formulário e no DOCX)", p.secao)
        opcoes = st.text_area("Opções — uma por linha (escolha única, múltipla ou menu)",
                              "\n".join(p.opcoes or []), height=110)
        texto_nada = st.text_area("Texto automático do “Nada a declarar” (resposta longa)", p.texto_nada,
                                  height=70, help="Deixe em branco para não oferecer “Nada a declarar”.")
        ajuda = st.text_input("Orientação ao preencher (opcional)", p.ajuda)
        col1, col2 = st.columns(2)
        obrig = col1.checkbox("Obrigatória", p.obrigatoria)
        ativo = col2.checkbox("Ativa", p.ativo)
        if st.form_submit_button("Criar pergunta" if novo else "Salvar alterações", type="primary"):
            lista = [o.strip() for o in opcoes.splitlines() if o.strip()]
            if not enunciado.strip():
                st.error("Escreva a pergunta.")
                return
            if tipo != "longa" and len(lista) < 2:
                st.error("Informe pelo menos duas opções.")
                return
            if tipo == "longa" and not texto_nada.strip():
                texto_nada = "Nada a declarar."
            p.enunciado, p.tipo, p.etapa, p.ordem = enunciado.strip(), tipo, responsavel, int(ordem)
            p.secao = secao.strip() or "Informações"
            p.opcoes = lista if tipo != "longa" else []
            p.texto_nada = texto_nada.strip() if tipo == "longa" else ""
            p.ajuda, p.obrigatoria, p.ativo = ajuda.strip(), obrig, ativo
            if novo:
                if not p.ordem:
                    maior = s.scalar(select(func.max(Pergunta.ordem)).where(Pergunta.etapa == responsavel))
                    p.ordem = (maior or 0) + 10
                s.add(p)
            s.commit()
            st.rerun()


def _perguntas() -> None:
    s = db.s()
    st.caption("As perguntas valem para todos os campi. Tipos aceitos: resposta longa (com “Nada a "
               "declarar”), escolha única, múltipla escolha e menu de seleção. Perguntas já respondidas "
               "não são apagadas: ficam inativas para preservar os PEIs existentes.")
    etapa = st.segmented_control("Quem responde", list(ETAPAS), format_func=ETAPAS.get,
                                 default="psicopedagogia", key="adm_etapa") or "psicopedagogia"
    lista = list(s.scalars(select(Pergunta).where(Pergunta.etapa == etapa)
                           .order_by(Pergunta.ordem, Pergunta.id)))
    with st.expander("➕ Nova pergunta", expanded=False):
        _form_pergunta(None, etapa, f"nova_perg_{etapa}")

    secao = None
    for i, p in enumerate(lista):
        if p.secao != secao:
            secao = p.secao
            st.markdown(f"**{secao}**")
        estado = "" if p.ativo else " · :gray-badge[inativa]"
        obrig = " · obrigatória" if p.obrigatoria else ""
        with st.expander(f"{p.enunciado[:90]}"):
            st.markdown(f"{TIPOS_PERGUNTA[p.tipo]}{obrig}{estado}")
            col1, col2, col3 = st.columns(3)
            if col1.button("↑ Subir", key=f"up_{p.id}", disabled=i == 0, use_container_width=True):
                a = lista[i - 1]
                a.ordem, p.ordem = p.ordem, a.ordem
                if a.ordem == p.ordem:
                    p.ordem -= 1
                s.commit()
                st.rerun()
            if col2.button("↓ Descer", key=f"down_{p.id}", disabled=i == len(lista) - 1,
                           use_container_width=True):
                b = lista[i + 1]
                b.ordem, p.ordem = p.ordem, b.ordem
                if b.ordem == p.ordem:
                    p.ordem += 1
                s.commit()
                st.rerun()
            if col3.button("Excluir", key=f"del_{p.id}", use_container_width=True):
                usada = s.scalar(select(func.count(Resposta.id)).where(Resposta.pergunta_id == p.id))
                if usada:
                    p.ativo = False
                    st.session_state["msg_adm"] = "A pergunta já tinha respostas e foi apenas desativada."
                else:
                    s.delete(p)
                s.commit()
                st.rerun()
            _form_pergunta(p, etapa, f"perg_{p.id}")


# ---------------------------------------------------------------------------
def _sistema() -> None:
    s = db.s()
    col = st.columns(4)
    col[0].metric("Campi", s.scalar(select(func.count(Campus.id))))
    col[1].metric("Usuários", s.scalar(select(func.count(Usuario.id))))
    col[2].metric("PEIs", s.scalar(select(func.count(Pei.id))))
    col[3].metric("Perguntas ativas", s.scalar(select(func.count(Pergunta.id)).where(Pergunta.ativo)))
    st.markdown(f"""
- **SUAP:** `{config.SUAP_URL}` · login OAuth (redirecionamento) · client_id {"configurado" if config.SUAP_CLIENT_ID else "**não configurado**"} · retorno em `{config.SUAP_REDIRECT_URI}`
- **Banco:** `{db.engine.url.render_as_string(hide_password=True)}`
- **Modo de desenvolvimento (AUTOPEI_DEV):** {"**ATIVADO – todos entram com usuário e senha. Não use em produção!**" if config.DEV else "desativado"}
- **Simulador do SUAP (AUTOPEI_SUAP_FAKE):** {"**ATIVADO – não use em produção!**" if config.SUAP_FAKE else "desativado"}
""")
    st.caption("Tarefas por código: `python scripts/gerenciar.py --help` (criar admin, campus, etc.).")


def pagina() -> None:
    ui.cabecalho("Administração", "Configurações gerais do AutoPEI")
    if msg := st.session_state.pop("msg_adm", None):
        st.info(msg)
    abas = st.tabs(["Campi e gestores", "Perguntas", "Usuários e administradores", "Sistema"])
    with abas[0]:
        _campi()
    with abas[1]:
        _perguntas()
    with abas[2]:
        _usuarios()
    with abas[3]:
        _sistema()
