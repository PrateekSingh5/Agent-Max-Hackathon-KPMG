import sqlalchemy as _sql
import sqlalchemy.ext.declarative as _declarative
from  sqlalchemy import orm as _orm
from dotenv import load_dotenv
import os 

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")  # URL-encode special chars like '@'
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = "postgresql://myuser:rootpassword@localhost:5432/agent_max"


# DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = _sql.create_engine(DATABASE_URL)

SessionLocal = _orm.sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = _declarative.declarative_base()

 