import os
from typing import Optional
from dotenv import load_dotenv
import socket

# Detectar si estamos en Docker
def is_running_in_docker():
    try:
        # Verificar si existe el archivo /.dockerenv (presente en contenedores Docker)
        return os.path.exists('/.dockerenv')
    except:
        return False

# Cargar variables de entorno desde .env
if is_running_in_docker():
    load_dotenv()  # Usar .env para Docker
    print("Ejecutándose en Docker - usando configuración Docker")
else:
    # Intentar cargar .env.local primero, luego .env como fallback
    if os.path.exists('.env.local'):
        load_dotenv('.env.local')
        print("Ejecutándose localmente - usando .env.local")
    else:
        load_dotenv()
        print("Ejecutándose localmente - usando .env")

# Configuración SMTP
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Servidor Escolar de Ajedrez")

# Configuración de la aplicación
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Configuración de la base de datos con detección automática de entorno
if is_running_in_docker():
    # En Docker, usar el nombre del servicio
    DEFAULT_MONGODB_URL = "mongodb://mongo:27017"
else:
    # En local, usar localhost
    DEFAULT_MONGODB_URL = "mongodb://localhost:27017"

MONGODB_URL = os.getenv("MONGODB_URL", DEFAULT_MONGODB_URL)
DATABASE_NAME = os.getenv("DATABASE_NAME", "ajedrez_db")

print(f"MongoDB URL configurada: {MONGODB_URL}")
print(f"Base de datos: {DATABASE_NAME}") 