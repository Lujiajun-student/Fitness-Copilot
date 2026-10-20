package com.fitnesscopilot.backend.service;

import com.fitnesscopilot.backend.dto.TrainingLogRequest;
import com.fitnesscopilot.backend.entity.TrainingLog;
import com.fitnesscopilot.backend.mapper.TrainingLogMapper;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class TrainingLogService {
    private final TrainingLogMapper trainingLogMapper;

    public TrainingLogService(TrainingLogMapper trainingLogMapper) {
        this.trainingLogMapper = trainingLogMapper;
    }

    public TrainingLog create(Long userId, TrainingLogRequest request) {
        return trainingLogMapper.save(new TrainingLog(userId, request));
    }

    public List<TrainingLog> listRecent(Long userId) {
        return trainingLogMapper.findTop30ByUserIdOrderByCompletedAtDesc(userId);
    }
}
