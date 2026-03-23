class W2TLayerNotFound(Exception):
    """Base class for all exceptions raised by the Wincan2Teksi plugin."""

    pass


class InvalidProjectFile(Exception):
    """Raised when the provided project file is invalid or corrupted."""

    pass
