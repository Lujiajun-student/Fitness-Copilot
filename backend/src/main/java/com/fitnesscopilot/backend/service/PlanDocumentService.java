package com.fitnesscopilot.backend.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fitnesscopilot.backend.dto.PlanDocumentRequest;
import com.fitnesscopilot.backend.entity.PlanDocument;
import com.fitnesscopilot.backend.mapper.PlanDocumentMapper;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class PlanDocumentService {
    private static final String MONTHLY_TRAINING = "MONTHLY_TRAINING";
    private static final String DAILY_NUTRITION = "DAILY_NUTRITION";

    private final PlanDocumentMapper planDocumentMapper;
    private final ObjectMapper objectMapper;

    public PlanDocumentService(PlanDocumentMapper planDocumentMapper, ObjectMapper objectMapper) {
        this.planDocumentMapper = planDocumentMapper;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public PlanDocument replaceMonthly(Long userId, PlanDocumentRequest request) {
        planDocumentMapper.deleteByUserIdAndDocumentType(userId, MONTHLY_TRAINING);
        return save(userId, MONTHLY_TRAINING, request);
    }

    public Map<String, Object> getLatestMonthly(Long userId) {
        return planDocumentMapper.findFirstByUserIdAndDocumentTypeOrderByCreatedAtDesc(userId, MONTHLY_TRAINING)
                .map(this::toResponse)
                .orElse(null);
    }

    public PlanDocument saveDailyNutrition(Long userId, PlanDocumentRequest request) {
        return save(userId, DAILY_NUTRITION, request);
    }

    private PlanDocument save(Long userId, String documentType, PlanDocumentRequest request) {
        try {
            String contentJson = objectMapper.writeValueAsString(request.getContent());
            return planDocumentMapper.save(new PlanDocument(userId, documentType, request.getGoal(), request.getPlanDate(), contentJson));
        } catch (JsonProcessingException exception) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "计划内容格式错误", exception);
        }
    }

    private Map<String, Object> toResponse(PlanDocument document) {
        try {
            Map<String, Object> response = new LinkedHashMap<>();
            response.put("id", document.getId());
            response.put("goal", document.getGoal());
            response.put("planDate", document.getPlanDate());
            response.put("content", objectMapper.readTree(document.getContentJson()));
            response.put("createdAt", document.getCreatedAt());
            return response;
        } catch (JsonProcessingException exception) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "已保存的计划无法读取", exception);
        }
    }
}
