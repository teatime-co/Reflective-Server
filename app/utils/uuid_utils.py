from uuid import UUID
from typing import Union, Optional
from pydantic import UUID4

def ensure_uuid(value: Union[str, UUID, None]) -> Optional[str]:
    """Convert any UUID-like value to a string representation"""
    if value is None:
        return None
    # Convert to string and clean it
    str_value = str(value)
    # Remove any hyphens and create a new UUID
    clean_str = str_value.replace('-', '')
    if len(clean_str) != 32:
        raise ValueError(f"Invalid UUID string length: {len(clean_str)}")
    # Format with hyphens
    return f"{clean_str[:8]}-{clean_str[8:12]}-{clean_str[12:16]}-{clean_str[16:20]}-{clean_str[20:]}"

def ensure_uuid4(value: Union[str, UUID, None]) -> str:
    """Convert any UUID-like value to a string representation"""
    if value is None:
        raise ValueError("UUID cannot be None")
    return ensure_uuid(value)

def format_uuid_for_weaviate(value: Union[str, UUID]) -> str:
    """Convert any UUID-like value to Weaviate format (no hyphens)"""
    # Convert to string and remove hyphens
    str_value = str(value)
    return str_value.replace("-", "")

def format_uuid_from_weaviate(uuid_str: str) -> str:
    """Convert a UUID string from Weaviate format to standard format with hyphens"""
    # Clean the string
    clean_str = uuid_str.replace("-", "")
    if len(clean_str) != 32:
        raise ValueError(f"Invalid UUID string length: {len(clean_str)}")
    
    # Insert hyphens in correct positions
    return f"{clean_str[:8]}-{clean_str[8:12]}-{clean_str[12:16]}-{clean_str[16:20]}-{clean_str[20:]}" 