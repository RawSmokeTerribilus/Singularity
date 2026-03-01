# Dashboard de Monitorización (Real-Time)

> **"Status at a glance. Control from anywhere."**

Singularity Core incluye un **Dashboard Web ligero** basado en FastAPI diseñado para monitorizar el progreso de tus tareas de larga duración (como el God Mode o subidas masivas) sin necesidad de estar pegado a la terminal.

## 🎯 ¿Para qué sirve?

*   **Monitorización Remota:** Visualiza el estado del sistema desde tu móvil, tablet u otro ordenador en la red local.
*   **Barras de Progreso Reales:** Muestra el porcentaje completado de las fases del pipeline.
*   **Historial de Tareas:** Indica qué está haciendo exactamente cada módulo en tiempo real.
*   **Resiliencia Visual:** El dashboard se auto-actualiza cada 5 segundos.

## 🛠️ ¿Cómo acceder?

El dashboard se inicia automáticamente en segundo plano cuando lanzas Singularity Core.

1.  **Asegúrate de que el contenedor está corriendo:** `make up`.
2.  **Abre tu navegador preferido.**
3.  **Introduce la dirección:**
    *   Si estás en la misma máquina: `http://localhost:8002`
    *   Desde otro dispositivo: `http://<IP_DEL_SERVIDOR>:8002`

## 🖥️ Interfaz y Datos

El panel presenta una serie de **Tarjetas de Módulo** que contienen:

| Campo | Descripción |
| :--- | :--- |
| **Módulo** | Identificador del sistema (CORE, PIPELINE, MKVERYTHING, etc.). |
| **Tarea** | El nombre de la operación actual (ej: "Fase 1: MKVerything"). |
| **Estado** | Estado operativo (ONLINE, IN_PROGRESS, SUCCESS, ERROR). |
| **Progreso** | Barra visual y porcentaje (solo para tareas compatibles). |
| **Detalles** | Información adicional (ej: "Extrayendo ISO: Pelicula.iso"). |
| **Última Actualización** | Tiempo transcurrido desde el último reporte del motor. |

## ⚙️ Funcionamiento Técnico (Para Admins)

*   **Puerto:** 8002 (Configurable en `core/dashboard.py`).
*   **Motor:** FastAPI + Jinja2 Templates + Uvicorn.
*   **Persistencia:** Los datos se leen desde [./logs/current_status.json](./logs/current_status.json).
*   **Seguridad:** El dashboard es de **Solo Lectura**. No acepta entradas del usuario ni permite ejecución de comandos, lo que lo hace seguro para exponer en redes locales.

## 🚀 Cómo Probarlo (Test Rápido)

1.  Lanza la suite: `make attach`.
2.  Entra en el **Singularity Mode (Opción 5)**.
3.  Configura una tarea mínima.
4.  En cuanto veas que la terminal empieza a trabajar, abre `http://localhost:8002`.
5.  Deberías ver la tarjeta **PIPELINE** en estado `IN_PROGRESS` con su barra de progreso moviéndose.
