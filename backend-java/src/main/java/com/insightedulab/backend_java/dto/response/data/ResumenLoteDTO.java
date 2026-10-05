package com.insightedulab.backend_java.dto.response.data;

import lombok.Data;

@Data
public class ResumenLoteDTO {

    private int totalMensajes;
    private int descartadosFiltro;
    private int testimonios;
    private int preguntasFaq;
    private int comentarios;
    private int otro;
    private int procesadosExito;
    private int requierenHumano;
}
