package com.fitnesscopilot.backend.body;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

@Service
public class BodyMeasurementService {
    private final BodyMeasurementRepository repository;

    public BodyMeasurementService(BodyMeasurementRepository repository) {
        this.repository = repository;
    }

    public BodyMeasurementResponse create(Long userId, BodyMeasurementRequest request) {
        BigDecimal heightMetres = request.getHeightCm().movePointLeft(2);
        BigDecimal bmi = request.getWeightKg().divide(heightMetres.multiply(heightMetres), 1, RoundingMode.HALF_UP);
        BodyMeasurement measurement = new BodyMeasurement(userId, request.getHeightCm(), request.getWeightKg(),
                request.getChestCm(), request.getWaistCm(), request.getHipCm(), request.getBodyFatPercent(), bmi);
        return new BodyMeasurementResponse(repository.save(measurement));
    }

    public BodyMeasurementResponse getLatest(Long userId) {
        return repository.findFirstByUserIdOrderByRecordedAtDesc(userId)
                .map(BodyMeasurementResponse::new)
                .orElse(null);
    }

    public List<BodyMeasurementResponse> list(Long userId) {
        return repository.findByUserIdOrderByRecordedAtDesc(userId).stream()
                .map(BodyMeasurementResponse::new)
                .collect(Collectors.toList());
    }
}
