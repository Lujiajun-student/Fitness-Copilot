package com.fitnesscopilot.backend.auth;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class AuthControllerTest {
    @Autowired
    private MockMvc mockMvc;

    @Test
    void userCanRegisterAndLogin() throws Exception {
        String account = "test_user_" + System.nanoTime();
        String payload = "{\"account\":\"" + account + "\",\"password\":\"strong-password-123\"}";

        mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(payload))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.account").value(account))
                .andExpect(jsonPath("$.token").isNotEmpty());

        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(payload))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.account").value(account))
                .andExpect(jsonPath("$.token").isNotEmpty());
    }

    @Test
    void loggedInUserCanRecordBodyMeasurement() throws Exception {
        String account = "body_user_" + System.nanoTime();
        String credentials = "{\"account\":\"" + account + "\",\"password\":\"strong-password-123\"}";
        MvcResult registration = mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(credentials))
                .andExpect(status().isCreated())
                .andReturn();
        String token = com.jayway.jsonpath.JsonPath.read(registration.getResponse().getContentAsString(), "$.token");

        mockMvc.perform(post("/api/body-measurements")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"heightCm\":175,\"weightKg\":70,\"chestCm\":96,\"waistCm\":80,\"hipCm\":94,\"bodyFatPercent\":18.5}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.bmi").value(22.9))
                .andExpect(jsonPath("$.waistCm").value(80));
    }

    @Test
    void loggedInUserCanUpdateProfile() throws Exception {
        String account = "profile_user_" + System.nanoTime();
        String credentials = "{\"account\":\"" + account + "\",\"password\":\"strong-password-123\"}";
        MvcResult registration = mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON).content(credentials))
                .andExpect(status().isCreated()).andReturn();
        String token = com.jayway.jsonpath.JsonPath.read(registration.getResponse().getContentAsString(), "$.token");

        mockMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch("/api/users/me")
                        .header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"bio\":\"坚持科学训练\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.account").value(account))
                .andExpect(jsonPath("$.bio").value("坚持科学训练"));
    }
}
