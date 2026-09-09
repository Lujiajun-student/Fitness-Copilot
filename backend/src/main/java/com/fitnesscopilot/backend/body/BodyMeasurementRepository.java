package com.fitnesscopilot.backend.body;

import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BodyMeasurementRepository extends JpaRepository<BodyMeasurement, Long> {
    Optional<BodyMeasurement> findFirstByUserIdOrderByRecordedAtDesc(Long userId);
    List<BodyMeasurement> findByUserIdOrderByRecordedAtDesc(Long userId);
}
