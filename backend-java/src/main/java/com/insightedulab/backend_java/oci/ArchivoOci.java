package com.insightedulab.backend_java.oci;

import com.fasterxml.jackson.annotation.JsonPropertyOrder;

import java.time.Instant;

/**
 * El archivo JSON de un borrador en OCI (DEC-128). Se arma con Jackson a partir de este objeto (F10): nunca
 * a mano, así las comillas, los saltos de línea, los emojis y las barras invertidas quedan bien escapados.
 *
 * <p>Es una foto del borrador en el momento de subirlo. Lleva el borrador y sus datos, y <b>nada de Discord
 * del alumno</b>: ni su usuario, ni ids de Discord, ni el mensaje original. El primer nombre y la cita ya van
 * dentro del texto (D6, DEC-81). Las pruebas comprueban que estos campos son los únicos.
 *
 * @param version               la forma de este archivo; sube si algún día cambia
 * @param id                    el id del borrador en la base
 * @param tipo                  POST_LINKEDIN, CASO_EXITO o FAQ
 * @param estado                PENDIENTE, APROBADO o RECHAZADO, en el momento de subirlo
 * @param textoIa               lo que propuso la IA
 * @param textoFinal            lo que quedó después de la edición humana (siempre existe en un aprobado)
 * @param consentimientoConfirmado si Marketing confirmó el consentimiento del alumno (D6)
 * @param creadoEn              cuándo lo generó la IA
 * @param aprobadoPor           el usuario del panel que lo aprobó
 * @param aprobadoEn            cuándo
 * @param tiempoCuraduriaSeg    cuánto tardó la revisión
 * @param motivoIa              por qué la IA lo vio publicable o, en la FAQ, el resumen de la semana
 * @param semana                solo en la FAQ, por ejemplo 2026-W40
 */
@JsonPropertyOrder({"version", "id", "tipo", "estado", "textoIa", "textoFinal", "consentimientoConfirmado",
        "creadoEn", "aprobadoPor", "aprobadoEn", "tiempoCuraduriaSeg", "motivoIa", "semana"})
public record ArchivoOci(String version, long id, String tipo, String estado, String textoIa, String textoFinal,
                         boolean consentimientoConfirmado, Instant creadoEn, String aprobadoPor, Instant aprobadoEn,
                         Integer tiempoCuraduriaSeg, String motivoIa, String semana) {

    public static final String VERSION = "1.0";
}
