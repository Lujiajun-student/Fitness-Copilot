package com.fitnesscopilot.backend.training;

import java.time.LocalDateTime;
import javax.persistence.*;

@Entity @Table(name = "training_log", indexes = @Index(name = "idx_training_log_user_completed", columnList = "userId,completedAt"))
public class TrainingLog {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    @Column(nullable = false) private Long userId;
    @Column(nullable = false, length = 20) private String category;
    @Column(nullable = false, length = 100) private String exercise;
    private Integer durationMinutes; private Integer sets; private Integer repetitions; private Double weightKg; private Double distanceKm; private Integer averageHeartRate; private Integer perceivedExertion;
    @Column(nullable = false) private LocalDateTime completedAt;
    protected TrainingLog() { }
    public TrainingLog(Long userId, TrainingLogRequest r) { this.userId=userId; this.category=r.getCategory(); this.exercise=r.getExercise(); this.durationMinutes=r.getDurationMinutes(); this.sets=r.getSets(); this.repetitions=r.getRepetitions(); this.weightKg=r.getWeightKg(); this.distanceKm=r.getDistanceKm(); this.averageHeartRate=r.getAverageHeartRate(); this.perceivedExertion=r.getPerceivedExertion(); this.completedAt=r.getCompletedAt()==null?LocalDateTime.now():r.getCompletedAt(); }
    public Long getId(){return id;} public String getCategory(){return category;} public String getExercise(){return exercise;} public Integer getDurationMinutes(){return durationMinutes;} public Integer getSets(){return sets;} public Integer getRepetitions(){return repetitions;} public Double getWeightKg(){return weightKg;} public Double getDistanceKm(){return distanceKm;} public Integer getAverageHeartRate(){return averageHeartRate;} public Integer getPerceivedExertion(){return perceivedExertion;} public LocalDateTime getCompletedAt(){return completedAt;}
}
