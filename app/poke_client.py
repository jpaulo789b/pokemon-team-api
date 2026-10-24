from typing import Any
import httpx


class PokeAPIError(Exception):
    """Exceção base para erros relacionados à PokeAPI."""
    pass


class PokemonNotFoundError(PokeAPIError):
    """Lançada quando a PokeAPI retorna status HTTP 404 (Pokémon não encontrado)."""
    pass


class PokeAPICommunicationError(PokeAPIError):
    """Lançada quando ocorrem erros de conexão, timeout ou respostas 5xx da PokeAPI."""
    pass


POKEAPI_BASE_URL = "https://pokeapi.co/api/v2/pokemon"


async def fetch_pokemon_from_api(name: str, timeout: float = 5.0) -> dict[str, Any]:
    """Busca os dados de um Pokémon na PokeAPI externa via HTTPX.

    Args:
        name: Nome do Pokémon a ser consultado.
        timeout: Tempo limite da requisição em segundos.

    Returns:
        dict com id, name, base_experience, height e weight normalizados.

    Raises:
        PokemonNotFoundError: Se a PokeAPI retornar 404.
        PokeAPICommunicationError: Se houver timeout, falha de rede ou resposta 5xx.
    """
    clean_name = name.strip().lower()
    url = f"{POKEAPI_BASE_URL}/{clean_name}"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)

        if response.status_code == 404:
            raise PokemonNotFoundError(f"Pokémon '{clean_name}' não foi encontrado na PokeAPI.")

        if response.status_code >= 500:
            raise PokeAPICommunicationError(
                f"PokeAPI externa indisponível ou com erro interno (HTTP {response.status_code})."
            )

        response.raise_for_status()
        data = response.json()

        return {
            "id": data["id"],
            "name": data["name"].lower(),
            "base_experience": data.get("base_experience"),
            "height": data["height"],
            "weight": data["weight"],
        }

    except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
        raise PokeAPICommunicationError(
            f"Falha de comunicação/timeout ao conectar com a PokeAPI: {exc}"
        ) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise PokemonNotFoundError(f"Pokémon '{clean_name}' não foi encontrado na PokeAPI.") from exc
        raise PokeAPICommunicationError(
            f"Erro HTTP inesperado ao consultar a PokeAPI: {exc}"
        ) from exc
