package com.fitnesscopilot.backend.service;

import com.fitnesscopilot.backend.dto.AuthResponse;
import com.fitnesscopilot.backend.dto.LoginRequest;
import com.fitnesscopilot.backend.dto.RegisterRequest;
import com.fitnesscopilot.backend.entity.AppUser;
import com.fitnesscopilot.backend.mapper.UserMapper;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AuthService {
    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    public AuthService(UserMapper userMapper, PasswordEncoder passwordEncoder, JwtService jwtService) {
        this.userMapper = userMapper;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
    }

    @Transactional
    public AuthResponse register(RegisterRequest request) {
        String account = request.getAccount().trim();
        if (userMapper.existsByAccount(account)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "账号已存在");
        }
        AppUser user = userMapper.save(new AppUser(account, passwordEncoder.encode(request.getPassword())));
        return responseFor(user);
    }

    public AuthResponse login(LoginRequest request) {
        AppUser user = userMapper.findByAccount(request.getAccount().trim())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "账号或密码错误"));
        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "账号或密码错误");
        }
        return responseFor(user);
    }

    private AuthResponse responseFor(AppUser user) {
        return new AuthResponse(user.getId(), user.getAccount(), jwtService.createToken(user.getId(), user.getAccount()));
    }
}
