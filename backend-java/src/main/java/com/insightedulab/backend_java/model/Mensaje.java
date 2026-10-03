package com.insightedulab.backend_java.model;

import com.insightedulab.backend_java.model.enums.AutorRol;
import com.insightedulab.backend_java.model.enums.AutorTipo;
import com.insightedulab.backend_java.model.enums.EstadoClasificacion;
import com.insightedulab.backend_java.model.enums.Intencion;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.Map;

/**
 * Un mensaje de Discord = una fila (F1).
 * Opción C: las columnas son "la etiqueta" para buscar rápido; {@code contrato} es "la caja",
 * con el mensaje completo del contrato v1. Para guardar mensajes que llegan de afuera se usa
 * {@link com.insightedulab.backend_java.repository.MensajeUpsertRepository}, no save().
 */
@Entity
@Table(name = "mensajes")
@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@ToString(exclude = "contrato")
public class Mensaje {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String discordId;              // id del contrato

    @Column(nullable = false)
    private String canalId;                // canal.id

    @Column(nullable = false)
    private String autorId;                // autor.id: estable, "sim-..." en los simulados

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private AutorTipo autorTipo;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private AutorRol autorRol;

    @Builder.Default
    @Column(nullable = false)
    private Boolean esSimulado = false;

    @Column(nullable = false)
    private Instant fecha;

    // Nombre explícito: Spring no separa con "_" una mayúscula final ("respondeA" → "respondea")
    @Column(name = "responde_a")
    private String respondeA;              // discord_id del mensaje al que responde, o null

    @Builder.Default
    @Column(nullable = false)
    private String texto = "";             // textoOriginal: puede venir vacío

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false)
    private Map<String, Object> contrato;  // la caja (jsonb)

    @Column(nullable = false)
    private String versionContrato;

    @Builder.Default
    @Column(nullable = false)
    private Instant primeraVezVisto = Instant.now();

    @Builder.Default
    @Column(nullable = false)
    private Instant actualizadoEn = Instant.now();

    // ── Etiquetas de la IA (el upsert nunca las pisa: F2) ──

    @Enumerated(EnumType.STRING)
    private Intencion intencion;

    private Double confianza;              // 0 a 1

    private String sentimiento;            // sin lista cerrada hasta la fase 3

    private String tema;

    @Builder.Default
    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private EstadoClasificacion estadoClasificacion = EstadoClasificacion.PENDIENTE;

    private Instant clasificadoEn;
}
