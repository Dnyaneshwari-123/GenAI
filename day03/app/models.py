from dataclasses import dataclass, asdict


@dataclass
class Record:
    fraud_name: str
    channel: str
    how_it_works: str
    warning_signs: str
    precautions: str
    source_url: str
    id: int = 0

    def to_dict(self):
        return asdict(self)