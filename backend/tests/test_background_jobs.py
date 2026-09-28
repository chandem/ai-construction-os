from app.background_jobs import build_pipeline_kwargs, normalize_job_row


def test_normalize_job_row_terminal():
    row = {
        "id": "j1",
        "document_id": "d1",
        "status": "completed",
        "processor": "construction-text-embedding-v1",
        "progress": 100,
        "error_message": None,
        "started_at": None,
        "completed_at": "2026-01-01T00:00:00Z",
        "created_at": "2026-01-01T00:00:00Z",
    }
    n = normalize_job_row(row)
    assert n["is_terminal"] is True
    assert n["status"] == "completed"
    assert n["progress"] == 100


def test_normalize_job_row_queued():
    n = normalize_job_row({"id": "j", "document_id": "d", "status": "queued", "progress": 0})
    assert n["is_terminal"] is False
    assert n["status"] == "queued"


def test_normalize_none():
    assert normalize_job_row(None) is None


def test_build_pipeline_kwargs():
    kw = build_pipeline_kwargs(
        project_id="p",
        document_id="d",
        job_id="j",
        knowledge_id="k",
        safe_name="a.pdf",
        content_type="application/pdf",
        data=b"%PDF",
        access_token="tok",
    )
    assert kw["project_id"] == "p"
    assert kw["data"] == b"%PDF"
    assert kw["access_token"] == "tok"


def test_pipeline_module_importable():
    from app import document_pipeline
    from app import background_jobs

    assert hasattr(document_pipeline, "run_document_pipeline")
    assert hasattr(document_pipeline, "run_document_pipeline_safe")
    assert hasattr(background_jobs, "schedule_document_job")
    assert hasattr(background_jobs, "execute_document_job")


class _FakeTable:
    def __init__(self, name):
        self.name = name

    def update(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def insert(self, *a, **k):
        return self

    def execute(self):
        return type("R", (), {"data": [{"id": "x"}]})()


class _FakeClient:
    def table(self, name):
        return _FakeTable(name)


def test_run_pipeline_safe_on_failure():
    from app.document_pipeline import run_document_pipeline_safe

    result = run_document_pipeline_safe(
        _FakeClient(),
        project_id="p",
        document_id="d",
        job_id="j",
        knowledge_id="k",
        safe_name="x.bin",
        content_type="application/octet-stream",
        data=b"not-a-real-file",
    )
    assert result["status"] == "failed"
    assert result["job_id"] == "j"
