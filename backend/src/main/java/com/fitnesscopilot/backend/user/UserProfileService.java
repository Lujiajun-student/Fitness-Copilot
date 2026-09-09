package com.fitnesscopilot.backend.user;

import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class UserProfileService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public UserProfileService(UserRepository userRepository, PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
    }

    public UserProfileResponse get(Long userId) {
        return new UserProfileResponse(findUser(userId));
    }

    @Transactional
    public UserProfileResponse update(Long userId, UserProfileRequest request) {
        AppUser user = findUser(userId);
        String account = request.getAccount() == null ? user.getAccount() : request.getAccount().trim();
        if (!account.equals(user.getAccount()) && userRepository.existsByAccount(account)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "账号已存在");
        }
        String bio = request.getBio() == null ? user.getBio() : request.getBio().trim();
        String avatar = request.getAvatarDataUrl() == null ? user.getAvatarDataUrl() : request.getAvatarDataUrl();
        user.updateProfile(account, bio, avatar);
        user.updateSafetyProfile(
                request.getTrainingExperience() == null ? user.getTrainingExperience() : request.getTrainingExperience(),
                request.getWeeklyTrainingDays() == null ? user.getWeeklyTrainingDays() : request.getWeeklyTrainingDays(),
                request.getSessionDurationMinutes() == null ? user.getSessionDurationMinutes() : request.getSessionDurationMinutes(),
                request.getAvailableTrainingTimes() == null ? user.getAvailableTrainingTimes() : request.getAvailableTrainingTimes().trim(),
                request.getAvailableEquipment() == null ? user.getAvailableEquipment() : request.getAvailableEquipment().trim(),
                request.getInjuryOrMedicalNotes() == null ? user.getInjuryOrMedicalNotes() : request.getInjuryOrMedicalNotes().trim(),
                request.getAverageSleepHours() == null ? user.getAverageSleepHours() : request.getAverageSleepHours(),
                request.getDietaryRestrictions() == null ? user.getDietaryRestrictions() : request.getDietaryRestrictions().trim());
        if (request.getNewPassword() != null && !request.getNewPassword().isEmpty()) {
            user.changePassword(passwordEncoder.encode(request.getNewPassword()));
        }
        return new UserProfileResponse(user);
    }

    private AppUser findUser(Long userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "用户不存在"));
    }
}
