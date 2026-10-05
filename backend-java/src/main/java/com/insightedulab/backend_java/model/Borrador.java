package com.insightedulab.backend_java.model;

import com.insightedulab.backend_java.model.enums.EstadoBorrador;
import com.insightedulab.backend_java.model.enums.TipoBorrador;
import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

/** Lo que genera la IA y una persona aprueba o rechaza en el panel (N3, N6, N7). */
@Entity
@Table(name = "borradores")
@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@ToString(exclude = "mensaje")
public class Borrador {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // Obligatorio salvo en la FAQ semanal, que junta varias preguntas (CHECK en V1)
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "mensaje_id")
    private Mensaje mensaje;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private TipoBorrador tipo;

    @Column(nullable = false)
    private String textoIa;                // lo que propuso la IA

    private String textoFinal;             // lo que quedó después de la edición humana

    @Builder.Default
    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private EstadoBorrador estado = EstadoBorrador.PENDIENTE;

    @Builder.Default
    @Column(nullable = false)
    private Boolean consentimientoConfirmado = false;

    private String aprobadoPor;

    private Instant aprobadoEn;

    private Integer tiempoCuraduriaSeg;

    private Integer tokensIn;

    private Integer tokensOut;

    // Sin uso desde la V8: cada borrador tiene dos subidas a OCI, y se siguen en la tabla subidas_oci (T09)
    private String estadoOci;

    private String rutaOci;

    @Builder.Default
    @Column(nullable = false)
    private Instant creadoEn = Instant.now();
}
