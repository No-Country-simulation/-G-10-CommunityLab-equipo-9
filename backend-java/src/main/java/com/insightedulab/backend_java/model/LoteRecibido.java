package com.insightedulab.backend_java.model;

import com.insightedulab.backend_java.model.enums.ModoLote;
import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

/** Cada lote que llega a la API: por lotes (cada hora) o de a un mensaje desde el bot. */
@Entity
@Table(name = "lotes_recibidos")
@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class LoteRecibido {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String loteId;                 // loteId del contrato: detecta los reenvíos

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private ModoLote modo;

    @Column(nullable = false)
    private String versionContrato;        // "1.0"

    @Builder.Default
    @Column(nullable = false)
    private Instant recibidoEn = Instant.now();

    // Resultado del upsert: los "sin cambios" son total - nuevos - actualizados
    @Builder.Default
    @Column(nullable = false)
    private Integer total = 0;

    @Builder.Default
    @Column(nullable = false)
    private Integer nuevos = 0;

    @Builder.Default
    @Column(nullable = false)
    private Integer actualizados = 0;
}
