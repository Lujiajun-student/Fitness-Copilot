package com.fitnesscopilot.backend.controller;

import com.fitnesscopilot.backend.dto.UserProfileRequest;
import com.fitnesscopilot.backend.dto.UserProfileResponse;
import com.fitnesscopilot.backend.service.JwtService;
import com.fitnesscopilot.backend.service.UserProfileService;

import javax.validation.Valid;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/users/me")
public class UserProfileController {
    private final UserProfileService service;
    private final JwtService jwtService;

    public UserProfileController(UserProfileService service, JwtService jwtService) {
        this.service = service;
        this.jwtService = jwtService;
    }

    @GetMapping
    public UserProfileResponse get(@RequestHeader(value = "Authorization", required = false) String authorization) {
        return service.get(jwtService.extractUserId(authorization));
    }

    @PatchMapping
    public UserProfileResponse update(@RequestHeader(value = "Authorization", required = false) String authorization,
                                      @Valid @RequestBody UserProfileRequest request) {
        return service.update(jwtService.extractUserId(authorization), request);
    }
}
