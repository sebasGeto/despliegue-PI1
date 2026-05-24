# Consultorio Jurídico ICESI — Buró

Sistema web para la gestión integral de citas y atención del Consultorio Jurídico de la Universidad ICESI. Permite a beneficiarios, secretarías, profesores y estudiantes gestionar el ciclo completo de citas (agendar, confirmar, cancelar, reagendar y consultar), con respaldo de reportes y métricas para auditoría.

---

## Equipo T5 — Gestión de Citas y Atención

| Integrante | Rol |
|---|---|
| Luciano Barbosa | Desarrollador |
| Karen Andrade Mosquera | Desarrolladora |
| Samuel Cifuentes | Desarrollador |
| Sebastian Romero | Desarrollador |
| Juan Camilo Criollo | Desarrollador |

---

## Stack Tecnológico

- **Backend:** Django 6.0.3 (Python 3.14)
- **Base de datos:** SQLite (desarrollo) / PostgreSQL (producción)
- **Frontend:** HTML + CSS + JavaScript vanilla (templates Django)
- **Despliegue:** Railway
- **Control de versiones:** Git + GitHub
- **Gestión de proyecto:** Jira (SCRUM)

---

## Arquitectura

El proyecto sigue una arquitectura modular basada en apps de Django. Cada app encapsula un dominio funcional:

```
ConsultorioJuridico/
├── consultorio/          # Configuración raíz del proyecto
├── usuarios/             # Autenticación y modelo de usuario
├── citas/                # Núcleo: casos, horarios, citas, asistencia
├── recordatorios/        # Envío y registro de recordatorios automáticos
├── notificaciones/       # Notificaciones internas (secretaría)
├── consentimiento/       # Tratamiento de datos personales
├── reportes/             # Métricas y reportes
└── templates/            # Templates compartidos (base, dashboard)
```

---

## Instalación local

### Requisitos previos
- Python 3.12+
- pip
- Git

### Pasos

* Equipo de Desarrollo: Todos los integrantes.
* Scrum Master: Karen Mosquera.
* Product Owner: Luciano Barbosa.
1. Clonar el repositorio:
```bash
git clone https://github.com/ICESI-PI1-202601/20261-g1-pi1-dreamteam.git
cd 20261-g1-pi1-dreamteam/ConsultorioJuridico
```

2. Crear y activar entorno virtual:
```bash
python -m venv venv
source venv/bin/activate    # macOS/Linux
venv\Scripts\activate       # Windows
```

# Sprint 2

## Entregables del Sprint 2

* Base de datos relacional
* Despliegue probado.
* HU y Ti asignadas al sprint.
* Seguimientos semanales.
* Implementacion del proyecto
3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Aplicar migraciones:
```bash
python manage.py migrate
```

5. Crear superusuario:
```bash
python manage.py createsuperuser
```

6. (Opcional) Poblar la base de datos con datos de prueba:
```bash
python manage.py populate_db
```

7. Levantar el servidor:
```bash
python manage.py runserver
```

El sistema queda disponible en `http://127.0.0.1:8000/`.

---

## Roles del sistema

| Rol | Permisos principales |
|---|---|
| **Beneficiario** | Agendar, consultar, confirmar, cancelar y reagendar sus propias citas |
| **Estudiante** | Consultar casos asignados |
| **Profesor** | Supervisión académica |
| **Secretaria** | Gestión completa de citas y casos, marcar asistencia |
| **Administrador** | Acceso total al sistema |

La autenticación se realiza por **documento de identidad + contraseña** mediante un backend personalizado (`DocumentoBackend`).


## 4. Estructura de URLs
### usuarios/urls.py:

* /login/ - Inicio de sesión
* /registro/ - Paso 1 del registro
* /registro/paso2/ - Paso 2 del registro
* /logout/ - Cierre de sesión

## citas/urls.py:

* /home/ - Dashboard principal
* /gestionar-citas/ - Gestión de citas
* /gestionar-casos/ - Gestión de casos
* /agendar-cita/ - Crear nueva cita
* /citas/<pk>/confirmar/ - Confirmar cita
* /citas/<pk>/cancelar/ - Cancelar cita
* /citas/<pk>/posponer/ - Posponer cita

## 5. Seguridad y Control de Acceso

* Decorador @login_required en todas las vistas de usuario
* Validación de propiedad: usuarios solo ven sus propias citas y casos
* Protección de relaciones (PROTECT en claves foráneas de horarios)
* Validación de máquina de estados para evitar transiciones inválidas
* Almacenamiento seguro de contraseñas con hash


---

## Comandos útiles

