package com.fitnesscopilot.backend.mapper;

import com.fitnesscopilot.backend.entity.PlanDocument;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface PlanDocumentMapper extends JpaRepository<PlanDocument, Long> {
    Optional<PlanDocument> findFirstByUserIdAndDocumentTypeOrderByCreatedAtDesc(Long userId, String documentType);

    long deleteByUserIdAndDocumentType(Long userId, String documentType);
}
