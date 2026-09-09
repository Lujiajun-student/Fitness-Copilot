package com.fitnesscopilot.backend.plan;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;
public interface PlanDocumentRepository extends JpaRepository<PlanDocument,Long> {
 Optional<PlanDocument> findFirstByUserIdAndDocumentTypeOrderByCreatedAtDesc(Long userId,String documentType);
 long deleteByUserIdAndDocumentType(Long userId,String documentType);
}
