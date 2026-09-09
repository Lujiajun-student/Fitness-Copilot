package com.fitnesscopilot.backend.plan;
import com.fasterxml.jackson.databind.JsonNode;
import java.time.LocalDate;
import javax.validation.constraints.NotNull;
public class PlanDocumentRequest { private String goal; private LocalDate planDate; @NotNull private JsonNode content; public String getGoal(){return goal;} public void setGoal(String v){goal=v;} public LocalDate getPlanDate(){return planDate;} public void setPlanDate(LocalDate v){planDate=v;} public JsonNode getContent(){return content;} public void setContent(JsonNode v){content=v;} }
