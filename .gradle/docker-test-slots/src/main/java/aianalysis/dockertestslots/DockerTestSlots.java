package aianalysis.dockertestslots;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.FileAlreadyExistsException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;
import java.util.stream.IntStream;
import java.util.stream.Stream;
import org.gradle.api.logging.Logger;
import org.gradle.api.logging.Logging;
import org.gradle.api.provider.Property;
import org.gradle.api.services.BuildService;
import org.gradle.api.services.BuildServiceParameters;
import org.gradle.tooling.events.FinishEvent;
import org.gradle.tooling.events.OperationCompletionListener;
import org.gradle.tooling.events.task.TaskFinishEvent;

// 동작 규칙은 ~/.gradle/init.d/ai-analysis-docker-test-slots.init.gradle.kts 머리 주석에 있다.
public abstract class DockerTestSlots implements BuildService<DockerTestSlots.Params>, OperationCompletionListener, AutoCloseable {

    public interface Params extends BuildServiceParameters {
        Property<Integer> getSlotCount();

        Property<String> getSlotRoot();

        Property<Boolean> getFileSlots();

        Property<Long> getReportAfterSeconds();
    }

    private static final long POLL_MILLIS = 2_000L;
    private static final long STALE_MILLIS = 60_000L;

    private record Held(Path slot, FileChannel lock) {}

    private final Logger logger = Logging.getLogger(DockerTestSlots.class);
    private final long myPid = ProcessHandle.current().pid();

    // 대기 루프가 모니터를 쥐면 슬롯을 놓는 쪽(release)이 같은 모니터를 기다려 교착한다. 그래서 잠금 없이 동시 맵을 쓴다.
    private final Map<String, Held> held = new ConcurrentHashMap<>();

    // mkdir 에 성공한 순간부터 놓을 때까지의 슬롯이다. pid 파일이 이 프로세스인데 여기에 없으면 지난 빌드가 남긴 것이다.
    private final Set<Path> ownSlots = ConcurrentHashMap.newKeySet();

    public void acquire(String owner, WorkerLeases leases) {
        if (!getParameters().getFileSlots().get() || held.containsKey(owner)) return;
        if (tryTake(owner)) return;
        logger.lifecycle("docker 테스트 슬롯 대기 중... ({})", owner);
        long reportAfterMillis = getParameters().getReportAfterSeconds().get() * 1_000L;
        long startedAt = System.currentTimeMillis();
        long[] nextReportAt = {startedAt + reportAfterMillis};
        leases.getService().blocking(() -> {
            while (!tryTake(owner)) {
                try {
                    Thread.sleep(POLL_MILLIS);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    throw new IllegalStateException("docker 테스트 슬롯 대기가 중단됐다(" + owner + ")", e);
                }
                long now = System.currentTimeMillis();
                if (now >= nextReportAt[0]) {
                    logger.warn("docker 테스트 슬롯을 {}초째 기다린다({}). 쥔 쪽: {}", (now - startedAt) / 1_000L, owner, describeHolders());
                    nextReportAt[0] += reportAfterMillis;
                }
            }
        });
    }

    @Override
    public void onFinish(FinishEvent event) {
        if (event instanceof TaskFinishEvent taskEvent) release(taskEvent.getDescriptor().getTaskPath());
    }

    @Override
    public void close() {
        new ArrayList<>(held.keySet()).forEach(this::release);
    }

    private void release(String owner) {
        Held entry = held.remove(owner);
        if (entry == null) return;
        deleteSlot(entry.slot());
        try {
            entry.lock().close();
        } catch (IOException ignored) {
            // 닫다 실패해도 프로세스가 끝나면 OS 잠금이 풀린다.
        }
        ownSlots.remove(entry.slot());
    }

    private Path slotPath(int index) {
        return Paths.get(getParameters().getSlotRoot().get() + index);
    }

    private boolean tryTake(String owner) {
        for (int index = 1; index <= getParameters().getSlotCount().get(); index++) {
            Path slot = slotPath(index);
            try {
                Files.createDirectory(slot);
            } catch (FileAlreadyExistsException e) {
                reclaimIfStale(slot);
                continue;
            } catch (IOException e) {
                throw new UncheckedIOException(e);
            }
            ownSlots.add(slot);
            try {
                // 잠금을 먼저 걸고 pid 파일을 마지막에 쓴다. 다른 프로세스는 pid 파일이 있을 때만 잠금으로 판정한다.
                FileChannel lock = FileChannel.open(slot.resolve("lock"), StandardOpenOption.CREATE, StandardOpenOption.WRITE);
                lock.lock();
                Files.writeString(slot.resolve("owner"), "task=" + owner + "\nacquiredAt=" + Instant.now() + "\n");
                Path pidTmp = slot.resolve("pid.tmp");
                Files.writeString(pidTmp, Long.toString(myPid));
                Files.move(pidTmp, slot.resolve("pid"), StandardCopyOption.ATOMIC_MOVE);
                held.put(owner, new Held(slot, lock));
            } catch (IOException e) {
                deleteSlot(slot);
                ownSlots.remove(slot);
                throw new UncheckedIOException(e);
            }
            return true;
        }
        return false;
    }

