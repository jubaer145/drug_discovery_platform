import json
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from httpx import AsyncClient

from core.websocket import ConnectionManager, send_progress_update
from models.schemas import JobProgressUpdate


class TestConnectionManager:

    @pytest.mark.asyncio
    async def test_connect_and_send(self):
        """Manager can connect a WebSocket and send progress."""
        mgr = ConnectionManager()
        ws = AsyncMock()

        await mgr.connect("job-1", ws)
        assert "job-1" in mgr.active_connections

        await mgr.send_progress("job-1", {"status": "running", "progress_pct": 50})
        ws.send_json.assert_called_once_with({"status": "running", "progress_pct": 50})

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Manager removes WebSocket on disconnect."""
        mgr = ConnectionManager()
        ws = AsyncMock()

        await mgr.connect("job-2", ws)
        mgr.disconnect("job-2", ws)
        assert "job-2" not in mgr.active_connections

    @pytest.mark.asyncio
    async def test_multiple_connections(self):
        """Multiple clients can connect to the same job."""
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await mgr.connect("job-3", ws1)
        await mgr.connect("job-3", ws2)
        assert len(mgr.active_connections["job-3"]) == 2

        await mgr.send_progress("job-3", {"pct": 75})
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()


class TestProgressUpdate:

    def test_progress_publishes_to_redis(self):
        """send_progress_update publishes to Redis pubsub channel."""
        mock_redis = MagicMock()

        with patch("core.websocket.redis.Redis") as mock_cls:
            mock_cls.from_url.return_value = mock_redis

            send_progress_update(
                job_id="job-4",
                step="docking",
                progress_pct=45,
                message="Docking molecule 45 of 100",
            )

        mock_redis.publish.assert_called_once()
        channel, data = mock_redis.publish.call_args[0]
        assert channel == "job_progress:job-4"
        parsed = json.loads(data)
        assert parsed["progress_pct"] == 45
        assert parsed["step"] == "docking"

    def test_progress_caches_latest(self):
        """send_progress_update caches latest progress in Redis."""
        mock_redis = MagicMock()

        with patch("core.websocket.redis.Redis") as mock_cls:
            mock_cls.from_url.return_value = mock_redis

            send_progress_update("job-5", "admet", 100, "Done", status="completed")

        mock_redis.set.assert_called_once()
        key = mock_redis.set.call_args[0][0]
        assert key == "job_progress_latest:job-5"


class TestJobProgressSchema:

    def test_schema_validation(self):
        """JobProgressUpdate validates all fields correctly."""
        update = JobProgressUpdate(
            job_id="test-123",
            status="running",
            step="docking",
            progress_pct=45,
            message="Docking molecule 45 of 100",
            completed_steps=["target_lookup", "structure_fetch"],
            current_step="docking",
            pending_steps=["admet", "ranking"],
        )
        assert update.progress_pct == 45
        assert update.step == "docking"
        assert len(update.completed_steps) == 2


# ---------------------------------------------------------------------------
# Route-level tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient):
    """GET /api/jobs/{non-existent-id} returns 404."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/jobs/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient):
    """GET /api/jobs/ returns paginated job list."""
    response = await client.get("/api/jobs/?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert "total" in data
    assert data["limit"] == 5
