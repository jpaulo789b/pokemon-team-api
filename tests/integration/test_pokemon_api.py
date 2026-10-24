import httpx
from fastapi.testclient import TestClient
from respx import MockRouter
from sqlalchemy.orm import Session

from app.models import Pokemon

POKEAPI_BASE_URL = "https://pokeapi.co/api/v2/pokemon"


# ==============================================================================
# CENÁRIO 1: CAMINHO FELIZ (HAPPY PATH)
# ==============================================================================


def test_post_pokemon_success_and_double_assert(
    client: TestClient,
    db_session: Session,
    mock_pokeapi: MockRouter,
) -> None:
    """Cenário 1.1: Adicionar um novo Pokémon à equipe com sucesso.

    Valida:
    - Status HTTP 201 (Created)
    - Resposta estruturada conforme o contrato
    - Assert Duplo: Persistência real verificada via ORM no banco e via GET /team
    """
    # --- ARRANGE ---
    pokemon_name = "pikachu"
    pokeapi_payload = {
        "id": 25,
        "name": "pikachu",
        "base_experience": 112,
        "height": 4,
        "weight": 60,
    }

    # Intercepta a fronteira HTTP externa simulando sucesso da PokeAPI
    mock_pokeapi.get(f"{POKEAPI_BASE_URL}/{pokemon_name}").mock(
        return_value=httpx.Response(200, json=pokeapi_payload)
    )

    # Garantir estado inicial limpo do banco
    initial_count = db_session.query(Pokemon).count()
    assert initial_count == 0

    # --- ACT ---
    response = client.post(f"/team/{pokemon_name}")

    # --- ASSERT ---
    # 1. Validação da resposta HTTP
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 25
    assert data["name"] == "pikachu"
    assert data["base_experience"] == 112
    assert data["height"] == 4
    assert data["weight"] == 60

    # 2. ASSERT DUPLO - Verificação direta no banco via ORM (pilha real)
    db_pokemon = db_session.query(Pokemon).filter(Pokemon.name == "pikachu").first()
    assert db_pokemon is not None
    assert db_pokemon.id == 25
    assert db_pokemon.name == "pikachu"
    assert db_pokemon.base_experience == 112
    assert db_pokemon.height == 4
    assert db_pokemon.weight == 60

    # 3. ASSERT DUPLO - Verificação de leitura via endpoint GET /team
    get_response = client.get("/team")
    assert get_response.status_code == 200
    team_list = get_response.json()
    assert len(team_list) == 1
    assert team_list[0]["id"] == 25
    assert team_list[0]["name"] == "pikachu"


def test_post_pokemon_already_in_database_returns_200(
    client: TestClient,
    db_session: Session,
    mock_pokeapi: MockRouter,
) -> None:
    """Cenário 1.2: Tentar adicionar Pokémon que já existe no banco.

    Valida:
    - Retorno com status HTTP 200 (OK)
    - Sem chamada repetida para a PokeAPI
    - Sem duplicidade de registros no SQLite
    """
    # --- ARRANGE ---
    existing_pokemon = Pokemon(
        id=6,
        name="charizard",
        base_experience=240,
        height=17,
        weight=905,
    )
    db_session.add(existing_pokemon)
    db_session.commit()

    # Se a API externa fosse chamada indevidamente, o teste falharia
    mock_route = mock_pokeapi.get(f"{POKEAPI_BASE_URL}/charizard").mock(
        return_value=httpx.Response(500)
    )

    # --- ACT ---
    response = client.post("/team/charizard")

    # --- ASSERT ---
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 6
    assert data["name"] == "charizard"
    assert data["base_experience"] == 240

    # Garante que a PokeAPI NÃO foi chamada, usando o cache/banco local
    assert not mock_route.called

    # Garante unicidade no banco de dados
    total_count = db_session.query(Pokemon).count()
    assert total_count == 1


def test_get_team_list_success(
    client: TestClient,
    db_session: Session,
) -> None:
    """Cenário 1.3: Listar todos os Pokémons salvos no banco.

    Valida:
    - Retorno HTTP 200 com lista completa de Pokémons previamente cadastrados
    """
    # --- ARRANGE ---
    p1 = Pokemon(id=1, name="bulbasaur", base_experience=64, height=7, weight=69)
    p2 = Pokemon(id=4, name="charmander", base_experience=62, height=6, weight=85)
    p3 = Pokemon(id=7, name="squirtle", base_experience=63, height=5, weight=90)
    db_session.add_all([p1, p2, p3])
    db_session.commit()

    # --- ACT ---
    response = client.get("/team")

    # --- ASSERT ---
    assert response.status_code == 200
    team = response.json()
    assert isinstance(team, list)
    assert len(team) == 3

    names = [p["name"] for p in team]
    assert names == ["bulbasaur", "charmander", "squirtle"]


