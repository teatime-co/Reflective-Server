import pytest
from fastapi import status
from datetime import datetime, timedelta
import base64
from app.models.models import User, EncryptedMetric


class TestEncryptionContext:
    """Tests for GET /api/encryption/context endpoint"""

    def test_get_encryption_context_success(self, client):
        """Test fetching HE context parameters"""
        response = client.get("/api/encryption/context")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "context_params" in data
        assert "serialized_context" in data

    def test_context_has_required_fields(self, client):
        """Test that context includes all required CKKS parameters"""
        response = client.get("/api/encryption/context")
        data = response.json()

        params = data["context_params"]
        assert params["scheme"] == "CKKS"
        assert params["poly_modulus_degree"] == 8192
        assert params["coeff_mod_bit_sizes"] == [60, 40, 40, 60]
        assert params["scale"] == 2 ** 40

    def test_context_serialization_valid(self, client):
        """Test that serialized context is base64 encoded"""
        response = client.get("/api/encryption/context")
        data = response.json()

        serialized = data.get("serialized_context")
        if serialized:
            try:
                base64.b64decode(serialized)
            except Exception:
                pytest.fail("Serialized context is not valid base64")


class TestUploadEncryptedMetrics:
    """Tests for POST /api/encryption/metrics endpoint"""

    def test_upload_encrypted_metrics_success(self, client, test_user, db):
        """Test successfully uploading encrypted metrics with analytics_sync tier"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'analytics_sync'
        db.commit()

        response = client.post(
            "/api/encryption/metrics",
            headers=test_user["headers"],
            json={
                "metrics": [
                    {
                        "metric_type": "word_count",
                        "encrypted_value": base64.b64encode(b"test_encrypted_value").decode(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert "Successfully stored 1 encrypted metrics" in data["message"]
        assert data["details"]["count"] == 1

    def test_upload_metrics_privacy_tier_local_only_forbidden(self, client, test_user, db):
        """Test that local_only users cannot upload encrypted metrics"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'local_only'
        db.commit()

        response = client.post(
            "/api/encryption/metrics",
            headers=test_user["headers"],
            json={
                "metrics": [
                    {
                        "metric_type": "word_count",
                        "encrypted_value": base64.b64encode(b"test").decode(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Cloud sync not enabled" in response.json()["detail"]

    def test_upload_metrics_analytics_sync_allowed(self, client, test_user, db):
        """Test that analytics_sync tier can upload metrics"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'analytics_sync'
        db.commit()

        response = client.post(
            "/api/encryption/metrics",
            headers=test_user["headers"],
            json={
                "metrics": [
                    {
                        "metric_type": "sentiment",
                        "encrypted_value": base64.b64encode(b"encrypted_sentiment").decode(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_upload_metrics_full_sync_allowed(self, client, test_user, db):
        """Test that full_sync tier can upload metrics"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'full_sync'
        db.commit()

        response = client.post(
            "/api/encryption/metrics",
            headers=test_user["headers"],
            json={
                "metrics": [
                    {
                        "metric_type": "duration",
                        "encrypted_value": base64.b64encode(b"encrypted_duration").decode(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_upload_metrics_batch(self, client, test_user, db):
        """Test uploading multiple metrics at once"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'full_sync'
        db.commit()

        response = client.post(
            "/api/encryption/metrics",
            headers=test_user["headers"],
            json={
                "metrics": [
                    {
                        "metric_type": "word_count",
                        "encrypted_value": base64.b64encode(b"value1").decode(),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    {
                        "metric_type": "sentiment",
                        "encrypted_value": base64.b64encode(b"value2").decode(),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    {
                        "metric_type": "duration",
                        "encrypted_value": base64.b64encode(b"value3").decode(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["details"]["count"] == 3


class TestAggregateMetrics:
    """Tests for POST /api/encryption/aggregate endpoint"""

    @pytest.fixture
    def setup_metrics(self, client, test_user, db):
        """Create encrypted metrics for aggregation tests"""
        from app.services.he_service import HEService

        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'full_sync'
        db.commit()

        context = HEService.create_context()

        for i in range(5):
            encrypted_value = HEService.encrypt_metric(float(i + 1), context)

            client.post(
                "/api/encryption/metrics",
                headers=test_user["headers"],
                json={
                    "metrics": [
                        {
                            "metric_type": "test_metric",
                            "encrypted_value": encrypted_value,
                            "timestamp": (datetime.utcnow() - timedelta(days=i)).isoformat()
                        }
                    ]
                }
            )

    def test_aggregate_metrics_sum(self, client, test_user, db, setup_metrics):
        """Test aggregating metrics with sum operation"""
        response = client.post(
            "/api/encryption/aggregate",
            headers=test_user["headers"],
            json={
                "metric_type": "test_metric",
                "operation": "sum"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metric_type"] == "test_metric"
        assert data["operation"] == "sum"
        assert data["count"] == 5
        assert "encrypted_result" in data

    def test_aggregate_metrics_average(self, client, test_user, db, setup_metrics):
        """Test aggregating metrics with average operation"""
        response = client.post(
            "/api/encryption/aggregate",
            headers=test_user["headers"],
            json={
                "metric_type": "test_metric",
                "operation": "average"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metric_type"] == "test_metric"
        assert data["operation"] == "average"
        assert data["count"] == 5

    def test_aggregate_metrics_not_found(self, client, test_user):
        """Test aggregating non-existent metrics returns 404"""
        response = client.post(
            "/api/encryption/aggregate",
            headers=test_user["headers"],
            json={
                "metric_type": "nonexistent_metric",
                "operation": "sum"
            }
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No encrypted metrics found" in response.json()["detail"]

    def test_aggregate_with_time_range_filter(self, client, test_user, db, setup_metrics):
        """Test aggregating metrics with time range filter"""
        now = datetime.utcnow()
        start = (now - timedelta(days=3)).isoformat()
        end = now.isoformat()

        response = client.post(
            "/api/encryption/aggregate",
            headers=test_user["headers"],
            json={
                "metric_type": "test_metric",
                "operation": "sum",
                "time_range": {
                    "start": start,
                    "end": end
                }
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] >=3 and data["count"] <= 4

    def test_aggregate_invalid_operation(self, client, test_user, db, setup_metrics):
        """Test that invalid operation returns 422"""
        response = client.post(
            "/api/encryption/aggregate",
            headers=test_user["headers"],
            json={
                "metric_type": "test_metric",
                "operation": "invalid_op"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
