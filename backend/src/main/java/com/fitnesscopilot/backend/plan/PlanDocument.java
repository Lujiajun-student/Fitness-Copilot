package com.fitnesscopilot.backend.plan;
import java.time.LocalDate;
import java.time.LocalDateTime;
import javax.persistence.*;
@Entity @Table(name="plan_document",indexes=@Index(name="idx_plan_document_user_type",columnList="userId,documentType")) public class PlanDocument {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) private Long id; @Column(nullable=false) private Long userId; @Column(nullable=false,length=30) private String documentType; @Column(length=100) private String goal; private LocalDate planDate; @Lob @Column(nullable=false) private String contentJson; @Column(nullable=false) private LocalDateTime createdAt;
 protected PlanDocument(){} public PlanDocument(Long userId,String documentType,String goal,LocalDate planDate,String contentJson){this.userId=userId;this.documentType=documentType;this.goal=goal;this.planDate=planDate;this.contentJson=contentJson;this.createdAt=LocalDateTime.now();}
 public Long getId(){return id;} public String getDocumentType(){return documentType;} public String getGoal(){return goal;} public LocalDate getPlanDate(){return planDate;} public String getContentJson(){return contentJson;} public LocalDateTime getCreatedAt(){return createdAt;}
}
