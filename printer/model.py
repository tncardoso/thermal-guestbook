import unicodedata
from pydantic import BaseModel, ConfigDict, field_validator

class Message(BaseModel):
    title: str
    img: bytes
    msg: str

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


