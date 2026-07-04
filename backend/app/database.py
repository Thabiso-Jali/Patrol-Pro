from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

settings = get_settings()
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine_args = {}
if SQLALCHEMY_DATABASE_URL.startswith('sqlite'):
    engine_args['connect_args'] = {'check_same_thread': False}

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
