"""Regras do fluxo do PEI.

Fluxo normal:

    psicopedagogia ─► etep ─► docentes (em paralelo) ─► revisao ─► aprovado ─► registrado

* Cada estudante tem UMA etapa de Psicopedagogia e UMA de ETEP.
* Depois da ETEP, o PEI é distribuído **ao mesmo tempo** para todos os docentes das
  disciplinas (códigos) do estudante — cada docente preenche o seu componente.
  Ele só segue para a revisão quando **todos** os componentes forem concluídos.
* Os docentes de cada código vêm da tabela de Ofertas do semestre (código → docente).
  Se um código ainda não tiver docente, o componente aparece como "sem docente" no
  painel e cai na caixa do docente assim que a gestão fizer a associação.

Correções: a gestão devolve o PEI para UMA etapa (Psicopedagogia, ETEP ou um docente).
O PEI volta apenas para essa etapa e, ao ser reenviado, retorna **direto para a revisão**
(``em_correcao=True``). Se a gestão marcar explicitamente "passar novamente pelas etapas
seguintes", o fluxo normal é retomado a partir da etapa escolhida.
"""
from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    DIAS_SEMANA,
    FREQUENCIAS,
    HORAS_ESTUDO,
    STATUS_FINAIS,
    Anexo,
    Componente,
    Estudante,
    EstudoIndividualizado,
    Historico,
    Oferta,
    Pei,
    Pergunta,
    Resposta,
    Semestre,
    Usuario,
)


class FluxoError(Exception):
    pass


NOME_ETAPA = {"psicopedagogia": "Psicopedagogia", "etep": "ETEP", "docente": "Docente"}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def log(s: Session, pei: Pei, usuario_id: int | None, acao: str,
        de: str = "", para: str = "", comentario: str = "") -> None:
    s.add(Historico(pei_id=pei.id, usuario_id=usuario_id, acao=acao[:300],
                    de_status=de, para_status=para, comentario=comentario or ""))


def _mudar_status(s: Session, pei: Pei, novo: str, usuario_id: int | None, acao: str,
                  comentario: str = "") -> None:
    antigo = pei.status
    pei.status = novo
    pei.atualizado_em = datetime.now()
    log(s, pei, usuario_id, acao, antigo, novo, comentario)


def perguntas(s: Session, etapa: str, incluir_inativas_do_pei: int | None = None) -> list[Pergunta]:
    q = select(Pergunta).where(Pergunta.etapa == etapa)
    if incluir_inativas_do_pei:
        respondidas = select(Resposta.pergunta_id).where(Resposta.pei_id == incluir_inativas_do_pei)
        q = q.where(Pergunta.ativo | Pergunta.id.in_(respondidas))
    else:
        q = q.where(Pergunta.ativo)
    return list(s.scalars(q.order_by(Pergunta.ordem, Pergunta.id)))


def respostas(s: Session, pei_id: int, componente_id: int | None = None) -> dict[int, Resposta]:
    q = select(Resposta).where(Resposta.pei_id == pei_id)
    q = q.where(Resposta.componente_id.is_(None) if componente_id is None
                else Resposta.componente_id == componente_id)
    return {r.pergunta_id: r for r in s.scalars(q)}


def salvar_resposta(s: Session, pei: Pei, pergunta: Pergunta, componente_id: int | None,
                    valor, nada: bool, usuario_id: int) -> None:
    atual = respostas(s, pei.id, componente_id).get(pergunta.id)
    nada = bool(nada) and pergunta.tipo == "longa"
    if atual is None:
        atual = Resposta(pei_id=pei.id, componente_id=componente_id, pergunta_id=pergunta.id, origem="")
        s.add(atual)
    elif (atual.valor or {}).get("v") == valor and atual.nada_declarar == nada:
        return  # nada mudou: mantém autor e a marca de pré-preenchimento
    atual.valor = {"v": valor}
    atual.nada_declarar = nada
    atual.origem = ""  # foi revisada/alterada
    atual.usuario_id = usuario_id
    atual.atualizado_em = datetime.now()


def preenchida(r: Resposta | None) -> bool:
    if r is None:
        return False
    if r.nada_declarar:
        return True
    v = (r.valor or {}).get("v")
    if isinstance(v, list):
        return len(v) > 0
    return bool(str(v or "").strip())


