import os

from dotenv import load_dotenv
from psycopg import connect
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL").replace(
    "postgresql://",
    "postgresql+psycopg://",
)

class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL)


def get_connection():
    return connect(DATABASE_URL)