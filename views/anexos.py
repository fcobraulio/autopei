"""Anexos internos do PEI (laudos, notificações, provas...). Não entram no DOCX."""
from __future__ import annotations

import streamlit as st

from core import config, db, fluxo
from core.models import Anexo, Pei
from views import ui

ROTULO = {"psicopedagogia": "Psicopedagogia", "etep": "ETEP", "docente": "Docente", "gestao": "NAPNE"}


def _tamanho(n: int) -> str:
    if n < 1024:
        return f"{n} bytes"
    return f"{n / 1024:.0f} KB" if n < 1024 * 1024 else f"{n / 1024 / 1024:.1f} MB"


def lista(pei: Pei, usuario_id: int | None = None, pode_excluir_todos: bool = False, chave: str = "") -> None:
    s = db.s()
    itens = fluxo.anexos(s, pei.id)
    if not itens:
        st.caption("Nenhum anexo.")
        return
    for a in itens:
        col1, col2, col3 = st.columns([6, 2, 1], vertical_alignment="center")
        quem = a.usuario.nome if a.usuario else "—"
        desc = f" — {a.descricao}" if a.descricao else ""
        col1.markdown(f"**{a.nome_arquivo}**{desc}  \n<small>{ROTULO.get(a.etapa, a.etapa)} · {quem} · "
                      f"{ui.data(a.criado_em, True)} · {_tamanho(a.tamanho)}</small>", unsafe_allow_html=True)
        col2.download_button("Baixar", a.dados, file_name=a.nome_arquivo, mime=a.mime,
                             key=f"anx_dl_{chave}_{a.id}", use_container_width=True)
        if pode_excluir_todos or (usuario_id and a.usuario_id == usuario_id):
            if col3.button("✕", key=f"anx_rm_{chave}_{a.id}", help="Excluir anexo"):
                fluxo.log(s, pei, usuario_id, f"Anexo excluído: {a.nome_arquivo}")
                s.delete(s.get(Anexo, a.id))
                s.commit()
                st.rerun()


def enviar(pei: Pei, etapa: str, usuario_id: int, componente_id: int | None = None) -> None:
    """Envio de anexos — só dentro das etapas de preenchimento (Psicopedagogia, ETEP, docentes).

    A gestão e os auxiliares apenas cadastram os dados do estudante: não anexam arquivos.
    Os laudos são anexados pela Psicopedagogia.
    """
    chave = f"{pei.id}_{etapa}_{componente_id or 0}"
    if etapa == "psicopedagogia":
        titulo = "**📎 Laudos e documentos de apoio**"
        exemplo = "ex.: laudo, relatório de especialista, notificação escolar"
    else:
        titulo = "**📎 Documentos de apoio**"
        exemplo = "ex.: notificação escolar, prova, atividade adaptada. Laudos são anexados pela Psicopedagogia"
    with st.container(border=True):
        st.markdown(f"{titulo} <small>(uso interno: ajudam a equipe a decidir, "
                    "mas não entram no documento final)</small>", unsafe_allow_html=True)
        lista(pei, usuario_id, chave=chave)
        n = st.session_state.get(f"anx_n_{chave}", 0)
        arquivo = st.file_uploader("Adicionar arquivo", key=f"anx_up_{chave}_{n}",
                                   help=f"Até {config.ANEXO_MAX_MB} MB ({exemplo}).")
        if arquivo is not None:
            desc = st.text_input("Descrição (opcional)", key=f"anx_desc_{chave}_{n}")
            if st.button("Anexar", key=f"anx_btn_{chave}_{n}", icon=":material/attach_file:"):
                s = db.s()
                try:
                    fluxo.anexar(s, pei, etapa, usuario_id, arquivo.name, arquivo.type or "", arquivo.getvalue(),
                                 desc, componente_id, config.ANEXO_MAX_MB)
                    s.commit()
                except fluxo.FluxoError as exc:
                    s.rollback()
                    st.error(str(exc))
                else:
                    st.session_state[f"anx_n_{chave}"] = n + 1
                    st.rerun()


def anteriores(pei: Pei) -> None:
    """Anexos dos PEIs de semestres anteriores do mesmo estudante (somente leitura)."""
    from sqlalchemy import select

    from core.models import Semestre

    s = db.s()
    itens = list(s.scalars(select(Anexo).join(Pei, Pei.id == Anexo.pei_id).join(Semestre).where(
        Pei.estudante_id == pei.estudante_id, Pei.id != pei.id).order_by(Semestre.codigo.desc(), Anexo.criado_em)))
    if not itens:
        return
    with st.expander(f"Anexos de semestres anteriores deste estudante ({len(itens)})"):
        for a in itens:
            col1, col2 = st.columns([6, 2], vertical_alignment="center")
            sem = s.get(Pei, a.pei_id).semestre.codigo
            col1.markdown(f"**{a.nome_arquivo}**{' — ' + a.descricao if a.descricao else ''}  \n"
                          f"<small>{sem} · {ROTULO.get(a.etapa, a.etapa)} · {a.usuario.nome if a.usuario else '—'}</small>",
                          unsafe_allow_html=True)
            col2.download_button("Baixar", a.dados, file_name=a.nome_arquivo, mime=a.mime,
                                 key=f"anx_ant_{pei.id}_{a.id}", use_container_width=True)
