-- V4 · Generación de borradores del Agente-Mod (tarea T06, DEC-80)
-- Cada logro (TESTIMONIO, OK, de una persona) se envía una vez a POST /v1/generar de la IA.
-- El upsert de la ingesta no toca estas columnas.

ALTER TABLE mensajes
    -- GENERADO: tiene sus dos borradores. NO_PUBLICABLE: la IA decidió que no vale un post (DEC-53).
    -- ERROR: falló el máximo de intentos. NULL: todavía no se generó
    ADD COLUMN generacion_estado text CHECK (generacion_estado IN ('GENERADO', 'NO_PUBLICABLE', 'ERROR')),
    -- Por qué es publicable o no (lo escribe la IA), o el motivo del último error
    ADD COLUMN generacion_motivo text,
    -- Cuántas veces se le pidió a la IA; al llegar al máximo, un fallo es definitivo
    ADD COLUMN generacion_intentos integer NOT NULL DEFAULT 0 CHECK (generacion_intentos >= 0),
    -- Cuándo se guardó el resultado (GENERADO o NO_PUBLICABLE)
    ADD COLUMN generado_en timestamptz,
    -- Reserva propia de la generación: reservado_hasta es de la clasificación (T04).
    -- Si Java se cae mientras la IA redacta, vence sola
    ADD COLUMN generacion_reservada_hasta timestamptz;

-- Para tomar rápido los logros que faltan, del más antiguo al más nuevo
CREATE INDEX idx_mensajes_por_generar ON mensajes (fecha, id)
    WHERE intencion = 'TESTIMONIO' AND estado_clasificacion = 'OK' AND generacion_estado IS NULL;

-- Nunca dos borradores pendientes del mismo tipo para el mismo mensaje
CREATE UNIQUE INDEX uq_borradores_pendiente_por_tipo ON borradores (mensaje_id, tipo) WHERE estado = 'PENDIENTE';