```bash
# Correr suite completa de tests
python manage.py test

# Correr tests de una app específica
python manage.py test citas

# Enviar recordatorios automáticos (job programable)
python manage.py enviar_recordatorios

# Poblar base de datos con datos de prueba
python manage.py populate_db
```

---

### Flujo de trabajo

1. Cada HU/TT se trabaja en una rama feature: `feat/nombre-hu` o `chore/nombre-tt`.
2. Cada subtarea genera un commit semántico (`feat`, `fix`, `chore`, `test`, `docs`).
3. Al completar una HU/TT, se abre un Pull Request hacia `develop`.
4. Tras revisión y aprobación, se hace merge a `develop`.
5. `main` se actualiza al cierre de cada Sprint.

### Convención de commits

```
<tipo>(<HU/TT>): <descripción corta>

<descripción extendida opcional>

Refs: <ID de Jira>
```

---

## Sprint 0 — Análisis y Diseño (2 feb – 16 feb)

**Objetivo:** Preparar el entorno, definir arquitectura y establecer las bases del desarrollo.

13 tareas técnicas completadas (100 puntos):
- Modelo de datos (MER y MR)
- Flujos BPM de agendamiento, confirmación, recordatorio, reagendamiento y cancelación
- Definición de estados y reglas de negocio del flujo de citas
- Esquema de seguridad y privacidad
- Diseño de Dashboard de métricas
- Sistema visual y paleta de colores
- Estructura de integración con módulo de comunicaciones
- Métricas de desempeño del módulo

---

## Sprint 1 — Funcionalidades base (25 mar – 7 abr)

**Objetivo:** Implementar el núcleo del sistema de gestión de citas.

5 HUs entregadas (25 puntos):
- **HU1** — Registro de citas en el sistema
- **HU2** — Confirmación digital de citas
- **HU3** — Registro y control de asistencia
- **HU13** — Registro de consentimiento informado
- **HU17** — Actualización automática del estado tras cancelación

### Componentes implementados

- Modelo `Usuario` personalizado con autenticación por documento
- Sistema de roles (5 roles)
- Modelos `Caso`, `HorarioDisponible`, `Cita`, `RegistroAsistencia`
- Máquina de estados de citas con transiciones validadas
- Registro en 2 pasos con consentimiento (Ley 1581 de 2012)
- Panel administrativo de Django personalizado
- Validaciones de lógica de negocio y propiedad de datos

---

## Sprint 2 — Ciclo de vida de la cita (13 abr – 27 abr)

**Objetivo:** Cerrar el ciclo de vida completo de las citas y dejar el sistema desplegado.

6 HUs + 9 TTs completadas (70 puntos):
- **HU4** — Reagendamiento de citas (atómico)
- **HU5** — Cancelación de citas con motivo
- **HU6** — Envío de recordatorios automáticos
- **HU11** — Agendamiento por llamada telefónica
- **HU12** — Actualización automática del calendario en tiempo real
- **HU16** — Notificación a secretaría ante reagendamiento

### Componentes técnicos
- Configuración de entorno de despliegue (Railway)
- Configuración de base de datos PostgreSQL en producción
- Repositorio Git con flujo de ramas formal
- Pruebas de despliegue end-to-end
- Documentación de proceso de despliegue y rollback

---

## Sprint 3 — Sprint Final (5 may – 26 may)

**Objetivo:** Entregar un MVP estable y desplegado, con módulo de reportes y trazabilidad completa.

7 HUs + 4 TTs comprometidas (51 puntos).

### HUs Must
- **HU8** — Consulta del estado de la cita
- **HU10** — Validación automática de disponibilidad 
- **HU9** — Historial de citas
- **HU18** — Exportación de reporte de asistencia (PDF/Excel)

### HUs Should
- **HU7** — Generación automática de métricas de asistencia
- **HU15** — Registro de entrega de recordatorios

### HUs Could
- **HU14** — Marcado automático de citas no confirmadas

### Tareas técnicas
- **TT-23** — Estabilización del despliegue en Railway
- **TT-24** — Limpieza de deuda técnica
- **TT-25** — Pruebas funcionales end-to-end del MVP
- **TT-26** — Tema claro/oscuro configurable

---

## Cumplimiento normativo

El sistema cumple con:
- **Ley 1581 de 2012** (Habeas Data) — Protección de datos personales
- **Ley 2113 de 2021** — Reglamentación de consultorios jurídicos
- **Decreto 2069 de 2023** — Indicadores y reportes de gestión

---

## Estructura de ramas

```
main          ← Producción estable
└── develop   ← Integración continua
    ├── feat/<nombre-hu>     ← Funcionalidades nuevas
    ├── chore/<nombre-tt>    ← Tareas técnicas
    └── fix/<descripción>    ← Correcciones
```