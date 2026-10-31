import aianalysis.dockertestslots.DockerTestSlots
import aianalysis.dockertestslots.TaskCompletionEvents
import aianalysis.dockertestslots.WorkerLeases

// ai-analysis 저장소의 Testcontainers 테스트를 이 머신 전체에서 동시에 N 개까지만 돌리는 개인 init 스크립트다.
//
// 서비스 클래스(DockerTestSlots)와 보조 클래스는 ~/.gradle/docker-test-slots/ 의 Java 프로젝트가 만든 jar 에 있다.
// 이 스크립트는 jar 를 initscript classpath 에 올리고 서비스 등록과 태스크 연결만 한다.
// 클래스를 스크립트 안에 정의하면 configuration cache 를 되살릴 때 서비스 인스턴스와 doFirst 가 서로 다른
// 스크립트 클래스 로더의 DockerTestSlots 를 보게 되어 ClassCastException(DockerTestSlots$Inject_ cannot be cast) 이 난다.
// 고친 뒤에는 그 폴더에서 ./gradlew installJar 를 돌린다. Gradle 버전은 ai-analysis 의 wrapper 와 맞춘다.
//
// 한 프로세스 안에서는 BuildService 의 maxParallelUsages 로 N 개를 넘기지 않는다. 넘는 태스크는 Gradle 스케줄러가
// 시작하지 않으므로 작업 스레드를 잡지 않는다.
// worktree 마다 Gradle 프로세스가 따로 떠서 프로세스 사이는 파일 시스템 잠금(mkdir 은 원자적이다)으로 막는다.
// 다른 프로세스가 슬롯을 놓기를 기다리는 동안에는 작업 스레드와 프로젝트 잠금을 놓는다(WorkerLeases, Gradle 내부 API).
// 쥔 채로 기다리면, 슬롯을 잡은 테스트가 두 번째 테스트 JVM 을 띄우는 데 필요한 작업 스레드를 대기자가 차지해 교착한다.
// 슬롯은 태스크가 끝나면(실패해도) 태스크 완료 이벤트에서 놓는다. 작업 스레드가 필요 없다. 빌드가 끝날 때 남은 것도 놓는다.
// 오래 기다리면(기본 10분마다) 슬롯을 쥔 pid 와 잡은 시각을 경고로 남긴다.
// Gradle 을 올리다 내부 API 이름이 바뀌면 build 가 멈춘다. 그때는 이 파일을 init.d 에서 빼고 jar 를 고친다.
//
// 슬롯 경로는 docker-test-slot.sh 래퍼와 같아, 두 방식이 섞여도 합쳐서 N 개를 넘지 않는다.
// 래퍼가 슬롯을 잡고 Gradle 을 부를 때는 AI_ANALYSIS_DOCKER_SLOT_HELD 에 잡은 슬롯 경로를 넘긴다.
// 그러면 파일 잠금을 건너뛰고 컨테이너 테스트를 한 번에 하나만 돌린다(같은 슬롯을 또 기다려 교착하지 않게).
//
// 슬롯 수는 -PdockerTestSlots=N 으로 덮고(기본 2), 0 이면 끈다. CI=true 면 끈다.
// -PdockerTestSlotRoot 와 -PdockerTestSlotReportSeconds 는 회귀 테스트가 쓴다.

initscript {
    dependencies {
        classpath(files("/Users/nhn/.gradle/docker-test-slots/docker-test-slots.jar"))
    }
}

gradle.rootProject {
    if (name != "ai-analysis") return@rootProject
    val slotCount = providers.gradleProperty("dockerTestSlots").map { it.toInt() }.orElse(2)
    val ciRun = providers.environmentVariable("CI").map { it == "true" }.orElse(false)
    val heldByWrapper = providers.environmentVariable("AI_ANALYSIS_DOCKER_SLOT_HELD").map { it.isNotBlank() }.orElse(false)
    if (ciRun.get() || slotCount.get() <= 0) return@rootProject

    val slots = gradle.sharedServices.registerIfAbsent("dockerTestSlots", DockerTestSlots::class) {
        maxParallelUsages.set(if (heldByWrapper.get()) 1 else slotCount.get())
        parameters.slotCount.set(slotCount)
        parameters.fileSlots.set(heldByWrapper.map { !it })
        parameters.slotRoot.set(providers.gradleProperty("dockerTestSlotRoot").orElse("/tmp/ai-analysis-docker-slot-"))
        parameters.reportAfterSeconds.set(providers.gradleProperty("dockerTestSlotReportSeconds").map { it.toLong() }.orElse(600L))
    }
    objects.newInstance<TaskCompletionEvents>().registry.onTaskCompletion(slots)
    // 컨테이너를 띄우는 테스트가 있는 모듈. 저장소의 모듈에 Testcontainers 의존성이 더해지면 여기에도 적는다.
    val containerModules = setOf("admin-api", "analysis-api", "analysis-scheduler", "knowledge-graph-api", "sensor-api")
    subprojects {
        if (name !in containerModules) return@subprojects
        val leases = objects.newInstance<WorkerLeases>()
        tasks.withType<Test>().configureEach {
            val owner = path
            usesService(slots)
            doFirst { slots.get().acquire(owner, leases) }
        }
    }
}
