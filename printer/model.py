import unicodedata
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional

class Message(BaseModel):
    title: str
    img: Optional[bytes]
    msg: str
    ip_address: Optional[str] = None # Added IP address field

    def strip_accents(self, text: str) -> str:
        text = unicodedata.normalize('NFD', text)
        return ''.join([c for c in text if not unicodedata.combining(c)])

    @property
    def title_ascii(self) -> str:
        return self.strip_accents(self.title)

    @property
    def msg_ascii(self) -> str:
        return self.strip_accents(self.msg)

    model_config = ConfigDict(
        ser_json_bytes="base64",
        val_json_bytes="base64",
    )

