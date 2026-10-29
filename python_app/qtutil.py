"""Small Qt helper shared by the FitPlay windows."""
import threading

from PySide6.QtCore import QObject, Signal, Slot


class _Bridge(QObject):
    """Lives in the GUI thread. Worker threads emit `delivered`; the slot below then
    runs in the GUI thread, so callbacks may safely touch widgets."""
    delivered = Signal(object)

    def __init__(self):
        super().__init__()
        self.delivered.connect(self._deliver)

    @Slot(object)
    def _deliver(self, payload):
        callback, value = payload
        try:
            callback(value)
        except Exception as e:       # a UI callback must never kill the app
            print(f"[qtutil] callback error: {e}")


_bridge = None


def run_async(work, done, fail=None):
    """Run work() on a background thread, then call done(result) on the GUI thread.
    If work() raises, fail(message) is called instead (or the error is printed).
    Call this from the GUI thread."""
    global _bridge
    if _bridge is None:
        _bridge = _Bridge()
    bridge = _bridge

    def target():
        try:
            result = work()
        except Exception as e:
            msg = str(e) or e.__class__.__name__
            if fail is not None:
                bridge.delivered.emit((fail, msg))
            else:
                print(f"[qtutil] background error: {msg}")
            return
        bridge.delivered.emit((done, result))

    threading.Thread(target=target, daemon=True).start()