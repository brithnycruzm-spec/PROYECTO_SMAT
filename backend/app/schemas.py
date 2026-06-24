from pydantic import BaseModel

class EstacionCreate(BaseModel):
    id: int
    nombre: str
    ubicacion: str

class EstacionResponse(EstacionCreate):
    class Config:
        from_attributes = True

# ── NUEVO: schema para actualizar (sin id, no se cambia) ────
class EstacionUpdate(BaseModel):
    nombre: str
    ubicacion: str

class LecturaCreate(BaseModel):
    valor: float
    estacion_id: int

class LecturaResponse(BaseModel):
    id: int
    valor: float
    estacion_id: int
    class Config:
        from_attributes = True

# ── NUEVO: estación con su última lectura ───────────────────
class EstacionConLectura(BaseModel):
    id: int
    nombre: str
    ubicacion: str
    ultima_lectura: float | None = None
    class Config:
        from_attributes = True