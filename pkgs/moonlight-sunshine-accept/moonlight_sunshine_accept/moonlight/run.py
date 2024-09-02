import subprocess
import sys
import threading


class MoonlightPairing:
    def __init__(self) -> None:
        self.process: subprocess.Popen | None = None
        self.output = ""
        self.found = threading.Event()

    def init_pairing(self, host: str, pin: str) -> bool:
        # host = f"[{host}]"
        args = ["moonlight", "pair", host, "--pin", pin]
        print("Trying to pair")
        try:
            print(f"Running command: {args}")
            self.process = subprocess.Popen(args, stdout=subprocess.PIPE)
            print("Pairing initiated")
            thread = threading.Thread(
                target=self.stream_output,
                args=('Latest supported GFE server: "99.99.99.99"',),
            )
            thread.start()
            print("Thread started")
            return True
        except Exception as e:
            print(
                "Error occurred while starting the process: ", str(e), file=sys.stderr
            )
            return False

    def check(self, host: str) -> bool:
        try:
            result = subprocess.run(
                ["moonlight", "list", "localhost", host], check=True
            )
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False

    def terminate(self) -> None:
        if self.process:
            self.process.terminate()
            self.process.wait()

    def stream_output(self, target_string: str) -> None:
        assert self.process is not None
        assert self.process.stdout is not None
        for line in iter(self.process.stdout.readline, b""):
            line = line.decode()
            self.output += line
            if target_string in line:
                self.found.set()
                break

    def wait_until_started(self, timeout: int = 10) -> None:
        if self.found.wait(timeout):
            print("Started up.")
        else:
            print("Starting up took took too long. Terminated the process.")
