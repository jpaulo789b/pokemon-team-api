from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class PokemonBase(BaseModel):
    name: str = Field(..., description="Nome do Pokémon", min_length=1, max_length=50)
    base_experience: Optional[int] = Field(None, description="Experiência base do Pokémon")
    height: int = Field(..., description="Altura do Pokémon em decímetros")
    weight: int = Field(..., description="Peso do Pokémon em hectogramas")


class PokemonCreate(PokemonBase):
    id: int = Field(..., description="ID oficial da Pokédex / PokeAPI")


class PokemonResponse(PokemonBase):
    id: int = Field(..., description="Identificador único na base / Pokédex")

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Mensagem de erro detalhada")
