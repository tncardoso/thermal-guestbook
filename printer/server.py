import io
import argparse
import uvicorn
import logging
import base64
from pathlib import Path
from typing import Optional
from escpos.printer import Usb
from printer.model import Message
import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException
from starlette.responses import FileResponse
from pydantic import BaseModel, Field # Import Field
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

# Pydantic model for the print request body with validation
class PrintRequest(BaseModel):
    # Allow None, but if present, limit length. Default to None if empty string is sent.
    title: Optional[str] = Field(default=None, max_length=40)
    # Image data URL is required, but content validation happens later
    img: str
    # Message is required (can be empty string), limit length
    msg: str = Field(max_length=180)

@app.get("/")
def index() -> FileResponse:
    # not using StaticFiles to be extra-safe
    return FileResponse("public/index.html")

@app.get("/printer.png")
def printer_png() -> FileResponse:
    # not using StaticFiles to be extra-safe
    return FileResponse("public/printer.png")

@app.post("/print")
async def print_message(request: PrintRequest): # FastAPI now validates request against PrintRequest model
    try:
        # Extract base64 data from the data URL
        img_data = b""
        if request.img and "," in request.img:
            try:
                header, encoded = request.img.split(",", 1)
                # Basic check if it looks like a PNG data URL header
                if header.startswith("data:image/png;base64"):
                    img_data = base64.b64decode(encoded)
                else:
                    logging.warning(f"Received image data URL with unexpected header: {header[:30]}...")
                    # Decide if you want to reject or proceed without image
                    # Proceeding without image for now
            except (ValueError, base64.binascii.Error) as decode_error:
                logging.warning(f"Could not decode image data URL: {decode_error}. Proceeding without image.")

        # Use provided title or a default if empty/None
        # Pydantic handles the None default, use "Web Print" if title is None or ""
        print_title = request.title if request.title else "Web Print"

        # Create the message object (Data is already validated by FastAPI/Pydantic)
        msg = Message(
            title=print_title,
            img=img_data,
            msg=request.msg, # Already validated for length
        )
        logging.info(f"Received print request: title='{print_title}', msg='{request.msg[:50]}...', img_size={len(img_data)} bytes") # Log truncated msg

        # Publish to MQTT
        client.publish("printer", msg.model_dump_json(), qos=2)

        logging.info("Published message to MQTT topic 'printer'")
        return {"status": "success", "message": "Print job sent"}
    except HTTPException:
         # Re-raise HTTP exceptions (like validation errors from FastAPI)
         raise
    except Exception as e:
        logging.error(f"Error processing print request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process print request: {e}")

