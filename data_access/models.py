import datetime
from sqlalchemy import create_engine, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship
from core.enums import UserLevel

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
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=datetime.datetime.now)

def init_db():
    Base.metadata.create_all(engine)
