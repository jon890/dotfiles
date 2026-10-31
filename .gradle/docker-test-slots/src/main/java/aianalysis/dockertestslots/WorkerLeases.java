package aianalysis.dockertestslots;

import javax.inject.Inject;
import org.gradle.internal.work.WorkerLeaseService;

// 기다리는 동안 작업 스레드와 프로젝트 잠금을 놓는 데 쓴다. Gradle 내부 API 다. 공개 API 에는 태스크가 작업 스레드를 놓고 기다리는 방법이 없다.
// BuildService 에는 내부 서비스를 주입할 수 없어 프로젝트의 ObjectFactory 로 만든 객체에 받는다.
// Gradle 을 올리다 이 이름이 바뀌면 init 스크립트가 클래스를 못 찾아 build 가 멈춘다. 그때는 init 스크립트를 init.d 에서 빼고 고친다.
public abstract class WorkerLeases {
    @Inject
    public abstract WorkerLeaseService getService();
}
