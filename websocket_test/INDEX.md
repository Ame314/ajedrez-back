# 📂 Estructura de la Carpeta websocket_test

## 📁 Archivos Organizados

```
websocket_test/
├── 📋 Documentación
│   ├── README.md              # Guía principal y inicio rápido
│   ├── TESTING_GUIDE.md       # Guía detallada de testing
│   ├── EXAMPLES.md            # Ejemplos específicos de uso
│   └── INDEX.md               # Este archivo
│
├── 🧪 Scripts de Testing
│   ├── quick_test.py          # Prueba rápida básica (30 seg)
│   ├── test_full_game.py      # Simulación partida completa (1 min)
│   ├── test_websockets.py     # Testing interactivo manual
│   └── test_automated.py      # Suite automatizada completa
│
├── 🌐 Interfaz Web
│   └── websocket_tester.html  # Tester visual en navegador
│
└── ⚙️ Configuración
    ├── requirements.txt       # Dependencias Python
    └── setup.bat             # Script de instalación automática
```

## 🎯 Propósito de Cada Archivo

### 📋 Documentación

| Archivo | Propósito | Cuándo usar |
|---------|-----------|-------------|
| `README.md` | Introducción general y guía de inicio rápido | Primera vez usando los tests |
| `TESTING_GUIDE.md` | Guía detallada con debugging y solución de problemas | Cuando necesites entender algo específico |
| `EXAMPLES.md` | Ejemplos prácticos y casos de uso específicos | Para copiar/pegar comandos y entender escenarios |
| `INDEX.md` | Este índice de archivos | Para entender la estructura |

### 🧪 Scripts de Testing

| Archivo | Duración | Nivel | Propósito |
|---------|----------|-------|-----------|
| `quick_test.py` | 30 seg | Básico | Verificación rápida que todo funciona |
| `test_full_game.py` | 1 min | Intermedio | Simula partida completa entre 2 jugadores |
| `test_websockets.py` | Variable | Avanzado | Control manual completo, debugging |
| `test_automated.py` | 45 seg | Intermedio | Suite automatizada con reporte detallado |

### 🌐 Interfaz Web

| Archivo | Características | Mejor para |
|---------|-----------------|------------|
| `websocket_tester.html` | Visual, interactivo, tiempo real | Testing manual, debugging visual, demostraciones |

### ⚙️ Configuración

| Archivo | Propósito | Cuándo usar |
|---------|-----------|-------------|
| `requirements.txt` | Lista de dependencias Python | Instalación manual con pip |
| `setup.bat` | Configuración automática completa | Primera instalación en Windows |

## 🚀 Flujo de Uso Recomendado

### 1. Primera vez - Configuración

```bash
# Opción A: Automática (Windows)
setup.bat

# Opción B: Manual
pip install -r requirements.txt
```

### 2. Testing diario - Verificación rápida

```bash
python quick_test.py
```

### 3. Testing de funcionalidades - Completo  

```bash
python test_full_game.py
```

### 4. Debugging específico - Manual

```bash
python test_websockets.py
# o abrir websocket_tester.html
```

### 5. Testing exhaustivo - Automatizado

```bash
python test_automated.py
```

## 📊 Matriz de Funcionalidades

| Funcionalidad | quick_test | test_full_game | test_websockets | websocket_tester | test_automated |
|---------------|------------|----------------|-----------------|------------------|----------------|
| ✅ Login | ✅ | ✅ | ✅ | ✅ | ✅ |
| ✅ WebSocket | ✅ | ✅ | ✅ | ✅ | ✅ |
| ✅ Ping/Pong | ✅ | ✅ | ✅ | ✅ | ✅ |
| ✅ Matchmaking | ✅ | ✅ | ✅ | ✅ | ✅ |
| ✅ Partida completa | ❌ | ✅ | ⚠️ Manual | ⚠️ Manual | ✅ |
| ✅ Movimientos | ❌ | ✅ | ✅ | ✅ | ⚠️ Básico |
| ✅ Chat | ❌ | ✅ | ✅ | ✅ | ❌ |
| ✅ Rendición | ❌ | ❌ | ✅ | ✅ | ❌ |
| ✅ Debugging | ⚠️ Básico | ⚠️ Básico | ✅ | ✅ | ⚠️ Básico |
| ✅ Visual | ❌ | ❌ | ❌ | ✅ | ❌ |
| ✅ Automatizado | ✅ | ✅ | ❌ | ❌ | ✅ |

### Leyenda

- ✅ = Totalmente soportado
- ⚠️ = Parcialmente soportado / Manual
- ❌ = No soportado

## 🎮 Casos de Uso Específicos

### Para Desarrollador Backend

1. **Cambio de código** → `quick_test.py`
2. **Nueva funcionalidad** → `test_full_game.py`
3. **Bug específico** → `test_websockets.py`

### Para QA/Testing

1. **Regression testing** → `test_automated.py`
2. **Manual testing** → `websocket_tester.html`
3. **Edge cases** → `test_websockets.py`

### Para Demo/Presentación

1. **Demo visual** → `websocket_tester.html`
2. **Demo automática** → `test_full_game.py`

### Para CI/CD

1. **Pipeline testing** → `test_automated.py`
2. **Smoke tests** → `quick_test.py`

## 🔧 Personalización

### Modificar credenciales por defecto

En cada script Python, buscar y cambiar:

```python
EMAIL = "test@example.com"
PASSWORD = "password123"
```

### Cambiar servidor

```python
BASE_URL = "http://localhost:8000"  # Cambiar si es necesario
```

### Añadir timeouts

```python
TIMEOUT = 5.0  # Aumentar para conexiones lentas
```

---

**🎯 Con esta estructura organizada puedes probar eficientemente cualquier aspecto de tu sistema WebSocket de ajedrez.**
