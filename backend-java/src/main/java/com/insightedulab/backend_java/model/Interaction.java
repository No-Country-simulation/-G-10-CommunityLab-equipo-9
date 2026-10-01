package com.insightedulab.backend_java.model;

import com.fasterxml.jackson.annotation.JsonBackReference;
import com.insightedulab.backend_java.model.enums.ClasificacionSentimiento;
import com.insightedulab.backend_java.model.enums.TipoAutor;
import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

@Entity
@Table(name = "interacciones_originales")
@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@ToString(exclude = "packageResult")
public class Interaction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String loteId;                                // ID del lote recibido

    private String tipoServidor;                          // Ej: Discord_ONE_G10, Slack, etc.

    @ManyToOne(fetch =  FetchType.LAZY)
    @JoinColumn(name = "package_result_id")
    private PackageResult packageResult;

    // Identificadores técnicos de la plataforma (Discord / n8n)
    private String discordId;                             // ID único del mensaje en la plataforma
    private String channelId;                             // ID del canal de origen
    private String authorId;                              // ID único del usuario en Discord
    private String authorUsername;                        // Username de la cuenta (ej: ComunityLab)

    // Datos del creador del post original
    private String autorNombre;                          // Nombre de quien creó el mensaje

    private String autorRol;                              // Rol del miembro (ej: Estudiante, Mentor)

    @Column(columnDefinition = "TEXT")
    private String textoMensaje;                          // Contenido textual de la interacción

    @Enumerated(EnumType.STRING)
    private TipoAutor tipoAutor;                          // HUMANO (generalmente en la entrada)

    @Enumerated(EnumType.STRING)
    private ClasificacionSentimiento clasificacionSentimiento;  // POSITIVO / NEGATIVO / NEUTRO etc.


    private Instant timestampMensaje;                      // Marca de tiempo del mensaje original
}