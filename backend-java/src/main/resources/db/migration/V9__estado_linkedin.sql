-- V9 · Estado de la publicación en LinkedIn (tarea T13, DEC-160; reemplaza a DEC-151)
-- Al aprobar un post, Java lo manda a LinkedIn en segundo plano. Hasta ahora el resultado solo quedaba en el
-- registro de api-java; desde aquí se guarda en el borrador, y el panel lo muestra en Borradores y en el dashboard.
-- Los posts aprobados antes de esta migración quedan sin dato (no se rellenan). No hay reintento: un reintento
-- podría publicar dos veces en público.

ALTER TABLE borradores
    -- PUBLICADO: LinkedIn lo aceptó. SIMULADO: encendido sin token ni autor. APAGADO: LINKEDIN_HABILITADA=false.
    -- ERROR: no se publicó (ver linkedin_motivo). NULL: sin dato (no es un post, no está aprobado o es de antes)
    ADD COLUMN linkedin_estado  text CHECK (linkedin_estado IN ('PUBLICADO', 'SIMULADO', 'APAGADO', 'ERROR')),
    -- El identificador que devolvió LinkedIn (urn:li:share:…). Solo en PUBLICADO
    ADD COLUMN linkedin_post_id text CHECK (char_length(linkedin_post_id) <= 200),
    -- Cuándo se guardó el resultado
    ADD COLUMN linkedin_en      timestamptz,
    -- Un texto corto y fijo que arma Java ("Pasa de 3.000 caracteres", "LinkedIn respondió HTTP 401"). Nunca el
    -- mensaje de una excepción ni el cuerpo de la respuesta de LinkedIn
    ADD COLUMN linkedin_motivo  text CHECK (char_length(linkedin_motivo) <= 200);

-- Solo un post de LinkedIn aprobado tiene estado en LinkedIn, y ese estado siempre dice cuándo se guardó
ALTER TABLE borradores
    ADD CONSTRAINT borradores_linkedin_check
        CHECK (linkedin_estado IS NULL
               OR (tipo = 'POST_LINKEDIN' AND estado = 'APROBADO' AND linkedin_en IS NOT NULL)),
    ADD CONSTRAINT borradores_linkedin_publicado_check
        CHECK (linkedin_post_id IS NULL OR linkedin_estado = 'PUBLICADO');
