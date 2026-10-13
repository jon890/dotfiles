import java.io.IOException
import java.nio.channels.FileChannel
import java.nio.channels.OverlappingFileLockException
import java.nio.file.FileAlreadyExistsException
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths
import java.nio.file.StandardCopyOption
import java.nio.file.StandardOpenOption
import java.time.Instant
import java.util.concurrent.ConcurrentHashMap
import javax.inject.Inject
import org.gradle.build.event.BuildEventsListenerRegistry
import org.gradle.internal.work.WorkerLeaseService
import org.gradle.tooling.events.FinishEvent
import org.gradle.tooling.events.OperationCompletionListener
import org.gradle.tooling.events.task.TaskFinishEvent

// ai-analysis 저장소의 Testcontainers 테스트를 이 머신 전체에서 동시에 N 개까지만 돌리는 개인 init 스크립트다.
// ~/.gradle/init.d/ 에 두면 루트 프로젝트 이름이 ai-analysis 인 build 에만 걸린다. 저장소에는 두지 않는다.
//
// 한 프로세스 안에서는 BuildService 의 maxParallelUsages 로 N 개를 넘기지 않는다. 넘는 태스크는 Gradle 스케줄러가
// 시작하지 않으므로 작업 스레드를 잡지 않는다.
// worktree 마다 Gradle 프로세스가 따로 떠서 프로세스 사이는 파일 시스템 잠금(mkdir 은 원자적이다)으로 막는다.
// 다른 프로세스가 슬롯을 놓기를 기다리는 동안에는 작업 스레드와 프로젝트 잠금을 놓는다.
// 쥔 채로 기다리면, 슬롯을 잡은 테스트가 두 번째 테스트 JVM 을 띄우는 데 필요한 작업 스레드를 대기자가 차지해 교착한다.
// 슬롯은 태스크가 끝나면(실패해도) 태스크 완료 이벤트에서 놓는다. 작업 스레드가 필요 없다. 빌드가 끝날 때 남은 것도 놓는다.
// 오래 기다리면(기본 10분마다) 슬롯을 쥔 pid 와 잡은 시각을 경고로 남긴다.
//
// 슬롯 경로는 docker-test-slot.sh 래퍼와 같아, 두 방식이 섞여도 합쳐서 N 개를 넘지 않는다.
// 래퍼가 슬롯을 잡고 Gradle 을 부를 때는 AI_ANALYSIS_DOCKER_SLOT_HELD 에 잡은 슬롯 경로를 넘긴다.
// 그러면 파일 잠금을 건너뛰고 컨테이너 테스트를 한 번에 하나만 돌린다(같은 슬롯을 또 기다려 교착하지 않게).
//
// 슬롯 수는 -PdockerTestSlots=N 으로 덮고(기본 2), 0 이면 끈다. CI=true 면 끈다.
// -PdockerTestSlotRoot 와 -PdockerTestSlotReportSeconds 는 회귀 테스트가 쓴다.

abstract class DockerTestSlots : BuildService<DockerTestSlots.Params>, OperationCompletionListener, AutoCloseable {
    interface Params : BuildServiceParameters {
        val slotCount: Property<Int>
        val slotRoot: Property<String>
        val fileSlots: Property<Boolean>
        val reportAfterSeconds: Property<Long>
    }

    private class Held(val slot: Path, val lock: FileChannel)

    private val logger = Logging.getLogger(DockerTestSlots::class.java)
    private val myPid = ProcessHandle.current().pid()

    // 대기 루프가 모니터를 쥐면 슬롯을 놓는 쪽(release)이 같은 모니터를 기다려 교착한다. 그래서 잠금 없이 동시 맵을 쓴다.
    private val held = ConcurrentHashMap<String, Held>()

    // mkdir 에 성공한 순간부터 놓을 때까지의 슬롯이다. pid 파일이 이 프로세스인데 여기에 없으면 지난 빌드가 남긴 것이다.
    private val ownSlots = ConcurrentHashMap.newKeySet<Path>()

    fun acquire(owner: String, leases: WorkerLeases) {
        if (!parameters.fileSlots.get() || held.containsKey(owner)) return
        if (tryTake(owner)) return
        logger.lifecycle("docker 테스트 슬롯 대기 중... ($owner)")
        val reportAfterMillis = parameters.reportAfterSeconds.get() * 1_000L
        val startedAt = System.currentTimeMillis()
        var nextReportAt = startedAt + reportAfterMillis
        leases.service.blocking(
            Runnable {
                while (!tryTake(owner)) {
                    Thread.sleep(POLL_MILLIS)
                    val now = System.currentTimeMillis()
                    if (now >= nextReportAt) {
                        logger.warn("docker 테스트 슬롯을 ${(now - startedAt) / 1_000L}초째 기다린다($owner). 쥔 쪽: ${describeHolders()}")
                        nextReportAt += reportAfterMillis
                    }
                }
            },
        )
    }

    override fun onFinish(event: FinishEvent) {
        if (event is TaskFinishEvent) release(event.descriptor.taskPath)
    }

    override fun close() {
        held.keys.toList().forEach { release(it) }
    }

    private fun release(owner: String) {
        val entry = held.remove(owner) ?: return
        deleteSlot(entry.slot)
        runCatching { entry.lock.close() }
        ownSlots.remove(entry.slot)
    }

    private fun slotPath(index: Int): Path = Paths.get("${parameters.slotRoot.get()}$index")

