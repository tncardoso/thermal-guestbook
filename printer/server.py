import io
import argparse
import uvicorn
import logging
from pathlib import Path
from escpos.printer import Usb
from printer.model import Message
import paho.mqtt.client as mqtt
from fastapi import FastAPI
from starlette.responses import FileResponse 
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

@app.get("/")
def index() -> FileResponse:
    # not using StaticFiles to be extra-safe
    return FileResponse("public/index.html")

@app.get("/printer.png")
def printer_png() -> FileResponse:
    # not using StaticFiles to be extra-safe
    return FileResponse("public/printer.png")

@app.get("/send")
def send():
    img_data = open("download.png", "rb").read()
    msg = Message(
        title="Hello world!",
        img=img_data,
        msg="here a short tweet I want to share!",
    )
    print(msg.model_dump_json())
    client.publish("printer", msg.model_dump_json(), qos=2)

