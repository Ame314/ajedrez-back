import os
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración SMTP
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Servidor Escolar de Ajedrez")

# Configuración de la aplicación
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Configuración de la base de datos
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongo:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "ajedrez_db") 