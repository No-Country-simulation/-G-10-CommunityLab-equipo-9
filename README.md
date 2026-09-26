# 🎓 InsightEdu Lab

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

### 2. 🔌 Módulo de Controladores y Contratos (`controller/`, `dto/`)
* **Responsable:** [Integrante 2]
* **`dto/`**: Definición de los objetos de transferencia de datos (`CommunityInputDto`, `PackageOutputDto`) para asegurar el contrato JSON estricto con Streamlit y Python.
* **`controller/`**: Exposición de los endpoints REST (`CommunityController`, `OciStorageController`) para la recepción de lotes de interacciones y gestión de reportes.

### 3. ⚙️ Módulo de Servicios, Clientes e Infraestructura (`service/`, `client/`, `config/`)
* **Responsable:** [Integrante 3]
* **`service/`**: Lógica de negocio principal (`ProcessingService`, `OciStorageService`) y orquestación del control de tokens y métricas.
* **`client/`**: Conexión HTTP externa mediante `PythonAiClient` hacia el microservicio de IA en FastAPI.
* **`config/`**: Configuraciones globales y Beans (`OciConfig`, `RestClientConfig`).

---

> ⚠️ *Nota: Los nombres de las clases y entidades están a modo de sugerencia y están dispuestos a modificaciones según avance el desarrollo.*