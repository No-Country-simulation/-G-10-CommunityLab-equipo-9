package com.insightedulab.backend_java.error;

import com.insightedulab.backend_java.seguridad.IdCorrelacionFilter;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.util.List;

/**
 * Manejo global de errores (F13). Todas las respuestas usan ErrorApi, con el id de correlación.
 * El detalle técnico va solo al registro; al cliente nunca (S7).
 */
@RestControllerAdvice
public class ManejadorErrores {

    private static final Logger log = LoggerFactory.getLogger(ManejadorErrores.class);

    @ExceptionHandler(ContratoInvalidoException.class)
    public ResponseEntity<ErrorApi> contratoInvalido(ContratoInvalidoException e, HttpServletRequest req) {
        log.warn("Lote rechazado: {} errores de contrato", e.getErrores().size());
        return responder(HttpStatus.UNPROCESSABLE_ENTITY, new ErrorApi("CONTRATO_INVALIDO",
                "El lote no cumple el contrato v1.", e.getErrores(), IdCorrelacionFilter.de(req)));
    }

    @ExceptionHandler(DatoInvalidoException.class)
    public ResponseEntity<ErrorApi> datoInvalido(DatoInvalidoException e, HttpServletRequest req) {
        log.warn("Pedido rechazado: el campo {} no es válido ({} {})", e.getCampo(), req.getMethod(), req.getRequestURI());
        return responder(HttpStatus.UNPROCESSABLE_ENTITY, new ErrorApi("DATO_INVALIDO", e.getMessage(),
                List.of(new ErrorApi.ErrorCampo(e.getCampo(), e.getMessage())), IdCorrelacionFilter.de(req)));
    }

    @ExceptionHandler(ConflictoException.class)
    public ResponseEntity<ErrorApi> conflicto(ConflictoException e, HttpServletRequest req) {
        log.info("Pedido rechazado por el estado: {} ({} {})", e.getMessage(), req.getMethod(), req.getRequestURI());
        return responder(HttpStatus.CONFLICT, ErrorApi.de("CONFLICTO", e.getMessage(), IdCorrelacionFilter.de(req)));
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ErrorApi> parametroInvalido(MethodArgumentTypeMismatchException e, HttpServletRequest req) {
        return responder(HttpStatus.UNPROCESSABLE_ENTITY, new ErrorApi("DATO_INVALIDO", "Un parámetro no es válido.",
                List.of(new ErrorApi.ErrorCampo(e.getName(), "No tiene el formato esperado.")), IdCorrelacionFilter.de(req)));
    }

    @ExceptionHandler(ProhibidoException.class)
    public ResponseEntity<ErrorApi> prohibido(ProhibidoException e, HttpServletRequest req) {
        log.warn("Pedido rechazado en el controlador: la clave no es del cliente de esta ruta ({} {})",
                req.getMethod(), req.getRequestURI());
        return responder(HttpStatus.FORBIDDEN, ErrorApi.de("PROHIBIDO", e.getMessage(), IdCorrelacionFilter.de(req)));
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErrorApi> cuerpoIlegible(HttpMessageNotReadableException e, HttpServletRequest req) {
        log.warn("Cuerpo ilegible: {}", e.getMostSpecificCause().getClass().getSimpleName());
        return responder(HttpStatus.BAD_REQUEST, ErrorApi.de("CUERPO_INVALIDO",
                "El cuerpo no es un JSON válido o no tiene la forma del contrato v1.", IdCorrelacionFilter.de(req)));
    }

    @ExceptionHandler({NoEncontradoException.class, NoResourceFoundException.class})
    public ResponseEntity<ErrorApi> noEncontrado(Exception e, HttpServletRequest req) {
        String mensaje = e instanceof NoEncontradoException ? e.getMessage() : "La ruta no existe.";
        return responder(HttpStatus.NOT_FOUND, ErrorApi.de("NO_ENCONTRADO", mensaje, IdCorrelacionFilter.de(req)));
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<ErrorApi> metodoNoPermitido(HttpRequestMethodNotSupportedException e, HttpServletRequest req) {
        return responder(HttpStatus.METHOD_NOT_ALLOWED, ErrorApi.de("METODO_NO_PERMITIDO",
                "La ruta no acepta " + e.getMethod() + ".", IdCorrelacionFilter.de(req)));
    }

    @ExceptionHandler(HttpMediaTypeNotSupportedException.class)
    public ResponseEntity<ErrorApi> tipoNoSoportado(HttpMediaTypeNotSupportedException e, HttpServletRequest req) {
        return responder(HttpStatus.UNSUPPORTED_MEDIA_TYPE, ErrorApi.de("TIPO_NO_SOPORTADO",
                "El cuerpo debe ser application/json.", IdCorrelacionFilter.de(req)));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorApi> errorInterno(Exception e, HttpServletRequest req) {
        String id = IdCorrelacionFilter.de(req);
        log.error("Error interno (idCorrelacion={})", id, e);
        return responder(HttpStatus.INTERNAL_SERVER_ERROR, ErrorApi.de("ERROR_INTERNO",
                "No se pudo procesar el pedido. Reintentar más tarde.", id));
    }

    private static ResponseEntity<ErrorApi> responder(HttpStatus estado, ErrorApi error) {
        return ResponseEntity.status(estado).body(error);
    }
}
