"""Unit tests for scripts.dag_builder (v1.1.14)."""
from scripts.dag_builder import Task, Wave, build_waves, detect_conflicts


def test_task_dataclass_default_model_sonnet():
    t = Task(id=1, name="Foo", files=["a.py"], deps=[])
    assert t.model == "sonnet"


def test_wave_dataclass_holds_tasks():
    t1 = Task(id=1, name="Foo", files=["a.py"], deps=[])
    t2 = Task(id=2, name="Bar", files=["b.py"], deps=[])
    w = Wave(index=1, tasks=[t1, t2])
    assert len(w.tasks) == 2
    assert w.index == 1


def test_build_waves_linear_deps():
    """Task 2 depends on Task 1 → 2 waves of 1 task each."""
    t1 = Task(id=1, name="A", files=["a.py"], deps=[])
    t2 = Task(id=2, name="B", files=["b.py"], deps=[1])
    waves = build_waves([t1, t2])
    assert len(waves) == 2
    assert [t.id for t in waves[0].tasks] == [1]
    assert [t.id for t in waves[1].tasks] == [2]


def test_build_waves_independent_files():
    """3 tasks no deps, no file overlap → 1 wave with all 3."""
    tasks = [
        Task(id=1, name="A", files=["a.py"]),
        Task(id=2, name="B", files=["b.py"]),
        Task(id=3, name="C", files=["c.py"]),
    ]
    waves = build_waves(tasks)
    assert len(waves) == 1
    assert {t.id for t in waves[0].tasks} == {1, 2, 3}


def test_build_waves_file_conflict_serializes():
    """Tasks 2 and 3 both touch foo.py → DAG forces serialize."""
    tasks = [
        Task(id=1, name="A", files=["a.py"]),
        Task(id=2, name="B", files=["foo.py"]),
        Task(id=3, name="C", files=["foo.py"]),
    ]
    waves = build_waves(tasks)
    assert len(waves) >= 2
    for wave in waves:
        ids = {t.id for t in wave.tasks}
        assert not (2 in ids and 3 in ids)


def test_detect_conflicts_disjoint_returns_empty():
    """Two manifests touching different files → no conflicts."""
    manifests = {
        1: ["a.py", "b.py"],
        2: ["c.py", "d.py"],
    }
    assert detect_conflicts(manifests) == []


def test_detect_conflicts_shared_file_returns_pair():
    """Two manifests overlap on b.py → conflict pair (1, 2, 'b.py')."""
    manifests = {
        1: ["a.py", "b.py"],
        2: ["b.py", "c.py"],
    }
    conflicts = detect_conflicts(manifests)
    assert (1, 2, "b.py") in conflicts


def test_detect_conflicts_three_way_overlap():
    """Three manifests share x.py → 3 pairwise conflicts."""
    manifests = {
        1: ["x.py"],
        2: ["x.py"],
        3: ["x.py"],
    }
    conflicts = detect_conflicts(manifests)
    assert len(conflicts) == 3


def test_strict_deps_ordering_with_file_overlap():
    """T2 deps=[T1]. 둘 다 같은 파일 만지면 T2 가 T1 앞에 wave 배치 X.

    Bug context (v1.1.16): Kahn indegree 0 후보가 T1 만일 때 정상이지만,
    file overlap 으로 T1, T2 가 같은 wave 못 들어가면 T2 는 다음 wave 로
    deferred. 이때 deps 우선순위 보장 — T2 가 W2 가 아니라 T1 의 W1 다음에
    배치되어야 함. 회귀 패턴: deferred 후 deps 재계산 누락.
    """
    from scripts.dag_builder import Task, build_waves
    tasks = [
        Task(id=1, name="A", files=["shared.py"], deps=[]),
        Task(id=2, name="B", files=["shared.py"], deps=[1]),
    ]
    waves = build_waves(tasks)
    assert len(waves) == 2
    assert [t.id for t in waves[0].tasks] == [1]
    assert [t.id for t in waves[1].tasks] == [2]


def test_deps_violated_when_file_overlap_defers_dep():
    """후행 task 의 deps 가 같은 wave 내 다른 candidate 보다 앞에 와야 함.

    예: T1, T2 (deps=[]), T3 deps=[T2]. T2/T3 파일 동일.
    Kahn 0 후보 = [T1, T2]. file overlap 없음 → 둘 다 W1.
    T3 는 deps=[T2] 만족 + T2 와 file overlap → W2.
    """
    from scripts.dag_builder import Task, build_waves
    tasks = [
        Task(id=1, name="A", files=["a.py"], deps=[]),
        Task(id=2, name="B", files=["b.py"], deps=[]),
        Task(id=3, name="C", files=["b.py"], deps=[2]),
    ]
    waves = build_waves(tasks)
    assert len(waves) == 2
    assert sorted(t.id for t in waves[0].tasks) == [1, 2]
    assert [t.id for t in waves[1].tasks] == [3]
