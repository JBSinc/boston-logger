from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("boston-logger")
except PackageNotFoundError:
    # package is not installed
    __version__ = "Unknown"
