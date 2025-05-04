import base64
from pydantic import BaseModel, ConfigDict, field_validator

class Message(BaseModel):
    title: str
    img: bytes
    msg: str

    model_config = ConfigDict(
        ser_json_bytes="base64",
        val_json_bytes="base64",
    )


