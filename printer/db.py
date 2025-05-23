import sqlite3
import logging
from datetime import datetime
# Message model now includes ip_address field
from printer.model import Message

class DB:
    """
    Handles database operations for the printer application using SQLite.
    Assumes the table is created from scratch on initialization.
    """

    def __init__(self, db_path: str = "printer_messages.db"):
        """
        Initializes the database connection, sets journal mode to WAL,
        and creates the messages table.

        Args:
            db_path: The path to the SQLite database file.
        """
        try:
            self.db_path = db_path
            self.conn = sqlite3.connect(db_path, check_same_thread=False) # Allow access from different threads if needed
            self.cursor = self.conn.cursor()

            # Set journal mode to WAL
            self.cursor.execute("PRAGMA journal_mode=WAL;")
            current_journal_mode = self.cursor.fetchone()
            logging.info(f"SQLite journal mode set to: {current_journal_mode[0] if current_journal_mode else 'Unknown'}")
            if current_journal_mode and current_journal_mode[0].lower() != 'wal':
                 logging.warning(f"Failed to set journal_mode to WAL. Current mode: {current_journal_mode[0]}")


            self._create_table()
            logging.info(f"Database initialized successfully at {db_path}")
        except sqlite3.Error as e:
            logging.error(f"Database error during initialization: {e}", exc_info=True)
            if self.conn: # Attempt to close connection if it was opened before error
                self.conn.close()
            raise  # Re-raise the exception after logging

    def _create_table(self):
        """
        Creates the 'messages' table if it doesn't already exist.
        Includes the ip_address column. Assumes no pre-existing table needs altering.
        """
        try:
            # Create table with ip_address column if it doesn't exist
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    title TEXT,
                    img BLOB,
                    msg TEXT,
                    ip_address TEXT
                )
            """)
            self.conn.commit() # Commit the table creation
            logging.info("Table 'messages' checked/created successfully.")
        except sqlite3.Error as e:
            logging.error(f"Database error creating table: {e}", exc_info=True)
            raise

    def insert(self, message: Message):
        """
        Inserts a message into the database table, including the IP address.

        Args:
            message: A Message object containing the data to insert.

        Returns:
            The row ID of the inserted message, or None if insertion fails.
        """
        # Update SQL query to include ip_address
        sql = "INSERT INTO messages (title, img, msg, ip_address) VALUES (?, ?, ?, ?)"
        try:
            # Ensure img is bytes or None.
            img_data = message.img if isinstance(message.img, bytes) or message.img is None else None
            if message.img is not None and not isinstance(message.img, bytes):
                 logging.warning(f"Image data for insert was not bytes (type: {type(message.img)}), inserting NULL for image.")

            # Get ip_address from the message object (defaults to None in model)
            ip_addr = message.ip_address

            # Update parameters tuple to include ip_address
            self.cursor.execute(sql, (message.title, img_data, message.msg, ip_addr))
            self.conn.commit()
            last_id = self.cursor.lastrowid
            logging.info(f"Inserted message with ID: {last_id} from IP: {ip_addr}")
            return last_id
        except sqlite3.Error as e:
            logging.error(f"Database error inserting message: {e}", exc_info=True)
            self.conn.rollback() # Rollback on error
            return None


    def count(self) -> int:
        """
        Counts the total number of messages in the database.

        Returns:
            The total number of messages, or 0 if an error occurs or table is empty.
        """
        sql = "SELECT COUNT(*) FROM messages"
        try:
            self.cursor.execute(sql)
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            logging.error(f"Database error counting messages: {e}", exc_info=True)
            return 0 # Return 0 on error

    def close(self):
        """
        Closes the database connection.
        """
        if self.conn:
            try:
                # Optional: Commit any pending changes before closing, though WAL mode handles this differently.
                # self.conn.commit()
                self.conn.close()
                self.conn = None # Ensure the connection attribute is cleared
                logging.info("Database connection closed.")
            except sqlite3.Error as e:
                logging.error(f"Error closing database connection: {e}", exc_info=True)


    def __del__(self):
        """
        Ensure connection is closed when the object is destroyed.
        """
        self.close()

