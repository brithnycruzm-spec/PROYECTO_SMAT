from pydantic import BaseModel


class EstacionCreate(BaseModel):
    id: int
    nombre: str
    ubicacion: str
db_estaciones = []
db_lectura = []

class LecturaCreate(BaseModel):
    
    valor: float
    estacion_id: int