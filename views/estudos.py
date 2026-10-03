"""Estudos individualizados: cadastrados pelo DOCENTE no seu componente (opcional)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import db, fluxo
from core.models import DIAS_SEMANA, FREQUENCIAS, HORAS_ESTUDO, Componente, EstudoIndividualizado, Pei, faixa_hora


def editor(pei: Pei, comp: Componente, usuario_id: int) -> None:
    s = db.s()
    chave = f"est_{pei.id}_{comp.id}"
    with st.container(border=True):
        st.markdown("**🕒 Estudos individualizados** <small>(opcional — cadastre só se você vê a necessidade "
                    "de atender este(a) estudante em horário extra)</small>", unsafe_allow_html=True)
        itens = fluxo.estudos(s, pei.id, comp.id)
        if not itens:
            st.caption("Nenhum horário cadastrado para o seu componente. Se nenhum docente cadastrar, o PEI "
                       "informa que o(a) estudante não tem estudo individualizado.")
        for e in itens:
            col1, col2 = st.columns([8, 1], vertical_alignment="center")
            local = f" · {e.local}" if e.local else ""
            col1.markdown(f"**{e.dia}, {faixa_hora(e.hora)}** · {FREQUENCIAS[e.frequencia]}{local}")
            if col2.button("✕", key=f"{chave}_rm_{e.id}", help="Remover este horário"):
                try:
                    fluxo.remover_estudo(s, pei, s.get(EstudoIndividualizado, e.id), usuario_id)
                    s.commit()
                except fluxo.FluxoError as exc:
                    s.rollback()
                    st.error(str(exc))
                st.rerun()

        n = st.session_state.get(f"{chave}_n", 0)
        col1, col2, col3 = st.columns([2, 2, 3])
        dia = col1.selectbox("Dia", DIAS_SEMANA, index=None, placeholder="Escolha", key=f"{chave}_dia_{n}")
        hora = col2.selectbox("Horário", HORAS_ESTUDO, index=None, placeholder="Escolha", format_func=faixa_hora,
                              key=f"{chave}_hora_{n}")
        freq = col3.radio("Frequência", list(FREQUENCIAS), format_func=lambda f: f.capitalize(), horizontal=True,
                          key=f"{chave}_freq_{n}",
                          help="Semanal: toda semana · Quinzenal: a cada 2 semanas · Mensal: 1 vez por mês. "
                               "Para mais de um atendimento por semana, cadastre um horário para cada dia.")
        local = st.text_input("Local / observação (opcional)", key=f"{chave}_local_{n}",
                              placeholder="ex.: Laboratório 3; a partir de 10/03; semanas ímpares")
        if st.button("Adicionar horário", icon=":material/add_alarm:", key=f"{chave}_add_{n}"):
            if dia is None or hora is None:
                st.error("Escolha o dia e o horário.")
            else:
                try:
                    fluxo.adicionar_estudo(s, pei, comp, usuario_id, dia, hora, freq, local)
                    s.commit()
                except fluxo.FluxoError as exc:
                    s.rollback()
                    st.error(str(exc))
                else:
                    st.session_state[f"{chave}_n"] = n + 1
                    st.rerun()


def tabela(pei: Pei, componente_id: int | None = None) -> None:
    """Visualização (somente leitura) para a gestão e para os outros docentes."""
    s = db.s()
    itens = fluxo.estudos(s, pei.id, componente_id)
    if not itens:
        st.caption("Nenhum estudo individualizado cadastrado pelos docentes." if componente_id is None
                   else "Nenhum estudo individualizado neste componente.")
        return
    comps = {c.id: c for c in pei.componentes}
    st.dataframe(pd.DataFrame([{
        "Componente": fluxo.rotulo_componente(s, comps[e.componente_id]) if e.componente_id in comps else "—",
        "Docente": e.usuario.nome if e.usuario else "—",
        "Dia": e.dia, "Horário": faixa_hora(e.hora), "Frequência": FREQUENCIAS[e.frequencia],
        "Local / observação": e.local,
    } for e in itens]), hide_index=True, use_container_width=True)