    private fun tryTake(owner: String): Boolean {
        for (index in 1..parameters.slotCount.get()) {
            val slot = slotPath(index)
            try {
                Files.createDirectory(slot)
            } catch (_: FileAlreadyExistsException) {
                reclaimIfStale(slot)
                continue
            }
            ownSlots.add(slot)
            try {
                // 잠금을 먼저 걸고 pid 파일을 마지막에 쓴다. 다른 프로세스는 pid 파일이 있을 때만 잠금으로 판정한다.
                val lock = FileChannel.open(slot.resolve("lock"), StandardOpenOption.CREATE, StandardOpenOption.WRITE)
                lock.lock()
                Files.writeString(slot.resolve("owner"), "task=$owner\nacquiredAt=${Instant.now()}\n")
                val pidTmp = slot.resolve("pid.tmp")
                Files.writeString(pidTmp, myPid.toString())
                Files.move(pidTmp, slot.resolve("pid"), StandardCopyOption.ATOMIC_MOVE)
                held[owner] = Held(slot, lock)
            } catch (e: IOException) {
                deleteSlot(slot)
                ownSlots.remove(slot)
                throw e
            }
            return true
        }
        return false
    }

    // 쥔 쪽이 없는 슬롯을 회수한다.
    // - pid 파일이 없으면 막 잡는 중일 수 있어 STALE_MILLIS 가 지난 뒤에만 회수한다(잡다가 죽은 슬롯이 영구히 남지 않게).
    // - 이 프로세스의 pid 인데 지금 쥐고 있지 않으면 같은 daemon 의 지난 빌드가 남긴 것이다.
    // - 이 스크립트가 잡은 슬롯은 잡은 동안 lock 파일에 OS 잠금을 건다. 잠금을 얻을 수 있으면 pid 가 살아 있어도 놓은 것이다.
    //   OS 잠금은 프로세스가 죽거나 파일을 닫으면 풀린다.
    // - lock 파일이 없는 슬롯(docker-test-slot.sh)은 pid 가 죽었을 때만 회수한다.
    // 지우기 전에 고유한 이름으로 원자적 rename 을 해, 여러 대기자가 같은 슬롯을 회수해도 이긴 하나만 지운다.
    private fun reclaimIfStale(slot: Path) {
        val pidFile = slot.resolve("pid")
        val pid = if (Files.exists(pidFile)) runCatching { Files.readString(pidFile).trim().toLong() }.getOrNull() else null
        val stale = when {
            pid == null -> runCatching { System.currentTimeMillis() - Files.getLastModifiedTime(slot).toMillis() > STALE_MILLIS }.getOrDefault(false)
            pid == myPid -> slot !in ownSlots
            Files.exists(slot.resolve("lock")) -> lockIsFree(slot.resolve("lock"))
            else -> !ProcessHandle.of(pid).map { it.isAlive }.orElse(false)
        }
        if (!stale) return
        val claimed = slot.resolveSibling("${slot.fileName}.reclaim-$myPid-${System.nanoTime()}")
        try {
            Files.move(slot, claimed, StandardCopyOption.ATOMIC_MOVE)
        } catch (_: IOException) {
            return
        }
        logger.lifecycle("쥔 쪽이 없는 docker 테스트 슬롯을 회수했다: $slot (pid=$pid)")
        deleteSlot(claimed)
    }

    // 다른 프로세스의 lock 파일만 연다. 같은 프로세스에서 파일을 닫으면 그 파일의 다른 잠금까지 풀릴 수 있다(POSIX 잠금).
    private fun lockIsFree(lockFile: Path): Boolean = try {
        FileChannel.open(lockFile, StandardOpenOption.WRITE).use { channel -> channel.tryLock()?.let { it.release(); true } ?: false }
    } catch (_: IOException) {
        false
    } catch (_: OverlappingFileLockException) {
        false
    }

    private fun describeHolders(): String = (1..parameters.slotCount.get()).joinToString(", ") { index ->
        val slot = slotPath(index)
        if (!Files.isDirectory(slot)) return@joinToString "$slot 비어 있음"
        val pid = runCatching { Files.readString(slot.resolve("pid")).trim() }.getOrDefault("?")
        val owner = runCatching { Files.readAllLines(slot.resolve("owner")).associate { it.substringBefore('=') to it.substringAfter('=') } }
            .getOrDefault(emptyMap())
        val acquiredAt = owner["acquiredAt"] ?: runCatching { Files.getLastModifiedTime(slot).toInstant().toString() }.getOrDefault("?")
        "$slot pid=$pid 잡은 시각=$acquiredAt" + (owner["task"]?.let { " 태스크=$it" } ?: "")
    }

    private fun deleteSlot(slot: Path) {
        runCatching {
            Files.deleteIfExists(slot.resolve("pid"))
            Files.list(slot).use { entries -> entries.forEach { Files.deleteIfExists(it) } }
            Files.deleteIfExists(slot)
        }
    }

    companion object {
        private const val POLL_MILLIS = 2_000L
        private const val STALE_MILLIS = 60_000L
    }
}

// 기다리는 동안 작업 스레드와 프로젝트 잠금을 놓는 데 쓴다. Gradle 내부 API 다. 공개 API 에는 태스크가 작업 스레드를 놓고 기다리는 방법이 없다.
// BuildService 에는 내부 서비스를 주입할 수 없어 프로젝트의 ObjectFactory 로 만든 객체에 받는다.
// Gradle 을 올리다 이 이름이 바뀌면 init 스크립트 컴파일이 실패해 build 가 멈춘다. 그때는 이 파일을 init.d 에서 빼고 고친다.
abstract class WorkerLeases {
    @get:Inject
    abstract val service: WorkerLeaseService
}

// 스크립트 안에서 BuildEventsListenerRegistry 를 받는 공개 방법이 주입뿐이라 둔다.
abstract class TaskCompletionEvents {
    @get:Inject
    abstract val registry: BuildEventsListenerRegistry
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
