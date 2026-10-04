-- V2 · Clasificación en segundo plano (tarea T04)
-- Las listas cerradas vienen del contrato Java ↔ IA v1 (docs/contratos/JAVA_IA_v1.md §4.2 y §4.3).

-- Listas cerradas que V1 dejó libres a la espera de la IA
ALTER TABLE mensajes
    ADD CONSTRAINT mensajes_sentimiento_check
        CHECK (sentimiento IN ('MUY_POSITIVO', 'POSITIVO', 'NEUTRO', 'NEGATIVO', 'MUY_NEGATIVO')),
    ADD CONSTRAINT mensajes_tema_check
        CHECK (tema IN ('inscripciones', 'becas_pagos', 'calendario_clases', 'evaluaciones', 'contenido_curso',
                        'herramientas_entorno', 'plataforma_acceso', 'proyectos', 'empleo', 'comunidad', 'otro'));

ALTER TABLE mensajes
    -- Cuántas veces se intentó clasificar; al llegar al máximo, un ERROR de la IA es definitivo
    ADD COLUMN intentos_clasificacion integer NOT NULL DEFAULT 0 CHECK (intentos_clasificacion >= 0),
    -- Quién decidió las etiquetas: el LLM, el respaldo por palabras clave o una regla (bots, avisos, sin texto)
    ADD COLUMN metodo_clasificacion text CHECK (metodo_clasificacion IN ('llm', 'palabrasClave', 'regla')),
    -- servidorId del lote: la IA lo exige en el Lote y no viene dentro de la caja.
    -- Vacío en los mensajes recibidos antes de V2: se completa cuando el mensaje se reenvía
    ADD COLUMN servidor_id text,
    -- "Ocupado hasta": una tanda reservó el mensaje mientras espera a la IA. Si Java se cae, la reserva vence sola
    ADD COLUMN reservado_hasta timestamptz;

-- Para tomar rápido los pendientes, del más antiguo al más nuevo
CREATE INDEX idx_mensajes_pendientes ON mensajes (fecha, id) WHERE estado_clasificacion = 'PENDIENTE';
