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
# Import Request from FastAPI
from fastapi import FastAPI, HTTPException, Request
from starlette.responses import FileResponse
from pydantic import BaseModel, Field # Import Field
from printer.log import init
# Import the DB class
from printer.db import DB

# init log config
init()

# --- Expected Image Dimensions ---
EXPECTED_WIDTH = 256
EXPECTED_HEIGHT = 256
# ---------------------------------

# --- Initialize Database ---
try:
    db = DB() # Default path "printer_messages.db"
    logging.info("Database connection established for server.")
except Exception as e:
    logging.critical(f"Failed to initialize database: {e}", exc_info=True)
    import sys; sys.exit(1) # Exit if DB connection fails
# ---------------------------

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
    # Image data URL is optional
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

# Add Request to the function signature
@app.post("/print")
async def print_message(print_req: PrintRequest, req: Request): # FastAPI validates length constraints from PrintRequest
    try:
        # Get client IP address
        client_ip = req.client.host if req.client else "Unknown"
        logging.info(f"Received print request from IP: {client_ip}")

        # --- Image Decoding ---
        img_data = b"" # Default to empty bytes
        if print_req.img and "," in print_req.img:
            try:
                header, encoded = print_req.img.split(",", 1)
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
        elif print_req.img is not None: # Handle case where img is present but not a valid data URL format
             logging.warning("Received 'img' field but it was not a valid data URL format.")
             # Treat as no image
             img_data = None # Explicitly set to None if format is invalid

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
            except HTTPException:
                 raise # Re-raise validation HTTPException
            except Exception as img_err: # Catch PIL errors (invalid format etc.)
                logging.warning(f"Failed to process image data: {img_err}", exc_info=True)
                raise HTTPException(status_code=400, detail="Invalid or corrupted image data.")
        else:
            # If img field in request was present but resulted in empty img_data (e.g., empty data URL or invalid format handled above),
            # log that we are proceeding without an image.
            logging.info("No valid image data provided or decoded, proceeding without image.")
            img_data = None # Ensure img_data is None if no valid image


        # --- Prepare Message ---
        # Use provided title or a default if empty/None
        # Pydantic handles the None default, use "Web Print" if title is None or ""
        print_title = print_req.title if print_req.title else "No Title Message"

        # Create the message object (Data lengths already validated by FastAPI/Pydantic)
        # Add the client_ip here
        msg = Message(
            title=print_title,
            img=img_data, # Use the validated (or None) image data
            msg=print_req.msg,
            ip_address=client_ip # Add the IP address
        )
        logging.info(f"Prepared message: title='{print_title}', msg='{print_req.msg[:50]}...', img_size={len(img_data) if img_data else 0} bytes, ip={client_ip}")

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

# --- New Endpoint for Message Count ---
@app.get("/count")
async def get_message_count():
    """
    Returns the total number of messages stored in the database.
    """
    try:
        count = db.count()
        logging.debug(f"Retrieved message count: {count}")
        return {"count": count}
    except Exception as e:
        logging.error(f"Error retrieving message count from database: {e}", exc_info=True)
        # Return a 500 error if the database count fails
        raise HTTPException(status_code=500, detail="Could not retrieve message count.")
# --------------------------------------

# --- Graceful Shutdown ---
# Consider adding lifespan events for cleaner DB closing if needed,
# but __del__ in DB class provides some safety.
# @app.on_event("shutdown")
# def shutdown_event():
#     logging.info("Shutting down server...")
#     if db:
#         db.close()
#     client.loop_stop()
#     logging.info("MQTT client loop stopped.")
# -------------------------

