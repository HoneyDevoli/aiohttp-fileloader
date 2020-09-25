class ValidationError(Exception):
    """Exception raised for errors in the input request.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message=''):
        self.message = message
        super().__init__(self.message)
