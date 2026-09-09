package com.fitnesscopilot.backend.training;
import java.time.LocalDateTime;
import javax.validation.constraints.*;
public class TrainingLogRequest {
    @NotBlank @Pattern(regexp="^(strength|cardio|recovery)$") private String category;
    @NotBlank @Size(max=100) private String exercise;
    @Min(1) @Max(600) private Integer durationMinutes; @Min(1) @Max(50) private Integer sets; @Min(1) @Max(200) private Integer repetitions;
    @DecimalMin("0.0") @DecimalMax("1000.0") private Double weightKg; @DecimalMin("0.0") @DecimalMax("1000.0") private Double distanceKm; @Min(30) @Max(240) private Integer averageHeartRate; @Min(1) @Max(10) private Integer perceivedExertion; private LocalDateTime completedAt;
    public String getCategory(){return category;} public void setCategory(String v){category=v;} public String getExercise(){return exercise;} public void setExercise(String v){exercise=v;} public Integer getDurationMinutes(){return durationMinutes;} public void setDurationMinutes(Integer v){durationMinutes=v;} public Integer getSets(){return sets;} public void setSets(Integer v){sets=v;} public Integer getRepetitions(){return repetitions;} public void setRepetitions(Integer v){repetitions=v;} public Double getWeightKg(){return weightKg;} public void setWeightKg(Double v){weightKg=v;} public Double getDistanceKm(){return distanceKm;} public void setDistanceKm(Double v){distanceKm=v;} public Integer getAverageHeartRate(){return averageHeartRate;} public void setAverageHeartRate(Integer v){averageHeartRate=v;} public Integer getPerceivedExertion(){return perceivedExertion;} public void setPerceivedExertion(Integer v){perceivedExertion=v;} public LocalDateTime getCompletedAt(){return completedAt;} public void setCompletedAt(LocalDateTime v){completedAt=v;}
}
