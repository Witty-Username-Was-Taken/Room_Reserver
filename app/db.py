from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DATABASE_URL = "postgresql+psycopg://booking:booking@localhost:5432/booking"

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
