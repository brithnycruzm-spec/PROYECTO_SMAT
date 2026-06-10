from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
import models
from database import engine, get_db
from pydantic import BaseModel
from typing import List, Optional

models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Smat persistente")


class EstacionCreate(BaseModel):
    id: int
    nombre: str
    ubicacion: str
db_estaciones = []
db_lectura = []

class LecturaCreate(BaseModel):
    
    valor: float
    estacion_id: int

@app.get("/")
async def root():
    return {"status": "success","plataforma":"UNMSM", "servicio":"Smat","message": "Bienvenido al Ecosistema Multiplataforma"}

@app.post("/estaciones/",status_code=201)
def crear_estacion(estacion: EstacionCreate, db: Session = Depends(get_db)):
    nueva_estacion = models.Estacion(id=estacion.id, nombre=estacion.nombre, ubicacion=estacion.ubicacion)
    db.add(nueva_estacion)
    db.commit()
    db.refresh(nueva_estacion)
    return {"msj": "Estación guardada en DB", "data": nueva_estacion}

@app.get("/estaciones/")
async def listar_estaciones():
    return db_estaciones

@app.post("/lectura/",status_code=201)
def registrar_lectura(lectura: LecturaCreate, db: Session = Depends(get_db)):
    estacion = db.query(models.Estacion).filter(models.Estacion.id == lectura.estacion_id).first()
    if not estacion:
        raise HTTPException(status_code=404, detail="Estación no existe")
    nueva_lectura = models.LecturaDB(valor=lectura.valor, estacion_id=lectura.estacion_id)
    db.add(nueva_lectura)
    db.commit()
    return {"status": "Lectura guardada en DB"}

@app.get("/estaciones/{id}/riesgo")
async def obtener_riesgo_estacion(id: int):
    estacion_existe = any((e.id == id) for e in db_estaciones)
    if not estacion_existe:
        raise HTTPException(status_code=404, detail="Estación no encontrada")
    
    lecturas = [l for l in db_lectura if l.estacion_id == id]
    if not lecturas:
        return {"id": id, "nivel": "SIN DATOS", "valor": 0}
    
    ultima_lectura = lecturas[-1].valor
    if ultima_lectura>20:
        nivel = "Peligro"
    elif ultima_lectura>10:
        nivel = "Alerta"
    else:
        nivel = "Normal"
    return {"id": id, "nivel": nivel, "valor": ultima_lectura}

@app.get("/estaciones/{id}/historial")
async def obtener_historial_estacion(id: int, db: Session = Depends(get_db)):
    estacion_existe = db.query(models.LecturaDB).filter(models.LecturaDB.estacion_id == id).first()
    if not estacion_existe:
        raise HTTPException(status_code=404, detail="Estación no encontrada")
    lecturas = db.query(models.LecturaDB).filter(models.LecturaDB.estacion_id == id).all()
    numero_lecturas = len(lecturas)
    if numero_lecturas == 0:
        media = 0
    else:
        media = sum(l.valor for l in lecturas) / numero_lecturas
    return {"media": media, "lecturas": lecturas, "numero_lecturas": numero_lecturas}


@app.get("/health")
def health_check():
    return {"check": "Servicios Cloud operativos"}