def faltantes(s: Session, pei: Pei, etapa: str, componente_id: int | None = None) -> list[str]:
    resp = respostas(s, pei.id, componente_id)
    return [p.enunciado for p in perguntas(s, etapa) if p.obrigatoria and not preenchida(resp.get(p.id))]


# ---------------------------------------------------------------------------
# Ofertas (código da disciplina → docentes)
# ---------------------------------------------------------------------------
def ofertas_do_codigo(s: Session, semestre_id: int, codigo: str) -> list[Oferta]:
    return list(s.scalars(select(Oferta).where(Oferta.semestre_id == semestre_id, Oferta.codigo == codigo)
                          .order_by(Oferta.docente_nome)))


def nome_disciplina(s: Session, comp: Componente) -> str:
    if comp.disciplina:
        return comp.disciplina
    for o in ofertas_do_codigo(s, comp.pei.semestre_id, comp.codigo):
        if o.disciplina:
            return o.disciplina
    return ""


def rotulo_componente(s: Session, comp: Componente) -> str:
    nome = nome_disciplina(s, comp)
    return f"{comp.codigo} — {nome}" if nome else comp.codigo


def docentes_do_componente(s: Session, comp: Componente) -> list[str]:
    """Nomes dos docentes do componente (pela oferta do semestre)."""
    nomes = []
    for o in ofertas_do_codigo(s, comp.pei.semestre_id, comp.codigo):
        u = s.scalar(select(Usuario).where(Usuario.username == o.docente_matricula))
        nomes.append((u.nome if u else "") or o.docente_nome or o.docente_matricula)
    return nomes


def docente_do_componente(s: Session, comp: Componente, username: str) -> bool:
    return any(o.docente_matricula == username for o in ofertas_do_codigo(s, comp.pei.semestre_id, comp.codigo))


def salvar_oferta(s: Session, semestre_id: int, codigo: str, disciplina: str,
                  docente_matricula: str, docente_nome: str = "") -> Oferta:
    codigo, docente_matricula = codigo.strip().upper(), docente_matricula.strip().lower()
    if not codigo or not docente_matricula:
        raise FluxoError("Informe o código da disciplina e a matrícula SUAP do docente.")
    o = s.scalar(select(Oferta).where(Oferta.semestre_id == semestre_id, Oferta.codigo == codigo,
                                      Oferta.docente_matricula == docente_matricula))
    if o is None:
        o = Oferta(semestre_id=semestre_id, codigo=codigo, docente_matricula=docente_matricula)
        s.add(o)
    if disciplina.strip():
        o.disciplina = disciplina.strip()
        for outra in ofertas_do_codigo(s, semestre_id, codigo):  # mantém o nome consistente
            outra.disciplina = disciplina.strip()
    if docente_nome.strip():
        o.docente_nome = docente_nome.strip()
    s.flush()
    return o


def importar_ofertas(s: Session, semestre_id: int, texto: str) -> tuple[int, list[str]]:
    """Linhas no formato  codigo; disciplina; matricula_docente; nome_docente (opcional)."""
    ok, erros = 0, []
    for n, linha in enumerate(texto.splitlines(), start=1):
        if not linha.strip():
            continue
        partes = [p.strip() for p in re.split(r"[;\t]", linha)]
        if len(partes) < 3:
            erros.append(f"Linha {n}: use  código; disciplina; matrícula do docente")
            continue
        try:
            salvar_oferta(s, semestre_id, partes[0], partes[1], partes[2], partes[3] if len(partes) > 3 else "")
            ok += 1
        except FluxoError as exc:
            erros.append(f"Linha {n}: {exc}")
    return ok, erros


# ---------------------------------------------------------------------------
# Semestres e criação do PEI
# ---------------------------------------------------------------------------
def semestre_aberto(s: Session, campus_id: int) -> Semestre | None:
    return s.scalar(select(Semestre).where(Semestre.campus_id == campus_id, Semestre.status == "aberto")
                    .order_by(Semestre.codigo.desc()))


def criar_semestre(s: Session, campus_id: int, codigo: str) -> Semestre:
    codigo = codigo.strip()
    if not re.fullmatch(r"\d{4}\.[12]", codigo):
        raise FluxoError("Use o formato AAAA.S, por exemplo 2026.2.")
    if s.scalar(select(Semestre.id).where(Semestre.campus_id == campus_id, Semestre.codigo == codigo)):
        raise FluxoError(f"O semestre {codigo} já existe neste campus.")
    sem = Semestre(campus_id=campus_id, codigo=codigo)
    s.add(sem)
    s.flush()
    return sem


