package com.insightedulab.backend_java.repository;

import com.insightedulab.backend_java.model.LoteRecibido;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface LoteRecibidoRepository extends JpaRepository<LoteRecibido, Long> {

    Optional<LoteRecibido> findByLoteId(String loteId);
}
