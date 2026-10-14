# 🚀 Automatización de Publicación en LinkedIn por Código (InsightEdu Lab)

> **Módulo:** Automatización de Posts de LinkedIn  
> **Rama de origen:** `feature/automatizacion-linkedin` (MaxxyGuti3rr3z y cevallosgabriel), integrada en `main` con `integracion/linkedin`  
> **Objetivo:** Publicar automáticamente en LinkedIn los posts aprobados por el equipo humano en el panel de curaduría, conectando el backend directamente con la API oficial de LinkedIn (sin intermediarios ni n8n).
>
> ⚠️ **Viene apagada por defecto** (`LINKEDIN_HABILITADA=false`, DEC-149): no publica ni simula nada. Encendida y con credenciales, **cada post de LinkedIn que se aprueba se publica de verdad y en público**. Cómo encenderla para una prueba o para la demo, paso a paso: [OPERACION.md §13](OPERACION.md). Cómo funciona dentro del sistema: [ARQUITECTURA.md §4.9](ARQUITECTURA.md).

---

## 1. 🎯 ¿Cómo funciona el flujo de publicación?

```
┌─────────────────────────┐
│     Panel Web           │  El revisor humano lee el post,
│    (Streamlit :8501)    │  edita si es necesario y hace clic en "Aprobar".
└───────────┬─────────────┘
            │ POST /api/v1/borradores/{id}/aprobar
            ▼
┌─────────────────────────┐
│   CuraduriaService      │  Guarda el estado APROBADO en PostgreSQL.
│     (Java Backend)      │  Detecta si el borrador es de tipo "POST_LINKEDIN".
└───────────┬─────────────┘
            │ Dispara la publicación con el texto final validado
            ▼
┌─────────────────────────┐
│     LinkedinService     │  Evalúa el entorno:
│   & LinkedinClient      │   • ¿Hay credenciales? ➔ Envía HTTP POST a LinkedIn API.
└───────────┬─────────────┘   • ¿No hay credenciales? ➔ Modo simulado seguro para desarrollo local.
            │
            ▼
┌─────────────────────────┐
│   API REST LinkedIn     │  POST https://api.linkedin.com/rest/posts
│   (Feed oficial)        │  ¡Post publicado exitosamente en el perfil o empresa! 🎉
└─────────────────────────┘
```

---

## 2. 📁 Archivos creados y modificados (Mapa de componentes)

### 🔹 Núcleo en Java (`backend-java/`)

| Archivo | Tipo | Rol y qué hace |
| :--- | :--- | :--- |
| [`LinkedinProperties.java`](../backend-java/src/main/java/com/insightedulab/backend_java/linkedin/LinkedinProperties.java) | Creado | Lee la configuración desde `application.properties` y variables de entorno: `LINKEDIN_HABILITADA`, `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_AUTHOR_URN` y `LINKEDIN_API_URL`. Incluye el método `estaConfigurado()`. |
| [`LinkedinPostRequest.java`](../backend-java/src/main/java/com/insightedulab/backend_java/linkedin/LinkedinPostRequest.java) | Creado | Representa el modelo JSON oficial exigido por la API de Posts de LinkedIn (`https://api.linkedin.com/rest/posts`) con autor (`author`), texto (`commentary`), visibilidad (`PUBLIC`), distribución (`MAIN_FEED`) y estado (`PUBLISHED`). |
| [`LinkedinPostResponse.java`](../backend-java/src/main/java/com/insightedulab/backend_java/linkedin/LinkedinPostResponse.java) | Creado | DTO con el resultado de la publicación: `publicado` (boolean), `simulado` (boolean), `idPost` (URN o ID asignado) y `mensaje`. |
| [`LinkedinConfig.java`](../backend-java/src/main/java/com/insightedulab/backend_java/linkedin/LinkedinConfig.java) | Creado | Configuración de Spring que define el bean `RestClient` (`linkedinRestClient`) con tiempos de espera controlados (5s conexión, 15s lectura). |
| [`LinkedinClient.java`](../backend-java/src/main/java/com/insightedulab/backend_java/linkedin/LinkedinClient.java) | Creado | Cliente HTTP encargado de la comunicación directa con LinkedIn. Inyecta los headers oficiales: `Authorization: Bearer <token>`, `LinkedIn-Version: 202503` y `X-Restli-Protocol-Version: 2.0.0`. Lee el header `x-restli-id` de la respuesta para obtener el URN del post creado. |
| [`LinkedinService.java`](../backend-java/src/main/java/com/insightedulab/backend_java/linkedin/LinkedinService.java) | Creado | Servicio principal del negocio. Gestiona el modo real vs modo simulado. Si no hay token configurado, simula el post en los logs (solo su largo, nunca el texto) sin romper la ejecución. Si el texto pasa de 3.000 caracteres, no lo envía (DEC-151). Si LinkedIn falla por corte de red, captura el error sin frenar la aprobación en base de datos (resiliencia). |
| [`CuraduriaService.java`](../backend-java/src/main/java/com/insightedulab/backend_java/curaduria/CuraduriaService.java) | Modificado | Inyecta `LinkedinService`. En el método `aprobar(...)`, cuando el borrador es de tipo `POST_LINKEDIN`, obtiene el texto final editado y llama a `linkedinService.publicarBorrador(id, textoParaPublicar)` **en segundo plano**, para que el panel no espere a LinkedIn. |
| [`application.properties`](../backend-java/src/main/resources/application.properties) | Modificado | Registra las propiedades bajo el prefijo `linkedin.*` conectadas a las variables de entorno. |
| [`LinkedinServiceTest.java`](../backend-java/src/test/java/com/insightedulab/backend_java/LinkedinServiceTest.java) | Creado | 6 pruebas unitarias automatizadas con JUnit 5 y Mockito para verificar el modo deshabilitado, modo simulado, modo real, resiliencia ante errores, armado del JSON oficial y el tope de 3.000 caracteres. Las demás pruebas de Java corren con LinkedIn apagado (`pom.xml`), así que nunca publican. |