def pei_anterior(s: Session, estudante_id: int, semestre: Semestre) -> Pei | None:
    return s.scalar(select(Pei).join(Semestre).where(
        Pei.estudante_id == estudante_id, Semestre.codigo < semestre.codigo, Pei.status != "cancelado")
        .order_by(Semestre.codigo.desc()))


def _prefill(s: Session, novo: Pei, anterior: Pei) -> int:
    """Copia as respostas de Psicopedagogia, ETEP e dos docentes (mesmo código de disciplina)."""
    n = 0
    etapas = {p.id: p.etapa for p in s.scalars(select(Pergunta).where(Pergunta.ativo))}
    comp_novo = {c.codigo: c.id for c in novo.componentes}
    comp_antigo = {c.id: c.codigo for c in anterior.componentes}
    for r in s.scalars(select(Resposta).where(Resposta.pei_id == anterior.id)):
        etapa = etapas.get(r.pergunta_id)
        if etapa in ("psicopedagogia", "etep") and r.componente_id is None:
            destino = None
        elif etapa == "docente" and comp_antigo.get(r.componente_id) in comp_novo:
            destino = comp_novo[comp_antigo[r.componente_id]]
        else:
            continue
        s.add(Resposta(pei_id=novo.id, componente_id=destino, pergunta_id=r.pergunta_id,
                       valor=r.valor, nada_declarar=r.nada_declarar, origem=anterior.semestre.codigo))
        n += 1
    novo.prefill_origem = anterior.semestre.codigo
    return n


def criar_pei(s: Session, estudante: Estudante, semestre: Semestre, usuario_id: int,
              codigos: list[tuple[str, str]], pre_preencher: bool = True) -> Pei:
    """codigos: lista de (código, nome da disciplina — opcional)."""
    if semestre.status != "aberto":
        raise FluxoError("O semestre está encerrado.")
    if s.scalar(select(Pei.id).where(Pei.estudante_id == estudante.id, Pei.semestre_id == semestre.id)):
        raise FluxoError("Este estudante já possui PEI neste semestre.")
    pei = Pei(estudante_id=estudante.id, semestre_id=semestre.id, campus_id=estudante.campus_id,
              status="psicopedagogia", criado_por_id=usuario_id)
    s.add(pei)
    s.flush()
    vistos = set()
    for codigo, nome in codigos:
        codigo = codigo.strip().upper()
        if codigo and codigo not in vistos:
            vistos.add(codigo)
            s.add(Componente(pei_id=pei.id, codigo=codigo, disciplina=(nome or "").strip()))
    s.flush()
    s.refresh(pei)
    log(s, pei, usuario_id, "PEI cadastrado e enviado à Psicopedagogia", "", "psicopedagogia")
    if pre_preencher and (ant := pei_anterior(s, estudante.id, semestre)):
        n = _prefill(s, pei, ant)
        if n:
            log(s, pei, usuario_id, f"Respostas pré-preenchidas a partir do PEI de {ant.semestre.codigo} ({n})")
    s.flush()
    return pei


def adicionar_componente(s: Session, pei: Pei, codigo: str, nome: str, usuario_id: int) -> None:
    if pei.status in {"aprovado", "registrado", "cancelado"}:
        raise FluxoError("Não é possível alterar componentes de um PEI aprovado, registrado ou cancelado.")
    codigo = codigo.strip().upper()
    if not codigo:
        raise FluxoError("Informe o código da disciplina.")
    if any(c.codigo == codigo for c in pei.componentes):
        raise FluxoError("Este código já está no PEI.")
    s.add(Componente(pei_id=pei.id, codigo=codigo, disciplina=nome.strip()))
    log(s, pei, usuario_id, f"Componente incluído: {codigo}")
    if pei.status == "revisao":  # o novo docente precisa preencher antes da revisão
        pei.em_correcao = True
        _mudar_status(s, pei, "docente", usuario_id, "PEI voltou aos docentes (novo componente)")
    s.flush()


def remover_componente(s: Session, pei: Pei, comp: Componente, usuario_id: int) -> None:
    if pei.status in {"aprovado", "registrado", "cancelado"}:
        raise FluxoError("Não é possível alterar componentes de um PEI aprovado, registrado ou cancelado.")
    log(s, pei, usuario_id, f"Componente removido: {comp.codigo}")
    s.delete(comp)
    s.flush()
    s.refresh(pei)
    if pei.status == "docente" and all(c.status == "concluido" for c in pei.componentes):
        pei.em_correcao = False
        _mudar_status(s, pei, "revisao", usuario_id, "Todos os docentes concluíram")


