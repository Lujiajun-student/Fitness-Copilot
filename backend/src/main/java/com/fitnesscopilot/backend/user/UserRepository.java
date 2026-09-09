package com.fitnesscopilot.backend.user;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserRepository extends JpaRepository<AppUser, Long> {
    Optional<AppUser> findByAccount(String account);
    boolean existsByAccount(String account);
}
