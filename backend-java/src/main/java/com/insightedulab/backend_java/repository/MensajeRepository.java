package com.insightedulab.backend_java.repository;

import com.insightedulab.backend_java.model.Mensaje;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

/** Lecturas y cambios de etiquetas. Para guardar mensajes que llegan de afuera: MensajeUpsertRepository. */
@Repository
public interface MensajeRepository extends JpaRepository<Mensaje, Long> {

    Optional<Mensaje> findByDiscordId(String discordId);
}
