package com.fitnesscopilot.backend.training;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
public interface TrainingLogRepository extends JpaRepository<TrainingLog,Long> { List<TrainingLog> findTop30ByUserIdOrderByCompletedAtDesc(Long userId); }
