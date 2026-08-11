#requires -Version 5.1
<#
.SYNOPSIS
Creates and validates shortcuts for the emulator apps installed under T:\Emulation.

.DESCRIPTION
The script manages the current user's Desktop and Start Menu shortcuts and
repairs existing taskbar shortcut files in place. It backs up each existing link
before changing it, then verifies the saved target, working directory, and icon.
For apps without an existing taskbar entry, it uses a Windows Shell pin verb only
when the Shell exposes one.

Important invariants:
  - Emulator targets come from T:\Emulation\Emulators, never C:\PCSX2.
  - All launchers are resolved and validated before any shortcut is changed.
  - Existing taskbar entries are repaired in place after backup; new pins are
    created only through an exposed Shell verb, never by copying files into the
    pinned-shortcut folder.
  - Existing user shortcut files are copied to LocalAppData before repair.

.NOTES
This script does not launch emulators or games and does not access save files.
#>
[CmdletBinding()]
param(
    [switch]$SkipTaskbarPinning
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$emulationRoot = 'T:\Emulation'
$emulatorRoot = Join-Path $emulationRoot 'Emulators'
if (-not (Test-Path -LiteralPath $emulatorRoot -PathType Container)) {
    throw "Emulator directory is unavailable: $emulatorRoot"
}

# Keep this manifest limited to user-facing emulator launchers. Tools, updaters,
# SDL frontends, uninstallers, and other support executables are not shortcuts.
$launcherSpecs = @(
    [pscustomobject]@{ Name = 'Dolphin'; RelativePath = 'Dolphin\Dolphin.exe' },
    [pscustomobject]@{ Name = 'PrimeHack'; RelativePath = 'PrimeHack\Dolphin.exe' },
    [pscustomobject]@{ Name = 'PCSX2'; RelativePath = 'PCSX2\pcsx2-qt.exe' },
    [pscustomobject]@{ Name = 'DuckStation'; RelativePath = 'DuckStation\duckstation-qt-x64-ReleaseLTCG.exe' },
    [pscustomobject]@{ Name = 'Mesen'; RelativePath = 'Mesen\Mesen.exe' },
    [pscustomobject]@{ Name = 'mGBA Stable'; RelativePath = 'mGBA\mGBA-0.10.5-win64\mGBA.exe' }
)

$devRoot = Join-Path $emulatorRoot 'mGBA-dev'
if (-not (Test-Path -LiteralPath $devRoot -PathType Container)) {
    throw "mGBA development build directory is unavailable: $devRoot"
}
$devCandidates = @(
    Get-ChildItem -LiteralPath $devRoot -Directory -Filter 'mGBA-build-*' |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'mGBA.exe') -PathType Leaf }
)
if ($devCandidates.Count -ne 1) {
    throw "Expected one mGBA development build with mGBA.exe under $devRoot; found $($devCandidates.Count)."
}
$launcherSpecs += [pscustomobject]@{
    Name = 'mGBA Development'
    RelativePath = Join-Path 'mGBA-dev' (Join-Path (Split-Path -Leaf $devCandidates[0].FullName) 'mGBA.exe')
}

# Validate the full manifest first so a missing emulator cannot leave a partial
# set of shortcut changes behind.
$launchers = foreach ($spec in $launcherSpecs) {
    $candidate = Join-Path $emulatorRoot $spec.RelativePath
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        throw "Expected emulator launcher is missing: $candidate"
    }

    $file = Get-Item -LiteralPath $candidate
    if ($file.Length -le 0) {
        throw "Emulator launcher is empty: $candidate"
    }
    $workingDirectory = Split-Path -Parent $file.FullName
    if (-not (Test-Path -LiteralPath $workingDirectory -PathType Container)) {
        throw "Emulator working directory is missing: $workingDirectory"
    }

    [pscustomobject]@{
        Name = $spec.Name
        TargetPath = $file.FullName
        WorkingDirectory = $workingDirectory
        IconLocation = "$($file.FullName),0"
        Description = if ($file.VersionInfo.FileVersion) {
            "$($spec.Name) ($($file.VersionInfo.FileVersion))"
        } else {
            $spec.Name
        }
    }
}

