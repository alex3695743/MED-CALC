# MED-CALC

Aplicación web para el cálculo de la tasa de filtrado glomerular estimada (eGFR) mediante las ecuaciones CKD-EPI.

## Requisitos

Antes de empezar, instala:

- [Node.js](https://nodejs.org/) 20.19 o superior.
- [Python](https://www.python.org/downloads/) 3.11 o superior, con `pip`.

El proyecto usa `pnpm` para el frontend. Corepack se incluye con Node.js y permite usarlo sin instalarlo de forma global.

## Instalación

Clona el repositorio y sitúate en la carpeta de la aplicación:

```bat
git clone <URL_DEL_REPOSITORIO>
cd MED-CALC\med-calc-app
```

### Backend

Desde `med-calc-app`, crea el entorno virtual e instala las dependencias:

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Frontend

En otra terminal, desde `med-calc-app`, instala las dependencias del frontend:

```bat
cd frontend
corepack enable
pnpm install --frozen-lockfile
```

## Ejecutar la aplicación

Se necesitan dos terminales, una para el backend y otra para el frontend.

### 1. Iniciar el backend

Desde `med-calc-app\backend`:

```bat
.venv\Scripts\activate
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

La documentación interactiva de la API estará disponible en [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 2. Iniciar el frontend

Desde `med-calc-app\frontend`:

```bat
pnpm dev
```

Abre la dirección que muestre Vite, normalmente [http://localhost:5173](http://localhost:5173/). El frontend se comunica con el backend local en el puerto 8000.

Para detener cualquiera de los servicios, pulsa `Ctrl+C` en su terminal.

## Ejecutar los tests

Con el backend detenido o iniciado, desde `med-calc-app\backend`:

```bat
.venv\Scripts\activate
python -m pip install -r tests\requirements.lock
python -m tests
```

Las pruebas están reunidas en `backend/tests/test_suite.py`. Al finalizar, se muestra el resultado en la terminal y se genera el informe `backend/tests/reports/latest-report.json`.
