"""
Tests for Homomorphic Encryption Service

Tests CKKS encryption, aggregation, and serialization.
"""

import pytest
import tenseal as ts
from app.services.he_service import (
    HEService,
    create_client_context,
    encrypt_user_metrics,
    decrypt_user_metrics
)


class TestHEServiceContextCreation:
    """Test context creation and serialization"""

    def test_create_context(self):
        """Test basic context creation"""
        context = HEService.create_context()

        assert context is not None
        assert context.is_private() is True  # Has secret key

    def test_context_parameters(self):
        """Test context has correct parameters"""
        context = HEService.create_context()

        # Check poly modulus degree
        # Note: TenSEAL doesn't expose poly_modulus_degree directly,
        # but we can verify context was created successfully
        assert context.global_scale == HEService.SCALE

    def test_serialize_deserialize_context(self):
        """Test context serialization roundtrip"""
        original_context = HEService.create_context()

        serialized = HEService.serialize_context(original_context)
        assert isinstance(serialized, str)
        assert len(serialized) > 0

        deserialized_context = HEService.deserialize_context(serialized)
        assert deserialized_context is not None

        # Test encryption works with deserialized context
        encrypted = HEService.encrypt_metric(42.5, deserialized_context)
        assert isinstance(encrypted, str)

    def test_get_context_params(self):
        """Test getting context parameters"""
        params = HEService.get_context_params()

        assert params["scheme"] == "CKKS"
        assert params["poly_modulus_degree"] == 8192
        assert params["coeff_mod_bit_sizes"] == [60, 40, 40, 60]
        assert params["scale"] == 2 ** 40

    def test_create_client_context(self):
        """Test creating context for client use"""
        context, serialized_public = create_client_context()

        # Context should have secret key
        assert context.is_private() is True

        # Serialized public context should be a string
        assert isinstance(serialized_public, str)
        assert len(serialized_public) > 0

        # Public context should not have secret key
        public_context = HEService.deserialize_context(serialized_public)
        assert public_context.is_private() is False


class TestHEServiceEncryption:
    """Test encryption and decryption"""

    def test_encrypt_decrypt_single_value(self):
        """Test encrypting and decrypting a single value"""
        context = HEService.create_context()
        original_value = 42.5

        encrypted = HEService.encrypt_metric(original_value, context)
        assert isinstance(encrypted, str)

        decrypted = HEService.decrypt_result(encrypted, context)
        assert isinstance(decrypted, float)
        assert abs(decrypted - original_value) < 0.01  # Allow small precision error

    def test_encrypt_decrypt_batch(self):
        """Test encrypting and decrypting multiple values"""
        context = HEService.create_context()
        original_values = [10.5, 20.3, 30.7, 40.2]

        encrypted = HEService.encrypt_metrics_batch(original_values, context)
        assert isinstance(encrypted, str)

        decrypted = HEService.decrypt_batch(encrypted, context)
        assert isinstance(decrypted, list)
        assert len(decrypted) == len(original_values)

        for original, decrypted_val in zip(original_values, decrypted):
            assert abs(decrypted_val - original) < 0.01

    def test_encrypt_zero(self):
        """Test encrypting zero value"""
        context = HEService.create_context()

        encrypted = HEService.encrypt_metric(0.0, context)
        decrypted = HEService.decrypt_result(encrypted, context)

        assert abs(decrypted - 0.0) < 0.01

    def test_encrypt_negative(self):
        """Test encrypting negative values"""
        context = HEService.create_context()
        original_value = -15.7

        encrypted = HEService.encrypt_metric(original_value, context)
        decrypted = HEService.decrypt_result(encrypted, context)

        assert abs(decrypted - original_value) < 0.01

    def test_encrypt_large_value(self):
        """Test encrypting large values"""
        context = HEService.create_context()
        original_value = 999999.99

        encrypted = HEService.encrypt_metric(original_value, context)
        decrypted = HEService.decrypt_result(encrypted, context)

        assert abs(decrypted - original_value) < 1.0  # Allow larger error for large values


