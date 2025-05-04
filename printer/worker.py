import io
import logging
import argparse
from escpos.printer import Usb
from printer.model import Message
import paho.mqtt.client as mqtt

VENDOR_ID = 0x6868
PRODUCT_ID = 0x0200
IN_EP = 0x81
OUT_EP = 0x03
PROFILE = "NT-5890K"

dry_run = False

def send_to_printer(msg: Message):
    printer = Usb(VENDOR_ID, PRODUCT_ID, in_ep=IN_EP, out_ep=OUT_EP, profile=PROFILE)
    printer.ln()
    printer.set(bold=True, align="center")
    printer.text(msg.title_ascii)
    printer.ln()

    if msg.img != None:
        printer.ln(2)
        printer.image(io.BytesIO(msg.img), center=True)

    if msg.msg.strip() != "":
        printer.ln(2)
        printer.set(bold=False, align="left")
        printer.text(msg.msg_ascii)

    printer.ln(2)
    printer.text("-" * 30)
    printer.ln(2)
    printer.buzzer()
    #printer.cut()
    printer.close()

def on_connect(client, userdata, flags, rc, props):
    if rc == 0:
        logging.success("Connected to MQTT broker!")
    else:
        logging.fatal(f"Failed to connect, return code: {rc}")
        import sys; sys.exit(1)

def on_message(client, userdata, raw_msg):
    msg = Message.model_validate_json(raw_msg.payload)
    logging.info(f"Printing message: '{msg.title}'")
    if not dry_run:
        send_to_printer(msg)
    else:
        logging.info("DRY RUN: printer would be called")

def main():
    global dry_run

    from printer.log import init
    init()

    parser = argparse.ArgumentParser()
    parser.add_argument("--mqtt-broker", type=str, default="127.0.0.1",
                        help="MQTT broker")
    parser.add_argument("--mqtt-port", type=int, default=1883,
                        help="MQTT port")
    parser.add_argument("--dry", default=False, action="store_true",
                        help="Dry run, do not print")
    args = parser.parse_args()

    logging.info("Connecting to MQTT broker...")
    dry_run = args.dry
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.mqtt_broker, args.mqtt_port)
    client.subscribe("printer")
    client.loop_forever()

if __name__ == "__main__":
    main()