# ---------------------------------------------------------------------------
# Envio das etapas
# ---------------------------------------------------------------------------
def _distribuir_docentes(s: Session, pei: Pei, usuario_id: int, acao: str) -> str:
    """Envia o PEI, em paralelo, para os docentes de todos os componentes."""
    if not pei.componentes:
        _mudar_status(s, pei, "revisao", usuario_id, acao + " (sem componentes: direto à revisão)")
        return "revisao"
    for c in pei.componentes:
        c.status, c.concluido_em, c.concluido_por_id = "pendente", None, None
    _mudar_status(s, pei, "docente", usuario_id,
                  acao + f" — distribuído em paralelo para {len(pei.componentes)} componente(s)")
    return "docente"


def enviar(s: Session, pei: Pei, etapa: str, usuario: Usuario, componente: Componente | None = None) -> str:
    """Conclui a etapa do usuário. Retorna o novo status do PEI."""
    if pei.status != etapa:
        raise FluxoError("Este PEI não está mais aguardando esta etapa.")
    falta = faltantes(s, pei, etapa, componente.id if componente else None)
    if falta:
        raise FluxoError("Responda as perguntas obrigatórias: " + "; ".join(falta))

    if etapa in ("psicopedagogia", "etep"):
        acao = f"{NOME_ETAPA[etapa]} concluiu o preenchimento"
        if pei.em_correcao:  # correção pontual: volta direto para a revisão
            pei.em_correcao = False
            _mudar_status(s, pei, "revisao", usuario.id, acao + " (correção) — volta à revisão")
            return "revisao"
        if etapa == "psicopedagogia":
            _mudar_status(s, pei, "etep", usuario.id, acao)
            return "etep"
        return _distribuir_docentes(s, pei, usuario.id, acao)

    if etapa == "docente":
        if componente is None or componente.pei_id != pei.id or componente.status != "pendente":
            raise FluxoError("Componente inválido ou já concluído.")
        if not docente_do_componente(s, componente, usuario.username):
            raise FluxoError("Você não está associado(a) a esta disciplina.")
        componente.status = "concluido"
        componente.concluido_em = datetime.now()
        componente.concluido_por_id = usuario.id
        log(s, pei, usuario.id, f"Docente concluiu: {rotulo_componente(s, componente)}")
        s.flush()
        pendentes = [c for c in pei.componentes if c.status != "concluido"]
        if not pendentes:
            pei.em_correcao = False
            _mudar_status(s, pei, "revisao", usuario.id, "Todos os docentes concluíram")
        return pei.status

    raise FluxoError("Etapa inválida.")


# ---------------------------------------------------------------------------
# Revisão, aprovação e registro
# ---------------------------------------------------------------------------
def devolver(s: Session, pei: Pei, usuario_id: int, destino: str, comentario: str,
             componente_id: int | None = None, cascata: bool = False) -> None:
    """Devolve para correção. Por padrão, volta só para quem recebeu e depois direto à revisão.

    cascata=True: o PEI passa novamente pelas etapas seguintes (decisão explícita da gestão).
    """
    if pei.status != "revisao":
        raise FluxoError("Só é possível devolver PEIs que estão em revisão.")
    if not comentario.strip():
        raise FluxoError("Explique o que precisa ser corrigido.")
    if destino not in ("psicopedagogia", "etep", "docente"):
        raise FluxoError("Destino inválido.")
    if destino == "docente":
        alvos = [c for c in pei.componentes if componente_id in (None, c.id)]
        if not alvos:
            raise FluxoError("Escolha o componente/docente.")
        for c in alvos:
            c.status, c.concluido_em, c.concluido_por_id = "pendente", None, None
        quem = ", ".join(rotulo_componente(s, c) for c in alvos)
        cascata = False  # os docentes são a última etapa antes da revisão
    else:
        quem = NOME_ETAPA[destino]
    pei.em_correcao = not cascata
    sufixo = " (passará novamente pelas etapas seguintes)" if cascata else " (volta direto à revisão)"
    _mudar_status(s, pei, destino, usuario_id, f"Devolvido para correção: {quem}{sufixo}", comentario)


