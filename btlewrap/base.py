"""Bluetooth Backends available for miflora and other btle sensors."""
from threading import Lock
from typing import List, Tuple, Optional


class BluetoothInterface:
    """Wrapper around the bluetooth adapters.

    This class takes care of locking and the context managers.
    """

    def __init__(
        self,
        backend: type,
        *,
        adapter: str = "hci0",
        address_type: str = "public",
        **kwargs
    ):
        self._backend = backend(adapter=adapter, address_type=address_type, **kwargs)
        self._backend.check_backend()

    def __del__(self):
        if self.is_connected():
            self._backend.disconnect()

    def connect(self, mac, timeout=None) -> "_BackendConnection":
        """Connect to the sensor."""
        return _BackendConnection(self._backend, mac, timeout)

    @staticmethod
    def is_connected() -> bool:
        """Check if we are connected to the sensor."""
        return _BackendConnection.is_connected()


class _BackendConnection:  # pylint: disable=too-few-public-methods
    """Context Manager for a bluetooth connection.

    This creates the context for the connection and manages locking.
    """

    _lock = Lock()

    def __init__(self, backend: "AbstractBackend", mac: str, timeout=None):
        self._backend = backend  # type: AbstractBackend
        self._mac = mac  # type: str
        self._timeout = timeout
        self._has_lock = False

    def __enter__(self) -> "AbstractBackend":
        self._lock.acquire()
        self._has_lock = True
        try:
            self._backend.connect(self._mac, timeout=self._timeout)
        # release lock on any exceptions otherwise it will never be unlocked
        except:  # noqa: E722
            self._cleanup()
            raise
        return self._backend

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup()

    def __del__(self):
        self._cleanup()

    def _cleanup(self):
        if self._has_lock:
            try:
                self._backend.disconnect()
            finally:
                self._lock.release()
                self._has_lock = False

    @staticmethod
    def is_connected() -> bool:
        """Check if the BackendConnection is connected."""
        return _BackendConnection._lock.locked()  # pylint: disable=no-member


class BluetoothBackendException(Exception):
    """Exception thrown by the different backends.

    This is a wrapper for other exception specific to each library."""


class AbstractBackend:
    """Abstract base class for talking to Bluetooth LE devices.

    This class will be overridden by the different backends used by miflora and other btle sensors.
    """

    _DATA_MODE_LISTEN = bytes([0x01, 0x00])

    def __init__(self, adapter: str, address_type: str, **kwargs):
        self.adapter = adapter
        self.address_type = address_type
        self.kwargs = kwargs

    def connect(self, mac: str, timeout=None):
        """connect to a device with the given @mac.

        only required by some backends"""

    def disconnect(self):
        """disconnect from a device.

        Only required by some backends"""

    def write_handle(self, handle: int, value: bytes):
        """Write a value to a handle.

        You must be connected to a device first."""
        raise NotImplementedError

    def wait_for_notification(self, handle: int, delegate, notification_timeout: float):
        """registers as a listener and calls the delegate's handleNotification
        for each notification received
        @param handle - the handle to use to register for notifications
        @param delegate - the delegate object's handleNotification is called for every notification received
        @param notification_timeout - wait this amount of seconds for notifications

        """
        raise NotImplementedError

    def read_handle(self, handle: int, timeout=None) -> bytes:
        """Read a handle from the sensor.

        You must be connected to a device first."""
        raise NotImplementedError

    @staticmethod
    def check_backend() -> bool:
        """Check if the backend is available on the current system.

        Returns True if the backend is available and False otherwise
        """
        raise NotImplementedError

    @staticmethod
    def scan_for_devices(
        timeout: int, adapter: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """Scan for additional devices.

        Returns a list of all the mac addresses of Xiaomi Mi Flower sensor that could be found.
        """
        raise NotImplementedError

    @staticmethod
    def supports_scanning() -> bool:
        """Check if this backend supports scanning for adapters."""
        raise NotImplementedError
