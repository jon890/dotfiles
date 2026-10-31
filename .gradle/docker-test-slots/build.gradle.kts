// ~/.gradle/init.d/ai-analysis-docker-test-slots.init.gradle.kts 가 initscript classpath 로 읽는 jar 를 만든다.
// 스크립트 본문에 클래스를 정의하면 configuration cache 를 되살릴 때 서비스와 태스크 동작이 서로 다른 클래스 로더의
// 클래스를 보게 되어 ClassCastException 이 난다. jar 의 클래스는 initscript classpath 로더 하나에서만 올라온다.
//
// 고친 뒤: ./gradlew installJar
// installJar 는 새 파일에 쓰고 원자적 rename 으로 바꾼다. 실행 중인 daemon 이 열어 둔 jar 를 덮어쓰지 않기 위해서다.
// Gradle 버전은 ai-analysis 의 wrapper 와 맞춘다. 내부 API(WorkerLeaseService)를 쓰므로 그 저장소 Gradle 을 올리면 여기도 올리고 다시 만든다.
import java.nio.file.Files
import java.nio.file.StandardCopyOption

plugins {
    `java-library`
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(25)
    }
}

dependencies {
    compileOnly(gradleApi())
}

tasks.register("installJar") {
    // doLast 가 스크립트 수준 값을 잡으면 configuration cache 에 저장할 수 없어 값은 이 블록 안에 둔다.
    val built = tasks.jar.flatMap { it.archiveFile }
    val target = layout.projectDirectory.file("docker-test-slots.jar").asFile.toPath()
    inputs.file(built)
    outputs.file(target.toFile())
    doLast {
        val tmp = target.resolveSibling("${target.fileName}.tmp")
        Files.copy(built.get().asFile.toPath(), tmp, StandardCopyOption.REPLACE_EXISTING)
        Files.move(tmp, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
    }
}
