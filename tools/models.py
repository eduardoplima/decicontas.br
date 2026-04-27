import enum

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Date,
    Boolean,
    Text,
    JSON,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.schema import DDL, CheckConstraint
from sqlalchemy.dialects.mssql import TIMESTAMP

from sqlalchemy import (
    Column,
    Integer,
    String,
    Enum,
    Date,
    Text,
    ForeignKey,
    DateTime,
    Text,
    func,
)

from sqlalchemy.orm import relationship


class RoleEnum(str, enum.Enum):
    reviewer = "reviewer"
    admin = "admin"


Base = declarative_base()


class ObrigacaoORM(Base):
    __tablename__ = "Obrigacao"

    IdObrigacao = Column(Integer, primary_key=True, index=True)
    IdProcesso = Column(Integer, nullable=False)
    IdComposicaoPauta = Column(Integer, nullable=False)
    IdVotoPauta = Column(Integer, nullable=False)
    DescricaoObrigacao = Column(Text, nullable=False)
    DeFazer = Column(Boolean, default=True)
    Prazo = Column(String, nullable=True)
    DataCumprimento = Column(Date, nullable=True)
    OrgaoResponsavel = Column(String, nullable=True)
    IdOrgaoResponsavel = Column(Integer, nullable=True)
    TemMultaCominatoria = Column(Boolean, default=False)
    NomeResponsavelMultaCominatoria = Column(String, nullable=True)
    DocumentoResponsavelMultaCominatoria = Column(String, nullable=True)
    IdPessoaMultaCominatoria = Column(Integer, nullable=True)
    ValorMultaCominatoria = Column(Float, nullable=True)
    PeriodoMultaCominatoria = Column(String, nullable=True)
    EMultaCominatoriaSolidaria = Column(Boolean, default=False)
    SolidariosMultaCominatoria = Column(JSON, nullable=True)

    ReservadoPor = Column(String(255), nullable=True)
    DataReserva = Column(DateTime, nullable=True)


class RecomendacaoORM(Base):
    __tablename__ = "Recomendacao"

    IdRecomendacao = Column(Integer, primary_key=True, autoincrement=True)
    IdProcesso = Column(Integer, nullable=False)
    IdComposicaoPauta = Column(Integer, nullable=False)
    IdVotoPauta = Column(Integer, nullable=False)
    DescricaoRecomendacao = Column(String)
    PrazoCumprimentoRecomendacao = Column(String)
    DataCumprimentoRecomendacao = Column(Date)
    NomeResponsavel = Column(String)
    IdPessoaResponsavel = Column(Integer)
    OrgaoResponsavel = Column(String)
    IdOrgaoResponsavel = Column(Integer)
    Cancelado = Column(Boolean)

    ReservadoPor = Column(String(255), nullable=True)
    DataReserva = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<Recomendacao(IdRecomendacao={self.IdRecomendacao}, "
            f"IdProcesso={self.IdProcesso})>"
        )


# NERORM
class NERDecisaoORM(Base):
    __tablename__ = "NERDecisao"

    IdNerDecisao = Column(Integer, primary_key=True, autoincrement=True)
    IdProcesso = Column(Integer, nullable=False)
    IdComposicaoPauta = Column(Integer, nullable=False)
    IdVotoPauta = Column(Integer, nullable=False)

    Modelo = Column(String(100), nullable=True)
    VersaoPrompt = Column(String(50), nullable=True)
    RunId = Column(String(64), nullable=True)  # se usar MLflow ou algo similar

    RawJson = Column(Text, nullable=False)

    DataExtracao = Column(DateTime, server_default=func.now())

    multas = relationship(
        "NERMultaORM",
        back_populates="decisao",
        cascade="all, delete-orphan",
    )
    ressarcimentos = relationship(
        "NERRessarcimentoORM",
        back_populates="decisao",
        cascade="all, delete-orphan",
    )
    obrigacoes = relationship(
        "NERObrigacaoORM",
        back_populates="decisao",
        cascade="all, delete-orphan",
    )
    recomendacoes = relationship(
        "NERRecomendacaoORM",
        back_populates="decisao",
        cascade="all, delete-orphan",
    )


class NERMultaORM(Base):
    __tablename__ = "NERMulta"

    IdNerMulta = Column(Integer, primary_key=True, autoincrement=True)
    IdNerDecisao = Column(
        Integer, ForeignKey("NERDecisao.IdNerDecisao"), nullable=False
    )
    Ordem = Column(Integer, nullable=False)
    DescricaoMulta = Column(Text, nullable=False)

    decisao = relationship("NERDecisaoORM", back_populates="multas")


class NERRessarcimentoORM(Base):
    __tablename__ = "NERRessarcimento"

    IdNerRessarcimento = Column(Integer, primary_key=True, autoincrement=True)
    IdNerDecisao = Column(
        Integer, ForeignKey("NERDecisao.IdNerDecisao"), nullable=False
    )
    Ordem = Column(Integer, nullable=False)
    DescricaoRessarcimento = Column(Text, nullable=False)

    decisao = relationship("NERDecisaoORM", back_populates="ressarcimentos")


class NERObrigacaoORM(Base):
    __tablename__ = "NERObrigacao"

    IdNerObrigacao = Column(Integer, primary_key=True, autoincrement=True)
    IdNerDecisao = Column(
        Integer, ForeignKey("NERDecisao.IdNerDecisao"), nullable=False
    )
    Ordem = Column(Integer, nullable=False)
    DescricaoObrigacao = Column(Text, nullable=False)

    decisao = relationship("NERDecisaoORM", back_populates="obrigacoes")


