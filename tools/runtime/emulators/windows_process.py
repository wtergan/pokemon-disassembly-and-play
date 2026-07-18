"""Own a Windows emulator process launched from WSL.

Terminating the WSL interop launcher does not reliably terminate its Windows
GUI child. Capture the actual Windows PID and creation time and use both when
closing, so cleanup cannot target an unrelated process after PID reuse.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import subprocess


_SPEC_VARIABLE = "POKEMON_RUNTIME_LAUNCH_SPEC"
_START = r'''
$ErrorActionPreference = 'Stop'
$spec = $env:POKEMON_RUNTIME_LAUNCH_SPEC | ConvertFrom-Json
$quoted = @($spec.arguments | ForEach-Object { '"' + $_.Replace('"', '\"') + '"' })
$launched = Start-Process -FilePath $spec.executable -ArgumentList $quoted -WorkingDirectory $spec.cwd -PassThru
@{ processId = $launched.Id; created = $launched.StartTime.ToUniversalTime().Ticks.ToString() } | ConvertTo-Json -Compress
'''
_STOP = r'''
$ErrorActionPreference = 'Stop'
$spec = $env:POKEMON_RUNTIME_LAUNCH_SPEC | ConvertFrom-Json
$owned = Get-Process -Id $spec.processId -ErrorAction SilentlyContinue
if ($owned -and $owned.StartTime.ToUniversalTime().Ticks.ToString() -eq $spec.created) {
    Stop-Process -InputObject $owned
    $owned.WaitForExit(5000) | Out-Null
}
'''


def _run(script: str, spec: dict, env: dict[str, str]) -> str:
    launch_env = dict(env)
    launch_env[_SPEC_VARIABLE] = json.dumps(spec)
    exports = launch_env.get("WSLENV", "").split(":")
    if not any(item.split("/")[0] == _SPEC_VARIABLE for item in exports):
        exports.append(f"{_SPEC_VARIABLE}/w")
    launch_env["WSLENV"] = ":".join(item for item in exports if item)
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        env=launch_env, check=True, capture_output=True, text=True, timeout=20,
    )
    return result.stdout.strip()


@dataclass
class WindowsProcess:
    """Actual Windows PID with a creation-time guard for deterministic cleanup."""

    process_id: int
    created: str
    env: dict[str, str]

    @classmethod
    def start(cls, executable: str, arguments: list[str], cwd: str, env: dict[str, str]) -> WindowsProcess:
        result = json.loads(_run(_START, {"executable": executable, "arguments": arguments, "cwd": cwd}, env))
        return cls(process_id=int(result["processId"]), created=str(result["created"]), env=env)

    def close(self) -> None:
        """Stop only the process with the captured PID and creation time."""

        _run(_STOP, {"processId": self.process_id, "created": self.created}, self.env)
