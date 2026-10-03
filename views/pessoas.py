"""Componentes de cadastro de acessos, usados em Acessos (gestor) e Administração."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import select

from core import db
from core.models import PERFIS, Acesso, Usuario
from core.security import hash_senha, senha_forte
from views import ui


def autorizar_matricula(campus_id: int, perfis: list[str], chave: str) -> None:
    """Formulário para incluir matrículas SUAP na lista de autorizados."""
    s = db.s()
    with st.form(f"autorizar_{chave}", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 3, 2])
        matricula = col1.text_input("Matrícula SUAP *")
        nome = col2.text_input("Nome (opcional)")
        perfil = col3.selectbox("Perfil", perfis, format_func=PERFIS.get) if len(perfis) > 1 else perfis[0]
        if st.form_submit_button("Autorizar", type="primary"):
            matricula = matricula.strip().lower()
            if not matricula:
                st.error("Informe a matrícula.")
                return
            a = s.scalar(select(Acesso).where(Acesso.campus_id == campus_id, Acesso.matricula == matricula,
                                              Acesso.perfil == perfil))
            if a is None:
                s.add(Acesso(campus_id=campus_id, matricula=matricula, perfil=perfil, nome=nome.strip(),
                             ativo=True, criado_por_id=ui.ctx().usuario_id))
            else:
                a.ativo = True
                a.nome = nome.strip() or a.nome
            s.commit()
            st.success(f"Matrícula {matricula} autorizada como {PERFIS[perfil]}. "
                       "No próximo login pelo SUAP o perfil já estará disponível.")


def lista_acessos(campus_id: int, perfis: list[str], chave: str) -> None:
    s = db.s()
    itens = list(s.scalars(select(Acesso).where(Acesso.campus_id == campus_id, Acesso.perfil.in_(perfis))
                           .order_by(Acesso.perfil, Acesso.nome, Acesso.matricula)))
    if not itens:
        st.caption("Ninguém cadastrado.")
        return
    usuarios = {u.username: u for u in s.scalars(select(Usuario).where(
        Usuario.username.in_([a.matricula for a in itens])))}
    st.dataframe(pd.DataFrame([{
        "Matrícula / usuário": a.matricula,
        "Nome": (usuarios[a.matricula].nome if a.matricula in usuarios else "") or a.nome or "—",
        "Perfil": PERFIS[a.perfil],
        "Situação": "ativo" if a.ativo else "desativado",
        "Último acesso": ui.data(usuarios[a.matricula].ultimo_login, True) if a.matricula in usuarios else "ainda não entrou",
    } for a in itens]), hide_index=True, use_container_width=True)
    col1, col2 = st.columns([4, 1], vertical_alignment="bottom")
    alvo = ui.escolher("Selecionar para ativar/desativar ou remover", itens, onde=col1, index=None,
                       placeholder="Selecione…", key=f"sel_{chave}",
                       format_func=lambda a: f"{a.matricula} · {PERFIS[a.perfil]} · {'ativo' if a.ativo else 'desativado'}")
    if alvo:
        c1, c2 = st.columns(2)
        if c1.button("Desativar" if alvo.ativo else "Reativar", key=f"tog_{chave}", use_container_width=True):
            alvo.ativo = not alvo.ativo
            s.commit()
            st.rerun()
        if c2.button("Remover", key=f"rm_{chave}", use_container_width=True):
            s.delete(alvo)
            s.commit()
            st.rerun()


def psicopedagogas(campus_id: int) -> None:
    """Contas locais da Psicopedagogia (criadas pelo gestor; a pessoa pode trocar a senha)."""
    s = db.s()
    with st.form("nova_psico", clear_on_submit=True):
        st.markdown("**Nova conta de Psicopedagogia**")
        col1, col2 = st.columns([1, 2])
        usuario = col1.text_input("Usuário *", help="Usado para entrar. Ex.: ana.souza")
        nome = col2.text_input("Nome completo *")
        col1, col2 = st.columns(2)
        email = col1.text_input("E-mail")
        senha = col2.text_input("Senha inicial *", type="password",
                                help="A psicopedagoga pode trocá-la depois em Meu perfil.")
        if st.form_submit_button("Criar conta", type="primary"):
            usuario = usuario.strip().lower()
            existente = s.scalar(select(Usuario).where(Usuario.username == usuario))
            if not usuario or not nome.strip():
                st.error("Informe usuário e nome.")
            elif existente and existente.auth != "local":
                st.error("Esse identificador já pertence a uma conta SUAP. Escolha outro usuário.")
            elif (erro := senha_forte(senha)) and not existente:
                st.error(erro)
            else:
                if existente is None:
                    s.add(Usuario(username=usuario, nome=nome.strip(), email=email.strip(), auth="local",
                                  senha_hash=hash_senha(senha), ativo=True, is_admin=False))
                if not s.scalar(select(Acesso).where(Acesso.campus_id == campus_id, Acesso.matricula == usuario,
                                                     Acesso.perfil == "psicopedagogia")):
                    s.add(Acesso(campus_id=campus_id, matricula=usuario, perfil="psicopedagogia",
                                 nome=nome.strip(), ativo=True, criado_por_id=ui.ctx().usuario_id))
                s.commit()
                st.success(f"Conta “{usuario}” criada. Ela entra em “Deseja entrar com login e senha?”.")
    lista_acessos(campus_id, ["psicopedagogia"], f"psico_{campus_id}")
    contas = list(s.scalars(select(Usuario).join(Acesso, Acesso.matricula == Usuario.username).where(
        Acesso.campus_id == campus_id, Acesso.perfil == "psicopedagogia", Usuario.auth == "local")))
    if contas:
        with st.expander("Redefinir a senha de uma psicopedagoga"):
            u = ui.escolher("Conta", contas, lambda x: f"{x.nome} ({x.username})", key="psico_reset_u")
            nova = st.text_input("Nova senha", type="password", key="psico_reset_s")
            if st.button("Redefinir senha", key="psico_reset_b"):
                if erro := senha_forte(nova):
                    st.error(erro)
                else:
                    u.senha_hash = hash_senha(nova)
                    s.commit()
                    st.success("Senha redefinida.")
