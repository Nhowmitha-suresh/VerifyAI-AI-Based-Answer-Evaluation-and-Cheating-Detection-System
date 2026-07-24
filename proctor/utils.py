"""
Utility Functions & OS File Descriptor / Win32 Kernel Redirector for C++ Log Silencing.
"""

import os
import sys
import math
import ctypes
import numpy as np

class SilenceFD:
    """
    Context manager that redirects OS-level file descriptors 1 (stdout) & 2 (stderr)
    AND Win32 OS Kernel STD_OUTPUT_HANDLE & STD_ERROR_HANDLE to NUL device.
    This 100% silences C++ protobuf calculator graph logging from MediaPipe/TensorFlow on Windows.
    """
    def __init__(self):
        self._enabled = True
        self._win32 = (sys.platform == "win32")

    def __enter__(self):
        try:
            sys.stdout.flush()
            sys.stderr.flush()

            # Win32 OS Kernel Handle Redirection
            if self._win32:
                try:
                    kernel32 = ctypes.windll.kernel32
                    self._h_out_orig = kernel32.GetStdHandle(-11)
                    self._h_err_orig = kernel32.GetStdHandle(-12)
                    self._h_null = kernel32.CreateFileW("NUL", 0xc0000000, 3, None, 3, 0, None)
                    kernel32.SetStdHandle(-11, self._h_null)
                    kernel32.SetStdHandle(-12, self._h_null)
                except Exception:
                    pass

            # C-Runtime (CRT) File Descriptor Redirection
            self._null_fd = os.open(os.devnull, os.O_RDWR)
            self._stdout_save = os.dup(1)
            self._stderr_save = os.dup(2)
            os.dup2(self._null_fd, 1)
            os.dup2(self._null_fd, 2)
        except Exception:
            self._enabled = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._enabled:
            try:
                os.dup2(self._stdout_save, 1)
                os.dup2(self._stderr_save, 2)
                os.close(self._stdout_save)
                os.close(self._stderr_save)
                os.close(self._null_fd)

                if self._win32:
                    try:
                        kernel32 = ctypes.windll.kernel32
                        kernel32.SetStdHandle(-11, self._h_out_orig)
                        kernel32.SetStdHandle(-12, self._h_err_orig)
                        kernel32.CloseHandle(self._h_null)
                    except Exception:
                        pass
            except Exception:
                pass


def normalized_iris_center(iris_pts):
    """Calculate normalized (x, y) relative position of iris center within eye box."""
    if len(iris_pts) == 0:
        return 0.5, 0.5
    cx, cy = iris_pts.mean(axis=0)
    x0, x1 = int(iris_pts[:, 0].min()), int(iris_pts[:, 0].max())
    y0, y1 = int(iris_pts[:, 1].min()), int(iris_pts[:, 1].max())
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    return (cx - x0) / w, (cy - y0) / h


def calculate_ear(lm_px, mouth_indices=(13, 14)):
    """Calculate normalized mouth aspect ratio / EAR measure."""
    try:
        top = lm_px[mouth_indices[0]]
        bot = lm_px[mouth_indices[1]]
        nose = lm_px[1]
        chin = lm_px[152]
        face_h = np.linalg.norm(nose - chin)
        return float(np.linalg.norm(top - bot) / max(1.0, face_h))
    except Exception:
        return 0.0
