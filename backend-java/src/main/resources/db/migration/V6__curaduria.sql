-- V6 · Curaduría en el panel (tarea T07, DEC-110 a DEC-112)
-- V1 ya tiene lo de la aprobación (aprobado_por, aprobado_en, tiempo_curaduria_seg, consentimiento_confirmado).
-- Faltaba lo del rechazo.

ALTER TABLE borradores
    -- Quién lo rechazó en el panel (su usuario), cuándo y, si lo escribió, por qué
    ADD COLUMN rechazado_por  text,
    ADD COLUMN rechazado_en   timestamptz,
    ADD COLUMN motivo_rechazo text CHECK (char_length(motivo_rechazo) <= 500);

-- D6, segunda capa (la primera es Java): un post o un caso de éxito nombra al alumno,
-- así que nunca queda APROBADO sin el consentimiento confirmado. La FAQ no nombra alumnos
ALTER TABLE borradores
    ADD CONSTRAINT borradores_consentimiento_check
        CHECK (estado <> 'APROBADO' OR tipo = 'FAQ' OR consentimiento_confirmado),
    -- Lo aprobado y lo rechazado siempre dicen quién y cuándo
    ADD CONSTRAINT borradores_aprobado_check
        CHECK (estado <> 'APROBADO' OR (aprobado_por IS NOT NULL AND aprobado_en IS NOT NULL
                                        AND texto_final IS NOT NULL)),
    ADD CONSTRAINT borradores_rechazado_check
        CHECK (estado <> 'RECHAZADO' OR (rechazado_por IS NOT NULL AND rechazado_en IS NOT NULL));

-- Para listar rápido lo que quedó en ERROR (página "Errores" del panel)
CREATE INDEX idx_mensajes_clasificacion_error ON mensajes (fecha) WHERE estado_clasificacion = 'ERROR';
CREATE INDEX idx_mensajes_generacion_error    ON mensajes (fecha) WHERE generacion_estado = 'ERROR';
