from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship
from core.enums import UserLevel, Container



engine = create_engine("sqlite:///database.db", echo=False)
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    pin: Mapped[int] = mapped_column(Integer)
    level: Mapped[int] = mapped_column(Integer, default=UserLevel.OPERATOR)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class ItemDirectoryModel(Base):
    __tablename__ = "item_directory"
    part_no: Mapped[str] = mapped_column(String(50), primary_key=True)
    manufacturer: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(100))
    containers: Mapped[List["ContainerModel"]] = relationship(back_populates="item")

class ContainerModel(Base):
    __tablename__ = "containers"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    part_no: Mapped[Optional[str]] = mapped_column(ForeignKey("item_directory.part_no"), nullable=True)
    item: Mapped[Optional["ItemDirectoryModel"]] = relationship(back_populates="containers")
    status: Mapped[int] = mapped_column(default=Container.Status.Content.NONE)
    deposited_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    lock_outp_pin: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sens_inp_pin: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    g_led_outp_pin: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    r_led_outp_pin: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


def init_db():
    Base.metadata.create_all(engine)
