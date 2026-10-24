from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.poke_client import PokeAPICommunicationError, PokemonNotFoundError
from app.schemas import ErrorResponse, PokemonResponse
from app.services import PokemonService

router = APIRouter(prefix="/team", tags=["Pokemon Team"])


@router.post(
    "/{name}",
    response_model=PokemonResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"description": "Pokémon já existia na equipe e foi retornado do banco."},
        201: {"description": "Pokémon obtido da PokeAPI e cadastrado com sucesso."},
        404: {"model": ErrorResponse, "description": "Pokémon não encontrado na PokeAPI."},
        422: {"description": "Erro de validação nos parâmetros da requisição."},
        502: {"model": ErrorResponse, "description": "Falha de comunicação ou timeout na PokeAPI externa."},
    },
    summary="Adicionar Pokémon à equipe",
)
async def add_pokemon_to_team(
    response: Response,
    name: str = Path(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[a-zA-Z0-9-]+$",
        description="Nome ou slug do Pokémon (apenas caracteres alfanuméricos e hífens)",
    ),
    db: Session = Depends(get_db),
) -> PokemonResponse:
    """Busca o Pokémon pelo nome.

    Se já estiver salvo no banco de dados local, retorna o registro existente (HTTP 200).
    Caso contrário, busca na PokeAPI, persiste os dados no SQLite e retorna o novo registro (HTTP 201).
    """
    service = PokemonService(db)

    try:
        pokemon, created = await service.add_pokemon_to_team(name)
        if not created:
            response.status_code = status.HTTP_200_OK
        return pokemon
    except PokemonNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PokeAPICommunicationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[PokemonResponse],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Lista de Pokémons cadastrados na equipe."},
        422: {"description": "Parâmetros de consulta inválidos fora do contrato."},
    },
    summary="Listar todos os Pokémons da equipe",
)
def get_team(
    limit: Optional[int] = Query(
        default=None,
        ge=1,
        le=100,
        description="Limite de Pokémons a serem retornados para paginação (1 a 100)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset para paginação",
    ),
    db: Session = Depends(get_db),
) -> list[PokemonResponse]:
    """Retorna todos os Pokémons persistidos localmente no banco de dados SQLite."""
    service = PokemonService(db)
    return service.get_all_team(limit=limit, offset=offset)
