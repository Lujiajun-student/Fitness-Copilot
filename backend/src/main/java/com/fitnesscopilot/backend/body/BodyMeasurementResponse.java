package com.fitnesscopilot.backend.body;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class BodyMeasurementResponse {
    private final Long id;
    private final BigDecimal heightCm;
    private final BigDecimal weightKg;
    private final BigDecimal chestCm;
    private final BigDecimal waistCm;
    private final BigDecimal hipCm;
    private final BigDecimal bodyFatPercent;
    private final BigDecimal bmi;
    private final LocalDateTime recordedAt;

    public BodyMeasurementResponse(BodyMeasurement measurement) {
        this.id = measurement.getId();
        this.heightCm = measurement.getHeightCm();
        this.weightKg = measurement.getWeightKg();
        this.chestCm = measurement.getChestCm();
        this.waistCm = measurement.getWaistCm();
        this.hipCm = measurement.getHipCm();
        this.bodyFatPercent = measurement.getBodyFatPercent();
        this.bmi = measurement.getBmi();
        this.recordedAt = measurement.getRecordedAt();
    }

    public Long getId() { return id; }
    public BigDecimal getHeightCm() { return heightCm; }
    public BigDecimal getWeightKg() { return weightKg; }
    public BigDecimal getChestCm() { return chestCm; }
    public BigDecimal getWaistCm() { return waistCm; }
    public BigDecimal getHipCm() { return hipCm; }
    public BigDecimal getBodyFatPercent() { return bodyFatPercent; }
    public BigDecimal getBmi() { return bmi; }
    public LocalDateTime getRecordedAt() { return recordedAt; }
}
