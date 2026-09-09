import subprocess
from dataclasses import dataclass


def host_key_options(*, loose_ssh: bool, accept_new: bool = False) -> list[str]:
    if loose_ssh:
        return [
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
        ]
    return ["-o", "StrictHostKeyChecking=accept-new"] if accept_new else []


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
            *host_key_options(loose_ssh=True),
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
