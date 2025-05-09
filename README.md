# Thermal Guestbook

## Overview

The Thermal Guestbook is a project that allows users to submit messages through a web interface. These messages are then queued via MQTT and printed on a connected thermal receipt printer. It serves as a digital-to-physical guestbook, creating tangible printouts of user entries.

## Components

- **Web Server**: A FastAPI-based web application that serves the user interface and handles message submission
- **Message Queue**: MQTT broker for reliable message passing
- **Printer Worker**: Processes messages from the queue and sends them to the thermal printer
- **Database**: Stores all submitted messages with metadata

## Running the Application

The application uses `uv` to run Python scripts and consists of three main components that need to be running simultaneously:

### 1. Web Server

The web server handles user requests and provides the web interface.

```bash
uv run fastapi run printer/server.py
```

Or using make:

```bash
make server
```

### 2. Printer Worker

The worker listens for new messages and sends them to the thermal printer.

```bash
uv run printer/worker.py
```

Or using make:

```bash
make worker
```

### 3. Cloudflare Tunnel (Optional)

If you want to expose your application to the internet:

```bash
cloudflared tunnel run printer
```

Or using make:

```bash
make tunnel
```

### Running Everything at Once

To start all components in the background:

```bash
make all
```

## Configuration

### Printer Settings

Configure your thermal printer in `printer/worker.py`:

```python
VENDOR_ID = 0x6868
PRODUCT_ID = 0x0200
IN_EP = 0x81
OUT_EP = 0x03
PROFILE = "NT-5890K"  # or "POS-5890" depending on your printer
```

Adjust these values to match your specific thermal printer model.
