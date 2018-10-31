"""Mock SQS message object."""


class MockMessage():
    """Mock SQS message."""

    def __init__(self, body):
        """Initialize the message."""
        self.body = body
        self.deleted = False

    def delete(self):
        """Mock delete function."""
        self.deleted = True
