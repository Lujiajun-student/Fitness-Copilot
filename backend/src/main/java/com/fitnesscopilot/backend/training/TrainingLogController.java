package com.fitnesscopilot.backend.training;
import com.fitnesscopilot.backend.auth.JwtService;
import java.util.List;
import javax.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
@RestController @RequestMapping("/api/training-logs") public class TrainingLogController {
 private final TrainingLogRepository repo; private final JwtService jwt;
 public TrainingLogController(TrainingLogRepository repo, JwtService jwt){this.repo=repo;this.jwt=jwt;}
 @PostMapping @ResponseStatus(HttpStatus.CREATED) public TrainingLog create(@RequestHeader(value="Authorization",required=false) String auth,@Valid @RequestBody TrainingLogRequest r){return repo.save(new TrainingLog(jwt.extractUserId(auth),r));}
 @GetMapping public List<TrainingLog> list(@RequestHeader(value="Authorization",required=false) String auth){return repo.findTop30ByUserIdOrderByCompletedAtDesc(jwt.extractUserId(auth));}
}
