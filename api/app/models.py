from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)

    clues = relationship("Clue", back_populates="category")


class Clue(Base):
    __tablename__ = "clues"

    id = Column(Integer, primary_key=True, index=True)
    answer = Column(String)
    question = Column(String)
    value = Column(Integer)

    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="clues")