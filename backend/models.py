from sqlalchemy import Column, ForeignKey, Integer, String
from database import Base
from sqlalchemy.orm import relationship

class Estacion(Base):
    __tablename__ = "estaciones"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    ubicacion = Column(String)
    lecturas = relationship("LecturaDB", back_populates="estacion")
class LecturaDB(Base):
    __tablename__ = "lecturas"
    id = Column(Integer, primary_key=True, index=True)
    valor = Column(Integer)
    estacion_id = Column(Integer, ForeignKey("estaciones.id"))
    estacion = relationship("Estacion", back_populates="lecturas")