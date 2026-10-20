package com.fitnesscopilot.backend.controller;

import com.fitnesscopilot.backend.dto.PlanDocumentRequest;
import com.fitnesscopilot.backend.entity.PlanDocument;
import com.fitnesscopilot.backend.service.JwtService;
import com.fitnesscopilot.backend.service.PlanDocumentService;

import java.util.Map;
import javax.validation.Valid;

import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/plans")
public class PlanDocumentController {
    private final PlanDocumentService planDocumentService;
    private final JwtService jwt;

    public PlanDocumentController(PlanDocumentService planDocumentService, JwtService jwt) {
        this.planDocumentService = planDocumentService;
        this.jwt = jwt;
    }

    /**
     * Replaces the authenticated user's active generated month plan.
     */
    @PostMapping("/monthly")
    @ResponseStatus(HttpStatus.CREATED)
    public PlanDocument saveMonthly(@RequestHeader(value = "Authorization", required = false) String auth, @Valid @RequestBody PlanDocumentRequest r) {
        return planDocumentService.replaceMonthly(jwt.extractUserId(auth), r);
    }

    @GetMapping("/monthly/latest")
    public ResponseEntity<?> latestMonthly(@RequestHeader(value = "Authorization", required = false) String auth) {
        Map<String, Object> document = planDocumentService.getLatestMonthly(jwt.extractUserId(auth));
        return document == null ? ResponseEntity.noContent().build() : ResponseEntity.ok(document);
    }

    @PostMapping("/nutrition-daily")
    @ResponseStatus(HttpStatus.CREATED)
    public PlanDocument saveNutrition(@RequestHeader(value = "Authorization", required = false) String auth, @Valid @RequestBody PlanDocumentRequest r) {
        return planDocumentService.saveDailyNutrition(jwt.extractUserId(auth), r);
    }
}
