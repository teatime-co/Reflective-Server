from uuid import UUID

def format_uuid_for_weaviate(uuid_str: str) -> str:
    """Convert a UUID string to the format used in Weaviate (no hyphens)"""
    return str(UUID(uuid_str)).replace("-", "")

def format_uuid_from_weaviate(uuid_str: str) -> str:
    """Convert a UUID string from Weaviate format to standard format with hyphens"""
    # If already has hyphens, return as is
    if "-" in uuid_str:
        return uuid_str
    
    # Insert hyphens in correct positions
    return f"{uuid_str[:8]}-{uuid_str[8:12]}-{uuid_str[12:16]}-{uuid_str[16:20]}-{uuid_str[20:]}"
