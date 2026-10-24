from sqlalchemy import Column, Integer, String
from app.database import Base


class Pokemon(Base):
    """SQLAlchemy model representing a Pokemon entity in the team database."""

    __tablename__ = "pokemons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    base_experience = Column(Integer, nullable=True)
    height = Column(Integer, nullable=False)
    weight = Column(Integer, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Pokemon(id={self.id}, name='{self.name}', "
            f"base_experience={self.base_experience}, height={self.height}, weight={self.weight})>"
        )
