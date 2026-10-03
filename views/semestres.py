"""Semestres letivos do campus."""
from __future__ import annotations

from datetime import date

import streamlit as st
from sqlalchemy import func, select

from core import db, fluxo
from core.models import STATUS_FINAIS, Pei, Semestre
from views import ui


def _sugestao(existentes: set[str]) -> str:
    hoje = date.today()
    ano, s = hoje.year, (1 if hoje.month <= 6 else 2)
    for _ in range(6):
        cod = f"{ano}.{s}"
        if cod not in existentes:
            return cod
        ano, s = (ano, 2) if s == 1 else (ano + 1, 1)
    return ""


def pagina() -> None:
    c = ui.ctx()
    s = db.s()
    ui.cabecalho("Semestres", f"NAPNE {c.campus_nome}")
    semestres = list(s.scalars(select(Semestre).where(Semestre.campus_id == c.campus_id)
                               .order_by(Semestre.codigo.desc())))

    if c.critico:
        with st.container(border=True):
            col1, col2 = st.columns([2, 1], vertical_alignment="bottom")
            codigo = col1.text_input("Novo semestre", _sugestao({x.codigo for x in semestres}),
                                     help="Formato AAAA.S — ex.: 2026.2")
            if col2.button("Criar semestre", type="primary", use_container_width=True):
                try:
                    fluxo.criar_semestre(s, c.campus_id, codigo)
                    s.commit()
                    st.rerun()
                except fluxo.FluxoError as exc:
                    st.error(str(exc))

    if not semestres:
        st.info("Nenhum semestre cadastrado.")
        return

    for sem in semestres:
        total = s.scalar(select(func.count(Pei.id)).where(Pei.semestre_id == sem.id)) or 0
        pend = fluxo.pendencias_semestre(s, sem)
        with st.container(border=True):
            col1, col2 = st.columns([3, 1], vertical_alignment="center")
            situacao = ":green-badge[Aberto]" if sem.status == "aberto" else ":gray-badge[Encerrado]"
            texto = f"### {sem.codigo} {situacao}\n{total} PEI(s) · "
            texto += (f"{pend} ainda não registrado(s) ou cancelado(s)" if pend
                      else "todos registrados ou cancelados")
            if sem.status != "aberto":
                texto += f" · encerrado em {ui.data(sem.encerrado_em)}"
            col1.markdown(texto)
            if sem.status == "aberto" and c.critico:
                if col2.button("Encerrar semestre", key=f"enc_{sem.id}", disabled=pend > 0,
                               help="Disponível quando todos os PEIs estiverem registrados ou cancelados.",
                               use_container_width=True):
                    try:
                        fluxo.encerrar_semestre(s, sem, c.usuario_id)
                        s.commit()
                        st.rerun()
                    except fluxo.FluxoError as exc:
                        st.error(str(exc))
            elif sem.status != "aberto" and c.is_admin:
                if col2.button("Reabrir", key=f"reab_{sem.id}", use_container_width=True):
                    fluxo.reabrir_semestre(s, sem)
                    s.commit()
                    st.rerun()
    st.caption("Semestres encerrados ficam disponíveis apenas para consulta. "
               f"Estados considerados concluídos: {', '.join(sorted(STATUS_FINAIS))}.")
