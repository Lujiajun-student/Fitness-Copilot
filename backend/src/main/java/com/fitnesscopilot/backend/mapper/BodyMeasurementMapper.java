package com.fitnesscopilot.backend.mapper;

import com.fitnesscopilot.backend.entity.BodyMeasurement;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

public interface BodyMeasurementMapper extends JpaRepository<BodyMeasurement, Long> {
    Optional<BodyMeasurement> findFirstByUserIdOrderByRecordedAtDesc(Long userId);

    List<BodyMeasurement> findByUserIdOrderByRecordedAtDesc(Long userId);
}
