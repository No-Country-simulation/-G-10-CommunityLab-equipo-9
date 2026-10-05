package com.insightedulab.backend_java.service;

import com.insightedulab.backend_java.client.NlpDataClient;
import com.insightedulab.backend_java.dto.request.CommunityProcessRequestDto;
import com.insightedulab.backend_java.dto.response.data.OutputOrquestadorDTO;
import com.insightedulab.backend_java.dto.response.data.PaqueteFinalDTO;
import com.insightedulab.backend_java.model.Interaction;
import com.insightedulab.backend_java.model.PackageResult;
import com.insightedulab.backend_java.model.enums.TipoAutor;
import com.insightedulab.backend_java.repository.InteractionRepository;
import com.insightedulab.backend_java.repository.PackageResultRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.stream.Collectors;

@Service
public class OrquestadorPersistenceService {

    @Autowired
    private NlpDataClient nlpDataClient;

    @Autowired
    private PackageResultRepository packageResultRepository;

    @Autowired
    private InteractionRepository interactionRepository;

    @Transactional
    public OutputOrquestadorDTO procesarYGuardarLote(CommunityProcessRequestDto inputDto) {
        // 1. Llamamos a FastAPI a través de nuestro cliente (con soporte de Fallback)
        OutputOrquestadorDTO output = nlpDataClient.ejecutarOrquestador(inputDto);

        // 2. Mapeamos el Output a nuestra entidad PackageResult
        PackageResult packageResult = new PackageResult();
        packageResult.setLoteId(output.getLoteId());

        if (output.getLogEjecucion() != null) {
            packageResult.setLogId(output.getLogEjecucion().getLoteId());

            if (output.getLogEjecucion().getTimestampInicio() != null) {
                packageResult.setTimestampInicio(
                        Instant.from(DateTimeFormatter.ISO_DATE_TIME.withZone(ZoneOffset.UTC).parse(output.getLogEjecucion().getTimestampInicio()))
                );
            }

            if (output.getLogEjecucion().getTimestampFin() != null) {
                packageResult.setTimestampFin(
                        Instant.from(DateTimeFormatter.ISO_DATE_TIME.withZone(ZoneOffset.UTC).parse(output.getLogEjecucion().getTimestampFin()))
                );
            }

            packageResult.setTokensIn(output.getLogEjecucion().getTokensTotales());
        }

        if (output.getPaqueteFinal() != null) {
            PaqueteFinalDTO paqueteDto = output.getPaqueteFinal();
            packageResult.setTipoServidor(inputDto.getOrigen());
            packageResult.setTemaFaq(paqueteDto.getTemaFaq());
            packageResult.setPreguntaFaq(paqueteDto.getPreguntaFaq());
            packageResult.setRespuestaFaq(paqueteDto.getRespuestaFaq());
            packageResult.setPostLinkedin(paqueteDto.getPostLinkedin());
            packageResult.setSimilitudPromedio(paqueteDto.getSimilitudPromedio());
            packageResult.setFueEditadoPorHumano(paqueteDto.getFueEditadoPorHumano());

            packageResult.setTipoAutorRespuesta(TipoAutor.AI);
        }

        // 3. Guardamos primero el PackageResult para obtener su ID generado
        PackageResult savedPackageResult = packageResultRepository.save(packageResult);

        // 4. Mapeamos los mensajes de entrada hacia la entidad Interaction y los asociamos
        if (inputDto.getMensajes() != null) {
            var interacciones = inputDto.getMensajes().stream().map(msg -> {
                Interaction interaction = new Interaction();
                interaction.setLoteId(inputDto.getLoteId());
                interaction.setTipoServidor(inputDto.getServidor());
                interaction.setPackageResult(savedPackageResult);

                interaction.setDiscordId(msg.getDiscordId());
                interaction.setChannelId(msg.getChannelId());
                interaction.setAuthorId(msg.getAuthorId());
                interaction.setAuthorUsername(msg.getAuthorUsername());
                interaction.setAutorNombre(msg.getAutorNombre());
                interaction.setTextoMensaje(msg.getTextoMensaje());
                interaction.setTipoAutor(msg.getTipoAutor() != null ? msg.getTipoAutor() : TipoAutor.HUMANO);

                // Como timestampMensaje ya es Instant, asignamos directo sin .isBlank() ni .parse()
                interaction.setTimestampMensaje(msg.getTimestampMensaje() != null ? msg.getTimestampMensaje() : Instant.now());

                return interaction;
            }).collect(Collectors.toList());

            interactionRepository.saveAll(interacciones);
        }

        // 5. Retornamos el DTO de salida para que el controlador lo responda correctamente
        return output;
    }
}