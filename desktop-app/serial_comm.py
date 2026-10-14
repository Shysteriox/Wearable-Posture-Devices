"""
Serial Communication for Wrist Posture Visualizer
Handles USB detection of the ESP32 wrist device and file transfer over serial.
"""
import os
import time
import threading
from typing import List, Optional, Callable

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


# Protocol constants
BAUD_RATE = 115200
HANDSHAKE_CMD = "\nCMD:HANDSHAKE\n"
LIST_CMD = "\nCMD:LIST\n"
DOWNLOAD_CMD = "\nCMD:DOWNLOAD:{filename}\n"
EXPECTED_HANDSHAKE = "WRIST_DEVICE_V1"
END_MARKER = "END"
EOF_MARKER = "EOF"
TIMEOUT = 3.0  # seconds


class DeviceConnection:
    """Manages USB serial connection to the wrist device."""

    def __init__(self):
        self._port: Optional[serial.Serial] = None
        self._port_name: str = ""
        self._connected: bool = False
        self._lock = threading.Lock()

    @property
    def connected(self) -> bool:
        return self._connected and self._port is not None and self._port.is_open

    @property
    def port_name(self) -> str:
        return self._port_name

    def scan_ports(self) -> List[dict]:
        """
        Scan all COM ports and return info about each.
        Returns list of dicts with keys: port, description, hwid
        """
        if not HAS_SERIAL:
            return []

        ports = []
        for p in serial.tools.list_ports.comports():
            ports.append({
                "port": p.device,
                "description": p.description or "",
                "hwid": p.hwid or "",
                "manufacturer": getattr(p, "manufacturer", "") or "",
            })
        return ports

    def find_esp32_port(self) -> Optional[str]:
        """
        Try to find the ESP32's COM port by checking known USB VID/PID
        combinations and descriptions.
        """
        if not HAS_SERIAL:
            return None

        esp32_indicators = [
            "CP210",       # Silicon Labs CP2102/CP2104 (common ESP32 USB chip)
            "CH340",       # CH340 USB-serial
            "CH910",       # CH9102
            "FTDI",        # FTDI chips
            "ESP32",       # Direct ESP32-S2/S3 USB
            "USB Serial",  # Generic
        ]

        # Known VID:PID pairs for common ESP32 USB chips
        esp32_vids = [
            "10C4",  # Silicon Labs
            "1A86",  # QinHeng CH340
            "0403",  # FTDI
            "303A",  # Espressif
        ]

        for p in serial.tools.list_ports.comports():
            desc = (p.description or "").upper()
            hwid = (p.hwid or "").upper()

            # Check VID
            for vid in esp32_vids:
                if vid.upper() in hwid:
                    return p.device

            # Check description
            for indicator in esp32_indicators:
                if indicator.upper() in desc:
                    return p.device

        return None

    def connect(self, port: Optional[str] = None) -> str:
        """
        Connect to the wrist device.
        If port is None, auto-detect the ESP32.
        Returns 'CONNECTED', 'PORT_BUSY', 'HANDSHAKE_FAILED', or 'NOT_FOUND'.
        """
        if not HAS_SERIAL:
            return "NOT_FOUND"

        with self._lock:
            # Close existing connection
            self.disconnect()

            # Find port
            target_port = port or self.find_esp32_port()
            if not target_port:
                return "NOT_FOUND"
            try:
                self._port = serial.Serial(
                    target_port,
                    baudrate=BAUD_RATE,
                    timeout=0.2,    # Short read timeout so we can poll quickly
                    write_timeout=1.0,
                )
                self._port.dtr = False  # Keep DTR low
                self._port.rts = False  # Keep RTS low — releases the ESP32 from bootloader/reset
                self._port_name = target_port

                # Wait for the serial port to settle
                time.sleep(0.5)
                self._port.reset_input_buffer()

                print(f"Connecting to {target_port}, waiting for bootloader & WiFi sync (up to 12s)...")
                
                # Listen to boot logs silently until ready
                start_time = time.time()
                device_ready = False
                while time.time() - start_time < 12.0:
                    if self._port.in_waiting > 0:
                        try:
                            line = self._port.readline().decode("utf-8", errors="ignore").strip()
                            if line:
                                print(f"Boot log: {line}")
                            if "Tracking started!" in line or "PitchDiff:" in line or "Calibration complete!" in line:
                                device_ready = True
                                break
                        except Exception as le:
                            print(f"Log read error: {le}")
                    time.sleep(0.1)

                # Short sleep to let it stabilize, then flush input buffer
                time.sleep(0.2)
                self._port.reset_input_buffer()

                # Send handshake
                print("Sending CMD:HANDSHAKE...")
                try:
                    self._port.write(HANDSHAKE_CMD.encode("utf-8"))
                    self._port.flush()
                except Exception as we:
                    print(f"Write error during handshake: {we}")

                # Read response
                deadline = time.time() + 3.0
                while time.time() < deadline:
                    try:
                        line = self._port.readline().decode("utf-8", errors="ignore").strip()
                        if EXPECTED_HANDSHAKE in line:
                            self._connected = True
                            self._port.timeout = TIMEOUT
                            print("Connection established successfully!")
                            return "CONNECTED"
                    except Exception as re:
                         print(f"Read error during handshake: {re}")
                    time.sleep(0.1)

                # Handshake failed
                self._port.close()
                self._port = None
                return "HANDSHAKE_FAILED"

            except serial.SerialException as se:
                print(f"Serial connect error: {se}")
                self._port = None
                if "PermissionError" in str(se) or "Access is denied" in str(se):
                    return "PORT_BUSY"
                return "NOT_FOUND"
            except Exception as e:
                print(f"Serial connect error: {e}")
                self._port = None
                return "NOT_FOUND"

    def disconnect(self):
        """Close the serial connection."""
        try:
            if self._port and self._port.is_open:
                self._port.close()
        except Exception:
            pass
        self._port = None
        self._connected = False
        self._port_name = ""

    def list_files(self) -> List[str]:
        """
        Request file listing from the device.
        Returns list of CSV filenames on the SD card.
        """
        if not self.connected:
            return []

        with self._lock:
            try:
                self._port.reset_input_buffer()
                self._port.write(LIST_CMD.encode("utf-8"))
                self._port.flush()

                files = []
                deadline = time.time() + TIMEOUT * 2
                while time.time() < deadline:
                    line = self._port.readline().decode("utf-8", errors="ignore").strip()
                    if line == END_MARKER:
                        break
                    if line.upper().endswith(".CSV"):
                        files.append(line)
                return files

            except Exception as e:
                print(f"Serial list_files error: {e}")
                return []

    def download_file(self, filename: str, save_dir: str,
                      progress_callback: Optional[Callable[[int], None]] = None) -> Optional[str]:
        """
        Download a CSV file from the device's SD card.
        Saves it to save_dir and returns the full path, or None on failure.
        """
        if not self.connected:
            return None

        with self._lock:
            try:
                self._port.reset_input_buffer()
                cmd = DOWNLOAD_CMD.format(filename=filename)
                self._port.write(cmd.encode("utf-8"))
                self._port.flush()

                lines = []
                bytes_received = 0
                deadline = time.time() + 30.0  # 30 second timeout for file download

                while time.time() < deadline:
                    line = self._port.readline().decode("utf-8", errors="ignore")
                    stripped = line.strip()

                    if stripped == EOF_MARKER:
                        break
                    if stripped.startswith("ERROR"):
                        print(f"Device error: {stripped}")
                        return None
                    
                    # Ignore any debug print statements or empty lines that were in the serial buffer
                    if not (stripped.startswith("elapsed_sec") or (stripped and stripped[0].isdigit())):
                        continue

                    lines.append(line)
                    bytes_received += len(line)

                    if progress_callback:
                        progress_callback(bytes_received)

                if not lines:
                    return None

                # Save to file
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, filename)
                with open(save_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)

                return save_path

            except Exception as e:
                print(f"Serial download error: {e}")
                return None

    def download_all_files(self, save_dir: str,
                           progress_callback: Optional[Callable[[str, int, int], None]] = None
                           ) -> List[str]:
        """
        Download all CSV files from the device.
        progress_callback(filename, current_index, total_count)
        Returns list of saved file paths.
        """
        files = self.list_files()
        if not files:
            return []

        saved = []
        for i, filename in enumerate(files):
            if progress_callback:
                progress_callback(filename, i + 1, len(files))
            path = self.download_file(filename, save_dir)
            if path:
                saved.append(path)

        return saved


# Singleton instance
_device = DeviceConnection()

def get_device() -> DeviceConnection:
    """Get the global DeviceConnection singleton."""
    return _device