class TestHEServiceAggregation:
    """Test homomorphic aggregation operations"""

    def test_aggregate_sum_two_values(self):
        """Test summing two encrypted values"""
        context = HEService.create_context()
        value1, value2 = 10.5, 20.3

        encrypted1 = HEService.encrypt_metric(value1, context)
        encrypted2 = HEService.encrypt_metric(value2, context)

        encrypted_sum = HEService.aggregate_sum([encrypted1, encrypted2], context)

        decrypted_sum = HEService.decrypt_result(encrypted_sum, context)

        expected_sum = value1 + value2
        assert abs(decrypted_sum - expected_sum) < 0.01

    def test_aggregate_sum_multiple_values(self):
        """Test summing multiple encrypted values"""
        context = HEService.create_context()
        values = [10.0, 20.0, 30.0, 40.0, 50.0]

        encrypted_values = [HEService.encrypt_metric(v, context) for v in values]

        encrypted_sum = HEService.aggregate_sum(encrypted_values, context)

        decrypted_sum = HEService.decrypt_result(encrypted_sum, context)

        expected_sum = sum(values)
        assert abs(decrypted_sum - expected_sum) < 0.1

    def test_aggregate_average_two_values(self):
        """Test averaging two encrypted values"""
        context = HEService.create_context()
        value1, value2 = 10.0, 20.0

        encrypted1 = HEService.encrypt_metric(value1, context)
        encrypted2 = HEService.encrypt_metric(value2, context)

        encrypted_avg = HEService.aggregate_average([encrypted1, encrypted2], context)

        decrypted_avg = HEService.decrypt_result(encrypted_avg, context)

        expected_avg = (value1 + value2) / 2
        assert abs(decrypted_avg - expected_avg) < 0.01

    def test_aggregate_average_multiple_values(self):
        """Test averaging multiple encrypted values"""
        context = HEService.create_context()
        values = [100.0, 200.0, 300.0, 400.0, 500.0]

        encrypted_values = [HEService.encrypt_metric(v, context) for v in values]

        encrypted_avg = HEService.aggregate_average(encrypted_values, context)

        decrypted_avg = HEService.decrypt_result(encrypted_avg, context)

        expected_avg = sum(values) / len(values)
        assert abs(decrypted_avg - expected_avg) < 1.0

    def test_aggregate_sum_with_negatives(self):
        """Test sum with mixed positive/negative values"""
        context = HEService.create_context()
        values = [10.0, -5.0, 20.0, -10.0, 15.0]

        encrypted_values = [HEService.encrypt_metric(v, context) for v in values]
        encrypted_sum = HEService.aggregate_sum(encrypted_values, context)
        decrypted_sum = HEService.decrypt_result(encrypted_sum, context)

        expected_sum = sum(values)
        assert abs(decrypted_sum - expected_sum) < 0.1

    def test_aggregate_empty_list_raises_error(self):
        """Test that aggregating empty list raises error"""
        context = HEService.create_context()

        with pytest.raises(ValueError, match="Cannot aggregate empty list"):
            HEService.aggregate_sum([], context)

        with pytest.raises(ValueError, match="Cannot aggregate empty list"):
            HEService.aggregate_average([], context)


class TestHEServiceUserMetrics:
    """Test convenience functions for user metrics"""

    def test_encrypt_user_metrics(self):
        """Test encrypting dictionary of user metrics"""
        context = HEService.create_context()
        metrics = {
            "word_count": 500.0,
            "sentiment": 0.75,
            "duration": 1200.0
        }

        encrypted = encrypt_user_metrics(metrics, context)

        assert isinstance(encrypted, dict)
        assert len(encrypted) == 3
        assert all(isinstance(v, str) for v in encrypted.values())

    def test_decrypt_user_metrics(self):
        """Test decrypting dictionary of user metrics"""
        context = HEService.create_context()
        metrics = {
            "word_count": 500.0,
            "sentiment": 0.75,
            "duration": 1200.0
        }

        # Encrypt then decrypt
        encrypted = encrypt_user_metrics(metrics, context)
        decrypted = decrypt_user_metrics(encrypted, context)

        assert isinstance(decrypted, dict)
        assert len(decrypted) == 3

        for key, original_value in metrics.items():
            assert abs(decrypted[key] - original_value) < 0.01

    def test_encrypt_decrypt_metrics_roundtrip(self):
        """Test full roundtrip of metrics encryption"""
        context = HEService.create_context()
        original_metrics = {
            "word_count": 750.0,
            "sentiment_score": 0.82,
            "complexity_score": 0.65,
            "session_duration": 1800.0,
            "vocabulary_diversity": 0.71
        }

        encrypted = encrypt_user_metrics(original_metrics, context)
        decrypted = decrypt_user_metrics(encrypted, context)

        # Verify all metrics preserved
        for key, original_value in original_metrics.items():
            assert key in decrypted
            assert abs(decrypted[key] - original_value) < 0.01


