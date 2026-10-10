package com.insightedulab.backend_java.repository;

import com.insightedulab.backend_java.model.Borrador;
import com.insightedulab.backend_java.model.enums.EstadoBorrador;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface BorradorRepository extends JpaRepository<Borrador, Long> {

    List<Borrador> findByEstado(EstadoBorrador estado);
}
