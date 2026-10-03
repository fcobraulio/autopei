"""PEIs do campus: lista, cadastro, revisão, aprovação e registro."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy import select

from core import db, fluxo
from core.docx_pei import gerar_docx, nome_arquivo
from core.models import (
    ETAPAS,
    STATUS,
    STATUS_CURTO,
    STATUS_FINAIS,
    Estudante,
    Oferta,
    Pei,
    Semestre,
)
from views import anexos, estudos, formulario, ui

NIVEIS = ["Técnico Integrado Regular", "Técnico Integrado EJA", "Técnico Subsequente",
          "Superior de Tecnologia", "Licenciatura", "Outros"]
TURNOS = ["Matutino", "Vespertino", "Noturno", "Integral"]
MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _catalogo(semestre_id: int) -> dict[str, str]:
    """Códigos de disciplina do semestre → nome (das associações docente ↔ disciplina)."""
    cat: dict[str, str] = {}
    for o in db.s().scalars(select(Oferta).where(Oferta.semestre_id == semestre_id).order_by(Oferta.codigo)):
        if o.codigo not in cat or (o.disciplina and not cat[o.codigo]):
            cat[o.codigo] = o.disciplina
    return cat


def _seletor_codigos(sem: Semestre, chave: str, atuais: list[str] | None = None) -> list[str]:
    cat = _catalogo(sem.id)
    opcoes = sorted(set(cat) | set(atuais or []))
    escolha = st.multiselect(
        "Códigos das disciplinas do estudante *", opcoes, default=atuais or [], key=chave,
        format_func=lambda cod: f"{cod} — {cat[cod]}" if cat.get(cod) else cod,
        accept_new_options=True, placeholder="Digite ou escolha os códigos (ex.: 123, 456, 789)",
        help="Os docentes de cada código vêm de **Disciplinas e docentes**. Se um código ainda não "
             "tiver docente, você pode associá-lo depois: o PEI chegará ao docente automaticamente.")
    return [x.strip().upper() for x in escolha if x.strip()]


# ---------------------------------------------------------------------------
# Novo PEI
# ---------------------------------------------------------------------------
def _campos_estudante(prefixo: str, e: Estudante | None = None) -> dict:
    e = e or Estudante(nome="", matricula="", curso="", nivel_forma="", periodo="", turno="",
                       nee="", responsavel="")
    col1, col2 = st.columns([2, 1])
    nome = col1.text_input("Nome completo *", e.nome, key=prefixo + "nome")
    matricula = col2.text_input("Matrícula", e.matricula, key=prefixo + "mat")
    col1, col2, col3 = st.columns(3)
    nasc = col1.date_input("Data de nascimento", e.data_nascimento, min_value=date(1940, 1, 1),
                           max_value=date.today(), format="DD/MM/YYYY", key=prefixo + "nasc")
    nivel = col2.selectbox("Nível de ensino / forma", NIVEIS,
                           index=NIVEIS.index(e.nivel_forma) if e.nivel_forma in NIVEIS else 0,
                           key=prefixo + "nivel")
    turno = col3.selectbox("Turno", TURNOS, index=TURNOS.index(e.turno) if e.turno in TURNOS else 1,
                           key=prefixo + "turno")
    col1, col2 = st.columns([2, 1])
    curso = col1.text_input("Curso *", e.curso, key=prefixo + "curso")
    periodo = col2.text_input("Ano / período", e.periodo, placeholder="ex.: 1º ano", key=prefixo + "per")
    nee = st.text_area("Necessidades educacionais específicas (resumo) *", e.nee, height=70,
                       key=prefixo + "nee",
                       help="Ex.: Transtorno do Espectro Autista (TEA) e TDAH. A psicopedagogia detalha depois.")
    resp = st.text_input("Responsável legal", e.responsavel, key=prefixo + "resp")
    return dict(nome=nome.strip(), matricula=matricula.strip(), data_nascimento=nasc, nivel_forma=nivel,
                turno=turno, curso=curso.strip(), periodo=periodo.strip(), nee=nee.strip(),
                responsavel=resp.strip())


def _novo_pei(sem: Semestre) -> None:
    c = ui.ctx()
    s = db.s()
    st.markdown("### Cadastrar novo PEI")
    st.caption(f"Semestre {sem.codigo}. Após o cadastro, o PEI entra na caixa da Psicopedagogia.")

    ja_tem = select(Pei.estudante_id).where(Pei.semestre_id == sem.id)
    existentes = list(s.scalars(select(Estudante).where(
        Estudante.campus_id == c.campus_id, Estudante.id.notin_(ja_tem)).order_by(Estudante.nome)))
    modo = st.radio("Estudante", ["Novo estudante", "Estudante já cadastrado (semestres anteriores)"],
                    horizontal=True, disabled=not existentes)
    if modo.startswith("Novo") or not existentes:
        dados = _campos_estudante("novo_")
        est = None
    else:
        est = ui.escolher("Selecione o estudante", existentes,
                          format_func=lambda e: f"{e.nome} ({e.matricula or 'sem matrícula'})")
        with st.expander("Atualizar dados do estudante"):
            dados = _campos_estudante(f"exist_{est.id}_", est)

    st.markdown("**Componentes curriculares**")
    codigos = _seletor_codigos(sem, "novo_codigos")
    cat = _catalogo(sem.id)
    sem_doc = [x for x in codigos if x not in cat]
    if sem_doc:
        st.caption(f":orange[Ainda sem docente associado: {', '.join(sem_doc)}.]")
    prefill = True
    if est is not None and (ant := fluxo.pei_anterior(s, est.id, sem)):
        prefill = st.checkbox(
            f"Pré-preencher com as respostas do PEI de {ant.semestre.codigo} (recomendado)", value=True,
            help="Psicopedagogia, ETEP e docentes das mesmas disciplinas recebem os campos já preenchidos "
                 "e só ajustam o que mudou. Disciplinas novas começam em branco.")

    if st.button("Cadastrar PEI e enviar à Psicopedagogia", type="primary", icon=":material/add:"):
        erros = []
        if not dados["nome"] or not dados["curso"] or not dados["nee"]:
            erros.append("Preencha nome, curso e necessidades educacionais específicas.")
        if not codigos:
            erros.append("Informe ao menos um código de disciplina.")
        if erros:
            st.error(" ".join(erros))
            return
        try:
            if est is None:
                est = Estudante(campus_id=c.campus_id, **dados)
                s.add(est)
                s.flush()
            else:
                for k, v in dados.items():
                    setattr(est, k, v)
            pei = fluxo.criar_pei(s, est, sem, c.usuario_id, [(x, "") for x in codigos], prefill)
            s.commit()
        except fluxo.FluxoError as exc:
            s.rollback()
            st.error(str(exc))
            return
        st.session_state["pei_sel"] = pei.id
        st.session_state["msg"] = "PEI cadastrado e enviado à Psicopedagogia."
        for chave in [k for k in st.session_state.keys() if str(k).startswith("novo_")]:
            del st.session_state[chave]
        st.session_state["peis_modo"] = "lista"
        st.rerun()


# ---------------------------------------------------------------------------
# Detalhe
# ---------------------------------------------------------------------------
def _aba_resumo(pei: Pei) -> None:
    st.markdown(ui.dados_estudante_md(pei))
    st.markdown("**Componentes curriculares**")
    if not pei.componentes:
        st.caption("Nenhum componente vinculado.")
    s = db.s()
    for comp in pei.componentes:
        situacao = ":green-badge[Concluído]" if comp.status == "concluido" else ":orange-badge[Pendente]"
        if pei.status in ("psicopedagogia", "etep"):
            situacao = ":gray-badge[Aguardando Psicopedagogia/ETEP]"
        docentes = ", ".join(fluxo.docentes_do_componente(s, comp)) or ":red[sem docente associado]"
        st.markdown(f"- **{fluxo.rotulo_componente(s, comp)}** — {docentes} {situacao}")
    if pei.componentes:
        st.caption("Depois da ETEP, o PEI vai ao mesmo tempo para todos esses docentes.")
    if pei.prefill_origem:
        st.caption(f"Respostas pré-preenchidas a partir do PEI de {pei.prefill_origem}.")
    anteriores = list(s.scalars(select(Pei).join(Semestre).where(
        Pei.estudante_id == pei.estudante_id, Pei.id != pei.id).order_by(Semestre.codigo.desc())))
    if anteriores:
        st.markdown("**PEIs de outros semestres**")
        for p in anteriores:
            col1, col2 = st.columns([4, 1], vertical_alignment="center")
            col1.markdown(f"{p.semestre.codigo} · {ui.badge(p.status)}")
            if p.docx:
                col2.download_button("DOCX", p.docx, file_name=p.docx_nome or nome_arquivo(p),
                                     mime=MIME_DOCX, key=f"dl_ant_{p.id}", use_container_width=True)
    st.markdown("**Estudos individualizados** (cadastrados pelos docentes)")
    estudos.tabela(pei)


def _aba_respostas(pei: Pei) -> None:
    s = db.s()
    resp = fluxo.respostas(s, pei.id)
    for etapa in ("psicopedagogia", "etep"):
        with st.expander(ETAPAS[etapa], expanded=False):
            ui.mostrar_respostas(fluxo.perguntas(s, etapa, pei.id), resp)
    for comp in pei.componentes:
        with st.expander(f"Docente · {fluxo.rotulo_componente(s, comp)}"):
            ui.mostrar_respostas(fluxo.perguntas(s, "docente", pei.id), fluxo.respostas(s, pei.id, comp.id))
            st.markdown("**Estudos individualizados**")
            estudos.tabela(pei, comp.id)
    with st.expander(ETAPAS["gestao"]):
        ui.mostrar_respostas(fluxo.perguntas(s, "gestao", pei.id), resp)


def _aba_historico(pei: Pei) -> None:
    linhas = [{"Data": ui.data(h.criado_em, True), "Por": h.usuario.nome if h.usuario else "—",
               "Ação": h.acao, "Comentário": h.comentario} for h in reversed(pei.historico)]
    st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)


def _download(pei: Pei, rotulo: str, previa: bool = False) -> None:
    dados = gerar_docx(db.s(), pei) if previa else pei.docx
    if dados:
        st.download_button(rotulo, dados, file_name=("PREVIA_" if previa else "") + nome_arquivo(pei),
                           mime=MIME_DOCX, icon=":material/download:",
                           type="secondary" if previa else "primary", key=f"dl_{pei.id}_{previa}")


def _aba_acoes(pei: Pei) -> None:
    c = ui.ctx()
    s = db.s()
    sem_aberto = pei.semestre.status == "aberto"

    if pei.status in ("psicopedagogia", "etep", "docente"):
        st.info(f"Este PEI está com **{ui.com_quem(pei)}**. As ações de revisão ficam disponíveis "
                "quando todas as etapas forem concluídas.")
        _download(pei, "Baixar prévia do DOCX", previa=True)

    elif pei.status == "revisao":
        st.markdown("#### 1. Parecer da equipe")
        perguntas = fluxo.perguntas(s, "gestao")
        formulario.renderizar(perguntas, fluxo.respostas(s, pei.id), pei.id, None, bloqueado=not sem_aberto)
        if st.button("Salvar parecer", icon=":material/save:", disabled=not sem_aberto):
            formulario.salvar(perguntas, pei, None, c.usuario_id)
            s.commit()
            st.toast("Parecer salvo.")
        _download(pei, "Baixar prévia do DOCX", previa=True)

        st.markdown("#### 2. Devolver para correção")
        destinos = {"psicopedagogia": "Psicopedagogia", "etep": "ETEP"}
        if pei.componentes:
            destinos["docente"] = "Docente"
        col1, col2 = st.columns(2)
        destino = col1.selectbox("Devolver para", list(destinos), format_func=destinos.get, key="dev_dest")
        comp_id = None
        if destino == "docente":
            comp = ui.escolher("Componente", pei.componentes, onde=col2, key="dev_comp",
                               format_func=lambda x: f"{fluxo.rotulo_componente(s, x)} — "
                                                        f"{', '.join(fluxo.docentes_do_componente(s, x)) or 'sem docente'}")
            comp_id = comp.id
        comentario = st.text_area("O que precisa ser corrigido? *", key="dev_coment", height=80)
        cascata = False
        if destino == "docente":
            st.info("O PEI volta **apenas para o docente deste componente** e, depois de corrigido, "
                    "retorna direto para você.", icon=":material/info:")
        else:
            artigo = {"psicopedagogia": "a Psicopedagogia", "etep": "a ETEP"}[destino]
            st.info(f"O PEI volta **apenas para {artigo}** e, depois de corrigido, retorna "
                    "direto para você — **não** passa de novo pelas etapas seguintes.", icon=":material/info:")
            cascata = st.checkbox("Passar novamente pelas etapas seguintes depois da correção "
                                  + ("(ETEP e docentes)" if destino == "psicopedagogia" else "(docentes)"),
                                  key="dev_cascata")
        if st.button("Devolver para correção", icon=":material/undo:", disabled=not sem_aberto):
            try:
                fluxo.devolver(s, pei, c.usuario_id, destino, comentario, comp_id, cascata)
                s.commit()
                st.session_state["msg"] = "PEI devolvido para correção."
                st.rerun()
            except fluxo.FluxoError as exc:
                s.rollback()
                st.error(str(exc))

        st.markdown("#### 3. Aprovar")
        if not c.critico:
            st.caption("Somente o(a) gestor(a) pode aprovar o PEI.")
        else:
            st.caption("Ao aprovar, o DOCX final é gerado e o PEI fica aguardando o registro no SUAP.")
            if st.button("Aprovar PEI e gerar DOCX", type="primary", icon=":material/task_alt:",
                         disabled=not sem_aberto):
                formulario.salvar(perguntas, pei, None, c.usuario_id)
                try:
                    fluxo.aprovar(s, pei, c.usuario_id)
                    s.commit()
                    st.session_state["msg"] = "PEI aprovado! Baixe o DOCX, suba no SUAP e depois marque como registrado."
                    st.rerun()
                except fluxo.FluxoError as exc:
                    s.commit()  # mantém o parecer salvo
                    st.error(str(exc))

    elif pei.status == "aprovado":
        st.success(f"Aprovado em {ui.data(pei.aprovado_em, True)}. Próximos passos: baixe o DOCX, "
                   "cole o conteúdo no SUAP, colete as assinaturas e depois marque como registrado.")
        _download(pei, "Baixar DOCX aprovado")
        if c.critico:
            obs = st.text_input("Observação (opcional): nº do documento/processo no SUAP", key="reg_obs")
            col1, col2 = st.columns(2)
            if col1.button("Marcar como registrado no SUAP", type="primary", icon=":material/verified:",
                           use_container_width=True):
                fluxo.registrar(s, pei, c.usuario_id, obs)
                s.commit()
                st.session_state["msg"] = "PEI registrado."
                st.rerun()
            if col2.button("Desfazer aprovação (voltar à revisão)", use_container_width=True):
                fluxo.reabrir(s, pei, c.usuario_id, obs or "Aprovação desfeita pela gestão")
                s.commit()
                st.rerun()
        else:
            st.caption("Somente o(a) gestor(a) pode marcar o PEI como registrado.")

    elif pei.status == "registrado":
        st.success(f"Registrado no SUAP em {ui.data(pei.registrado_em, True)}.")
        _download(pei, "Baixar DOCX")

    elif pei.status == "cancelado":
        st.info("Este PEI foi cancelado.")

    if c.critico and pei.status not in STATUS_FINAIS and sem_aberto:
        with st.expander("Cancelar este PEI"):
            motivo = st.text_input("Motivo (ex.: estudante transferido)", key="canc_motivo")
            if st.button("Cancelar PEI", icon=":material/block:"):
                try:
                    fluxo.cancelar(s, pei, c.usuario_id, motivo)
                    s.commit()
                    st.rerun()
                except fluxo.FluxoError as exc:
                    st.error(str(exc))


def _aba_editar(pei: Pei) -> None:
    c = ui.ctx()
    s = db.s()
    editavel = pei.status not in {"aprovado", "registrado", "cancelado"} and pei.semestre.status == "aberto"
    if not editavel:
        st.info("Os dados não podem ser alterados neste estado.")
        return
    with st.form(f"form_est_{pei.id}"):
        st.markdown("**Dados do estudante**")
        dados = _campos_estudante(f"ed_{pei.id}_", pei.estudante)
        if st.form_submit_button("Salvar dados", icon=":material/save:"):
            if not dados["nome"]:
                st.error("Informe o nome.")
            else:
                for k, v in dados.items():
                    setattr(pei.estudante, k, v)
                fluxo.log(s, pei, c.usuario_id, "Dados do estudante atualizados")
                s.commit()
                st.toast("Dados salvos.")

    st.markdown("**Componentes curriculares (códigos das disciplinas)**")
    for comp in list(pei.componentes):
        col1, col2 = st.columns([5, 1], vertical_alignment="center")
        docentes = ", ".join(fluxo.docentes_do_componente(s, comp)) or ":red[sem docente associado]"
        col1.markdown(f"{fluxo.rotulo_componente(s, comp)} — {docentes}")
        if col2.button("Remover", key=f"rm_comp_{comp.id}"):
            fluxo.remover_componente(s, pei, comp, c.usuario_id)
            s.commit()
            st.rerun()
    cat = _catalogo(pei.semestre_id)
    col1, col2 = st.columns([4, 1], vertical_alignment="bottom")
    novo = col1.selectbox("Incluir código", sorted(set(cat) - {x.codigo for x in pei.componentes}),
                          index=None, accept_new_options=True, placeholder="Digite ou escolha o código",
                          format_func=lambda cod: f"{cod} — {cat[cod]}" if cat.get(cod) else cod,
                          key=f"add_cod_{pei.id}")
    if col2.button("Incluir", key=f"add_btn_{pei.id}", use_container_width=True):
        try:
            fluxo.adicionar_componente(s, pei, novo or "", "", c.usuario_id)
            s.commit()
            st.rerun()
        except fluxo.FluxoError as exc:
            s.rollback()
            st.error(str(exc))


def _aba_anexos(pei: Pei) -> None:
    c = ui.ctx()
    st.caption("Laudos (anexados pela Psicopedagogia) e documentos de apoio da ETEP e dos docentes "
               "(notificações, provas...). Aqui é só consulta: o NAPNE não anexa arquivos. São de uso "
               "interno e **não entram no DOCX**.")
    anexos.lista(pei, c.usuario_id, chave="det")
    anexos.anteriores(pei)


def _detalhe(pei: Pei) -> None:
    if st.button("← Voltar à lista"):
        st.session_state.pop("pei_sel", None)
        st.rerun()
    st.markdown(f"## {pei.estudante.nome}")
    corr = " :red-badge[Em correção]" if pei.em_correcao else ""
    st.markdown(f"{ui.badge(pei.status)}{corr} · PEI {pei.semestre.codigo} · com: {ui.com_quem(pei)}")
    n_anexos = len(fluxo.anexos(db.s(), pei.id))
    abas = st.tabs(["Revisão e ações", "Resumo", "Respostas", f"Anexos ({n_anexos})", "Histórico", "Editar dados"])
    with abas[0]:
        _aba_acoes(pei)
    with abas[1]:
        _aba_resumo(pei)
    with abas[2]:
        _aba_respostas(pei)
    with abas[3]:
        _aba_anexos(pei)
    with abas[4]:
        _aba_historico(pei)
    with abas[5]:
        _aba_editar(pei)


# ---------------------------------------------------------------------------
def pagina() -> None:
    c = ui.ctx()
    s = db.s()
    if msg := st.session_state.pop("msg", None):
        st.success(msg)

    sel = st.session_state.get("pei_sel")
    if sel:
        pei = s.get(Pei, sel)
        if pei and pei.campus_id == c.campus_id:
            _detalhe(pei)
            return
        st.session_state.pop("pei_sel", None)

    ui.cabecalho("PEIs", f"NAPNE {c.campus_nome}")
    semestres = list(s.scalars(select(Semestre).where(Semestre.campus_id == c.campus_id)
                               .order_by(Semestre.codigo.desc())))
    if not semestres:
        st.info("Crie primeiro um semestre letivo em **Semestres**." if c.critico
                else "Nenhum semestre aberto. Peça ao(à) gestor(a) para criar o semestre.")
        return
    aberto = next((x for x in semestres if x.status == "aberto"), semestres[0])

    col1, col2, col3 = st.columns([1, 2, 2], vertical_alignment="bottom")
    sem = ui.escolher("Semestre", semestres, onde=col1, index=semestres.index(aberto),
                      format_func=lambda x: x.codigo + (" (encerrado)" if x.status != "aberto" else ""))
    busca = col2.text_input("Buscar estudante", placeholder="nome ou matrícula")
    filtro = col3.multiselect("Etapa", list(STATUS), format_func=STATUS_CURTO.get, placeholder="Todas")

    novo = st.session_state.get("peis_modo") == "novo"
    if sem.status == "aberto":
        if st.button("Fechar cadastro" if novo else "Novo PEI", icon=":material/close:" if novo else ":material/add:",
                     type="secondary" if novo else "primary"):
            st.session_state["peis_modo"] = "lista" if novo else "novo"
            st.rerun()
        if novo:
            with st.container(border=True):
                _novo_pei(sem)
    else:
        st.caption("Semestre encerrado: somente consulta.")

    peis = list(s.scalars(select(Pei).join(Estudante).where(Pei.semestre_id == sem.id).order_by(Estudante.nome)))
    if busca:
        b = busca.lower()
        peis = [p for p in peis if b in p.estudante.nome.lower() or b in (p.estudante.matricula or "").lower()]
    if filtro:
        peis = [p for p in peis if p.status in filtro]
    if not peis:
        st.info("Nenhum PEI encontrado.")
        return

    df = pd.DataFrame([{
        "id": p.id,
        "Estudante": p.estudante.nome,
        "Disciplinas": ", ".join(x.codigo for x in p.componentes),
        "Etapa": STATUS_CURTO[p.status] + (" (correção)" if p.em_correcao else ""),
        "Com quem": ui.com_quem(p),
        "Atualizado": ui.data(p.atualizado_em),
    } for p in peis])
    st.caption("Clique em uma linha para abrir o PEI.")
    evento = st.dataframe(df.drop(columns="id"), hide_index=True, use_container_width=True,
                          on_select="rerun", selection_mode="single-row", key=f"tab_peis_{sem.id}")
    linhas = evento.selection.rows if evento else []
    if linhas:
        st.session_state["pei_sel"] = int(df.iloc[linhas[0]]["id"])
        st.session_state.pop(f"tab_peis_{sem.id}", None)
        st.rerun()
