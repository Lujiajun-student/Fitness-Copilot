package com.fitnesscopilot.backend.mapper;

import com.fitnesscopilot.backend.entity.AppUser;

import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

public interface UserMapper extends JpaRepository<AppUser, Long> {
    Optional<AppUser> findByAccount(String account);

    boolean existsByAccount(String account);
}
