from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
import models
from database import engine, get_db
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(
            title="Smat - Sistema de Monitoreo de Alerta Temprana",
            description="""API robusta para la gestión y monitoreo de desastres naturales.
            Permite la telemetría de sensores en tiempo real y el cálculo de niveles de riesgo basados en datos históricos.
            
            **Entidades principales:**
            * **Estaciones:** Puntos de monitoreo físico.
            * **Lecturas:** Datos capturados por sensores.
            * **Riesgos:** Análisis de criticidad basado en umbrales.
            """,
            version="1.0.0",
            terms_of_service="http://unmsm.edu.pe/terms/",
            contact={
                "FISI": "Equipo de Desarrollo Smat",
                "url": "http://fisi.unmsm.edu.pe/smat",
                "email": "desarrollo.smat@unmsm.edu.pe"
            },
            license_info={
                "name": "Apache 2.0",
                "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
            },
)
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

@app.post("/estaciones/",status_code=201,
        responses = {
            201: {"description": "Estación creada exitosamente"},
            400: {"description": "Solicitud inválida"},
            500: {"description": "Error interno del servidor"}
        },
        tags=["Gestión de Estaciones"],
        summary="Registrar una nueva estación de monitoreo",
        description="Permite crear una nueva estación física")
def crear_estacion(estacion: EstacionCreate, db: Session = Depends(get_db)):
    nueva_estacion = models.Estacion(id=estacion.id, nombre=estacion.nombre, ubicacion=estacion.ubicacion)
    db.add(nueva_estacion)
    db.commit()
    db.refresh(nueva_estacion)
    return {"msj": "Estación guardada en DB", "data": nueva_estacion}

@app.get("/estaciones/",
         responses = {
            200: {"description": "Listado de estaciones obtenido exitosamente"},
            500: {"description": "Error interno del servidor"}
         },
         tags=["Gestión de Estaciones"],
         summary="Listar todas las estaciones registradas",
         description="Devuelve un listado completo de todas las estaciones de monitoreo registradas en el sistema")
async def listar_estaciones(db: Session = Depends(get_db)):
    return db.query(models.Estacion).all()

@app.post("/lectura/",status_code=201,
        responses = {
            201: {"description": "Lectura registrada exitosamente"},
            400: {"description": "Solicitud inválida"},
            404: {"description": "Estación no encontrada"},
            500: {"description": "Error interno del servidor"}
        },
        tags=["Telemetría de Sensores"],
        summary="Recibir datos de telemetría",
        description="Recibe el valor capturado por un sensor y lo víncula a una estación existente medante su ID")
def registrar_lectura(lectura: LecturaCreate, db: Session = Depends(get_db)):
    estacion = db.query(models.Estacion).filter(models.Estacion.id == lectura.estacion_id).first()
    if not estacion:
        raise HTTPException(status_code=404, detail="Estación no existe")
    nueva_lectura = models.LecturaDB(valor=lectura.valor, estacion_id=lectura.estacion_id)
    db.add(nueva_lectura)
    db.commit()
    return {"status": "Lectura guardada en DB"}

@app.get("/estaciones/{id}/riesgo",
         responses = {
            200: {"description": "Nivel de riesgo obtenido exitosamente"},
            404: {"description": "Estación no encontrada"},
            500: {"description": "Error interno del servidor"}
         },
         tags=["Análisis de Riesgo"],
         summary="Evaluar nivel de peligro actual de una estación",
         description="Analiza la última lectura registrada para una estación específica y determina si el estado es 'Normal', 'Alerta' o 'Peligro' basado en umbrales predefinidos")
async def obtener_riesgo_estacion(id: int, db: Session = Depends(get_db)):
    estacion_existe = db.query(models.Estacion).filter(models.Estacion.id == id).first()
    if not estacion_existe:
        raise HTTPException(status_code=404, detail="Estación no encontrada")

    lecturas = db.query(models.LecturaDB).filter(models.LecturaDB.estacion_id == id).all()
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

@app.get("/estaciones/{id}/historial",
         responses = {
            200: {"description": "Historial de lecturas obtenido exitosamente"},
            404: {"description": "Estación no encontrada"},
            500: {"description": "Error interno del servidor"}
         },
         tags = ["Análisis de Riesgo"],
         summary="Obtener historial de lecturas y nivel de riesgo promedio",
         description="Proporciona un resumen del historial de lecturas para una estación específica y calcula el nivel de riesgo promedio")
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

