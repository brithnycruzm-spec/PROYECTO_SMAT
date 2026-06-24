from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models
from app import schemas
 
def obtener_estacion_por_id(db: Session, estacion_id: int):
    return db.query(models.Estacion).filter(models.Estacion.id == estacion_id).first()
 
def crear_estacion_db(db: Session, estacion: schemas.EstacionCreate):
    nueva_estacion = models.Estacion(id=estacion.id, nombre=estacion.nombre, ubicacion=estacion.ubicacion)
    db.add(nueva_estacion)
    db.commit()
    db.refresh(nueva_estacion)
    return nueva_estacion
 
# ── NUEVO: actualizar estación ──────────────────────────────
def actualizar_estacion_db(db: Session, estacion_id: int, datos: schemas.EstacionUpdate):
    estacion = db.query(models.Estacion).filter(models.Estacion.id == estacion_id).first()
    if not estacion:
        return None
    estacion.nombre = datos.nombre
    estacion.ubicacion = datos.ubicacion
    db.commit()
    db.refresh(estacion)
    return estacion
 
# ── NUEVO: eliminar estación ────────────────────────────────
def eliminar_estacion_db(db: Session, estacion_id: int):
    estacion = db.query(models.Estacion).filter(models.Estacion.id == estacion_id).first()
    if not estacion:
        return False
    # Eliminar lecturas asociadas primero para no violar FK
    db.query(models.LecturaDB).filter(models.LecturaDB.estacion_id == estacion_id).delete()
    db.delete(estacion)
    db.commit()
    return True
 
def contar_total_estaciones(db: Session):
    return db.query(models.Estacion).count()
 
def obtener_todas_estaciones(db: Session):
    return db.query(models.Estacion).all()
 
def obtener_lectura_maxima(db: Session):
    return db.query(func.max(models.LecturaDB.valor)).scalar()
 
def obtener_registro_lectura_maxima(db: Session, valor_maximo: float):
    return db.query(models.LecturaDB).filter(models.LecturaDB.valor == valor_maximo).first()
 
def crear_lectura_db(db: Session, lectura: schemas.LecturaCreate):
    nueva_lectura = models.LecturaDB(valor=lectura.valor, estacion_id=lectura.estacion_id)
    db.add(nueva_lectura)
    db.commit()
    return nueva_lectura
 
def obtener_lecturas_por_estacion(db: Session, estacion_id: int):
    return db.query(models.LecturaDB).filter(models.LecturaDB.estacion_id == estacion_id).all()
 
def verificar_existencia_lectura_estacion(db: Session, estacion_id: int):
    return db.query(models.LecturaDB).filter(models.LecturaDB.estacion_id == estacion_id).first()
 
# ── NUEVO: última lectura de una estación ───────────────────
def obtener_ultima_lectura(db: Session, estacion_id: int):
    return (
        db.query(models.LecturaDB)
        .filter(models.LecturaDB.estacion_id == estacion_id)
        .order_by(models.LecturaDB.id.desc())
        .first()
    )