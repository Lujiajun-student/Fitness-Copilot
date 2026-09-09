package com.fitnesscopilot.backend.user;

import javax.validation.constraints.Pattern;
import javax.validation.constraints.Size;
import javax.validation.constraints.Max;
import javax.validation.constraints.Min;
import java.math.BigDecimal;

public class UserProfileRequest {
    @Size(min = 3, max = 50, message = "账号长度必须在 3 到 50 个字符之间")
    @Pattern(regexp = "^$|^[A-Za-z0-9_-]+$", message = "账号只能包含字母、数字、下划线和连字符")
    private String account;

    @Size(max = 160, message = "个人简介不能超过 160 个字符")
    private String bio;

    @Size(max = 1000000, message = "头像文件过大")
    private String avatarDataUrl;

    @Size(min = 8, max = 72, message = "新密码长度必须在 8 到 72 个字符之间")
    private String newPassword;

    @Pattern(regexp = "^$|BEGINNER|INTERMEDIATE|ADVANCED$", message = "训练经验取值无效") private String trainingExperience;
    @Min(value = 1, message = "每周训练天数至少为 1") @Max(value = 7, message = "每周训练天数不能超过 7") private Integer weeklyTrainingDays;
    @Min(value = 15, message = "单次训练时长至少为 15 分钟") @Max(value = 240, message = "单次训练时长不能超过 240 分钟") private Integer sessionDurationMinutes;
    @Size(max = 300) private String availableTrainingTimes;
    @Size(max = 500) private String availableEquipment;
    @Size(max = 1000) private String injuryOrMedicalNotes;
    @Min(value = 1, message = "平均睡眠时长无效") @Max(value = 24, message = "平均睡眠时长无效") private BigDecimal averageSleepHours;
    @Size(max = 500) private String dietaryRestrictions;

    public String getAccount() { return account; }
    public void setAccount(String account) { this.account = account; }
    public String getBio() { return bio; }
    public void setBio(String bio) { this.bio = bio; }
    public String getAvatarDataUrl() { return avatarDataUrl; }
    public void setAvatarDataUrl(String avatarDataUrl) { this.avatarDataUrl = avatarDataUrl; }
    public String getNewPassword() { return newPassword; }
    public void setNewPassword(String newPassword) { this.newPassword = newPassword; }
    public String getTrainingExperience(){return trainingExperience;} public void setTrainingExperience(String v){trainingExperience=v;}
    public Integer getWeeklyTrainingDays(){return weeklyTrainingDays;} public void setWeeklyTrainingDays(Integer v){weeklyTrainingDays=v;}
    public Integer getSessionDurationMinutes(){return sessionDurationMinutes;} public void setSessionDurationMinutes(Integer v){sessionDurationMinutes=v;}
    public String getAvailableTrainingTimes(){return availableTrainingTimes;} public void setAvailableTrainingTimes(String v){availableTrainingTimes=v;}
    public String getAvailableEquipment(){return availableEquipment;} public void setAvailableEquipment(String v){availableEquipment=v;}
    public String getInjuryOrMedicalNotes(){return injuryOrMedicalNotes;} public void setInjuryOrMedicalNotes(String v){injuryOrMedicalNotes=v;}
    public BigDecimal getAverageSleepHours(){return averageSleepHours;} public void setAverageSleepHours(BigDecimal v){averageSleepHours=v;}
    public String getDietaryRestrictions(){return dietaryRestrictions;} public void setDietaryRestrictions(String v){dietaryRestrictions=v;}
}
