package com.fitnesscopilot.backend.dto;

import com.fasterxml.jackson.databind.JsonNode;

import java.time.LocalDate;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;

public class PlanDocumentRequest {
    @Size(max = 4000, message = "计划目标不能超过 4000 个字符")
    private String goal;
    private LocalDate planDate;
    @NotNull
    private JsonNode content;

    public String getGoal() {
        return goal;
    }

    public void setGoal(String v) {
        goal = v;
    }

    public LocalDate getPlanDate() {
        return planDate;
    }

    public void setPlanDate(LocalDate v) {
        planDate = v;
    }

    public JsonNode getContent() {
        return content;
    }

    public void setContent(JsonNode v) {
        content = v;
    }
}
