"""Disciplinas e docentes do semestre: associação código da disciplina ↔ docente(s).

É por essa associação que o PEI chega automaticamente aos docentes: quando o PEI de
um estudante com os códigos 123, 456 e 789 passa pela Psicopedagogia e pela ETEP, ele
aparece ao mesmo tempo na caixa dos docentes desses três códigos.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import select

from core import db, fluxo
from core.models import Componente, Oferta, Pei, Semestre, Usuario
from views import ui


def pagina() -> None:
    c = ui.ctx()
    s = db.s()
    ui.cabecalho("Disciplinas e docentes",
                 "Associe o código de cada disciplina ao(s) docente(s) que a lecionam neste semestre.")
    semestres = list(s.scalars(select(Semestre).where(Semestre.campus_id == c.campus_id)
                               .order_by(Semestre.codigo.desc())))
    if not semestres:
        st.info("Crie primeiro o semestre em **Semestres**.")
        return
    aberto = next((x for x in semestres if x.status == "aberto"), semestres[0])
    sem = ui.escolher("Semestre", semestres, index=semestres.index(aberto),
                      format_func=lambda x: x.codigo + (" (encerrado)" if x.status != "aberto" else ""))
    editavel = sem.status == "aberto"

    st.info("Quando o PEI de um estudante passa pela Psicopedagogia e pela ETEP, ele é enviado "
            "**automaticamente e ao mesmo tempo** para os docentes de todos os códigos de disciplina do "
            "estudante. Qualquer pessoa que entra pelo SUAP pode ser docente: basta a matrícula estar aqui.",
            icon=":material/call_split:")

    sem_doc = fluxo.componentes_sem_docente(s, sem.id)
    if sem_doc:
        cods = sorted({x.codigo for x in sem_doc})
        st.warning(f"Códigos de estudantes com NEE ainda sem docente: **{', '.join(cods)}**", icon=":material/person_off:")

    if editavel:
        aba1, aba2, aba3 = st.tabs(["Adicionar", "Colar uma lista", "Copiar de outro semestre"])
        with aba1:
            docentes_conhecidos = list(s.scalars(select(Usuario).where(
                Usuario.auth == "suap", Usuario.suap_tipo.ilike("%docente%")).order_by(Usuario.nome)))
            with st.form("nova_oferta", clear_on_submit=True):
                col1, col2 = st.columns([1, 3])
                codigo = col1.text_input("Código *", placeholder="ex.: 123", value=sem_doc[0].codigo if sem_doc else "")
                disciplina = col2.text_input("Nome da disciplina", placeholder="ex.: Banco de Dados")
                col1, col2 = st.columns([1, 3])
                matricula = col1.text_input("Matrícula SUAP do docente *")
                nome = col2.text_input("Nome do docente")
                conhecido = ui.escolher("…ou escolha um docente que já entrou no AutoPEI", docentes_conhecidos,
                                        lambda u: f"{u.nome} ({u.username})", index=None,
                                        placeholder="Opcional")
                if st.form_submit_button("Associar", type="primary"):
                    if conhecido:
                        matricula, nome = conhecido.username, conhecido.nome
                    try:
                        fluxo.salvar_oferta(s, sem.id, codigo, disciplina, matricula, nome)
                        s.commit()
                        st.rerun()
                    except fluxo.FluxoError as exc:
                        s.rollback()
                        st.error(str(exc))
        with aba2:
            st.caption("Uma linha por associação, no formato  **código; disciplina; matrícula do docente; nome "
                       "do docente**  (o nome é opcional). Pode colar direto de uma planilha.")
            texto = st.text_area("Lista", height=160, placeholder="123; Lógica de Programação; 1234567; Maria Souza\n"
                                                                  "456; Banco de Dados; 7654321")
            if st.button("Importar lista"):
                ok, erros = fluxo.importar_ofertas(s, sem.id, texto)
                s.commit()
                st.success(f"{ok} associação(ões) importada(s).")
                for e in erros:
                    st.error(e)
        with aba3:
            outros = [x for x in semestres if x.id != sem.id]
            if not outros:
                st.caption("Não há outros semestres.")
            else:
                origem = ui.escolher("Copiar associações de", outros, lambda x: x.codigo)
                if st.button("Copiar"):
                    n = 0
                    for o in s.scalars(select(Oferta).where(Oferta.semestre_id == origem.id)):
                        fluxo.salvar_oferta(s, sem.id, o.codigo, o.disciplina, o.docente_matricula, o.docente_nome)
                        n += 1
                    s.commit()
                    st.success(f"{n} associação(ões) copiada(s). Revise: docentes podem ter mudado.")

    ofertas = list(s.scalars(select(Oferta).where(Oferta.semestre_id == sem.id)
                             .order_by(Oferta.codigo, Oferta.docente_nome)))
    st.markdown(f"**Associações em {sem.codigo}** ({len(ofertas)})")
    if not ofertas:
        st.caption("Nenhuma associação ainda.")
        return
    usados = {cod for (cod,) in s.execute(select(Componente.codigo).join(Pei).where(Pei.semestre_id == sem.id))}
    nomes = {u.username: u.nome for u in s.scalars(select(Usuario).where(
        Usuario.username.in_([o.docente_matricula for o in ofertas])))}
    st.dataframe(pd.DataFrame([{
        "Código": o.codigo, "Disciplina": o.disciplina,
        "Docente": nomes.get(o.docente_matricula) or o.docente_nome or "—",
        "Matrícula": o.docente_matricula,
        "Já entrou no AutoPEI": "sim" if o.docente_matricula in nomes else "ainda não",
        "Estudantes com NEE": "sim" if o.codigo in usados else "",
    } for o in ofertas]), hide_index=True, use_container_width=True)
    if editavel:
        rm = ui.escolher("Remover associação", ofertas, index=None, placeholder="Selecione…",
                         format_func=lambda o: f"{o.codigo} — {o.disciplina or ''} — "
                                                f"{nomes.get(o.docente_matricula) or o.docente_nome or o.docente_matricula}")
        if rm and st.button("Remover", icon=":material/delete:"):
            s.delete(rm)
            s.commit()
            st.rerun()
