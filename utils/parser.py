from dataclasses import dataclass, asdict
from typing import Any, Dict
import json

### --- UTILITY FUNCTIONS --- ###

def parse_message(json_str: str) -> Any:
    """Parses a JSON string and returns the corresponding message object."""
    try:
        data = json.loads(json_str)
        if "Register" in data:
            return Register.from_dict(data["Register"])
        elif "Deregister" in data:
            return Deregister.from_dict(data["Deregister"])
        elif "Register-Denied" in data:
            return RegisterDenied.from_dict(data["Register-Denied"])
        elif "List_Item" in data:
            return ListItem.from_dict(data["List_Item"])
        else:
            raise ValueError("Unsupported message type.")
    except Exception as e:
        raise ValueError(f"Failed to parse message: {e}")

def is_message_complete(message: Any) -> bool:
    """Checks whether all fields in a message are set (i.e., not 'None')."""
    return message.is_complete()