---

### 🔹 Infraestructura y Docker

| Archivo | Tipo | Rol y qué hace |
| :--- | :--- | :--- |
| [`compose.yml`](../compose.yml) | Modificado | Agrega las variables `LINKEDIN_HABILITADA`, `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_AUTHOR_URN` y `LINKEDIN_API_URL` al contenedor `api-java`. |
| [`.env.example`](../.env.example) | Modificado | Documenta las nuevas variables de entorno para que cualquier miembro del equipo sepa cómo configurarlas. |

---

### 🔹 Herramientas de prueba para el equipo (`scripts/`)

| Archivo | Tipo | Rol y qué hace |
| :--- | :--- | :--- |
| [`scripts/publicar_linkedin.py`](../scripts/publicar_linkedin.py) | Creado | Script de consola en Python para probar la publicación directa o ver el JSON generado en pantalla sin necesidad de abrir el panel web. ⚠️ **Si el `.env` tiene token y autor, publica de inmediato, sin aprobación ni confirmación** (DEC-150): para una prueba real, usar el panel ([OPERACION.md §13](OPERACION.md)). |
| [`scripts/insertar_borrador_prueba.sql`](../scripts/insertar_borrador_prueba.sql) | Creado | Inserta un mensaje y un borrador de prueba directo en la base. ⚠️ Escribe en la base sin pasar por Java y con una alumna inventada: solo para una base de pruebas, nunca en la de la demo (DEC-150). |

---

## 3. 🧪 Modos de Operación

### Modo 0: Apagado (por defecto)
* Con `LINKEDIN_HABILITADA=false` (o sin la variable), aprobar un post no publica ni simula nada. El registro de Java dice `Publicación en LinkedIn deshabilitada por configuración`.

### Modo A: Simulado / Local (`LINKEDIN_HABILITADA=true`, sin credenciales)
* No requiere crear cuentas de desarrollador de LinkedIn para probar.
* Cuando se aprueba un borrador de LinkedIn en el panel web, Java genera el JSON oficial, lo registra en los logs del contenedor y asigna un ID simulado (`urn:li:share:simulado-<id>`).
* **Ventaja:** El equipo puede probar el flujo de curaduría de punta a punta en local sin trabas ni errores.

### Modo B: En Vivo (Producción / Con credenciales reales)
Para que el sistema publique en un perfil personal o página de empresa real (la lista completa de antes, durante y después está en [OPERACION.md §13](OPERACION.md)):
1. Abrir el archivo `.env` en la raíz.
2. Completar:
   ```env
   LINKEDIN_HABILITADA=true
   LINKEDIN_ACCESS_TOKEN=tu_access_token_de_linkedin
   LINKEDIN_AUTHOR_URN=urn:li:person:tu_id
   ```
   (`urn:li:person:` para un perfil o `urn:li:organization:` para una página de empresa, sin punto final.)
3. Reiniciar el contenedor de Java:
   ```powershell
   docker compose up -d --build api-java
   ```
4. A partir de ese momento, cada post aprobado se publica en el feed real de LinkedIn.

---

## 4. 🚀 Cómo probar lo que hicimos

### Opción 1: Probar el script en la terminal
⚠️ Con token y autor en el `.env`, estos comandos **publican de verdad** (DEC-150).
```powershell
python scripts/publicar_linkedin.py
```
*(Muestra el payload JSON oficial estructurado y verifica el estado de las credenciales).*

También se puede probar con un texto personalizado o con un archivo JSON:
```powershell
python scripts/publicar_linkedin.py --texto "¡Felicidades a los graduados del sprint de Inteligencia Artificial! 🚀"
```

### Opción 2: Correr las pruebas unitarias de Java
Java no está instalado en Windows: las pruebas corren en un contenedor de Maven, con el comando de [OPERACION.md §5](OPERACION.md). Para correr solo las de LinkedIn, cambiar `mvn test` por `mvn test -Dtest=LinkedinServiceTest`.
*(Debe terminar con `Tests run: 6, Failures: 0, Errors: 0, BUILD SUCCESS`).*

### Opción 3: Probar en el Panel Web
1. Levantar el sistema con `docker compose up -d` (con `LINKEDIN_HABILITADA=true` en el `.env`; sin token, queda en modo simulado).
2. Ingresar a `http://127.0.0.1:8501`.
3. Ir a la página **Borradores**, elegir el tipo `Post de LinkedIn` y un borrador pendiente.
4. Marcar la casilla de consentimiento y hacer clic en **Aprobar**.
5. Ver los logs de Java:
   ```powershell
   docker compose logs -f api-java
   ```
   Aparecerá el registro de publicación de LinkedIn (`[LinkedIn SIMULADO]` o `Post publicado exitosamente en LinkedIn`).
