"""Componentes visuais compartilhados entre as páginas."""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from core import config
from core.auth import Contexto
from core.models import ETAPAS, STATUS, STATUS_CURTO, Pei, Pergunta, Resposta

COR_STATUS = {
    "psicopedagogia": "violet",
    "etep": "blue",
    "docente": "orange",
    "revisao": "red",
    "aprovado": "primary",
    "registrado": "green",
    "cancelado": "gray",
}


def ctx() -> Contexto:
    return st.session_state["ctx"]


def escolher(label: str, objetos: list, format_func, *, onde=None, index: int | None = 0, **kw):
    """Selectbox de registros do banco que devolve SEMPRE o objeto da sessão atual.

    O st.selectbox guarda o valor escolhido entre execuções da página; se as opções forem
    objetos do SQLAlchemy, ele pode devolver a instância de uma execução anterior (de outra
    sessão do banco). Alterar ou excluir essa instância falha ("another instance with key ...
    is already present") ou simplesmente não grava. Por isso as opções são os ids.
    """
    mapa = {o.id: o for o in objetos}
    oid = (onde or st).selectbox(
        label, list(mapa), index=index if objetos else None,
        format_func=lambda i: format_func(mapa[i]) if i in mapa else str(i), **kw)
    return mapa.get(oid)


def logo_svg(largura: int = 180) -> str:
    svg = (config.ASSETS_DIR / "logo.svg").read_text()
    return svg.replace('width="200" height="48"', f'width="{largura}" height="{int(largura * 0.24)}"')


def badge(status: str, curto: bool = False) -> str:
    rot = STATUS_CURTO[status] if curto else STATUS[status]
    return f":{COR_STATUS.get(status, 'gray')}-badge[{rot}]"


def data(dt: datetime | None, hora: bool = False) -> str:
    if not dt:
        return "—"
    return dt.strftime("%d/%m/%Y %H:%M" if hora else "%d/%m/%Y")


def dias_desde(dt: datetime | None) -> int:
    return (datetime.now() - dt).days if dt else 0


def com_quem(pei: Pei) -> str:
    if pei.status == "docente":
        from core import db, fluxo

        nomes = []
        for c in pei.componentes:
            if c.status == "pendente":
                nomes += fluxo.docentes_do_componente(db.s(), c) or [f"{c.codigo}: sem docente"]
        return ", ".join(dict.fromkeys(nomes)) or "Docentes"
    if pei.status in ("revisao", "aprovado"):
        return "Gestão NAPNE"
    if pei.status in ("psicopedagogia", "etep"):
        return ETAPAS[pei.status]
    return "—"


def cabecalho(titulo: str, subtitulo: str = "") -> None:
    st.markdown(f"## {titulo}")
    if subtitulo:
        st.caption(subtitulo)


def ultimo_comentario_correcao(pei: Pei) -> str:
    for h in reversed(pei.historico):
        if h.acao.startswith("Devolvido para correção"):
            return h.comentario
    return ""


def valor_resposta_md(p: Pergunta, r: Resposta | None) -> str:
    if r is None:
        return "_Não respondido._"
    if r.nada_declarar:
        return f"_{p.texto_nada or 'Nada a declarar.'}_"
    v = (r.valor or {}).get("v")
    if isinstance(v, list):
        return "\n".join(f"- {i}" for i in v) if v else "_Não respondido._"
    v = str(v or "").strip()
    return v.replace("\n", "  \n") if v else "_Não respondido._"


def mostrar_respostas(perguntas: list[Pergunta], resp: dict[int, Resposta]) -> None:
    secao = None
    for p in perguntas:
        if p.secao != secao:
            secao = p.secao
            st.markdown(f"**{secao.upper()}**")
        st.markdown(f"<span style='color:#5f6b66'>{p.enunciado}</span>", unsafe_allow_html=True)
        st.markdown(valor_resposta_md(p, resp.get(p.id)))


def dados_estudante_md(pei: Pei, com_nome: bool = True) -> str:
    e = pei.estudante
    idade = ""
    if e.data_nascimento:
        hoje = datetime.now().date()
        anos = hoje.year - e.data_nascimento.year - (
            (hoje.month, hoje.day) < (e.data_nascimento.month, e.data_nascimento.day))
        idade = f" · {anos} anos"
    linhas = [
        f"**{e.nome}**{idade}" if com_nome else f"Matrícula {e.matricula or '—'}{idade}",
        f"{e.curso or 'Curso não informado'} · {e.periodo or '—'} · {e.turno or '—'}",
        f"NEE: {e.nee or 'não informado'}",
    ]
    return "  \n".join(linhas)
