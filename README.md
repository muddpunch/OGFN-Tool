# OGFN Tool

Simple PyQt6 utility for basic Fortnite / Epic Games repair tasks.

## Features

- Kill Fortnite and Epic Games launcher processes
- Clear local Fortnite / Epic cache, logs, crash data, and temp files
- Delete EasyAntiCheat and BattlEye cache folders
- Reset Fortnite config files
- Run all repair steps with one Full Clean action
- Safety checks that restrict deletion to known Fortnite / Epic / anti-cheat paths

## Requirements

- Windows
- Python 3.10+
- PyQt6

## Install

```powershell
pip install PyQt6
```

## Run

```powershell
py ogfntool.py
```

For best results, run it as administrator. The tool can restart itself with admin privileges from the startup prompt.

## Notes

- Game installation files are not deleted.
- Fortnite config reset will remove graphics and keybind settings.
- Some operations can fail without administrator privileges.
- Deleted cache/config folders are recreated automatically by Fortnite, Epic Games Launcher, or anti-cheat services.

## Project Structure

```text
ogfntool.py  # application source
README.md   # project documentation
```
