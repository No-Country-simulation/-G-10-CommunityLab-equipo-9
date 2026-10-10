-- V7 · Dashboard (tarea T08)
-- "¿Alguien le contestó a esta duda?" busca los mensajes cuyo responde_a es la duda (DEC-123).
-- Sin índice, PostgreSQL recorrería toda la tabla por cada duda.
CREATE INDEX idx_mensajes_responde_a ON mensajes (responde_a) WHERE responde_a IS NOT NULL;