    // 쥔 쪽이 없는 슬롯을 회수한다.
    // - pid 파일이 없으면 막 잡는 중일 수 있어 STALE_MILLIS 가 지난 뒤에만 회수한다(잡다가 죽은 슬롯이 영구히 남지 않게).
    // - 이 프로세스의 pid 인데 지금 쥐고 있지 않으면 같은 daemon 의 지난 빌드가 남긴 것이다.
    // - 이 클래스가 잡은 슬롯은 잡은 동안 lock 파일에 OS 잠금을 건다. 잠금을 얻을 수 있으면 pid 가 살아 있어도 놓은 것이다.
    //   OS 잠금은 프로세스가 죽거나 파일을 닫으면 풀린다.
    // - lock 파일이 없는 슬롯(docker-test-slot.sh)은 pid 가 죽었을 때만 회수한다.
    // 지우기 전에 고유한 이름으로 원자적 rename 을 해, 여러 대기자가 같은 슬롯을 회수해도 이긴 하나만 지운다.
    private void reclaimIfStale(Path slot) {
        Long pid = readPid(slot.resolve("pid"));
        boolean stale;
        if (pid == null) {
            try {
                stale = System.currentTimeMillis() - Files.getLastModifiedTime(slot).toMillis() > STALE_MILLIS;
            } catch (IOException e) {
                stale = false;
            }
        } else if (pid == myPid) {
            stale = !ownSlots.contains(slot);
        } else if (Files.exists(slot.resolve("lock"))) {
            stale = lockIsFree(slot.resolve("lock"));
        } else {
            stale = !ProcessHandle.of(pid).map(ProcessHandle::isAlive).orElse(false);
        }
        if (!stale) return;
        Path claimed = slot.resolveSibling(slot.getFileName() + ".reclaim-" + myPid + "-" + System.nanoTime());
        try {
            Files.move(slot, claimed, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            return;
        }
        logger.lifecycle("쥔 쪽이 없는 docker 테스트 슬롯을 회수했다: {} (pid={})", slot, pid);
        deleteSlot(claimed);
    }

    private static Long readPid(Path pidFile) {
        if (!Files.exists(pidFile)) return null;
        try {
            return Long.parseLong(Files.readString(pidFile).trim());
        } catch (IOException | NumberFormatException e) {
            return null;
        }
    }

    // 다른 프로세스의 lock 파일만 연다. 같은 프로세스에서 파일을 닫으면 그 파일의 다른 잠금까지 풀릴 수 있다(POSIX 잠금).
    private static boolean lockIsFree(Path lockFile) {
        try (FileChannel channel = FileChannel.open(lockFile, StandardOpenOption.WRITE)) {
            FileLock lock = channel.tryLock();
            if (lock == null) return false;
            lock.release();
            return true;
        } catch (IOException | OverlappingFileLockException e) {
            return false;
        }
    }

    private String describeHolders() {
        return IntStream.rangeClosed(1, getParameters().getSlotCount().get())
                .mapToObj(index -> {
                    Path slot = slotPath(index);
                    if (!Files.isDirectory(slot)) return slot + " 비어 있음";
                    String pid = readOr(slot.resolve("pid"), "?").trim();
                    Map<String, String> owner = readOwner(slot.resolve("owner"));
                    String acquiredAt = owner.get("acquiredAt");
                    if (acquiredAt == null) {
                        try {
                            acquiredAt = Files.getLastModifiedTime(slot).toInstant().toString();
                        } catch (IOException e) {
                            acquiredAt = "?";
                        }
                    }
                    String task = owner.get("task");
                    return slot + " pid=" + pid + " 잡은 시각=" + acquiredAt + (task != null ? " 태스크=" + task : "");
                })
                .collect(Collectors.joining(", "));
    }

    private static String readOr(Path file, String fallback) {
        try {
            return Files.readString(file);
        } catch (IOException e) {
            return fallback;
        }
    }

    private static Map<String, String> readOwner(Path ownerFile) {
        try {
            return Files.readAllLines(ownerFile).stream()
                    .collect(Collectors.toMap(
                            line -> line.contains("=") ? line.substring(0, line.indexOf('=')) : line,
                            line -> line.contains("=") ? line.substring(line.indexOf('=') + 1) : line,
                            (first, second) -> second));
        } catch (IOException e) {
            return Map.of();
        }
    }

    private static void deleteSlot(Path slot) {
        try {
            Files.deleteIfExists(slot.resolve("pid"));
            try (Stream<Path> entries = Files.list(slot)) {
                for (Path entry : (Iterable<Path>) entries::iterator) Files.deleteIfExists(entry);
            }
            Files.deleteIfExists(slot);
        } catch (IOException ignored) {
            // 원본도 runCatching 으로 실패를 무시했다. 남은 슬롯은 다음 대기자가 회수한다.
        }
    }
}
