package aianalysis.dockertestslots;

import javax.inject.Inject;
import org.gradle.build.event.BuildEventsListenerRegistry;

// init 스크립트에서 BuildEventsListenerRegistry 를 받는 공개 방법이 주입뿐이라 둔다.
public abstract class TaskCompletionEvents {
    @Inject
    public abstract BuildEventsListenerRegistry getRegistry();
}
