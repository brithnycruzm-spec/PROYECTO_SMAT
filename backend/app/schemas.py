from pydantic import BaseModel

class EstacionCreate(BaseModel):
    id: int
    nombre: str
    ubicacion: str
class EstacionResponse(EstacionCreate):
    class Config:
        from_attributes = True

class LecturaCreate(BaseModel):
    valor: float
    estacion_id: int
class LecturaResponse(BaseModel):
    id: int
    valor: float
    estacion_id: int
    class Config:
            from_attributes = True