def aprovar(s: Session, pei: Pei, usuario_id: int) -> None:
    from .docx_pei import gerar_docx, nome_arquivo

    if pei.status != "revisao":
        raise FluxoError("Só é possível aprovar PEIs em revisão.")
    falta = faltantes(s, pei, "gestao")
    if falta:
        raise FluxoError("Preencha antes de aprovar: " + "; ".join(falta))
    pei.aprovado_em = datetime.now()
    pei.aprovado_por_id = usuario_id
    _mudar_status(s, pei, "aprovado", usuario_id, "PEI aprovado e DOCX gerado")
    s.flush()
    pei.docx = gerar_docx(s, pei)
    pei.docx_nome = nome_arquivo(pei)


def registrar(s: Session, pei: Pei, usuario_id: int, comentario: str = "") -> None:
    if pei.status != "aprovado":
        raise FluxoError("Só é possível registrar PEIs aprovados.")
    pei.registrado_em = datetime.now()
    pei.registrado_por_id = usuario_id
    _mudar_status(s, pei, "registrado", usuario_id, "Registrado no SUAP (assinaturas concluídas)", comentario)


def reabrir(s: Session, pei: Pei, usuario_id: int, comentario: str) -> None:
    if pei.status != "aprovado":
        raise FluxoError("Só é possível reabrir PEIs aprovados e ainda não registrados.")
    pei.docx = None
    pei.aprovado_em = None
    pei.aprovado_por_id = None
    _mudar_status(s, pei, "revisao", usuario_id, "Aprovação desfeita; PEI voltou à revisão", comentario)


def cancelar(s: Session, pei: Pei, usuario_id: int, comentario: str) -> None:
    if pei.status in STATUS_FINAIS:
        raise FluxoError("Este PEI já está finalizado.")
    if not comentario.strip():
        raise FluxoError("Informe o motivo do cancelamento.")
    _mudar_status(s, pei, "cancelado", usuario_id, "PEI cancelado", comentario)


def pendencias_semestre(s: Session, semestre: Semestre) -> int:
    return s.scalar(select(func.count(Pei.id)).where(
        Pei.semestre_id == semestre.id, Pei.status.notin_(STATUS_FINAIS))) or 0


def encerrar_semestre(s: Session, semestre: Semestre, usuario_id: int) -> None:
    if semestre.status != "aberto":
        raise FluxoError("O semestre já está encerrado.")
    n = pendencias_semestre(s, semestre)
    if n:
        raise FluxoError(f"Ainda há {n} PEI(s) não registrados ou cancelados neste semestre.")
    semestre.status = "encerrado"
    semestre.encerrado_em = datetime.now()
    semestre.encerrado_por_id = usuario_id


def reabrir_semestre(s: Session, semestre: Semestre) -> None:
    semestre.status = "aberto"
    semestre.encerrado_em = None
    semestre.encerrado_por_id = None


# ---------------------------------------------------------------------------
# Estudos individualizados (cadastrados pelos docentes)
# ---------------------------------------------------------------------------
def _ordem_estudo(e: EstudoIndividualizado):
    return (list(FREQUENCIAS).index(e.frequencia) if e.frequencia in FREQUENCIAS else 9,
            DIAS_SEMANA.index(e.dia) if e.dia in DIAS_SEMANA else 9, e.hora)


def estudos(s: Session, pei_id: int, componente_id: int | None = None) -> list[EstudoIndividualizado]:
    q = select(EstudoIndividualizado).where(EstudoIndividualizado.pei_id == pei_id)
    if componente_id is not None:
        q = q.where(EstudoIndividualizado.componente_id == componente_id)
    itens = list(s.scalars(q))
    ordem_comp = {c: i for i, c in enumerate(s.scalars(
        select(Componente.id).where(Componente.pei_id == pei_id).order_by(Componente.id)))}
    return sorted(itens, key=lambda e: (ordem_comp.get(e.componente_id, 0), *_ordem_estudo(e)))


