package com.fitnesscopilot.backend.user;

import java.time.LocalDateTime;
import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.PrePersist;
import javax.persistence.Table;

@Entity
@Table(name = "app_user")
public class AppUser {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 50)
    private String account;

    @Column(nullable = false, length = 100)
    private String passwordHash;

    @Column(length = 160)
    private String bio;

    @Column(columnDefinition = "CLOB")
    private String avatarDataUrl;

    @Column(length = 20) private String trainingExperience;
    private Integer weeklyTrainingDays;
    private Integer sessionDurationMinutes;
    @Column(length = 300) private String availableTrainingTimes;
    @Column(length = 500) private String availableEquipment;
    @Column(length = 1000) private String injuryOrMedicalNotes;
    private java.math.BigDecimal averageSleepHours;
    @Column(length = 500) private String dietaryRestrictions;

    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    protected AppUser() {
    }

    public AppUser(String account, String passwordHash) {
        this.account = account;
        this.passwordHash = passwordHash;
    }

    @PrePersist
    private void beforeCreate() {
        this.createdAt = LocalDateTime.now();
    }

    public Long getId() { return id; }
    public String getAccount() { return account; }
    public String getPasswordHash() { return passwordHash; }
    public String getBio() { return bio; }
    public String getAvatarDataUrl() { return avatarDataUrl; }
    public String getTrainingExperience() { return trainingExperience; }
    public Integer getWeeklyTrainingDays() { return weeklyTrainingDays; }
    public Integer getSessionDurationMinutes() { return sessionDurationMinutes; }
    public String getAvailableTrainingTimes() { return availableTrainingTimes; }
    public String getAvailableEquipment() { return availableEquipment; }
    public String getInjuryOrMedicalNotes() { return injuryOrMedicalNotes; }
    public java.math.BigDecimal getAverageSleepHours() { return averageSleepHours; }
    public String getDietaryRestrictions() { return dietaryRestrictions; }
    public LocalDateTime getCreatedAt() { return createdAt; }

    public void updateProfile(String account, String bio, String avatarDataUrl) {
        this.account = account;
        this.bio = bio;
        this.avatarDataUrl = avatarDataUrl;
    }
    public void updateSafetyProfile(String trainingExperience, Integer weeklyTrainingDays, Integer sessionDurationMinutes, String availableTrainingTimes, String availableEquipment, String injuryOrMedicalNotes, java.math.BigDecimal averageSleepHours, String dietaryRestrictions) {
        this.trainingExperience = trainingExperience; this.weeklyTrainingDays = weeklyTrainingDays; this.sessionDurationMinutes = sessionDurationMinutes;
        this.availableTrainingTimes = availableTrainingTimes; this.availableEquipment = availableEquipment; this.injuryOrMedicalNotes = injuryOrMedicalNotes;
        this.averageSleepHours = averageSleepHours; this.dietaryRestrictions = dietaryRestrictions;
    }

    public void changePassword(String passwordHash) { this.passwordHash = passwordHash; }
}
