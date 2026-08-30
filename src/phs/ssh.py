import subprocess
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SSHTarget:
    host: str
    user: str
    port: int = 22


class SSHRunner:
    def run_script(
            self,
            target: SSHTarget,
            script: str,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            "ssh",
            "-p",
            str(target.port),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            f"{target.user}@{target.host}",
            "bash",
            "-s",
        ]

        try:
            return subprocess.run(
                command,
                input=script,
                text=True,
                check=True,
                # capture_output=True,
            )
        except subprocess.CalledProcessError as error:
            print(f"Command failed with exit code {error.returncode}")
            if error.stdout:
                print("stdout:")
                print(error.stdout)
            if error.stderr:
                print("stderr:")
                print(error.stderr)

            raise
