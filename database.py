import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker( #simple ga cheppali ante edi session factory
    autocommit=False, # session lo changes automatic ga commit avvakunda chesedi
    autoflush=False, # session lo changes automatic ga flush avvakunda chesedi
    bind=engine  # bind the session to the engine
) #session ante database tho interact cheyadaniki use chese object

Base = declarative_base() # parent class for all ORM models

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()