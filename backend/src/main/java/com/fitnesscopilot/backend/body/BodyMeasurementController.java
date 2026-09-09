package com.fitnesscopilot.backend.body;

import com.fitnesscopilot.backend.auth.JwtService;
import java.util.List;
import javax.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/body-measurements")
public class BodyMeasurementController {
    private final BodyMeasurementService service;
    private final JwtService jwtService;

    public BodyMeasurementController(BodyMeasurementService service, JwtService jwtService) {
        this.service = service;
        this.jwtService = jwtService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public BodyMeasurementResponse create(@RequestHeader(value = "Authorization", required = false) String authorization,
                                          @Valid @RequestBody BodyMeasurementRequest request) {
        return service.create(jwtService.extractUserId(authorization), request);
    }

    @GetMapping("/latest")
    public BodyMeasurementResponse latest(@RequestHeader(value = "Authorization", required = false) String authorization) {
        return service.getLatest(jwtService.extractUserId(authorization));
    }

    @GetMapping
    public List<BodyMeasurementResponse> list(@RequestHeader(value = "Authorization", required = false) String authorization) {
        return service.list(jwtService.extractUserId(authorization));
    }
}
