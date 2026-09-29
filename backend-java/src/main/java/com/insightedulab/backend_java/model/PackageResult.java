package com.insightedulab.backend_java.model;

import com.insightedulab.backend_java.model.enums.ClasificacionSentimiento;
import com.insightedulab.backend_java.model.enums.TipoAutor;
import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.List;

@Entity
@Table(name = "paquetes_resultados")
@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@ToString(exclude = "interacciones")
public class PackageResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String logId;                  // Ej: log_2026-09-19_001
    private String loteId;                 // Ej: lote_001
    private String tipoServidor;           // Canal o servidor de origen

    // Relación relacional con las interacciones que dieron origen a este paquete
    @OneToMany(mappedBy = "packageResult", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Interaction> interacciones;

    // Control de autoría y respuestas (IA vs Humano)
    @Enumerated(EnumType.STRING)
    private TipoAutor tipoAutorRespuesta;  // Define si el activo final fue adaptado por HUMANO o generado por AI

    @Enumerated(EnumType.STRING)
    private ClasificacionSentimiento clasificacionSentimiento;

    // Respuestas y Activos Generados
    @Column(columnDefinition = "TEXT")
    private String respuestaAi;            // Respuesta cruda o generada por el motor de Python
    @Column(columnDefinition = "TEXT")
    private String postLinkedin;           // Copy para LinkedIn (editable por el usuario)

    // Datos de FAQ (Servidor / RAG)
    private String temaFaq;
    @Column(columnDefinition = "TEXT")
    private String preguntaFaq;
    @Column(columnDefinition = "TEXT")
    private String respuestaFaq;

    // Control de Tokens (Guardados en BD para auditoría y costos)
    private Integer tokensIn;
    private Integer tokensOut;

    // Índices y Métricas de Curaduría
    private Double similitudPromedio;      // Qué tanto difiere el texto humano del de IA
    private Boolean fueEditadoPorHumano;   // Bandera para saber si pasó por Human-in-the-Loop
    private Integer tiempoCuraduriaSeg;    // Tiempo que tardó el operador

    // Control de Tiempos y OCI
    private Instant timestampInicio;
    private Instant timestampFin;
    private String statusOci;              // Estado de subida al bucket (ej: "exitoso")
}