# ==============================================================================
# CENÁRIO 2: ERROS, CONTRATO E LIMITES (EDGE CASES)
# ==============================================================================


def test_post_pokemon_not_found_on_external_pokeapi(
    client: TestClient,
    db_session: Session,
    mock_pokeapi: MockRouter,
) -> None:
    """Cenário 2.1: Erro de Negócio (HTTP 404).

    Tenta adicionar um Pokémon inexistente na PokeAPI externa.
    Valida:
    - Status HTTP 404
    - Formato de erro tratado
    - Banco permanece vazio (sem efeitos colaterais)
    """
    # --- ARRANGE ---
    unknown_name = "agumon-inexistente"
    mock_pokeapi.get(f"{POKEAPI_BASE_URL}/{unknown_name}").mock(
        return_value=httpx.Response(404, json={"detail": "Not found"})
    )

    # --- ACT ---
    response = client.post(f"/team/{unknown_name}")

    # --- ASSERT ---
    assert response.status_code == 404
    error_data = response.json()
    assert "detail" in error_data
    assert "não foi encontrado na PokeAPI" in error_data["detail"]

    # Garantir que nada foi inserido no banco
    assert db_session.query(Pokemon).count() == 0


def test_post_pokemon_external_service_500_error(
    client: TestClient,
    db_session: Session,
    mock_pokeapi: MockRouter,
) -> None:
    """Cenário 2.2: Falha de comunicação externa (Erro 500 do servidor da PokeAPI).

    Valida:
    - Retorno de status HTTP 502 (Bad Gateway) tratado
    - Aplicação não sofre crash ou exceção não tratada
    - Estado do banco permanece íntegro e vazio
    """
    # --- ARRANGE ---
    pokemon_name = "mewtwo"
    mock_pokeapi.get(f"{POKEAPI_BASE_URL}/{pokemon_name}").mock(
        return_value=httpx.Response(500, text="Internal Server Error on PokeAPI")
    )

    # --- ACT ---
    response = client.post(f"/team/{pokemon_name}")

    # --- ASSERT ---
    assert response.status_code == 502
    error_data = response.json()
    assert "detail" in error_data
    assert "indisponível ou com erro interno" in error_data["detail"]

    # O banco não deve ter nenhum registro
    assert db_session.query(Pokemon).count() == 0


def test_post_pokemon_external_timeout_error(
    client: TestClient,
    db_session: Session,
    mock_pokeapi: MockRouter,
) -> None:
    """Cenário 2.3: Falha de comunicação por Timeout / Falha de Rede externa.

    Valida:
    - Retorno de status HTTP 502 com mensagem amigável
    - Aplicação não trava
    - Banco permanece sem registros
    """
    # --- ARRANGE ---
    pokemon_name = "gengar"
    mock_pokeapi.get(f"{POKEAPI_BASE_URL}/{pokemon_name}").mock(
        side_effect=httpx.TimeoutException("Connection timed out waiting for pokeapi.co")
    )

    # --- ACT ---
    response = client.post(f"/team/{pokemon_name}")

    # --- ASSERT ---
    assert response.status_code == 502
    error_data = response.json()
    assert "detail" in error_data
    assert "Falha de comunicação/timeout" in error_data["detail"]

    # Banco permanece íntegro
    assert db_session.query(Pokemon).count() == 0


def test_validation_contract_error_422_invalid_query_parameter(
    client: TestClient,
) -> None:
    """Cenário 2.4: Erro de contrato/validação (HTTP 422) via Query Params.

    Envia dados fora do contrato no endpoint GET /team (ex: query param com tipo inválido).
    Valida:
    - Retorno HTTP 422 Unprocessable Entity
    - Detalhes de validação estruturados pelo FastAPI/Pydantic
    """
    # --- ARRANGE ---
    # limit deve ser um inteiro entre 1 e 100, string causará erro de validação
    invalid_query = "/team?limit=nao_e_um_numero"

    # --- ACT ---
    response = client.get(invalid_query)

    # --- ASSERT ---
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    # Valida que o FastAPI apontou erro no campo 'limit'
    error_field = data["detail"][0]["loc"]
    assert "limit" in error_field


def test_validation_contract_error_422_invalid_path_parameter(
    client: TestClient,
) -> None:
    """Cenário 2.5: Erro de contrato/validação (HTTP 422) via Path Param com formato inválido.

    Envia caracteres especiais proibidos pelo regex de validação da rota.
    Valida:
    - Retorno HTTP 422 Unprocessable Entity
    """
    # --- ARRANGE ---
    # Rota aceita apenas ^[a-zA-Z0-9-]+$
    invalid_name = "pikachu$$$@@@!!!"

    # --- ACT ---
    response = client.post(f"/team/{invalid_name}")

    # --- ASSERT ---
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any("name" in err.get("loc", []) for err in data["detail"])
