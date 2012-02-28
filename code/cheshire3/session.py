

class Session:
    """An object to be passed around amongst the processing objects to
    maintain a session.  It stores, for example, the current
    environment, user and identifier for the database."""
    user = None
    logger = None
    task = ""
    database = ""
    environment = ""

    def __init__(self, user=None, logger=None, task="", database="", environment="terminal"):
        self.user = user
        self.logger = logger
        self.task = task
        self.database = database
        self.environment = environment

        # a comment
