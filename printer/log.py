import logging

def init():
    # Define a new log level for success messages
    SUCCESS = 25  # Between INFO (20) and WARNING (30)

    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s][%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True,
    )

    def success(message, *args, **kwargs):
        """
        Log a success message with level SUCCESS.
        This level is between INFO and WARNING.
        """
        logging.log(SUCCESS, message, *args, **kwargs)

    # Custom log level formats
    logging.addLevelName(logging.DEBUG, "D")
    logging.addLevelName(logging.INFO, "*")
    logging.addLevelName(SUCCESS, "+")
    logging.addLevelName(logging.ERROR, "!")
    logging.addLevelName(logging.FATAL, "F")

    # Add the success method to the logging module
    logging.success = success
