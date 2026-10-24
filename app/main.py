from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from fastapi import FastAPI
from app.database import Base, engine
from app.routes import router as pokemon_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia o ciclo de vida da aplicação: cria tabelas no SQLite ao iniciar."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Pokemon Team Manager API",
    description="API para gerenciar equipe de Pokémons integrando com a PokeAPI externa e persistindo no SQLite.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(pokemon_router)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Endpoint de verificação de integridade da API."""
    return {"status": "ok"}
