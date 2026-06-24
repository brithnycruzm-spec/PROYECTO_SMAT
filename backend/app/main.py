
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app import models, schemas, crud, database
from app.database import engine, get_db
from fastapi.middleware.cors import CORSMiddleware
from app.auth import crear_token_acceso, obtener_identidad_actual
from app import crud
from fastapi.security import OAuth2PasswordRequestForm

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

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)

# ─────────────────────────────────────────────────────────────
# USUARIOS VÁLIDOS (en producción esto vendría de una BD)
# Agrega aquí los usuarios que necesites: {"username": "password"}
# ─────────────────────────────────────────────────────────────
USUARIOS_VALIDOS = {
    "yo": "123456",
    "admin": "admin123",
}


@app.get("/")
async def root():
    return {
        "status": "success",
        "plataforma": "UNMSM",
        "servicio": "Smat",
        "message": "Bienvenido al Ecosistema Multiplataforma"
    }


# ─────────────────────────────────────────────────────────────
# ENDPOINT DE LOGIN — único, corregido
# ─────────────────────────────────────────────────────────────
@app.post("/token", tags=["Autenticación"], summary="Obtener token de acceso")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    password_correcta = USUARIOS_VALIDOS.get(form_data.username)
    if password_correcta is None or form_data.password != password_correcta:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = crear_token_acceso({"sub": form_data.username})
    return {"access_token": token, "token_type": "bearer"}
 
# ── Estaciones: crear ────────────────────────────────────────
@app.post("/estaciones/", status_code=201,
    tags=["Gestión de Estaciones"],
    summary="Registrar nueva estación (requiere token)")
def crear_estacion(
    estacion: schemas.EstacionCreate,
    db: Session = Depends(get_db),
    usuario: str = Depends(obtener_identidad_actual),
):
    if crud.obtener_estacion_por_id(db, estacion_id=estacion.id):
        raise HTTPException(status_code=400,
            detail=f"La estación con ID {estacion.id} ya existe.")
    return crud.crear_estacion_db(db=db, estacion=estacion)
 
# ── Estaciones: listar con stats y última lectura ─────────────
@app.get("/estaciones/stats",
    tags=["Gestión de Estaciones"],
    summary="Listar estaciones con estadísticas y última lectura")
async def listar_estaciones(db: Session = Depends(get_db)):
    total = db.query(models.Estacion).count()
    lectura_max = db.query(func.max(models.LecturaDB.valor)).scalar()
    record = None
    if lectura_max is not None:
        reg = db.query(models.LecturaDB).filter(
            models.LecturaDB.valor == lectura_max).first()
        if reg:
            est = db.query(models.Estacion).filter(
                models.Estacion.id == reg.estacion_id).first()
            if est:
                record = {"estacion_id": est.id, "nombre": est.nombre,
                          "lectura_mas_alta": lectura_max}
 
    # Incluir la última lectura de cada estación para el color del ícono
    estaciones_raw = crud.obtener_todas_estaciones(db)
    estaciones = []
    for e in estaciones_raw:
        ultima = crud.obtener_ultima_lectura(db, e.id)
        estaciones.append({
            "id": e.id,
            "nombre": e.nombre,
            "ubicacion": e.ubicacion,
            "ultima_lectura": ultima.valor if ultima else None,
        })
 
    return {
        "cantidad_total_estaciones": total,
        "estacion_con_lectura_mas_alta": record or "No hay lecturas registradas aún",
        "estaciones": estaciones,
    }
 
# ── Estaciones: actualizar ───────────────────────────────────
@app.put("/estaciones/{id}",
    tags=["Gestión de Estaciones"],
    summary="Actualizar nombre y ubicación de una estación (requiere token)")
def actualizar_estacion(
    id: int,
    datos: schemas.EstacionUpdate,
    db: Session = Depends(get_db),
    usuario: str = Depends(obtener_identidad_actual),
):
    estacion = crud.actualizar_estacion_db(db, estacion_id=id, datos=datos)
    if not estacion:
        raise HTTPException(status_code=404, detail="Estación no encontrada")
    return estacion
 
# ── Estaciones: eliminar ─────────────────────────────────────
@app.delete("/estaciones/{id}",
    tags=["Gestión de Estaciones"],
    summary="Eliminar una estación y sus lecturas (requiere token)")
def eliminar_estacion(
    id: int,
    db: Session = Depends(get_db),
    usuario: str = Depends(obtener_identidad_actual),
):
    eliminado = crud.eliminar_estacion_db(db, estacion_id=id)
    if not eliminado:
        raise HTTPException(status_code=404, detail="Estación no encontrada")
    return {"mensaje": f"Estación {id} eliminada correctamente"}
 
# ── Lecturas ─────────────────────────────────────────────────
@app.post("/lectura/", status_code=201,
    tags=["Telemetría de Sensores"],
    summary="Registrar lectura de sensor")
def registrar_lectura(lectura: schemas.LecturaCreate, db: Session = Depends(get_db)):
    if not crud.obtener_estacion_por_id(db, estacion_id=lectura.estacion_id):
        raise HTTPException(status_code=404, detail="Estación no existe")
    crud.crear_lectura_db(db=db, lectura=lectura)
    return {"status": "Lectura guardada en DB"}
 
# ── Riesgo ───────────────────────────────────────────────────
@app.get("/estaciones/{id}/riesgo",
    tags=["Análisis de Riesgo"],
    summary="Evaluar nivel de peligro de una estación")
async def obtener_riesgo(id: int, db: Session = Depends(get_db)):
    if not crud.obtener_estacion_por_id(db, estacion_id=id):
        raise HTTPException(status_code=404, detail="Estación no encontrada")
    lecturas = crud.obtener_lecturas_por_estacion(db, estacion_id=id)
    if not lecturas:
        return {"id": id, "nivel": "SIN DATOS", "valor": 0}
    ultima = lecturas[-1].valor
    nivel = "Peligro" if ultima > 20 else "Alerta" if ultima > 10 else "Normal"
    return {"id": id, "nivel": nivel, "valor": ultima}
 
# ── Historial ────────────────────────────────────────────────
@app.get("/estaciones/{id}/historial",
    tags=["Análisis de Riesgo"],
    summary="Historial de lecturas y riesgo promedio")
async def obtener_historial(id: int, db: Session = Depends(get_db)):
    if not db.query(models.LecturaDB).filter(models.LecturaDB.estacion_id == id).first():
        raise HTTPException(status_code=404, detail="Estación no encontrada")
    lecturas = crud.obtener_lecturas_por_estacion(db, estacion_id=id)
    n = len(lecturas)
    media = sum(l.valor for l in lecturas) / n if n else 0
    return {"media": media, "lecturas": lecturas, "numero_lecturas": n}