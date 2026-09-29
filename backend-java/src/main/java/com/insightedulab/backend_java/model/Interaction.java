package com.insightedulab.backend_java.model;

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

    private String loteId;

    private String tipoServidor;

    @ManyToOne(fetch =  FetchType.LAZY)
    @JoinColumn(name = "package_result_id")
    private PackageResult packageResult;

    // Identificadores técnicos de la plataforma (Discord / n8n)
    private String discordId;
    private String channelId;
    private String authorId;
    private String authorUsername;

    // Datos del creador del post original
    private String authorNombre;
    private String authorRol;

    @Column(columnDefinition = "TEXT")
    private String textoMensaje;

    @Enumerated(EnumType.STRING)
    private TipoAutor tipoAutor;

    @Enumerated(EnumType.STRING)
    private ClasificacionSentimiento clasificacionSentimiento;

    private Instant timestampMensaje;
}