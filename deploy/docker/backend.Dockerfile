# Builds the control plane straight from the repository root.
#
# deploy/prod/backend/Dockerfile expects a pre-staged app.jar next to it, which
# is why `docker compose up --build` could never work from a clean checkout.
# This one compiles from source.
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /src
# Warm the dependency cache on the POMs alone so source edits don't refetch.
COPY pom.xml ./
COPY ruoyi-admin/pom.xml      ruoyi-admin/
COPY ruoyi-common/pom.xml     ruoyi-common/
COPY ruoyi-framework/pom.xml  ruoyi-framework/
COPY ruoyi-system/pom.xml     ruoyi-system/
COPY ruoyi-quartz/pom.xml     ruoyi-quartz/
COPY ruoyi-generator/pom.xml  ruoyi-generator/
COPY ruoyi-dca/pom.xml        ruoyi-dca/
RUN mvn -q -pl ruoyi-admin -am -DskipTests dependency:go-offline || true
COPY . .
RUN mvn -q -pl ruoyi-admin -am -DskipTests package

FROM eclipse-temurin:17-jre-alpine
RUN apk add --no-cache wget curl
WORKDIR /app
COPY --from=build /src/ruoyi-admin/target/ruoyi-admin.jar /app/app.jar
# logback.xml writes here; the upstream default (/home/ruoyi/logs) is not writable
# in this image and a failed appender aborts startup.
ENV LOG_PATH=/app/logs
RUN mkdir -p /app/logs /data/upload
EXPOSE 8080
CMD ["sh", "-c", "java $JAVA_OPTS -jar /app/app.jar"]
