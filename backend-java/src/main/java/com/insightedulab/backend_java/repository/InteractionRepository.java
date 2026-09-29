package com.insightedulab.backend_java.repository;

import com.insightedulab.backend_java.model.Interaction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface InteractionRepository extends JpaRepository<Interaction, Long> {

    // Para buscar interacciones asociadas a un lote específico
    List<Interaction> findByLoteId(String loteId);

    // Para buscar por ID de Discord de la plataforma de origen
    List<Interaction> findByDiscordId(String discordId);
}