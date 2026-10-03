# 🤖 Agente Orquestador — CommunityLab

<p align="center">
  <strong>Coordinando el flujo inteligente de procesamiento de testimonios</strong>
</p>

---

## 📌 Descripción

El **Agente Orquestador** es un componente del proyecto **CommunityLab** encargado de coordinar el procesamiento de mensajes y conectar las diferentes etapas del flujo de trabajo.

Su propósito es facilitar la transformación de mensajes recibidos en información estructurada y contenido que pueda utilizarse para la creación de publicaciones en LinkedIn.

## 🎯 Objetivo

Centralizar la coordinación del flujo de procesamiento, permitiendo:

* 📩 Recibir y procesar mensajes.
* 🔎 Identificar testimonios relevantes.
* 🧩 Extraer y estructurar la información.
* 📄 Representar los datos en formato JSON.
* ✍️ Generar borradores de publicaciones para LinkedIn.

## ⚙️ Flujo de procesamiento

El flujo de testimonios se organiza en las siguientes etapas:

```text
📩 Recepción del mensaje
          │
          ▼
🔎 Evaluación del contenido
          │
          ▼
🧩 Extracción de información
          │
          ▼
📄 Estructuración de datos (JSON)
          │
          ▼
✍️ Generación del borrador
          │
          ▼
💼 Publicación para LinkedIn
```

> **Nota:** El flujo contempla la generación de un borrador para LinkedIn; su publicación automática no se da por implementada.

## 🛠️ Tecnologías

| Tecnología    | Uso                         |
| ------------- | --------------------------- |
| 🐍 Python     | Lógica y procesamiento      |
| 💬 Discord.py | Integración con Discord     |
| 📦 JSON       | Estructuración de los datos |

## 📂 Estructura del directorio

```text
agentes/
└── orquestador/
    └── README.md
```

Este directorio centraliza la documentación y la futura implementación del agente orquestador dentro de la arquitectura de CommunityLab.

## 🚧 Estado del desarrollo

* [x] Creación de la rama de trabajo.
* [x] Creación del directorio del agente.
* [x] Documentación inicial del componente.
* [ ] Integración del código del orquestador en este directorio.
* [ ] Documentación de instalación y configuración.
* [ ] Pruebas del flujo completo.
* [ ] Documentación de la integración con los demás agentes.

## 🔮 Próximos pasos

* 🧱 Integrar la implementación del orquestador en la estructura del proyecto.
* 🔗 Definir la comunicación con los demás componentes.
* 🧪 Validar el procesamiento de testimonios mediante pruebas.
* 📚 Documentar la configuración y ejecución del agente.
* 🚀 Preparar el flujo para su integración con el sistema completo.

---

<p align="center">
  💡 <strong>CommunityLab</strong><br>
  <em>Transformando conversaciones en información y contenido de valor.</em>
</p>

---

# ☕ Backend Java — CommunityLab

