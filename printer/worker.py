import io
import logging
import argparse
from escpos.printer import Usb
from printer.model import Message
from printer.db import DB  # Import the DB class
import paho.mqtt.client as mqtt

VENDOR_ID = 0x6868
PRODUCT_ID = 0x0200
IN_EP = 0x81
OUT_EP = 0x03
PROFILE = "NT-5890K"

# Removed global variables:
# dry_run = False
# db_instance = None

def send_to_printer(msg: Message):
    try:
        printer = Usb(VENDOR_ID, PRODUCT_ID, in_ep=IN_EP, out_ep=OUT_EP, profile=PROFILE)
        printer.ln()
        printer.set(bold=True, align="center")
        printer.text(msg.title_ascii)
        printer.ln()

        # Ensure msg.img is bytes if not None before creating BytesIO
        img_bytes = msg.img if isinstance(msg.img, bytes) else None

        if img_bytes is not None:
            printer.ln(2)
            # Use the bytes directly with BytesIO
            printer.image(io.BytesIO(img_bytes), center=True)

        if msg.msg and msg.msg.strip() != "": # Check if msg exists and is not just whitespace
            printer.ln(2)
            printer.set(bold=False, align="left")
            printer.text(msg.msg_ascii)

        printer.ln(2)
        printer.text("-" * 30)
        printer.ln(2)
        printer.buzzer()
        #printer.cut()
        printer.close()
        logging.info(f"Successfully sent message '{msg.title}' to printer.")
    except Exception as e:
        logging.error(f"Failed to print message '{msg.title}': {e}", exc_info=True)


def on_connect(client, userdata, flags, rc, props):
    if rc == 0:
        logging.success("Connected to MQTT broker!")
        client.subscribe("printer") # Subscribe after successful connection
        logging.info("Subscribed to MQTT topic 'printer'")
    else:
        logging.fatal(f"Failed to connect to MQTT broker, return code: {rc}")
        import sys; sys.exit(1)

def on_message(client, userdata, raw_msg):
    # Access db_instance and dry_run from userdata dictionary
    db_instance = userdata.get('db')
    dry_run = userdata.get('dry_run', False) # Default to False if not found

    try:
        msg = Message.model_validate_json(raw_msg.payload)
        logging.info(f"Received message via MQTT: '{msg.title}'")

        # --- Save to Database ---
        if db_instance:
            logging.info(f"Attempting to save message '{msg.title}' to database...")
            insert_id = db_instance.insert(msg)
            if insert_id is not None:
                logging.success(f"Message '{msg.title}' saved to database with ID: {insert_id}")
            else:
                # Log error, but continue to print attempt
                logging.error(f"Failed to save message '{msg.title}' to database.")
        else:
            logging.warning("DB instance not available in userdata, skipping database save.")

        # --- Send to Printer ---
        logging.info(f"Attempting to print message: '{msg.title}'")
        if not dry_run:
            send_to_printer(msg)
        else:
            logging.info(f"DRY RUN: Printer function would be called for message '{msg.title}'.")

    except Exception as e:
        # Catch errors during message validation or processing
        logging.error(f"Error processing received MQTT message: {e}", exc_info=True)


def main():
    # No longer need global declarations here
    # global dry_run
    # global db_instance

    from printer.log import init
    init() # Initialize logging

    parser = argparse.ArgumentParser(description="Printer Worker: Listens for MQTT messages and prints them.")
    parser.add_argument("--mqtt-broker", type=str, default="127.0.0.1",
                        help="MQTT broker address (default: 127.0.0.1)")
    parser.add_argument("--mqtt-port", type=int, default=1883,
                        help="MQTT broker port (default: 1883)")
    parser.add_argument("--db-path", type=str, default="printer_messages.db",
                        help="Path to the SQLite database file (default: printer_messages.db)")
    parser.add_argument("--dry", default=False, action="store_true",
                        help="Dry run: process messages but do not send to the actual printer.")
    args = parser.parse_args()

    logging.info("Starting Printer Worker...")
    # Local variable for dry_run status
    dry_run_status = False
    if args.dry:
        logging.warning("Dry run mode enabled. Messages will not be sent to the printer.")
        dry_run_status = True

    # --- Initialize Database ---
    db_instance = None # Initialize local db_instance to None
    try:
        logging.info(f"Initializing database connection to: {args.db_path}")
        db_instance = DB(db_path=args.db_path)
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}. Worker will run without DB.", exc_info=True)
        # db_instance remains None

    # --- Initialize MQTT Client ---
    logging.info(f"Connecting to MQTT broker at {args.mqtt_broker}:{args.mqtt_port}...")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    # Set userdata to carry db_instance and dry_run status
    user_data = {'db': db_instance, 'dry_run': dry_run_status}
    client.user_data_set(user_data)

    try:
        client.connect(args.mqtt_broker, args.mqtt_port)
        client.loop_forever() # Blocks until client disconnects
    except Exception as e:
        logging.fatal(f"Failed to connect or run MQTT client loop: {e}", exc_info=True)
    finally:
        logging.info("Shutting down Printer Worker...")
        # Close DB connection if it was successfully created
        if db_instance:
            db_instance.close()
        # Stop MQTT client
        client.loop_stop() # Stop the network loop if loop_forever was interrupted
        client.disconnect()
        logging.info("MQTT client disconnected.")

if __name__ == "__main__":
    main()
