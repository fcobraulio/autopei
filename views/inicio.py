"""Página inicial: caixa de pendências (quem preenche) e painel (gestão)."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import select

from core import auth, db, fluxo
from core.models import ETAPAS, PERFIS_SUAP, STATUS, STATUS_CURTO, Componente, Historico, Pei, Semestre, Usuario
from views import anexos, estudos, formulario, nav, ui

ROTULO_ENVIAR = {
    "psicopedagogia": "Concluir e enviar para a ETEP",
    "etep": "Concluir e enviar para os docentes",
    "docente": "Concluir meu componente",
}


def _perfis_por_campus(c) -> dict[int, set[str]]:
    mapa: dict[int, set[str]] = {}
    for a in auth.acessos(db.s(), c.username):
        if c.via == "suap" or a.perfil not in PERFIS_SUAP:
            mapa.setdefault(a.campus_id, set()).add(a.perfil)
    return mapa


# ---------------------------------------------------------------------------
# Preenchimento
# ---------------------------------------------------------------------------
def _preencher(etapa: str, pei: Pei, comp: Componente | None) -> None:
    c = ui.ctx()
    s = db.s()
    usuario = s.get(Usuario, c.usuario_id)
    if st.button("← Voltar às pendências"):
        st.session_state.pop("abrir", None)
        st.rerun()

    titulo = ETAPAS[etapa] + (f" · {fluxo.rotulo_componente(s, comp)}" if comp else "")
    ui.cabecalho(pei.estudante.nome, f"PEI {pei.semestre.codigo} · {titulo}")
    st.markdown(ui.dados_estudante_md(pei, com_nome=False))

    if pei.em_correcao:
        st.warning(f"**Correção solicitada pelo NAPNE:** {ui.ultimo_comentario_correcao(pei)}  \n"
                   "Depois de corrigir, o PEI volta direto para a revisão do NAPNE.", icon=":material/undo:")
    if etapa == "docente":
        outros = [x for x in pei.componentes if x.id != comp.id]
        if outros:
            feitos = sum(1 for x in outros if x.status == "concluido")
            st.info(f"Este estudante está com **{len(pei.componentes)} componentes** ao mesmo tempo. "
                    f"Você preenche só o seu; os outros docentes preenchem os deles em paralelo "
                    f"({feitos} de {len(outros)} já concluídos). O PEI segue para a revisão quando todos terminarem.",
                    icon=":material/call_split:")
    resp = fluxo.respostas(s, pei.id, comp.id if comp else None)
    if any(r.origem for r in resp.values()):
        st.info(f"As respostas foram **pré-preenchidas com o PEI de {pei.prefill_origem}**. "
                "Revise e ajuste apenas o que mudou.", icon=":material/history:")

    anteriores = {"etep": ["psicopedagogia"], "docente": ["psicopedagogia", "etep"]}.get(etapa, [])
    if anteriores:
        with st.expander("Ver informações das etapas anteriores"):
            geral = fluxo.respostas(s, pei.id)
            for e in anteriores:
                st.markdown(f"**{ETAPAS[e]}**")
                ui.mostrar_respostas(fluxo.perguntas(s, e, pei.id), geral)
                st.divider()

    anexos.enviar(pei, etapa, c.usuario_id, comp.id if comp else None)
    anexos.anteriores(pei)
    st.divider()

    perguntas = fluxo.perguntas(s, etapa)
    comp_id = comp.id if comp else None
    formulario.renderizar(perguntas, resp, pei.id, comp_id)
    st.caption("Perguntas marcadas com \\* são obrigatórias.")
    if etapa == "docente":
        estudos.editor(pei, comp, c.usuario_id)

    col1, col2 = st.columns([1, 2])
    if col1.button("Salvar rascunho", icon=":material/save:", use_container_width=True):
        formulario.salvar(perguntas, pei, comp_id, c.usuario_id)
        s.commit()
        st.toast("Rascunho salvo.")
    rotulo = "Reenviar para a revisão do NAPNE" if pei.em_correcao else ROTULO_ENVIAR[etapa]
    if col2.button(rotulo, type="primary", icon=":material/send:", use_container_width=True):
        formulario.salvar(perguntas, pei, comp_id, c.usuario_id)
        s.commit()
        try:
            novo = fluxo.enviar(s, pei, etapa, usuario, comp)
            s.commit()
        except fluxo.FluxoError as exc:
            s.rollback()
            st.error(str(exc))
        else:
            formulario.limpar(pei.id, comp_id)
            st.session_state.pop("abrir", None)
            st.session_state["msg"] = {
                "etep": "Enviado para a ETEP.",
                "docente": "Enviado! O PEI foi distribuído ao mesmo tempo para todos os docentes do estudante."
                if etapa == "etep" else "Componente concluído. O PEI segue com os demais docentes.",
                "revisao": "Enviado para a revisão do NAPNE.",
            }.get(novo, "Enviado.")
            st.rerun()


def _caixa(s, itens) -> None:
    st.markdown("### Minhas pendências")
    if not itens:
        st.success("Nenhuma pendência no momento. 🎉")
        return
    for etapa, pei, comp in itens:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1], vertical_alignment="center")
            extra = f" · **{fluxo.rotulo_componente(s, comp)}**" if comp else ""
            marcas = "  :red-badge[Correção solicitada]" if pei.em_correcao else ""
            if pei.prefill_origem:
                marcas += f"  :orange-badge[Pré-preenchido de {pei.prefill_origem}]"
            col1.markdown(
                f"**{pei.estudante.nome}**{marcas}  \n"
                f"{ETAPAS[etapa]}{extra} · {pei.estudante.curso or ''} · "
                f"semestre {pei.semestre.codigo} · aguardando há {ui.dias_desde(pei.atualizado_em)} dia(s)"
            )
            if col2.button("Preencher", key=f"abrir_{etapa}_{pei.id}_{comp.id if comp else 0}",
                           type="primary", use_container_width=True):
                st.session_state["abrir"] = (etapa, pei.id, comp.id if comp else None)
                st.rerun()


def _enviados(s, usuario_id: int) -> None:
    meus = select(Historico.pei_id).where(Historico.usuario_id == usuario_id, Historico.acao.contains("concluiu"))
    peis = list(s.scalars(select(Pei).join(Semestre).where(Pei.id.in_(meus), Semestre.status == "aberto")
                          .order_by(Pei.atualizado_em.desc())))
    if peis:
        with st.expander(f"PEIs em que já trabalhei neste semestre ({len(peis)})"):
            for p in peis:
                st.markdown(f"{p.estudante.nome} · {p.semestre.codigo} · {ui.badge(p.status)}")


# ---------------------------------------------------------------------------
# Painel da gestão
# ---------------------------------------------------------------------------
def painel() -> None:
    c = ui.ctx()
    s = db.s()
    semestres = list(s.scalars(select(Semestre).where(Semestre.campus_id == c.campus_id)
                               .order_by(Semestre.codigo.desc())))
    st.markdown(f"### Painel · NAPNE {c.campus_nome}")
    if not semestres:
        st.info("Nenhum semestre cadastrado. Crie o semestre letivo em **Semestres**.")
        return
    aberto = next((x for x in semestres if x.status == "aberto"), semestres[0])
    sem = ui.escolher("Semestre", semestres, index=semestres.index(aberto),
                      format_func=lambda x: x.codigo + (" (encerrado)" if x.status != "aberto" else ""),
                       key="painel_sem")
    peis = list(s.scalars(select(Pei).where(Pei.semestre_id == sem.id)))
    cont = {k: 0 for k in STATUS}
    for p in peis:
        cont[p.status] += 1

    m = st.columns(5)
    m[0].metric("PEIs no semestre", len(peis) - cont["cancelado"])
    m[1].metric("Em preenchimento", cont["psicopedagogia"] + cont["etep"] + cont["docente"])
    m[2].metric("Para revisar", cont["revisao"])
    m[3].metric("Aguardando registro", cont["aprovado"])
    m[4].metric("Registrados", cont["registrado"])

    if not peis:
        st.info("Ainda não há PEIs neste semestre. Cadastre em **PEIs**.")
        return
    total_ativo = max(1, len(peis) - cont["cancelado"])
    st.progress(cont["registrado"] / total_ativo,
                text=f"{cont['registrado']} de {total_ativo} PEIs concluídos (registrados no SUAP)")

    sem_doc = fluxo.componentes_sem_docente(s, sem.id)
    if sem_doc:
        codigos = sorted({x.codigo for x in sem_doc})
        st.warning(f"**{len(codigos)} disciplina(s) de estudantes com NEE ainda sem docente associado:** "
                   f"{', '.join(codigos)}. Associe em **Disciplinas e docentes** para que os PEIs "
                   "cheguem a quem leciona.", icon=":material/person_off:")

    if cont["revisao"] or cont["aprovado"]:
        st.markdown("**Precisa da sua ação**")
        for p in peis:
            if p.status in ("revisao", "aprovado"):
                acao = "revisar e aprovar" if p.status == "revisao" else "subir no SUAP e marcar como registrado"
                col1, col2 = st.columns([5, 1], vertical_alignment="center")
                col1.markdown(f"{ui.badge(p.status, True)} **{p.estudante.nome}** — {acao}")
                if col2.button("Abrir", key=f"painel_abrir_{p.id}", use_container_width=True):
                    st.session_state["pei_sel"] = p.id
                    st.switch_page(nav.PAGINAS["peis"])

    st.markdown("**Onde está cada PEI**")
    linhas = []
    for p in sorted(peis, key=lambda x: list(STATUS).index(x.status)):
        docs = f"{sum(1 for x in p.componentes if x.status == 'concluido')}/{len(p.componentes)}" \
            if p.status == "docente" else ""
        linhas.append({
            "Estudante": p.estudante.nome,
            "Etapa": STATUS_CURTO[p.status] + (" (correção)" if p.em_correcao else ""),
            "Docentes concluídos": docs,
            "Com quem": ui.com_quem(p),
            "Dias na etapa": ui.dias_desde(p.atualizado_em),
        })
    st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
    st.caption("Na etapa dos docentes, o PEI fica com todos os docentes do estudante ao mesmo tempo; "
               "segue para a revisão quando todos concluírem.")


# ---------------------------------------------------------------------------
def pagina() -> None:
    c = ui.ctx()
    s = db.s()
    if msg := st.session_state.pop("msg", None):
        st.success(msg)

    usuario = s.get(Usuario, c.usuario_id)
    perfis = _perfis_por_campus(c)

    abrir = st.session_state.get("abrir")
    if abrir:
        etapa, pei_id, comp_id = abrir
        pei = s.get(Pei, pei_id)
        comp = s.get(Componente, comp_id) if comp_id else None
        if pei and pei.status == etapa and (comp is None or comp.status == "pendente"):
            _preencher(etapa, pei, comp)
            return
        st.session_state.pop("abrir", None)

    itens = fluxo.caixa(s, usuario, perfis, c.docente)
    preenche = bool(itens) or any(p & {"psicopedagogia", "etep"} for p in perfis.values())

    if preenche or not c.gestao:
        ui.cabecalho(f"Olá, {c.nome.split()[0]}!")
        _caixa(s, itens)
        _enviados(s, c.usuario_id)
        if not itens and not c.gestao and not perfis:
            st.caption("Como docente, você verá aqui os PEIs dos estudantes com NEE das suas disciplinas "
                       "assim que passarem pela Psicopedagogia e pela ETEP.")
        if c.gestao:
            st.divider()
    if c.gestao:
        painel()
