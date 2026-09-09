package com.fitnesscopilot.backend.body;

import java.math.BigDecimal;
import javax.validation.constraints.DecimalMax;
import javax.validation.constraints.DecimalMin;
import javax.validation.constraints.Digits;
import javax.validation.constraints.NotNull;

public class BodyMeasurementRequest {

    @NotNull(message = "身高不能为空")
    @DecimalMin(value = "80.0", message = "身高必须在 80 到 250 cm 之间")
    @DecimalMax(value = "250.0", message = "身高必须在 80 到 250 cm 之间")
    @Digits(integer = 3, fraction = 2)
    private BigDecimal heightCm;

    @NotNull(message = "体重不能为空")
    @DecimalMin(value = "20.0", message = "体重必须在 20 到 500 kg 之间")
    @DecimalMax(value = "500.0", message = "体重必须在 20 到 500 kg 之间")
    @Digits(integer = 3, fraction = 2)
    private BigDecimal weightKg;

    @DecimalMin(value = "20.0", message = "围度必须在 20 到 300 cm 之间")
    @DecimalMax(value = "300.0", message = "围度必须在 20 到 300 cm 之间")
    @Digits(integer = 3, fraction = 2)
    private BigDecimal chestCm;

    @DecimalMin(value = "20.0", message = "围度必须在 20 到 300 cm 之间")
    @DecimalMax(value = "300.0", message = "围度必须在 20 到 300 cm 之间")
    @Digits(integer = 3, fraction = 2)
    private BigDecimal waistCm;

    @DecimalMin(value = "20.0", message = "围度必须在 20 到 300 cm 之间")
    @DecimalMax(value = "300.0", message = "围度必须在 20 到 300 cm 之间")
    @Digits(integer = 3, fraction = 2)
    private BigDecimal hipCm;

    @DecimalMin(value = "2.0", message = "体脂率必须在 2 到 70% 之间")
    @DecimalMax(value = "70.0", message = "体脂率必须在 2 到 70% 之间")
    @Digits(integer = 2, fraction = 1)
    private BigDecimal bodyFatPercent;

    public BigDecimal getHeightCm() { return heightCm; }
    public void setHeightCm(BigDecimal heightCm) { this.heightCm = heightCm; }
    public BigDecimal getWeightKg() { return weightKg; }
    public void setWeightKg(BigDecimal weightKg) { this.weightKg = weightKg; }
    public BigDecimal getChestCm() { return chestCm; }
    public void setChestCm(BigDecimal chestCm) { this.chestCm = chestCm; }
    public BigDecimal getWaistCm() { return waistCm; }
    public void setWaistCm(BigDecimal waistCm) { this.waistCm = waistCm; }
    public BigDecimal getHipCm() { return hipCm; }
    public void setHipCm(BigDecimal hipCm) { this.hipCm = hipCm; }
    public BigDecimal getBodyFatPercent() { return bodyFatPercent; }
    public void setBodyFatPercent(BigDecimal bodyFatPercent) { this.bodyFatPercent = bodyFatPercent; }
}
