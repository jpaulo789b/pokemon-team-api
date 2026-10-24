from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import Pokemon
from app.poke_client import fetch_pokemon_from_api


class PokemonService:
    """Camada de serviço responsável pelas regras de negócio da equipe Pokémon."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_pokemon_by_name(self, name: str) -> Optional[Pokemon]:
        """Consulta um Pokémon localmente no banco de dados pelo nome (case-insensitive)."""
        clean_name = name.strip().lower()
        return self.db.query(Pokemon).filter(func.lower(Pokemon.name) == clean_name).first()

    def get_all_team(self, limit: Optional[int] = None, offset: int = 0) -> list[Pokemon]:
        """Recupera todos os Pokémons cadastrados na equipe local."""
        query = self.db.query(Pokemon).order_by(Pokemon.id)
        if offset > 0:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    async def add_pokemon_to_team(self, name: str) -> tuple[Pokemon, bool]:
        """Adiciona um Pokémon à equipe local.

        1. Verifica se o Pokémon já está cadastrado no SQLite local.
        2. Se existir, retorna a instância persistida e created=False.
        3. Se não existir, busca dados atualizados na PokeAPI externa,
           persiste no SQLite e retorna a instância e created=True.

        Returns:
            Tuple[Pokemon, bool]: Tupla com a entidade do Pokémon e booleano indicando criação.
        """
        clean_name = name.strip().lower()

        # 1. Checagem prévia no banco local
        existing_pokemon = self.get_pokemon_by_name(clean_name)
        if existing_pokemon is not None:
            return existing_pokemon, False

        # 2. Busca externa na PokeAPI
        poke_data = await fetch_pokemon_from_api(clean_name)

        # 3. Mapeamento e persistência
        pokemon = Pokemon(
            id=poke_data["id"],
            name=poke_data["name"],
            base_experience=poke_data["base_experience"],
            height=poke_data["height"],
            weight=poke_data["weight"],
        )
        self.db.add(pokemon)
        self.db.commit()
        self.db.refresh(pokemon)

        return pokemon, True
