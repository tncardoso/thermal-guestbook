import io
import argparse
import uvicorn
import logging
import base64
from pathlib import Path
from escpos.printer import Usb
from printer.model import Message
import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException
from starlette.responses import FileResponse
from pydantic import BaseModel
from printer.log import init

# init log config
init()

def on_connect(client, userdata, flags, rc, props):
    if rc == 0:
        logging.success("Connected to MQTT broker!")
    else:
        logging.fatal(f"Failed to connect, return code: {rc}")
        import sys; sys.exit(1)

# start MQTT Client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.connect("127.0.0.1", 1883)
client.loop_start()

app = FastAPI()

# Pydantic model for the print request body
class PrintRequest(BaseModel):
    img: str  # Base64 encoded image data URL (e.g., data:image/png;base64,...)
    msg: str

@app.get("/")
def index() -> FileResponse:
    # not using StaticFiles to be extra-safe
    return FileResponse("public/index.html")

@app.get("/printer.png")
def printer_png() -> FileResponse:
    # not using StaticFiles to be extra-safe
    return FileResponse("public/printer.png")

@app.post("/print")
async def print_message(request: PrintRequest):
    try:
        # Extract base64 data from the data URL
        header, encoded = request.img.split(",", 1)
        img_data = base64.b64decode(encoded)

        # Create the message object
        msg = Message(
            title="Web Print", # You might want to make the title dynamic later
            img=img_data,
            msg=request.msg,
        )
        logging.info(f"Received print request: msg='{request.msg}', img_size={len(img_data)} bytes")

        # Publish to MQTT
        client.publish("printer", msg.model_dump_json(), qos=2)

        logging.info("Published message to MQTT topic 'printer'")
        return {"status": "success", "message": "Print job sent"}
    except Exception as e:
        logging.error(f"Error processing print request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process print request: {e}")

