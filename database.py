"""
database.py
Manejo de la base de datos SQLite para reportes e historial de IA.
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from datetime import datetime

Base = declarative_base()

class Reporte(Base):
    __tablename__ = 'reportes'
    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, default=datetime.now)
    ecuacion = Column(String(255))
    x = Column(Float)
    y = Column(Float)
    concentracion = Column(Float)
    comentario = Column(Text)

class HistorialIA(Base):
    __tablename__ = 'historial_ia'
    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, default=datetime.now)
    pregunta = Column(Text)
    respuesta = Column(Text)
    contexto = Column(Text)

# Ruta absoluta: la BD siempre se crea junto a este archivo, sin importar desde dónde se ejecute.
_RUTA_BD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_contaminacion.db')
engine = create_engine(f'sqlite:///{_RUTA_BD}')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def guardar_reporte(ecuacion, x, y, concentracion, comentario):
    session = Session()
    nuevo_reporte = Reporte(
        ecuacion=ecuacion,
        x=x,
        y=y,
        concentracion=concentracion,
        comentario=comentario
    )
    session.add(nuevo_reporte)
    session.commit()
    session.close()

def guardar_historial_ia(pregunta, respuesta, contexto):
    session = Session()
    nuevo_historial = HistorialIA(
        pregunta=pregunta,
        respuesta=respuesta,
        contexto=contexto
    )
    session.add(nuevo_historial)
    session.commit()
    session.close()

def obtener_historial_ia(limit=10):
    session = Session()
    historial = session.query(HistorialIA).order_by(HistorialIA.fecha.desc()).limit(limit).all()
    session.close()
    return historial
