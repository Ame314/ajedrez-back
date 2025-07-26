@echo off
echo 🚀 Configurando entorno de testing para WebSockets...
echo.

echo 📁 Creando entorno virtual...
python -m venv .venv
if %errorlevel% neq 0 (
    echo ❌ Error creando entorno virtual
    pause
    exit /b 1
)

echo 🔧 Activando entorno virtual...
call .venv\Scripts\activate.bat

echo 📦 Instalando dependencias...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Error instalando dependencias
    pause
    exit /b 1
)

echo.
echo ✅ ¡Configuración completada!
echo.
echo 🎯 Para ejecutar las pruebas:
echo   python quick_test.py          - Prueba rápida
echo   python test_full_game.py      - Partida completa  
echo   python test_websockets.py     - Testing interactivo
echo   websocket_tester.html         - Interfaz web
echo.
echo 📚 Ver documentación:
echo   README.md                     - Guía principal
echo   TESTING_GUIDE.md             - Guía detallada
echo   EXAMPLES.md                  - Ejemplos de uso
echo.
pause