$desktopDirectory = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::DesktopDirectory)
$programsDirectory = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Programs)
if (-not $desktopDirectory -or -not (Test-Path -LiteralPath $desktopDirectory -PathType Container)) {
    throw "The current user's Desktop directory is unavailable: $desktopDirectory"
}
if (-not $programsDirectory -or -not (Test-Path -LiteralPath $programsDirectory -PathType Container)) {
    throw "The current user's Start Menu Programs directory is unavailable: $programsDirectory"
}

$backupDirectory = Join-Path $env:LOCALAPPDATA 'EmulatorShortcutBackups'
$wsh = New-Object -ComObject WScript.Shell
$shell = New-Object -ComObject Shell.Application

function Get-NormalizedPath {
    param([AllowNull()][string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return '' }
    try { return [System.IO.Path]::GetFullPath($Path).TrimEnd('\') } catch { return $Path.Trim() }
}

function Backup-ShortcutFile {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Cannot preserve a shortcut that is missing: $Path"
    }
    if (-not (Test-Path -LiteralPath $backupDirectory -PathType Container)) {
        New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
    }

    $stamp = Get-Date -Format 'yyyyMMdd-HHmmssfff'
    $backupName = "$(Split-Path -Leaf $Path).backup-$stamp"
    $backupPath = Join-Path $backupDirectory $backupName
    Copy-Item -LiteralPath $Path -Destination $backupPath

    $sourceHash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
    $backupHash = (Get-FileHash -LiteralPath $backupPath -Algorithm SHA256).Hash
    if ($sourceHash -ne $backupHash) {
        throw "Shortcut backup verification failed: $backupPath"
    }
    return $backupPath
}

function Get-ShortcutShellItem {
    param([Parameter(Mandatory)][string]$Path)

    $folder = $shell.Namespace((Split-Path -Parent $Path))
    if (-not $folder) { return $null }
    return $folder.ParseName((Split-Path -Leaf $Path))
}

function Get-ShellVerb {
    param(
        [Parameter(Mandatory)]$Item,
        [Parameter(Mandatory)][string]$Pattern
    )

    foreach ($verb in @($Item.Verbs())) {
        $label = ($verb.Name -replace '&', '').Trim()
        if ($label -match $Pattern) { return $verb }
    }
    return $null
}

function Get-TaskbarLinks {
    param([Parameter(Mandatory)][string]$Directory)

    if (-not (Test-Path -LiteralPath $Directory -PathType Container)) { return @() }
    foreach ($linkFile in Get-ChildItem -LiteralPath $Directory -Filter '*.lnk' -File) {
        $link = $wsh.CreateShortcut($linkFile.FullName)
        $targetExists = if ([string]::IsNullOrWhiteSpace($link.TargetPath)) {
            $false
        } else {
            Test-Path -LiteralPath $link.TargetPath -PathType Leaf
        }
        [pscustomobject]@{
            Name = $linkFile.Name
            LinkPath = $linkFile.FullName
            TargetPath = $link.TargetPath
            TargetExists = $targetExists
        }
    }
}

function Get-KnownTaskbarLinks {
    param(
        [Parameter(Mandatory)][string]$Directory,
        [Parameter(Mandatory)]$Launchers
    )

    foreach ($link in Get-TaskbarLinks -Directory $Directory) {
        $isKnownEmulator = $false
        foreach ($launcher in $Launchers) {
            if ($link.Name -ieq "$($launcher.Name).lnk" -or
                (Get-NormalizedPath $link.TargetPath) -ieq (Get-NormalizedPath $launcher.TargetPath)) {
                $isKnownEmulator = $true
                break
            }
        }
        if ($isKnownEmulator) { $link }
    }
}

function Set-UserShortcut {
    param(
        [Parameter(Mandatory)]$Launcher,
        [Parameter(Mandatory)][string]$Directory,
        [Parameter(Mandatory)][string]$Scope
    )

    $shortcutPath = Join-Path $Directory ("$($Launcher.Name).lnk")
    $existedBefore = Test-Path -LiteralPath $shortcutPath -PathType Leaf
    $needsWrite = $true
    if ($existedBefore) {
        $current = $wsh.CreateShortcut($shortcutPath)
        $needsWrite = (
            (Get-NormalizedPath $current.TargetPath) -ine (Get-NormalizedPath $Launcher.TargetPath) -or
            (Get-NormalizedPath $current.WorkingDirectory) -ine (Get-NormalizedPath $Launcher.WorkingDirectory) -or
            $current.Arguments -ne '' -or
            $current.IconLocation -ine $Launcher.IconLocation -or
            $current.Description -ne $Launcher.Description
        )
        if (-not $needsWrite) {
            return [pscustomobject]@{
                Action = 'Unchanged'
                Scope = $Scope
                Shortcut = $shortcutPath
                Target = $Launcher.TargetPath
            }
        }

        $backupPath = Backup-ShortcutFile -Path $shortcutPath
        Write-Output ([pscustomobject]@{
            Action = 'Backed up before repair'
            Scope = $Scope
            Shortcut = $shortcutPath
            Backup = $backupPath
        })
    }

    $shortcut = $wsh.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $Launcher.TargetPath
    $shortcut.WorkingDirectory = $Launcher.WorkingDirectory
    $shortcut.Arguments = ''
    $shortcut.IconLocation = $Launcher.IconLocation
    $shortcut.Description = $Launcher.Description
    $shortcut.Save()

    $saved = $wsh.CreateShortcut($shortcutPath)
    if ((Get-NormalizedPath $saved.TargetPath) -ine (Get-NormalizedPath $Launcher.TargetPath) -or
        (Get-NormalizedPath $saved.WorkingDirectory) -ine (Get-NormalizedPath $Launcher.WorkingDirectory) -or
        $saved.Arguments -ne '' -or $saved.IconLocation -ine $Launcher.IconLocation -or
        $saved.Description -ne $Launcher.Description) {
        throw "Shortcut verification failed: $shortcutPath"
    }

    return [pscustomobject]@{
        Action = if ($existedBefore) { 'Created or repaired' } else { 'Created' }
        Scope = $Scope
        Shortcut = $shortcutPath
        Target = $Launcher.TargetPath
    }
}

$shortcutResults = foreach ($launcher in $launchers) {
    Set-UserShortcut -Launcher $launcher -Directory $desktopDirectory -Scope 'Desktop'
    Set-UserShortcut -Launcher $launcher -Directory $programsDirectory -Scope 'Start Menu'
}

$taskbarDirectory = Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar'
$pinResults = [System.Collections.Generic.List[object]]::new()
$taskbarLinks = @(Get-KnownTaskbarLinks -Directory $taskbarDirectory -Launchers $launchers)

# Preserve the original pin targets in the run log before any repair. This report
# is limited to emulator links and omits unrelated pinned applications.
foreach ($launcher in $launchers) {
    $matchingPins = @($taskbarLinks | Where-Object {
        $_.Name -ieq "$($launcher.Name).lnk" -or
        (Get-NormalizedPath $_.TargetPath) -ieq (Get-NormalizedPath $launcher.TargetPath)
    })
    foreach ($pin in $matchingPins) {
        $pinResults.Add([pscustomobject]@{
            Action = 'Existing taskbar target'
            Emulator = $launcher.Name
            Shortcut = $pin.LinkPath
            Target = $pin.TargetPath
            TargetExists = $pin.TargetExists
        })
    }
}

# Repair existing pins in place after preserving the original .lnk. This keeps
# the Windows-owned taskbar pin entry instead of simulating a pin by copying a
# file into the taskbar folder.
foreach ($launcher in $launchers) {
    $taskbarShortcutPath = Join-Path $taskbarDirectory ("$($launcher.Name).lnk")
    if (Test-Path -LiteralPath $taskbarShortcutPath -PathType Leaf) {
        $shortcutResults = @($shortcutResults) + @(
            Set-UserShortcut -Launcher $launcher -Directory $taskbarDirectory -Scope 'Taskbar'
        )
    }
}

$taskbarLinks = @(Get-KnownTaskbarLinks -Directory $taskbarDirectory -Launchers $launchers)

if (-not $SkipTaskbarPinning) {
    foreach ($launcher in $launchers) {
        $alreadyPinned = @($taskbarLinks | Where-Object {
            (Get-NormalizedPath $_.TargetPath) -ieq (Get-NormalizedPath $launcher.TargetPath)
        }).Count -gt 0
        if ($alreadyPinned) {
            $pinResults.Add([pscustomobject]@{
                Action = 'Already pinned to canonical target'
                Emulator = $launcher.Name
                Target = $launcher.TargetPath
            })
            continue
        }

        $startMenuLink = Join-Path $programsDirectory ("$($launcher.Name).lnk")
        $item = Get-ShortcutShellItem -Path $startMenuLink
        $pinVerb = if ($item) { Get-ShellVerb -Item $item -Pattern '^Pin to taskbar$' } else { $null }
        if (-not $pinVerb) {
            $pinResults.Add([pscustomobject]@{
                Action = 'Not pinned; Pin to taskbar Shell verb is not exposed'
                Emulator = $launcher.Name
                Target = $launcher.TargetPath
            })
            continue
        }

        try {
            $pinVerb.DoIt()
            Start-Sleep -Milliseconds 750
            $taskbarLinks = @(Get-KnownTaskbarLinks -Directory $taskbarDirectory -Launchers $launchers)
            $confirmed = @($taskbarLinks | Where-Object {
                (Get-NormalizedPath $_.TargetPath) -ieq (Get-NormalizedPath $launcher.TargetPath)
            }).Count -gt 0
            $pinResults.Add([pscustomobject]@{
                Action = if ($confirmed) { 'Pinned and verified' } else { 'Pin verb ran; canonical taskbar target not observed' }
                Emulator = $launcher.Name
                Target = $launcher.TargetPath
            })
        } catch {
            $pinResults.Add([pscustomobject]@{
                Action = 'Pin verb failed'
                Emulator = $launcher.Name
                Target = $launcher.TargetPath
                Error = $_.Exception.Message
            })
        }
    }
}

$taskbarLinks = @(Get-KnownTaskbarLinks -Directory $taskbarDirectory -Launchers $launchers)
foreach ($launcher in $launchers) {
    $matchingPins = @($taskbarLinks | Where-Object {
        $_.Name -ieq "$($launcher.Name).lnk" -or
        (Get-NormalizedPath $_.TargetPath) -ieq (Get-NormalizedPath $launcher.TargetPath)
    })
    $canonicalPin = @($matchingPins | Where-Object {
        (Get-NormalizedPath $_.TargetPath) -ieq (Get-NormalizedPath $launcher.TargetPath)
    }) | Select-Object -First 1
    if ($canonicalPin) {
        $pinResults.Add([pscustomobject]@{
            Action = 'Final pin state: pinned to canonical target'
            Emulator = $launcher.Name
            Shortcut = $canonicalPin.LinkPath
            Target = $canonicalPin.TargetPath
            TargetExists = $canonicalPin.TargetExists
        })
    } elseif ($matchingPins.Count -gt 0) {
        foreach ($pin in $matchingPins) {
            $pinResults.Add([pscustomobject]@{
                Action = 'Final pin state: pinned to a different target'
                Emulator = $launcher.Name
                Shortcut = $pin.LinkPath
                Target = $pin.TargetPath
                TargetExists = $pin.TargetExists
            })
        }
    } else {
        $pinResults.Add([pscustomobject]@{
            Action = 'Final pin state: not pinned'
            Emulator = $launcher.Name
            Target = $launcher.TargetPath
            TargetExists = Test-Path -LiteralPath $launcher.TargetPath -PathType Leaf
        })
    }
}

$results = @($shortcutResults) + @($pinResults)
$results | Format-List
