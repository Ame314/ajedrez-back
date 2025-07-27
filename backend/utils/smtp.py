import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import secrets
import string
from typing import Optional
from config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_NAME, FRONTEND_URL

def generate_reset_token() -> str:
    """Genera un token seguro para restauración de contraseña"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))

def send_reset_email(email: str, token: str, username: str) -> bool:
    """
    Envía email de restauración de contraseña
    
    Args:
        email: Email del usuario
        token: Token de restauración
        username: Nombre de usuario
    
    Returns:
        bool: True si el email se envió correctamente
    """
    try:
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_USERNAME}>"
        msg['To'] = email
        msg['Subject'] = "Restauración de Contraseña - Servidor Escolar de Ajedrez"
        
        # Crear cuerpo del email
        reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
        
        html_content = f"""
        <html>
        <body>
            <h2>Restauración de Contraseña</h2>
            <p>Hola <strong>{username}</strong>,</p>
            <p>Has solicitado restablecer tu contraseña en el Servidor Escolar de Ajedrez.</p>
            <p>Para continuar con el proceso, haz clic en el siguiente enlace:</p>
            <p><a href="{reset_url}" style="background-color: #4CAF50; color: white; padding: 14px 20px; text-decoration: none; border-radius: 4px;">Restablecer Contraseña</a></p>
            <p>O copia y pega este enlace en tu navegador:</p>
            <p>{reset_url}</p>
            <p><strong>Este enlace expirará en 1 hora.</strong></p>
            <p>Si no solicitaste este cambio, puedes ignorar este email.</p>
            <br>
            <p>Saludos,</p>
            <p>Equipo del Servidor Escolar de Ajedrez</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_content, 'html'))
        
        # Crear contexto SSL
        context = ssl.create_default_context()
        
        # Conectar y enviar email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"Error enviando email: {e}")
        return False

async def create_reset_record(db, email: str, token: str) -> bool:
    """
    Crea un registro de restauración de contraseña en la base de datos
    
    Args:
        db: Conexión a la base de datos
        email: Email del usuario
        token: Token de restauración
    
    Returns:
        bool: True si se creó el registro correctamente
    """
    try:
        # Expiración en 1 hora
        expiration = datetime.utcnow() + timedelta(hours=1)
        
        reset_record = {
            "email": email,
            "token": token,
            "expires_at": expiration,
            "used": False
        }
        
        # Eliminar registros anteriores del mismo email
        await db.password_resets.delete_many({"email": email})
        
        # Insertar nuevo registro
        await db.password_resets.insert_one(reset_record)
        return True
        
    except Exception as e:
        print(f"Error creando registro de restauración: {e}")
        return False

async def verify_reset_token(db, token: str) -> Optional[str]:
    """
    Verifica si un token de restauración es válido
    
    Args:
        db: Conexión a la base de datos
        token: Token a verificar
    
    Returns:
        str: Email del usuario si el token es válido, None en caso contrario
    """
    try:
        reset_record = await db.password_resets.find_one({
            "token": token,
            "used": False,
            "expires_at": {"$gt": datetime.utcnow()}
        })
        
        if reset_record:
            return reset_record["email"]
        return None
        
    except Exception as e:
        print(f"Error verificando token: {e}")
        return None

async def mark_token_as_used(db, token: str) -> bool:
    """
    Marca un token como usado
    
    Args:
        db: Conexión a la base de datos
        token: Token a marcar
    
    Returns:
        bool: True si se marcó correctamente
    """
    try:
        result = await db.password_resets.update_one(
            {"token": token},
            {"$set": {"used": True}}
        )
        return result.modified_count > 0
        
    except Exception as e:
        print(f"Error marcando token como usado: {e}")
        return False 