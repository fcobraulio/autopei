"""Renderização dos formulários dinâmicos de perguntas."""
from __future__ import annotations

import streamlit as st

from core import db, fluxo
from core.models import Pei, Pergunta, Resposta


def _k(pei_id: int, comp_id: int | None, pid: int) -> str:
    return f"q_{pei_id}_{comp_id or 0}_{pid}"


def renderizar(perguntas: list[Pergunta], resp: dict[int, Resposta], pei_id: int,
               comp_id: int | None, bloqueado: bool = False) -> None:
    """Desenha as perguntas com os valores salvos como padrão."""
    secao = None
    for p in perguntas:
        if p.secao != secao:
            secao = p.secao
            st.markdown(f"##### {secao}")
        r = resp.get(p.id)
        v = (r.valor or {}).get("v") if r else None
        k = _k(pei_id, comp_id, p.id)
        rotulo = p.enunciado + (" *" if p.obrigatoria else "")
        ajuda = p.ajuda or None

        if p.tipo == "longa":
            nada = st.session_state.get(k + "_nada", bool(r and r.nada_declarar))
            if nada:
                st.text_area(rotulo, value=p.texto_nada or "Nada a declarar.", disabled=True,
                             key=k + "_auto", help=ajuda)
            else:
                st.text_area(rotulo, value=v if isinstance(v, str) else "", key=k,
                             disabled=bloqueado, help=ajuda, height=110)
            st.checkbox("Nada a declarar", value=bool(r and r.nada_declarar), key=k + "_nada",
                        disabled=bloqueado)
        elif p.tipo == "radio":
            st.radio(rotulo, p.opcoes, index=p.opcoes.index(v) if v in p.opcoes else None,
                     key=k, horizontal=len(p.opcoes) <= 4, disabled=bloqueado, help=ajuda)
        elif p.tipo == "select":
            st.selectbox(rotulo, p.opcoes, index=p.opcoes.index(v) if v in p.opcoes else None,
                         key=k, placeholder="Selecione…", disabled=bloqueado, help=ajuda)
        elif p.tipo == "checkbox":
            marcados = v if isinstance(v, list) else []
            st.markdown(rotulo, help=ajuda)
            colunas = st.columns(2)
            for i, opcao in enumerate(p.opcoes):
                colunas[i % 2].checkbox(opcao, value=opcao in marcados, key=f"{k}_{i}",
                                        disabled=bloqueado)
        if r is not None and r.origem:
            st.caption(f":orange[↺ Resposta trazida do PEI de {r.origem}. Revise e ajuste se mudou.]")
        st.write("")


def salvar(perguntas: list[Pergunta], pei: Pei, comp_id: int | None, usuario_id: int) -> None:
    ss = st.session_state
    s = db.s()
    for p in perguntas:
        k = _k(pei.id, comp_id, p.id)
        if p.tipo == "longa":
            nada = bool(ss.get(k + "_nada", False))
            texto = ss.get(k)
            if texto is None:  # campo oculto (estava em "nada a declarar"): mantém o salvo
                antigo = fluxo.respostas(s, pei.id, comp_id).get(p.id)
                texto = (antigo.valor or {}).get("v", "") if antigo else ""
            fluxo.salvar_resposta(s, pei, p, comp_id, texto or "", nada, usuario_id)
        elif p.tipo == "checkbox":
            marcados = [o for i, o in enumerate(p.opcoes) if ss.get(f"{k}_{i}")]
            fluxo.salvar_resposta(s, pei, p, comp_id, marcados, False, usuario_id)
        else:
            fluxo.salvar_resposta(s, pei, p, comp_id, ss.get(k) or "", False, usuario_id)
    s.flush()


def limpar(pei_id: int, comp_id: int | None) -> None:
    prefixo = f"q_{pei_id}_{comp_id or 0}_"
    for chave in [c for c in st.session_state.keys() if str(c).startswith(prefixo)]:
        del st.session_state[chave]
