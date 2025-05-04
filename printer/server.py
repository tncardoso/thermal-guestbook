import io
import argparse
import uvicorn
import logging
import base64
from pathlib import Path
from typing import Optional
# Import Pillow and BytesIO
from PIL import Image
from io import BytesIO
# Remove unused Usb import if not needed elsewhere in the full file
# from escpos.printer import Usb
from printer.model import Message
import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException
from starlette.responses import FileResponse
from pydantic import BaseModel, Field # Import Field
from printer.log import init

# init log config
init()

# --- Expected Image Dimensions ---
EXPECTED_WIDTH = 256
EXPECTED_HEIGHT = 256
# ---------------------------------

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
    img: Optional[str]
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

@app.get("/WebPlus_HP_100LX_6x8.woff")
def font_hp100() -> FileResponse:
    # not using StaticFiles to be extra-safe
    return FileResponse("public/WebPlus_HP_100LX_6x8.woff")

@app.post("/print")
async def print_message(request: PrintRequest): # FastAPI validates length constraints from PrintRequest
    try:
        # --- Image Decoding ---
        img_data = b""
        if request.img and "," in request.img:
            try:
                header, encoded = request.img.split(",", 1)
                # Basic check if it looks like a PNG data URL header
                if header.startswith("data:image/png;base64"):
                    img_data = base64.b64decode(encoded)
                else:
                    # If header is wrong, treat as bad request (invalid image format)
                    logging.warning(f"Received image data URL with unexpected header: {header[:30]}...")
                    raise HTTPException(status_code=400, detail="Invalid image format. Expected PNG data URL.")
            except (ValueError, base64.binascii.Error) as decode_error:
                logging.warning(f"Could not decode image base64 data: {decode_error}.")
                raise HTTPException(status_code=400, detail="Invalid image base64 data.")

        # --- Image Dimension Validation ---
        if img_data: # Only validate if image data was successfully decoded
            try:
                image_stream = BytesIO(img_data)
                with Image.open(image_stream) as img:
                    # Check dimensions
                    if img.width != EXPECTED_WIDTH or img.height != EXPECTED_HEIGHT:
                        logging.warning(f"Received image with incorrect dimensions: {img.width}x{img.height}. Expected {EXPECTED_WIDTH}x{EXPECTED_HEIGHT}.")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid image dimensions. Expected {EXPECTED_WIDTH}x{EXPECTED_HEIGHT}, but got {img.width}x{img.height}."
                        )
                    logging.info(f"Image dimensions validated: {img.width}x{img.height}")
            except Exception as img_err: # Catch PIL errors (invalid format etc.)
                logging.warning(f"Failed to process image data: {img_err}", exc_info=True)
                raise HTTPException(status_code=400, detail="Invalid or corrupted image data.")
        else:
            # If img field in request was present but resulted in empty img_data (e.g., empty data URL),
            # you might want to decide if this is an error or acceptable.
            # Currently, it proceeds without an image, which might be desired if only text/title is sent.
            logging.info("No valid image data provided or decoded, proceeding without image.")


        # --- Prepare Message ---
        # Use provided title or a default if empty/None
        # Pydantic handles the None default, use "Web Print" if title is None or ""
        print_title = request.title if request.title else "No Title Message"

        # Create the message object (Data lengths already validated by FastAPI/Pydantic)
        msg = Message(
            title=print_title,
            img=img_data, # Use the validated (or empty) image data
            msg=request.msg,
        )
        logging.info(f"Received print request: title='{print_title}', msg='{request.msg[:50]}...', img_size={len(img_data)} bytes") # Log truncated msg

        # --- Publish to MQTT ---
        client.publish("printer", msg.model_dump_json(), qos=2)

        logging.info("Published message to MQTT topic 'printer'")
        return {"status": "success", "message": "Thanks for your message!"}

    except HTTPException:
         # Re-raise HTTP exceptions (like validation errors from FastAPI or our custom ones)
         raise
    except Exception as e:
        # Catch any other unexpected errors during processing
        logging.error(f"Unexpected error processing print request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error processing print request.")

