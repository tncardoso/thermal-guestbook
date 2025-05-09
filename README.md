# Thermal Guestbook

## Overview

The Thermal Guestbook is a project that allows users to submit messages through a web interface. These messages are then queued via MQTT and printed on a connected thermal receipt printer. It serves as a digital-to-physical guestbook, creating tangible printouts of user entries.

The system comprises several key components:
-   **Web Server**: A FastAPI-based web application (`printer/server.py`) that serves the user interface and provides an API endpoint for message submission. It also handles image processing and validation.
-   **Message Queue**: MQTT is used as a message broker to decouple the web server from the printing process, ensuring messages are reliably passed to the printer worker.
-   **Printer Worker**: A Python script (`printer/worker.py`) that subscribes to MQTT topics, receives messages, stores them in a database, and sends them to the connected thermal printer using the `python-escpos` library.
-   **Database**: An SQLite database (`printer/db.py`) stores a record of all messages submitted, including an IP address and a unique ID that can be printed on the receipt.
-   **Data Model**: Pydantic models (`printer/model.py`) are used for data validation and serialization/deserialization.
-   **Logging**: A custom logging setup (`printer/log.py`) is used for clear and structured application logs.

## Configuration

Configuration of the Thermal Guestbook involves setting up parameters for the printer, MQTT broker, and database.

### Printer Settings
These settings are primarily located in `printer/worker.py`. You'll need to adjust them to match your specific thermal printer:
-   `VENDOR_ID`: The USB Vendor ID of your thermal printer (e.g., `0x6868`).
-   `PRODUCT_ID`: The USB Product ID of your thermal printer (e.g., `0x0200`).
-   `IN_EP`: The input endpoint for the USB printer.
-   `OUT_EP`: The output endpoint for the USB printer.
-   `PROFILE`: The printer profile name recognized by `python-escpos` (e.g., `"NT-5890K"`, `"POS-5890"`). This determines the command set used for printing.

Example in `printer/worker.py`:
