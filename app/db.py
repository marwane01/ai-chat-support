import os
from sqlmodel import SQLModel, create_engine, Session
from contextlib import contextmanager

db_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
engine = create_engine(db_url, pool_pre_ping=True)


def init_db():
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session():
    s = Session(engine)
    try:
        yield s
    finally:
        s.close()
