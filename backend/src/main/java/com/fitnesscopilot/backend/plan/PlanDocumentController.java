package com.fitnesscopilot.backend.plan;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fitnesscopilot.backend.auth.JwtService;
import java.util.LinkedHashMap;
import java.util.Map;
import javax.validation.Valid;
import org.springframework.http.*;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController @RequestMapping("/api/plans") public class PlanDocumentController {
 private final PlanDocumentRepository repo; private final JwtService jwt; private final ObjectMapper mapper;
 public PlanDocumentController(PlanDocumentRepository repo,JwtService jwt,ObjectMapper mapper){this.repo=repo;this.jwt=jwt;this.mapper=mapper;}

 /** Replaces the authenticated user's active generated month plan. */
 @PostMapping("/monthly") @ResponseStatus(HttpStatus.CREATED) @Transactional public PlanDocument saveMonthly(@RequestHeader(value="Authorization",required=false)String auth,@Valid @RequestBody PlanDocumentRequest r){
  Long userId=jwt.extractUserId(auth); repo.deleteByUserIdAndDocumentType(userId,"MONTHLY_TRAINING"); return save(userId,"MONTHLY_TRAINING",r);
 }
 @GetMapping("/monthly/latest") public ResponseEntity<?> latestMonthly(@RequestHeader(value="Authorization",required=false)String auth){
  Long userId=jwt.extractUserId(auth); PlanDocument document=repo.findFirstByUserIdAndDocumentTypeOrderByCreatedAtDesc(userId,"MONTHLY_TRAINING").orElse(null);
  return document==null?ResponseEntity.noContent().build():ResponseEntity.ok(toResponse(document));
 }
 @PostMapping("/nutrition-daily") @ResponseStatus(HttpStatus.CREATED) public PlanDocument saveNutrition(@RequestHeader(value="Authorization",required=false)String auth,@Valid @RequestBody PlanDocumentRequest r){return save(jwt.extractUserId(auth),"DAILY_NUTRITION",r);}
 private PlanDocument save(Long userId,String type,PlanDocumentRequest r){try{return repo.save(new PlanDocument(userId,type,r.getGoal(),r.getPlanDate(),mapper.writeValueAsString(r.getContent())));}catch(JsonProcessingException e){throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"计划内容格式错误",e);}}
 private Map<String,Object> toResponse(PlanDocument document){try{Map<String,Object> response=new LinkedHashMap<>();response.put("id",document.getId());response.put("goal",document.getGoal());response.put("planDate",document.getPlanDate());response.put("content",mapper.readTree(document.getContentJson()));response.put("createdAt",document.getCreatedAt());return response;}catch(JsonProcessingException e){throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR,"已保存的计划无法读取",e);}}
}
