package com.fitnesscopilot.backend.auth;

import com.fitnesscopilot.backend.user.AppUser;
import com.fitnesscopilot.backend.user.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AuthService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    public AuthService(UserRepository userRepository, PasswordEncoder passwordEncoder, JwtService jwtService) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
    }

    @Transactional
    public AuthResponse register(RegisterRequest request) {
        String account = request.getAccount().trim();
        if (userRepository.existsByAccount(account)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "账号已存在");
        }
        AppUser user = userRepository.save(new AppUser(account, passwordEncoder.encode(request.getPassword())));
        return responseFor(user);
    }

    public AuthResponse login(LoginRequest request) {
        AppUser user = userRepository.findByAccount(request.getAccount().trim())
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
