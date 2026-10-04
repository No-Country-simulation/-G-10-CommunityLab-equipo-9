-- V3 · Lo que respondió el bot en vivo (tarea T05, DEC-66)
-- Va en la fila del mensaje, como sus etiquetas: no es un borrador porque no se aprueba (D3).
-- El upsert de la ingesta no toca estas columnas: el lote de la hora no borra lo que respondió el bot.

ALTER TABLE mensajes
    -- RESPONDIDA: el bot publicó una respuesta con respaldo en los PDFs.
    -- DERIVADA: era una duda sin respaldo firme y el bot avisó que responderá un mentor.
    -- NULL: el bot no respondió (no era una duda, o falló Java o la IA y lo rescató el lote de la hora)
    ADD COLUMN respuesta_estado  text CHECK (respuesta_estado IN ('RESPONDIDA', 'DERIVADA')),
    -- El texto de la IA que publicó el bot (solo en RESPONDIDA)
    ADD COLUMN respuesta_texto   text,
    -- Documento y página que respaldan la respuesta, como lista JSON (solo en RESPONDIDA)
    ADD COLUMN respuesta_fuentes jsonb,
    -- Cuándo decidió Java la respuesta (RESPONDIDA o DERIVADA)
    ADD COLUMN respondido_en     timestamptz;
