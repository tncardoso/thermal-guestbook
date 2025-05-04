import io
import argparse
import uvicorn
import logging
import base64
from pathlib import Path
from typing import Optional # Import Optional
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
    title: Optional[str] = None # Add optional title field
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
        # Handle cases where the image might be empty (e.g., just text/title sent)
        img_data = b"" # Default to empty bytes
        if request.img and "," in request.img:
            try:
                header, encoded = request.img.split(",", 1)
                img_data = base64.b64decode(encoded)
            except (ValueError, base64.binascii.Error) as decode_error:
                logging.warning(f"Could not decode image data URL: {decode_error}. Proceeding without image.")
                # Keep img_data as empty bytes

        # Use provided title or a default if empty/None
        print_title = request.title if request.title else "Web Print"

        # Create the message object
        msg = Message(
            title=print_title, # Use the received or default title
            img=img_data,
            msg=request.msg,
        )
        logging.info(f"Received print request: title='{print_title}', msg='{request.msg}', img_size={len(img_data)} bytes")

        # Publish to MQTT
        client.publish("printer", msg.model_dump_json(), qos=2)

        logging.info("Published message to MQTT topic 'printer'")
        return {"status": "success", "message": "Print job sent"}
    except Exception as e:
        logging.error(f"Error processing print request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process print request: {e}")

