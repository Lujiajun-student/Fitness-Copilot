package com.fitnesscopilot.backend.auth;

public class AuthResponse {
    private final Long userId;
    private final String account;
    private final String token;
    private final String tokenType = "Bearer";

    public AuthResponse(Long userId, String account, String token) {
        this.userId = userId;
        this.account = account;
        this.token = token;
    }

    public Long getUserId() { return userId; }
    public String getAccount() { return account; }
    public String getToken() { return token; }
    public String getTokenType() { return tokenType; }
}
