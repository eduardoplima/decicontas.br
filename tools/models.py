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
    DataProcessamento = Column(TIMESTAMP, nullable=False)


class UserORM(Base):
    __tablename__ = "Users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(150), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(
        Enum(
            RoleEnum,
            name="user_role",
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
        default=RoleEnum.reviewer,
    )
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
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
    __tablename__ = "RefreshTokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("UserORM", back_populates="refresh_tokens")
