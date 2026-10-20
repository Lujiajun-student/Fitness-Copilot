package com.fitnesscopilot.backend.controller;

import com.fitnesscopilot.backend.dto.TrainingLogRequest;
import com.fitnesscopilot.backend.entity.TrainingLog;
import com.fitnesscopilot.backend.service.JwtService;
import com.fitnesscopilot.backend.service.TrainingLogService;

import java.util.List;
import javax.validation.Valid;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/training-logs")
public class TrainingLogController {
    private final TrainingLogService trainingLogService;
    private final JwtService jwt;

    public TrainingLogController(TrainingLogService trainingLogService, JwtService jwt) {
        this.trainingLogService = trainingLogService;
        this.jwt = jwt;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public TrainingLog create(@RequestHeader(value = "Authorization", required = false) String auth, @Valid @RequestBody TrainingLogRequest r) {
        return trainingLogService.create(jwt.extractUserId(auth), r);
    }

    @GetMapping
    public List<TrainingLog> list(@RequestHeader(value = "Authorization", required = false) String auth) {
        return trainingLogService.listRecent(jwt.extractUserId(auth));
    }
}
