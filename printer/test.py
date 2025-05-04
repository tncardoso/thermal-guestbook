from pydantic import BaseModel
from escpos.printer import Usb
from pathlib import Path
#from printer.profile import KNUP_PROFILE

VENDOR_ID = 0x6868
PRODUCT_ID = 0x0200
IN_EP = 0x81
OUT_EP = 0x03
#PROFILE = "NT-5890K"
PROFILE = "POS-5890"

class Message(BaseModel):
    msg: str
    img: Path

try:
    # Initialize USB printer
    printer = Usb(VENDOR_ID, PRODUCT_ID, in_ep=IN_EP, out_ep=OUT_EP, profile=PROFILE)
    printer.charcode("CP850")
    
    # Print text
    #printer.text("Hello, Knup Printer!\n")
    #printer.text("This is a test print.\n")
    printer.text("tésté çom acéntò\n")
    printer.text("tésté çom acéntò\n")
    printer.text("tésté çom acéntò\n")
    
    # Optional: Print a barcode
    #printer.barcode("123456789012", "EAN13")

    #printer.image("download.png", center=True)
    
    # Cut the paper (if supported)
    #printer.cut()
    
    # Close the connection
    printer.close()
except Exception as e:
    print(f"Error: {e}")
