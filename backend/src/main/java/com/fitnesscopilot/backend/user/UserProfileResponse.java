package com.fitnesscopilot.backend.user;

public class UserProfileResponse {
    private final Long userId;
    private final String account;
    private final String bio;
    private final String avatarDataUrl;
    private final String trainingExperience; private final Integer weeklyTrainingDays; private final Integer sessionDurationMinutes;
    private final String availableTrainingTimes; private final String availableEquipment; private final String injuryOrMedicalNotes;
    private final java.math.BigDecimal averageSleepHours; private final String dietaryRestrictions;

    public UserProfileResponse(AppUser user) {
        this.userId = user.getId();
        this.account = user.getAccount();
        this.bio = user.getBio();
        this.avatarDataUrl = user.getAvatarDataUrl();
        this.trainingExperience=user.getTrainingExperience(); this.weeklyTrainingDays=user.getWeeklyTrainingDays(); this.sessionDurationMinutes=user.getSessionDurationMinutes();
        this.availableTrainingTimes=user.getAvailableTrainingTimes(); this.availableEquipment=user.getAvailableEquipment(); this.injuryOrMedicalNotes=user.getInjuryOrMedicalNotes(); this.averageSleepHours=user.getAverageSleepHours(); this.dietaryRestrictions=user.getDietaryRestrictions();
    }

    public Long getUserId() { return userId; }
    public String getAccount() { return account; }
    public String getBio() { return bio; }
    public String getAvatarDataUrl() { return avatarDataUrl; }
    public String getTrainingExperience(){return trainingExperience;} public Integer getWeeklyTrainingDays(){return weeklyTrainingDays;} public Integer getSessionDurationMinutes(){return sessionDurationMinutes;}
    public String getAvailableTrainingTimes(){return availableTrainingTimes;} public String getAvailableEquipment(){return availableEquipment;} public String getInjuryOrMedicalNotes(){return injuryOrMedicalNotes;}
    public java.math.BigDecimal getAverageSleepHours(){return averageSleepHours;} public String getDietaryRestrictions(){return dietaryRestrictions;}
}
