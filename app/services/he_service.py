"""
Homomorphic Encryption Service

Provides privacy-preserving analytics using TenSEAL CKKS encryption scheme.
Allows server to aggregate encrypted metrics without seeing plaintext values.

Key Features:
- CKKS scheme for floating-point operations
- Encrypt individual metrics (word counts, sentiment scores, etc.)
- Aggregate encrypted values (sum, average) without decryption
- Client-side encryption/decryption

Security:
- Poly modulus degree: 8192 (128-bit security)
- Scale: 2^40 for precision
- No plaintext values on server
"""

from __future__ import annotations

import tenseal as ts
import base64
from typing import List, Dict, Any, Union
import json
import time
from ..api.metrics import he_operation_duration, he_context_creation_duration


class HEService:
    """Homomorphic Encryption service for privacy-preserving analytics"""

    POLY_MODULUS_DEGREE = 8192
    COEFF_MOD_BIT_SIZES = [60, 40, 40, 60]
    SCALE = 2 ** 40

    @classmethod
    def create_context(cls, generate_galois_keys: bool = True, generate_relin_keys: bool = True) -> ts.Context:
        """
        Create CKKS encryption context

        Args:
            generate_galois_keys: Generate keys for rotation operations
            generate_relin_keys: Generate keys for relinearization (needed for multiplication)

        Returns:
            TenSEAL CKKS context
        """
        start_time = time.time()
        context = ts.context(
            ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=cls.POLY_MODULUS_DEGREE,
            coeff_mod_bit_sizes=cls.COEFF_MOD_BIT_SIZES
        )
        context.global_scale = cls.SCALE

        if generate_galois_keys:
            context.generate_galois_keys()
        if generate_relin_keys:
            context.generate_relin_keys()

        duration = time.time() - start_time
        he_context_creation_duration.observe(duration)

        return context

    @classmethod
    def serialize_context(cls, context: ts.Context) -> str:
        """
        Serialize context for transmission to client

        Args:
            context: TenSEAL context

        Returns:
            Base64-encoded serialized context
        """
        serialized = context.serialize()
        return base64.b64encode(serialized).decode('utf-8')

    @classmethod
    def deserialize_context(cls, serialized_context: str) -> ts.Context:
        """
        Deserialize context from base64 string

        Args:
            serialized_context: Base64-encoded context

        Returns:
            TenSEAL context
        """
        context_bytes = base64.b64decode(serialized_context.encode('utf-8'))
        return ts.context_from(context_bytes)

    @classmethod
    def get_context_params(cls) -> Dict[str, Any]:
        """
        Get context parameters for client-side context creation

        Returns:
            Dictionary of context parameters
        """
        return {
            "scheme": "CKKS",
            "poly_modulus_degree": cls.POLY_MODULUS_DEGREE,
            "coeff_mod_bit_sizes": cls.COEFF_MOD_BIT_SIZES,
            "scale": cls.SCALE
        }

    @classmethod
    def encrypt_metric(cls, value: float, context: ts.Context) -> str:
        """
        Encrypt a single metric value

        Args:
            value: Metric value to encrypt (float)
            context: TenSEAL context

        Returns:
            Base64-encoded encrypted value
        """
        start_time = time.time()
        encrypted = ts.ckks_vector(context, [value])
        serialized = encrypted.serialize()
        duration = time.time() - start_time
        he_operation_duration.labels(operation='encrypt').observe(duration)
        return base64.b64encode(serialized).decode('utf-8')

    @classmethod
    def encrypt_metrics_batch(cls, values: List[float], context: ts.Context) -> str:
        """
        Encrypt multiple metrics as a single vector

        Args:
            values: List of metric values
            context: TenSEAL context

        Returns:
            Base64-encoded encrypted vector
        """
        encrypted = ts.ckks_vector(context, values)
        serialized = encrypted.serialize()
        return base64.b64encode(serialized).decode('utf-8')

    @classmethod
    def deserialize_encrypted(cls, encrypted_b64: str, context: ts.Context) -> ts.CKKSVector:
        """
        Deserialize encrypted value from base64

        Args:
            encrypted_b64: Base64-encoded encrypted value
            context: TenSEAL context

        Returns:
            TenSEAL CKKSVector
        """
        encrypted_bytes = base64.b64decode(encrypted_b64.encode('utf-8'))
        return ts.ckks_vector_from(context, encrypted_bytes)

    @classmethod
    def aggregate_sum(cls, encrypted_values: List[str], context: ts.Context) -> str:
        """
        Compute sum of encrypted values (homomorphic addition)

        Args:
            encrypted_values: List of base64-encoded encrypted values
            context: TenSEAL context

        Returns:
            Base64-encoded encrypted sum
        """
        if not encrypted_values:
            raise ValueError("Cannot aggregate empty list")

        start_time = time.time()
        result = cls.deserialize_encrypted(encrypted_values[0], context)

        for encrypted_val in encrypted_values[1:]:
            vec = cls.deserialize_encrypted(encrypted_val, context)
            result += vec

        serialized = result.serialize()
        duration = time.time() - start_time
        he_operation_duration.labels(operation='aggregate_sum').observe(duration)
        return base64.b64encode(serialized).decode('utf-8')

    @classmethod
    def aggregate_average(cls, encrypted_values: List[str], context: ts.Context) -> str:
        """
        Compute average of encrypted values (homomorphic addition + scalar division)

        Args:
            encrypted_values: List of base64-encoded encrypted values
            context: TenSEAL context

        Returns:
            Base64-encoded encrypted average
        """
        if not encrypted_values:
            raise ValueError("Cannot aggregate empty list")

        encrypted_sum = cls.deserialize_encrypted(
            cls.aggregate_sum(encrypted_values, context),
            context
        )

        count = len(encrypted_values)
        encrypted_avg = encrypted_sum * (1.0 / count)

        serialized = encrypted_avg.serialize()
        return base64.b64encode(serialized).decode('utf-8')

    @classmethod
    def decrypt_result(cls, encrypted_b64: str, context: ts.Context) -> float:
        """
        Decrypt encrypted result (client-side operation)

        Args:
            encrypted_b64: Base64-encoded encrypted value
            context: TenSEAL context with secret key

        Returns:
            Decrypted float value
        """
        start_time = time.time()
        encrypted = cls.deserialize_encrypted(encrypted_b64, context)
        decrypted_list = encrypted.decrypt()
        duration = time.time() - start_time
        he_operation_duration.labels(operation='decrypt').observe(duration)
        return decrypted_list[0]  # Return first element (single value)

    @classmethod
    def decrypt_batch(cls, encrypted_b64: str, context: ts.Context) -> List[float]:
        """
        Decrypt batch of encrypted values

        Args:
            encrypted_b64: Base64-encoded encrypted vector
            context: TenSEAL context with secret key

        Returns:
            List of decrypted float values
        """
        encrypted = cls.deserialize_encrypted(encrypted_b64, context)
        return encrypted.decrypt()