[![Java](https://img.shields.io/badge/Java-21--LTS-orange?style=flat&logo=openjdk)](https://www.oracle.com/java/)
[![Spring Boot](https://img.shields.io/badge/Spring_Boot-3.x-brightgreen?style=flat&logo=springboot)](https://spring.io/projects/spring-boot)
[![Lombok](https://img.shields.io/badge/Lombok-Library-yellow?style=flat)](https://projectlombok.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?style=flat&logo=docker)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![OCI](https://img.shields.io/badge/Oracle_Cloud-OCI-red?style=flat&logo=oracle)](https://www.oracle.com/cloud/)

---

## 🛠️ Tecnologías Empleadas

| Capa / Componente | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Core / Lenguaje** | Java 21 | Lenguaje principal de desarrollo backend (versión LTS). |
| **Framework** | Spring Boot / Spring Data JPA | Desarrollo ágil de APIs REST y mapeo objeto-relacional. |
| **Productividad** | Lombok | Eliminación de código repetitivo (Getters, Setters, constructores). |
| **Contenedores** | Docker & Docker Compose | Estandarización y levantamiento local de servicios (Base de Datos). |
| **Base de Datos** | PostgreSQL | Persistencia relacional de interacciones y resultados consolidados. |
| **Cloud / Storage** | OCI Object Storage | Gestión de respaldos y archivos en la nube de Oracle. |

---

## 📋 Hoja de Ruta y División de Tareas - Backend (Team Backend)

Para evitar cruces en Git y optimizar el desarrollo en paralelo entre los tres integrantes, el proyecto se divide según su arquitectura de paquetes:

### 1. 🗄️ Módulo de Persistencia y Modelos (`model/`, `model/enums/`, `repository/`)
* **Responsable:** [Integrante 1]
* **`model/` e `model/enums/`**: Implementación de las entidades JPA (`PackageResult`, `Interaction`) con su relación bidireccional y las enumeraciones de seguridad de tipos (`TipoAutor`, `ClasificacionSentimiento`).
* **`repository/`**: Creación de las interfaces `InteractionRepository` y `PackageResultRepository` para la gestión de base de datos con Spring Data JPA.
# ❎

### 2. 🔌 Módulo de Controladores y Contratos (`controller/`, `dto/`)
* **Responsable:** [Integrante 2]
* **`dto/`**: Definición de los objetos de transferencia de datos (`CommunityInputDto`, `PackageOutputDto`) para asegurar el contrato JSON estricto con Streamlit y Python.
* **`controller/`**: Exposición de los endpoints REST (`CommunityController`, `OciStorageController`) para la recepción de lotes de interacciones y gestión de reportes.
# ❎

### 3. ⚙️ Módulo de Servicios, Clientes e Infraestructura (`service/`, `client/`, `config/`)
* **Responsable:** [Integrante 3]
* **`service/`**: Lógica de negocio principal (`ProcessingService`, `OciStorageService`) y orquestación del control de tokens y métricas.
* **`client/`**: Conexión HTTP externa mediante `PythonAiClient` hacia el microservicio de IA en FastAPI.
* **`config/`**: Configuraciones globales y Beans (`OciConfig`, `RestClientConfig`).
# ❎

---
## 📂 Estructura del Proyecto

El proyecto sigue una arquitectura por capas desacoplada para garantizar mantenibilidad, seguridad y robustez:

```text
com.insightedulab.backend_java/
│
├── 📁 config/                 # Configuraciones globales (CORS, Beans, etc.)
├── 📁 controller/             # Controladores REST (Exponen endpoints y manejan HTTP)
├── 📁 dto/                    # Objetos de Transferencia de Datos (Request y Response)
├── 📁 exception/              # Manejo global de excepciones y respuestas de error personalizadas
├── 📁 model/                  # Entidades JPA (Base de datos)
│   └── 📁 enums/              # Enumeraciones del dominio (ej. TipoAutor, Sentimiento)
├── 📁 repository/             # Interfaces de acceso a datos (Spring Data JPA)
├── 📁 security/               # Filtros, configuración de Spring Security y JWT
└── 📁 service/                # Lógica de negocio e integraciones externas (OCI, etc.)
```
## Estado actual de los DTOs 📋
Con este último, ya tienes la arquitectura de datos de entrada y salida totalmente sólida:

* Entrada: `CommunityProcessRequestDto`, `InteractionInputDto`, `CurationRequestDto`.

* Salida: `CommunityProcessResponseDto`, `InteractionResponseDto`, `OciUploadResponseDto`, `PackageResultResponseDto`.

# Lo que sigue a desarrollar:

### 🛡️ Capas de Seguridad y Excepciones
1. Módulo de Seguridad (`/security`)
   Propósito: Gestionar la autenticación y autorización de las peticiones HTTP mediante tokens (JWT) y filtros personalizados de Spring Security.

* Componentes principales: Configuración de filtros de seguridad, codificación de contraseñas y validación de credenciales para proteger los endpoints de la API.

2. Manejo de Excepciones (`/exception`)
* 
* Propósito: Centralizar la captura de errores en toda la aplicación para evitar stack traces expuestos al cliente y estandarizar el formato de las respuestas HTTP en caso de fallos.

* Componentes principales:

* Clases de excepciones personalizadas (ej. recursos no encontrados, errores de validación).

* Un manejador global (`@ControllerAdvice`) que intercepta las excepciones y devuelve un JSON estructurado con el código de estado, mensaje descriptivo y marca de tiempo.
___
# 🐳 Despliegue e Infraestructura con Docker Compose
Este proyecto cuenta con un entorno containerizado utilizando **Docker y Docker Compose** para orquestar de forma automatizada la aplicación backend en Java 21 (Spring Boot) y la base de datos relacional PostgreSQL.

🛠️ Componentes de la Arquitectura

* Servicio de Base de Datos (`postgres`):
° Imagen oficial de PostgreSQL (`postgres:latest`) configurada mediante variables de entorno seguras para el aislamiento de credenciales y persistencia de datos.
* Servicio de Backend (`backend-java`):
° Construcción optimizada mediante un `Dockerfile` multi-etapa ubicado en el subdirectorio del microservicio.
° Mapeo de puertos hacia el host local (`8000:8080`) y comunicación interna mediante redes privadas de Docker con el servicio de base de datos.

# ⚙️ Gestión de Configuración y Seguridad
° Variables de Entorno: Se implementó un archivo **.env** en la raíz del proyecto para la gestión centralizada y segura de credenciales sensibles (excluido del control de versiones mediante **.gitignore**).

° Estandarización: Uso de un archivo plantilla (**.env.example**) para facilitar la configuración inicial de los colaboradores del equipo.

# Instrucciones de Ejecución
Para levantar todo el ecosistema de servicios y compilar la aplicación desde la raíz del proyecto, ejecuta el siguiente comando:

````bash
docker compose up --build
````
# 🐳 ¿Por qué necesitamos Docker Desktop?

Para ejecutar este proyecto de manera local, Docker Desktop es una herramienta indispensable por las siguientes razones:

1- Entornos Aislados y Consistentes (Elimina el "en mi máquina funciona"): Docker empaqueta la aplicación de Spring Boot (Java 21) junto con todas sus dependencias y el motor de la base de datos PostgreSQL en contenedores independientes. Esto garantiza que el comportamiento del software sea exactamente el mismo tanto en la computadora de cualquier miembro del equipo como en el servidor de producción.

2- Orquestación con Docker Compose: Permite levantar y conectar múltiples servicios de forma simultánea (el contenedor del backend y el contenedor de PostgreSQL) utilizando un único comando (**docker compose up --build**), configurando redes internas automáticas sin necesidad de instalar bases de datos o runtimes complejos directamente en el sistema operativo.

3- Gestión de Recursos y Variables de Entorno: Facilita la inyección segura de credenciales mediante archivos **.env** y mapeo de puertos hacia la máquina host de manera limpia y controlada.

# 🔗 Enlace de descarga oficial
Puedes descargar la versión correspondiente para tu sistema operativo (Windows, macOS o Linux) desde el sitio web oficial:

° [Sitio Oficial de Docker Desktop](https://www.docker.com/products/docker-desktop/)

> ⚠️ *Nota: Los nombres de las clases y entidades están a modo de sugerencia y están dispuestos a modificaciones según avance el desarrollo.*