class TestHEServiceSerialization:
    """Test serialization with encrypted values"""

    def test_deserialize_encrypted_value(self):
        """Test deserializing encrypted value"""
        context = HEService.create_context()
        value = 42.0

        encrypted = HEService.encrypt_metric(value, context)

        encrypted_vec = HEService.deserialize_encrypted(encrypted, context)

        assert encrypted_vec is not None
        assert isinstance(encrypted_vec, ts.CKKSVector)

        decrypted_list = encrypted_vec.decrypt()
        assert abs(decrypted_list[0] - value) < 0.01

    def test_serialize_deserialize_public_context(self):
        """Test public context can encrypt but not decrypt"""
        # Create context with secret key
        private_context = HEService.create_context()

        # Serialize without secret key
        private_serialized = private_context.serialize()
        public_serialized = private_context.serialize(save_secret_key=False)

        # Deserialize public context
        public_context = ts.context_from(public_serialized)

        # Public context should not be private
        assert public_context.is_private() is False

        # Encrypt with public context should work
        encrypted = HEService.encrypt_metric(42.0, public_context)
        assert isinstance(encrypted, str)

        # Decrypt with private context should work
        decrypted = HEService.decrypt_result(encrypted, private_context)
        assert abs(decrypted - 42.0) < 0.01


class TestHEServiceEdgeCases:
    """Test edge cases and error handling"""

    def test_very_small_values(self):
        """Test encrypting very small values"""
        context = HEService.create_context()
        value = 0.0001

        encrypted = HEService.encrypt_metric(value, context)
        decrypted = HEService.decrypt_result(encrypted, context)

        # Allow larger relative error for very small values
        assert abs((decrypted - value) / value) < 0.1 or abs(decrypted - value) < 0.0001

    def test_single_value_aggregation(self):
        """Test aggregating a single value"""
        context = HEService.create_context()
        value = 100.0

        encrypted = HEService.encrypt_metric(value, context)

        # Sum of single value
        encrypted_sum = HEService.aggregate_sum([encrypted], context)
        decrypted_sum = HEService.decrypt_result(encrypted_sum, context)
        assert abs(decrypted_sum - value) < 0.01

        # Average of single value
        encrypted_avg = HEService.aggregate_average([encrypted], context)
        decrypted_avg = HEService.decrypt_result(encrypted_avg, context)
        assert abs(decrypted_avg - value) < 0.01

    def test_precision_with_many_operations(self):
        """Test precision degradation with many operations"""
        context = HEService.create_context()

        # Create 100 small values
        values = [1.0] * 100

        # Encrypt all
        encrypted_values = [HEService.encrypt_metric(v, context) for v in values]

        # Sum (many additions)
        encrypted_sum = HEService.aggregate_sum(encrypted_values, context)
        decrypted_sum = HEService.decrypt_result(encrypted_sum, context)

        expected_sum = sum(values)
        # Allow larger error for many operations
        assert abs(decrypted_sum - expected_sum) < 1.0

        # Average
        encrypted_avg = HEService.aggregate_average(encrypted_values, context)
        decrypted_avg = HEService.decrypt_result(encrypted_avg, context)

        expected_avg = expected_sum / len(values)
        assert abs(decrypted_avg - expected_avg) < 0.1