def create_client_context() -> tuple[ts.Context, str]:
    """
    Create context for client use

    Returns:
        Tuple of (context, serialized_public_context)
    """
    context = HEService.create_context()

    # Create public context (no secret key) for server
    public_context = ts.context_from(context.serialize(save_secret_key=False))
    serialized_public = HEService.serialize_context(public_context)

    return context, serialized_public


def encrypt_user_metrics(metrics: Dict[str, float], context: ts.Context) -> Dict[str, str]:
    """
    Encrypt multiple user metrics

    Args:
        metrics: Dictionary of metric_type -> value
        context: TenSEAL context

    Returns:
        Dictionary of metric_type -> encrypted_value (base64)
    """
    encrypted_metrics = {}
    for metric_type, value in metrics.items():
        encrypted_metrics[metric_type] = HEService.encrypt_metric(value, context)
    return encrypted_metrics


def decrypt_user_metrics(encrypted_metrics: Dict[str, str], context: ts.Context) -> Dict[str, float]:
    """
    Decrypt multiple user metrics

    Args:
        encrypted_metrics: Dictionary of metric_type -> encrypted_value
        context: TenSEAL context with secret key

    Returns:
        Dictionary of metric_type -> decrypted_value
    """
    decrypted_metrics = {}
    for metric_type, encrypted_value in encrypted_metrics.items():
        decrypted_metrics[metric_type] = HEService.decrypt_result(encrypted_value, context)
    return decrypted_metrics
