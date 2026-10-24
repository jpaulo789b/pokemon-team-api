from collections.abc import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
import respx

from app.database import Base, get_db
from app.main import app

# Configuração de banco de dados SQLite isolado em memória com StaticPool
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Cria um banco de dados limpo para cada teste individual e descarta após o teste.

    Garante isolamento total entre os testes sem contaminação de estado.
    """
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient com injeção de dependência do banco de testes em memória.

    Não realiza mocks em rotas, serviços ou camadas de banco. A pilha real da aplicação
    é exercitada ponta a ponta.
    """
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_pokeapi() -> Generator[respx.MockRouter, None, None]:
    """Mock da fronteira HTTP externa da PokeAPI utilizando a biblioteca respx.

    Garante determinismo estrito e impede qualquer requisição de rede real externa.
    """
    with respx.mock(assert_all_called=False) as respx_mock:
        yield respx_mock
