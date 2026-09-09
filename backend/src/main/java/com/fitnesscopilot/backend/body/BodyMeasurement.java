package com.fitnesscopilot.backend.body;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Index;
import javax.persistence.PrePersist;
import javax.persistence.Table;

@Entity
@Table(name = "body_measurement", indexes = {
        @Index(name = "idx_body_measurement_user_recorded", columnList = "userId,recordedAt")
})
public class BodyMeasurement {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long userId;

    @Column(nullable = false, precision = 5, scale = 2)
    private BigDecimal heightCm;

    @Column(nullable = false, precision = 5, scale = 2)
    private BigDecimal weightKg;

    @Column(precision = 5, scale = 2)
    private BigDecimal chestCm;

    @Column(precision = 5, scale = 2)
    private BigDecimal waistCm;

    @Column(precision = 5, scale = 2)
    private BigDecimal hipCm;

    @Column(precision = 4, scale = 1)
    private BigDecimal bodyFatPercent;

    @Column(nullable = false, precision = 4, scale = 1)
    private BigDecimal bmi;

    @Column(nullable = false, updatable = false)
    private LocalDateTime recordedAt;

    protected BodyMeasurement() {
    }

    public BodyMeasurement(Long userId, BigDecimal heightCm, BigDecimal weightKg,
                           BigDecimal chestCm, BigDecimal waistCm, BigDecimal hipCm,
                           BigDecimal bodyFatPercent, BigDecimal bmi) {
        this.userId = userId;
        this.heightCm = heightCm;
        this.weightKg = weightKg;
        this.chestCm = chestCm;
        this.waistCm = waistCm;
        this.hipCm = hipCm;
        this.bodyFatPercent = bodyFatPercent;
        this.bmi = bmi;
    }

    @PrePersist
    private void setRecordedAt() {
        this.recordedAt = LocalDateTime.now();
    }

    public Long getId() { return id; }
    public Long getUserId() { return userId; }
    public BigDecimal getHeightCm() { return heightCm; }
    public BigDecimal getWeightKg() { return weightKg; }
    public BigDecimal getChestCm() { return chestCm; }
    public BigDecimal getWaistCm() { return waistCm; }
    public BigDecimal getHipCm() { return hipCm; }
    public BigDecimal getBodyFatPercent() { return bodyFatPercent; }
    public BigDecimal getBmi() { return bmi; }
    public LocalDateTime getRecordedAt() { return recordedAt; }
}
