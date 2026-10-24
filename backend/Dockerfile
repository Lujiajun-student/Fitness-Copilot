FROM maven:3.9-eclipse-temurin-8 AS build
WORKDIR /build
COPY pom.xml .
COPY src ./src
RUN --mount=type=cache,id=fitness-copilot-maven,target=/root/.m2 \
    mvn -B -ntp -Dmaven.wagon.http.retryHandler.count=3 package -DskipTests

FROM eclipse-temurin:8-jre
WORKDIR /app
COPY --from=build /build/target/fitness-copilot-backend-0.0.1-SNAPSHOT.jar /app/app.jar
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=45s --retries=12 \
  CMD bash -c 'echo > /dev/tcp/127.0.0.1/8080' || exit 1
ENTRYPOINT ["java", "-Duser.timezone=Asia/Shanghai", "-jar", "/app/app.jar"]
