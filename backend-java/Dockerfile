# ==========================================
# ETAPA 1: Construcción (Build) con Java 21
# ==========================================
FROM eclipse-temurin:21-jdk-alpine AS build
WORKDIR /app

# Copiamos los archivos de configuración de Maven y el wrapper
COPY mvnw .
COPY .mvn .mvn
COPY pom.xml .

# Descargamos las dependencias
RUN ./mvnw dependency:go-offline -B

# Copiamos el código fuente y compilamos el JAR
COPY src src
RUN ./mvnw clean package -DskipTests

# ==========================================
# ETAPA 2: Imagen final de ejecución ligera (JRE 21)
# ==========================================
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

# Copiamos el JAR generado desde la etapa de construcción
COPY --from=build /app/target/*.jar app.jar

# Exponemos el puerto interno de Spring Boot
EXPOSE 8080

# Comando para ejecutar la aplicación
ENTRYPOINT ["java", "-jar", "app.jar"]