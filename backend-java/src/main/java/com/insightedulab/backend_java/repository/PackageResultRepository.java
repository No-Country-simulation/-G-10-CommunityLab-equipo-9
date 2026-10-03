package com.insightedulab.backend_java.repository;

import com.insightedulab.backend_java.model.PackageResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface PackageResultRepository extends JpaRepository<PackageResult, Long> {

    // Buscar el paquete de resultados por su identificador de lote
    Optional<PackageResult> findByLoteId(String loteId);

    // Buscar por el logId de ejecución para auditoría
    Optional<PackageResult> findByLogId(String logId);
}