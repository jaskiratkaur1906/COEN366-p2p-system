@dataclass
class ListItem:
    RQ: str = "None"
    Item_Name: str = "None"
    Item_Description: str = "None"
    Start_Price: str = "None"
    Duration: str = "None"

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ListItem':
        return ListItem(
            RQ=data.get("RQ#", "None"),
            Item_Name=data.get("Item_Name", "None"),
            Item_Description=data.get("Item_Description", "None"),
            Start_Price=data.get("Start_Price", "None"),
            Duration=data.get("Duration", "None")
        )

    def is_complete(self) -> bool:
        return all(value != "None" for value in asdict(self).values())

