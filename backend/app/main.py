from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app import models, schemas, crud, database
from app.database import engine, get_db
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from app.auth import crear_token_acceso, obtener_identidad_actual
from app import crud
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

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
@app.post(
    "/token",
    tags=["Autenticación"],
    summary="Obtener token de acceso",
    description="Valida las credenciales del usuario y genera un token JWT. "
                "Usa usuario: **yo** / contraseña: **123456** para probar.",
)
async def login_para_tener_acceso(form_data: OAuth2PasswordRequestForm = Depends()):
    # 1. Verificar que el usuario existe
    password_correcta = USUARIOS_VALIDOS.get(form_data.username)

    # 2. Verificar que la contraseña coincide
    if password_correcta is None or form_data.password != password_correcta:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Credenciales correctas → generar token con el username real
    token = crear_token_acceso({"sub": form_data.username})
    return {"access_token": token, "token_type": "bearer"}


@app.post(
    "/estaciones/",
    status_code=201,
    responses={
        201: {"description": "Estación creada exitosamente"},
        400: {"description": "Solicitud inválida"},
        500: {"description": "Error interno del servidor"},
    },
    tags=["Gestión de Estaciones"],
    summary="Registrar una nueva estación de monitoreo",
    description="Permite crear una nueva estación física solo a personal autorizado",
)
def crear_estacion(
    estacion: schemas.EstacionCreate,
    db: Session = Depends(get_db),
    usuario: str = Depends(obtener_identidad_actual),
):
    estacion_existente = crud.obtener_estacion_por_id(db, estacion_id=estacion.id)
    if estacion_existente:
        raise HTTPException(
            status_code=400,
            detail=f"La estación con el ID {estacion.id} ya se encuentra registrada.",
        )
    return crud.crear_estacion_db(db=db, estacion=estacion)


@app.get(
    "/estaciones/stats",
    responses={
        200: {"description": "Resumen ejecutivo obtenido exitosamente"},
        500: {"description": "Error interno del servidor"},
    },
    tags=["Gestión de Estaciones"],
    summary="Listar todas las estaciones registradas con estadísticas",
    description="Devuelve la cantidad total de estaciones, el listado y la estación con la lectura más alta.",
)
async def listar_estaciones(db: Session = Depends(get_db)):
    total_estaciones = db.query(models.Estacion).count()

    lectura_maxima = db.query(func.max(models.LecturaDB.valor)).scalar()
    estacion_record_alta = None

    if lectura_maxima is not None:
        registro_maximo = (
            db.query(models.LecturaDB)
            .filter(models.LecturaDB.valor == lectura_maxima)
            .first()
        )
        if registro_maximo:
            estacion_obj = (
                db.query(models.Estacion)
                .filter(models.Estacion.id == registro_maximo.estacion_id)
                .first()
            )
            if estacion_obj:
                estacion_record_alta = {
                    "estacion_id": estacion_obj.id,
                    "nombre": estacion_obj.nombre,
                    "lectura_mas_alta": lectura_maxima,
                }

    return {
        "cantidad_total_estaciones": total_estaciones,
        "estacion_con_lectura_mas_alta": estacion_record_alta
        if estacion_record_alta
        else "No hay lecturas registradas aún",
        "estaciones": crud.obtener_todas_estaciones(db),
    }


@app.post(
    "/lectura/",
    status_code=201,
    responses={
        201: {"description": "Lectura registrada exitosamente"},
        400: {"description": "Solicitud inválida"},
        404: {"description": "Estación no encontrada"},
        500: {"description": "Error interno del servidor"},
    },
    tags=["Telemetría de Sensores"],
    summary="Recibir datos de telemetría",
    description="Recibe el valor capturado por un sensor y lo vincula a una estación existente mediante su ID",
)
def registrar_lectura(lectura: schemas.LecturaCreate, db: Session = Depends(get_db)):
    estacion = crud.obtener_estacion_por_id(db, estacion_id=lectura.estacion_id)
    if not estacion:
        raise HTTPException(status_code=404, detail="Estación no existe")
    crud.crear_lectura_db(db=db, lectura=lectura)
    return {"status": "Lectura guardada en DB"}


@app.get(
    "/estaciones/{id}/riesgo",
    responses={
        200: {"description": "Nivel de riesgo obtenido exitosamente"},
        404: {"description": "Estación no encontrada"},
        500: {"description": "Error interno del servidor"},
    },
    tags=["Análisis de Riesgo"],
    summary="Evaluar nivel de peligro actual de una estación",
    description="Analiza la última lectura registrada y determina si el estado es 'Normal', 'Alerta' o 'Peligro'",
)
async def obtener_riesgo_estacion(id: int, db: Session = Depends(get_db)):
    estacion_existe = crud.obtener_estacion_por_id(db, estacion_id=id)
    if not estacion_existe:
        raise HTTPException(status_code=404, detail="Estación no encontrada")

    lecturas = crud.obtener_lecturas_por_estacion(db, estacion_id=id)
    if not lecturas:
        return {"id": id, "nivel": "SIN DATOS", "valor": 0}

    ultima_lectura = lecturas[-1].valor
    if ultima_lectura > 20:
        nivel = "Peligro"
    elif ultima_lectura > 10:
        nivel = "Alerta"
    else:
        nivel = "Normal"
    return {"id": id, "nivel": nivel, "valor": ultima_lectura}


@app.get(
    "/estaciones/{id}/historial",
    responses={
        200: {"description": "Historial de lecturas obtenido exitosamente"},
        404: {"description": "Estación no encontrada"},
        500: {"description": "Error interno del servidor"},
    },
    tags=["Análisis de Riesgo"],
    summary="Obtener historial de lecturas y nivel de riesgo promedio",
    description="Proporciona un resumen del historial de lecturas y calcula el nivel de riesgo promedio",
)
async def obtener_historial_estacion(id: int, db: Session = Depends(get_db)):
    estacion_existe = (
        db.query(models.LecturaDB).filter(models.LecturaDB.estacion_id == id).first()
    )
    if not estacion_existe:
        raise HTTPException(status_code=404, detail="Estación no encontrada")

    lecturas = crud.obtener_lecturas_por_estacion(db, estacion_id=id)
    numero_lecturas = len(lecturas)
    media = sum(l.valor for l in lecturas) / numero_lecturas if numero_lecturas else 0
    return {"media": media, "lecturas": lecturas, "numero_lecturas": numero_lecturas}


@app.get("/health")
def health_check():
    return {"check": "Servicios Cloud operativos"}