class NERRecomendacaoORM(Base):
    __tablename__ = "NERRecomendacao"

    IdNerRecomendacao = Column(Integer, primary_key=True, autoincrement=True)
    IdNerDecisao = Column(
        Integer, ForeignKey("NERDecisao.IdNerDecisao"), nullable=False
    )
    Ordem = Column(Integer, nullable=False)
    DescricaoRecomendacao = Column(Text, nullable=False)

    decisao = relationship("NERDecisaoORM", back_populates="recomendacoes")


class ProcessedDecisionORM(Base):
    __tablename__ = "DecisaoProcessada"

    IdDecisaoProcessada = Column(Integer, primary_key=True, autoincrement=True)
    IdNERDecisao = Column(
        Integer, ForeignKey("NERDecisao.IdNerDecisao"), nullable=False
    )
    DataProcessamento = Column(DateTime, nullable=False)


class ProcessedMultaORM(Base):
    __tablename__ = "MultaProcessada"

    IdMultaProcessada = Column(Integer, primary_key=True, autoincrement=True)
    IdNerMulta = Column(Integer, ForeignKey("NERMulta.IdNerMulta"), nullable=False)
    DataProcessamento = Column(DateTime, nullable=False)


class ProcessedRessarcimentoORM(Base):
    __tablename__ = "RessarcimentoProcessado"

    IdRessarcimentoProcessado = Column(Integer, primary_key=True, autoincrement=True)
    IdNerRessarcimento = Column(
        Integer, ForeignKey("NERRessarcimento.IdNerRessarcimento"), nullable=False
    )
    DataProcessamento = Column(DateTime, nullable=False)


class ProcessedObrigacaoORM(Base):
    __tablename__ = "ObrigacaoProcessada"

    IdObrigacaoProcessada = Column(Integer, primary_key=True, autoincrement=True)
    IdNerObrigacao = Column(
        Integer, ForeignKey("NERObrigacao.IdNerObrigacao"), nullable=False
    )
    IdObrigacao = Column(Integer, ForeignKey("Obrigacao.IdObrigacao"), nullable=False)
    DataProcessamento = Column(DateTime, nullable=False)


class ProcessedRecomendacaoORM(Base):
    __tablename__ = "RecomendacaoProcessada"

    IdRecomendacaoProcessada = Column(Integer, primary_key=True, autoincrement=True)
    IdNerRecomendacao = Column(
        Integer, ForeignKey("NERRecomendacao.IdNerRecomendacao"), nullable=False
    )
    IdRecomendacao = Column(
        Integer, ForeignKey("Recomendacao.IdRecomendacao"), nullable=False
    )
    DataProcessamento = Column(DateTime, nullable=False)


class ExtracaoORM(Base):
    """One row per extraction run.

    TCE/RN sessions happen on Tuesdays and Thursdays, so ``[DataInicio, DataFim]``
    typically covers a window of a few weeks of session decisions.
    ``DataExecucao`` records when the run was triggered.

    A run progresses through three pipeline stages:

      1. ``decisoes`` — NER on raw decision texts (``run_ner_pipeline_for_dataframe``).
      2. ``obrigacoes`` — stage-2 obrigação extraction.
      3. ``recomendacoes`` — stage-2 recomendação extraction.

    The orchestrator task in ``app.worker`` updates ``Status`` / ``EtapaAtual``
    / counters as it progresses, so the frontend can poll for live status.
    """

    __tablename__ = "Extracao"

    IdExtracao = Column(Integer, primary_key=True, autoincrement=True)
    DataInicio = Column(Date, nullable=False)
    DataFim = Column(Date, nullable=False)
    DataExecucao = Column(DateTime, nullable=False, server_default=func.now())

    # Live job state. Defaults assume the orchestrator hasn't started yet.
    Status = Column(String(20), nullable=False, default="queued")
    EtapaAtual = Column(String(30), nullable=False, default="queued")
    DecisoesProcessadas = Column(Integer, nullable=False, default=0)
    ObrigacoesGeradas = Column(Integer, nullable=False, default=0)
    RecomendacoesGeradas = Column(Integer, nullable=False, default=0)
    Erros = Column(Integer, nullable=False, default=0)
    MensagemErro = Column(Text, nullable=True)
    JobId = Column(String(64), nullable=True)


class UserORM(Base):
    __tablename__ = "Usuarios"

    IdUsuario = Column(Integer, primary_key=True, autoincrement=True)
    NomeUsuario = Column(String(150), nullable=False, unique=True, index=True)
    Email = Column(String(255), nullable=False, unique=True, index=True)
    SenhaHash = Column(String(255), nullable=False)
    Papel = Column(
        Enum(
            RoleEnum,
            name="papel_usuario",
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
        default=RoleEnum.reviewer,
    )
    Ativo = Column(Boolean, nullable=False, default=True)
    DataCriacao = Column(DateTime, nullable=False, server_default=func.now())
    DataAtualizacao = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    refresh_tokens = relationship(
        "RefreshTokenORM",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class RefreshTokenORM(Base):
    __tablename__ = "TokensRenovacao"

    IdTokenRenovacao = Column(Integer, primary_key=True, autoincrement=True)
    IdUsuario = Column(
        Integer, ForeignKey("Usuarios.IdUsuario"), nullable=False, index=True
    )
    HashToken = Column(String(255), nullable=False, unique=True, index=True)
    DataExpiracao = Column(DateTime, nullable=False)
    DataRevogacao = Column(DateTime, nullable=True)
    DataCriacao = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("UserORM", back_populates="refresh_tokens")
