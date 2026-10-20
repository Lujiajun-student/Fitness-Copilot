package com.fitnesscopilot.backend.mapper;

import com.fitnesscopilot.backend.entity.TrainingLog;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

public interface TrainingLogMapper extends JpaRepository<TrainingLog, Long> {
    List<TrainingLog> findTop30ByUserIdOrderByCompletedAtDesc(Long userId);
}
