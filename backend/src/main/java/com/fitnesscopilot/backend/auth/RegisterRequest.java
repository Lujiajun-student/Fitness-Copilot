package com.fitnesscopilot.backend.auth;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Pattern;
import javax.validation.constraints.Size;

public class RegisterRequest {

    @NotBlank(message = "账号不能为空")
    @Size(min = 3, max = 50, message = "账号长度必须在 3 到 50 个字符之间")
    @Pattern(regexp = "^[A-Za-z0-9_-]+$", message = "账号只能包含字母、数字、下划线和连字符")
    private String account;

    @NotBlank(message = "密码不能为空")
    @Size(min = 8, max = 72, message = "密码长度必须在 8 到 72 个字符之间")
    private String password;

    public String getAccount() { return account; }
    public void setAccount(String account) { this.account = account; }
    public String getPassword() { return password; }
    public void setPassword(String password) { this.password = password; }
}