def adicionar_estudo(s: Session, pei: Pei, comp: Componente, usuario_id: int, dia: str, hora: int,
                     frequencia: str, local: str = "") -> EstudoIndividualizado:
    if pei.status != "docente" or comp.status != "pendente" or comp.pei_id != pei.id:
        raise FluxoError("Os estudos individualizados só podem ser alterados enquanto o componente "
                         "está com o docente.")
    if dia not in DIAS_SEMANA or hora not in HORAS_ESTUDO or frequencia not in FREQUENCIAS:
        raise FluxoError("Escolha dia, horário e frequência.")
    if any(e.dia == dia and e.hora == hora for e in estudos(s, pei.id, comp.id)):
        raise FluxoError(f"Já existe um estudo individualizado na {dia.lower()} às {hora}h neste componente.")
    e = EstudoIndividualizado(pei_id=pei.id, componente_id=comp.id, dia=dia, hora=hora,
                              frequencia=frequencia, local=(local or "").strip()[:200], usuario_id=usuario_id)
    s.add(e)
    log(s, pei, usuario_id, f"Estudo individualizado incluído ({comp.codigo}): {dia} {hora}h, {frequencia}")
    s.flush()
    return e


def remover_estudo(s: Session, pei: Pei, estudo: EstudoIndividualizado, usuario_id: int) -> None:
    comp = s.get(Componente, estudo.componente_id)
    if pei.status != "docente" or comp is None or comp.status != "pendente":
        raise FluxoError("Os estudos individualizados só podem ser alterados enquanto o componente "
                         "está com o docente.")
    log(s, pei, usuario_id, f"Estudo individualizado removido ({comp.codigo}): {estudo.dia} {estudo.hora}h")
    s.delete(estudo)
    s.flush()


# ---------------------------------------------------------------------------
# Anexos
# ---------------------------------------------------------------------------
def anexar(s: Session, pei: Pei, etapa: str, usuario_id: int, nome: str, mime: str, dados: bytes,
           descricao: str = "", componente_id: int | None = None, max_mb: int = 10) -> Anexo:
    # Gestão e auxiliares só cadastram os dados do estudante; laudos vêm da Psicopedagogia.
    if etapa not in NOME_ETAPA:
        raise FluxoError("Anexos são incluídos pela Psicopedagogia, ETEP ou docentes durante o preenchimento.")
    if pei.status != etapa:
        raise FluxoError("Só é possível anexar arquivos enquanto o PEI está na sua etapa.")
    if len(dados) > max_mb * 1024 * 1024:
        raise FluxoError(f"O arquivo passa de {max_mb} MB.")
    a = Anexo(pei_id=pei.id, componente_id=componente_id, etapa=etapa, nome_arquivo=nome[:255],
              mime=mime or "application/octet-stream", tamanho=len(dados), descricao=descricao[:300],
              dados=dados, usuario_id=usuario_id)
    s.add(a)
    log(s, pei, usuario_id, f"Anexo incluído ({NOME_ETAPA.get(etapa, etapa)}): {nome}")
    s.flush()
    return a


def anexos(s: Session, pei_id: int) -> list[Anexo]:
    return list(s.scalars(select(Anexo).where(Anexo.pei_id == pei_id).order_by(Anexo.criado_em)))


# ---------------------------------------------------------------------------
# Caixas de pendências
# ---------------------------------------------------------------------------
def caixa(s: Session, usuario: Usuario, perfis_por_campus: dict[int, set[str]],
          docente: bool) -> list[tuple[str, Pei, Componente | None]]:
    """Itens pendentes do usuário: (etapa, pei, componente)."""
    itens: list[tuple[str, Pei, Componente | None]] = []
    for etapa in ("psicopedagogia", "etep"):
        campi = [cid for cid, perfis in perfis_por_campus.items() if etapa in perfis]
        if campi:
            for pei in s.scalars(select(Pei).join(Semestre).where(
                    Pei.campus_id.in_(campi), Pei.status == etapa, Semestre.status == "aberto")
                    .order_by(Pei.atualizado_em)):
                itens.append((etapa, pei, None))
    if docente:
        meus = select(Oferta.id).where(Oferta.semestre_id == Pei.semestre_id, Oferta.codigo == Componente.codigo,
                                       Oferta.docente_matricula == usuario.username).exists()
        for comp in s.scalars(select(Componente).join(Pei).join(Semestre).where(
                Componente.status == "pendente", Pei.status == "docente", Semestre.status == "aberto", meus)
                .order_by(Pei.atualizado_em)):
            itens.append(("docente", comp.pei, comp))
    return itens


def componentes_sem_docente(s: Session, semestre_id: int) -> list[Componente]:
    tem = select(Oferta.id).where(Oferta.semestre_id == semestre_id, Oferta.codigo == Componente.codigo).exists()
    return list(s.scalars(select(Componente).join(Pei).where(
        Pei.semestre_id == semestre_id, Pei.status.notin_(STATUS_FINAIS), ~tem).order_by(Componente.codigo)))
