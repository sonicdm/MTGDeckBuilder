import subprocess
import sys
import time
import socket
import os

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def test_app_launch():
    """Test that the Gradio app launches and binds to port 42069."""
    app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
    app_path = os.path.abspath(app_path)
    port = 42069

    # Start the app in a subprocess
    proc = subprocess.Popen([sys.executable, app_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        # Wait a few seconds for the server to start
        for _ in range(20):
            if is_port_open(port):
                break
            time.sleep(0.5)
        else:
            raise AssertionError(f"App did not start on port {port} within timeout.")

        # Optionally, check for Gradio output in stdout
        # stdout, stderr = proc.communicate(timeout=2)
        # assert b"Running on local URL" in stdout or b"Local URL" in stdout

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
