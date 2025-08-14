
@dataclass
class Register:
    RQ: str = "None"
    Name: str = "None"
    Role: str = "None"
    IP_Address: str = "None"
    UDP_Socket: str = "None"
    TCP_Socket: str = "None"

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Register':
        return Register(
            RQ=data.get("RQ#", "None"),
            Name=data.get("Name", "None"),
            Role=data.get("Role", "None"),
            IP_Address=data.get("IP Address", "None"),
            UDP_Socket=data.get("UDP Socket#", "None"),
            TCP_Socket=data.get("TCP Socket#", "None")
        )

    def is_complete(self) -> bool:
        return all(value != "None" for value in asdict(self).values())

@dataclass
class Deregister:
    RQ: str = "None"
    Name: str = "None"

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Deregister':
        return Deregister(
            RQ=data.get("RQ#", "None"),
            Name=data.get("Name", "None")
        )

    def is_complete(self) -> bool:
        return all(value != "None" for value in asdict(self).values())


@dataclass
class RegisterDenied:
    RQ: str = "None"
    Reason: str = "None"

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'RegisterDenied':
        return RegisterDenied(
            RQ=data.get("RQ#", "None"),
            Reason=data.get("Reason", "None")
        )

    def is_complete(self) -> bool:
        return all(value != "None" for value in asdict(self).values())
