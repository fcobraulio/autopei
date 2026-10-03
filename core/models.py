"""Modelo de dados do AutoPEI (SQLAlchemy 2 + PostgreSQL)."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# ---------------------------------------------------------------------------
# Vocabulários
# ---------------------------------------------------------------------------
PERFIS = {
    "gestor": "Gestor(a) NAPNE",
    "auxiliar": "Auxiliar (bolsista)",
    "psicopedagogia": "Psicopedagogia",
    "etep": "ETEP",
    "docente": "Docente",
}
# Perfis que exigem login pelo SUAP (o docente é implícito: qualquer pessoa do SUAP).
PERFIS_SUAP = {"gestor", "auxiliar", "etep"}

ETAPAS = {
    "psicopedagogia": "Psicopedagogia",
    "etep": "ETEP",
    "docente": "Docente",
    "gestao": "Gestão NAPNE (revisão)",
}

TIPOS_PERGUNTA = {
    "longa": "Resposta longa",
    "radio": "Escolha única (botões de opção)",
    "checkbox": "Múltipla escolha (caixas de seleção)",
    "select": "Menu de seleção",
}

STATUS = {
    "psicopedagogia": "Aguardando Psicopedagogia",
    "etep": "Aguardando ETEP",
    "docente": "Com os docentes (em paralelo)",
    "revisao": "Em revisão (NAPNE)",
    "aprovado": "Aprovado · aguardando registro no SUAP",
    "registrado": "Registrado no SUAP",
    "cancelado": "Cancelado",
}
STATUS_CURTO = {
    "psicopedagogia": "Psicopedagogia",
    "etep": "ETEP",
    "docente": "Docentes",
    "revisao": "Revisão",
    "aprovado": "Aprovado",
    "registrado": "Registrado",
    "cancelado": "Cancelado",
}
STATUS_FINAIS = {"registrado", "cancelado"}
DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
# Estudos individualizados: horas fechadas (7 = 7h–8h ... 21 = 21h–22h).
HORAS_ESTUDO = list(range(7, 22))
FREQUENCIAS = {
    "semanal": "Semanal (toda semana)",
    "quinzenal": "Quinzenal (a cada 2 semanas)",
    "mensal": "Mensal (1 vez por mês)",
}


def faixa_hora(h: int) -> str:
    return f"{h:02d}h–{h + 1:02d}h"


class Base(DeclarativeBase):
    type_annotation_map = {dict: JSON, list: JSON}


class Campus(Base):
    __tablename__ = "campus"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True)
    sigla: Mapped[str] = mapped_column(String(20), default="")
    cidade: Mapped[str] = mapped_column(String(120), default="")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Usuario(Base):
    """Pessoa que já entrou no sistema (ou conta local criada)."""

    __tablename__ = "usuario"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    # Contas SUAP: matrícula SUAP (campo "identificacao"). Contas locais: usuário escolhido.
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(200), default="")
    senha_hash: Mapped[str | None] = mapped_column(String(300), nullable=True)
    auth: Mapped[str] = mapped_column(String(10), default="suap")  # suap | local
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    suap_tipo: Mapped[str] = mapped_column(String(80), default="")  # ex.: "Servidor (Docente)"
    suap_campus: Mapped[str] = mapped_column(String(80), default="")
    ultimo_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Acesso(Base):
    """Perfil concedido a uma matrícula/usuário em um campus.

    * gestor → cadastrado pelo administrador (matrícula SUAP)
    * auxiliar, etep → lista de matrículas autorizadas mantida pelo gestor (SUAP)
    * psicopedagogia → conta local criada pelo gestor
    O perfil docente não é cadastrado: qualquer pessoa que entra pelo SUAP pode ser docente.
    """

    __tablename__ = "acesso"
    __table_args__ = (UniqueConstraint("campus_id", "matricula", "perfil"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id", ondelete="CASCADE"))
    matricula: Mapped[str] = mapped_column(String(80), index=True)  # = Usuario.username
    perfil: Mapped[str] = mapped_column(String(20))
    nome: Mapped[str] = mapped_column(String(200), default="")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    campus: Mapped[Campus] = relationship()


class Semestre(Base):
    __tablename__ = "semestre"
    __table_args__ = (UniqueConstraint("campus_id", "codigo"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id", ondelete="CASCADE"))
    codigo: Mapped[str] = mapped_column(String(10))  # ex.: 2026.2
    status: Mapped[str] = mapped_column(String(10), default="aberto")  # aberto | encerrado
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    encerrado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    encerrado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)

    campus: Mapped[Campus] = relationship()


class Oferta(Base):
    """Disciplina (código) ofertada no semestre e o(s) docente(s) que a lecionam."""

    __tablename__ = "oferta"
    __table_args__ = (UniqueConstraint("semestre_id", "codigo", "docente_matricula"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    semestre_id: Mapped[int] = mapped_column(ForeignKey("semestre.id", ondelete="CASCADE"), index=True)
    codigo: Mapped[str] = mapped_column(String(40))
    disciplina: Mapped[str] = mapped_column(String(200), default="")
    docente_matricula: Mapped[str] = mapped_column(String(80))
    docente_nome: Mapped[str] = mapped_column(String(200), default="")


class Estudante(Base):
    __tablename__ = "estudante"
    id: Mapped[int] = mapped_column(primary_key=True)
    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id", ondelete="CASCADE"))
    nome: Mapped[str] = mapped_column(String(200))
    matricula: Mapped[str] = mapped_column(String(40), default="")
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    curso: Mapped[str] = mapped_column(String(200), default="")
    nivel_forma: Mapped[str] = mapped_column(String(80), default="")
    periodo: Mapped[str] = mapped_column(String(40), default="")
    turno: Mapped[str] = mapped_column(String(20), default="")
    nee: Mapped[str] = mapped_column(Text, default="")
    responsavel: Mapped[str] = mapped_column(String(200), default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    campus: Mapped[Campus] = relationship()


class Pei(Base):
    __tablename__ = "pei"
    __table_args__ = (UniqueConstraint("estudante_id", "semestre_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    estudante_id: Mapped[int] = mapped_column(ForeignKey("estudante.id", ondelete="CASCADE"))
    semestre_id: Mapped[int] = mapped_column(ForeignKey("semestre.id", ondelete="CASCADE"))
    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="psicopedagogia", index=True)
    # True quando o PEI foi devolvido a UMA etapa para correção: ao reenviar, volta
    # direto à revisão (sem passar pelas etapas seguintes).
    em_correcao: Mapped[bool] = mapped_column(Boolean, default=False)
    # Obsoleto (versões antigas: horários digitados pela gestão). Hoje os horários são os
    # estudos individualizados cadastrados pelos docentes (tabela EstudoIndividualizado).
    horarios: Mapped[dict] = mapped_column(JSON, default=dict)
    # Semestre do PEI anterior usado para pré-preencher as respostas ("" se nenhum).
    prefill_origem: Mapped[str] = mapped_column(String(10), default="")
    criado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    aprovado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    aprovado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    registrado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    registrado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    docx: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    docx_nome: Mapped[str] = mapped_column(String(200), default="")

    estudante: Mapped[Estudante] = relationship()
    semestre: Mapped[Semestre] = relationship()
    campus: Mapped[Campus] = relationship()
    componentes: Mapped[list["Componente"]] = relationship(
        back_populates="pei", cascade="all, delete-orphan", order_by="Componente.id"
    )
    historico: Mapped[list["Historico"]] = relationship(
        back_populates="pei", cascade="all, delete-orphan", order_by="Historico.id"
    )


class Componente(Base):
    """Componente curricular (código de disciplina) cursado pelo estudante.

    Os docentes NÃO ficam aqui: são obtidos da Oferta do semestre pelo código.
    Assim, quando o PEI chega à etapa dos docentes, ele aparece automaticamente
    (e em paralelo) na caixa de todos os docentes das disciplinas do estudante.
    """

    __tablename__ = "componente"
    id: Mapped[int] = mapped_column(primary_key=True)
    pei_id: Mapped[int] = mapped_column(ForeignKey("pei.id", ondelete="CASCADE"))
    codigo: Mapped[str] = mapped_column(String(40))
    disciplina: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(12), default="pendente")  # pendente | concluido
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    concluido_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)

    pei: Mapped[Pei] = relationship(back_populates="componentes")
    concluido_por: Mapped[Usuario | None] = relationship()


class Pergunta(Base):
    __tablename__ = "pergunta"
    id: Mapped[int] = mapped_column(primary_key=True)
    etapa: Mapped[str] = mapped_column(String(20), index=True)
    secao: Mapped[str] = mapped_column(String(120), default="")
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    enunciado: Mapped[str] = mapped_column(Text)
    ajuda: Mapped[str] = mapped_column(Text, default="")
    tipo: Mapped[str] = mapped_column(String(10), default="longa")
    opcoes: Mapped[list] = mapped_column(JSON, default=list)
    obrigatoria: Mapped[bool] = mapped_column(Boolean, default=True)
    texto_nada: Mapped[str] = mapped_column(Text, default="")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Resposta(Base):
    __tablename__ = "resposta"
    id: Mapped[int] = mapped_column(primary_key=True)
    pei_id: Mapped[int] = mapped_column(ForeignKey("pei.id", ondelete="CASCADE"), index=True)
    componente_id: Mapped[int | None] = mapped_column(
        ForeignKey("componente.id", ondelete="CASCADE"), nullable=True
    )
    pergunta_id: Mapped[int] = mapped_column(ForeignKey("pergunta.id", ondelete="CASCADE"))
    valor: Mapped[dict] = mapped_column(JSON, default=dict)  # {"v": str | list}
    nada_declarar: Mapped[bool] = mapped_column(Boolean, default=False)
    # Semestre de onde a resposta foi copiada (pré-preenchimento). Some quando alguém a altera.
    origem: Mapped[str] = mapped_column(String(10), default="")
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    pergunta: Mapped[Pergunta] = relationship()


class EstudoIndividualizado(Base):
    """Horário de estudo individualizado oferecido por um docente ao estudante.

    Cadastrado pelo DOCENTE no seu componente (não pela gestão), só quando ele vê a
    necessidade. Um docente pode cadastrar vários horários (ex.: dois por semana) e cada um
    tem a sua frequência (semanal, quinzenal ou mensal). Horários em horas fechadas.
    """

    __tablename__ = "estudo_individualizado"
    id: Mapped[int] = mapped_column(primary_key=True)
    pei_id: Mapped[int] = mapped_column(ForeignKey("pei.id", ondelete="CASCADE"), index=True)
    componente_id: Mapped[int] = mapped_column(ForeignKey("componente.id", ondelete="CASCADE"), index=True)
    dia: Mapped[str] = mapped_column(String(10))  # um de DIAS_SEMANA
    hora: Mapped[int] = mapped_column(Integer)  # hora de início; dura 1 hora
    frequencia: Mapped[str] = mapped_column(String(10), default="semanal")  # FREQUENCIAS
    local: Mapped[str] = mapped_column(String(200), default="")  # local / observação
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    usuario: Mapped[Usuario | None] = relationship()


class Anexo(Base):
    """Arquivo de apoio interno (laudo, notificação, prova...). Não entra no DOCX."""

    __tablename__ = "anexo"
    id: Mapped[int] = mapped_column(primary_key=True)
    pei_id: Mapped[int] = mapped_column(ForeignKey("pei.id", ondelete="CASCADE"), index=True)
    componente_id: Mapped[int | None] = mapped_column(
        ForeignKey("componente.id", ondelete="CASCADE"), nullable=True
    )
    etapa: Mapped[str] = mapped_column(String(20))
    nome_arquivo: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    tamanho: Mapped[int] = mapped_column(Integer, default=0)
    descricao: Mapped[str] = mapped_column(String(300), default="")
    dados: Mapped[bytes] = mapped_column(LargeBinary)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    usuario: Mapped[Usuario | None] = relationship()


class Historico(Base):
    __tablename__ = "historico"
    id: Mapped[int] = mapped_column(primary_key=True)
    pei_id: Mapped[int] = mapped_column(ForeignKey("pei.id", ondelete="CASCADE"), index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    acao: Mapped[str] = mapped_column(String(300))
    de_status: Mapped[str] = mapped_column(String(20), default="")
    para_status: Mapped[str] = mapped_column(String(20), default="")
    comentario: Mapped[str] = mapped_column(Text, default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    pei: Mapped[Pei] = relationship(back_populates="historico")
    usuario: Mapped[Usuario | None] = relationship()
