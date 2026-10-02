# Screen Capture

A small Windows utility for capturing predefined screen regions.

## Features

- Configure multiple screen regions.
- Edit, delete, list, and visualise regions.
- Copy a selected region directly to the clipboard.
- Save a selected region as a JPG.
- Change the active region and capture mode without restarting.
- Toggle region visualisation on and off while running.
- Visualisation follows the active region when it changes.
- Visualisation is hidden during capture so it is not included in screenshots.
- Supports single and multiple monitors.

## Setup

Create and activate a virtual environment:

    python -m venv .venv
    .venv\Scripts\activate

Install dependencies:

    python -m pip install -r requirements.txt

## Configure

Run:

    python configure.py

Use the configuration menu to add and manage regions.

## Capture

Run:

    python capture.py

At startup, choose:

1. Region
2. Capture mode
3. Whether to visualise the selected region

While running, you can:

1. Capture
2. Change region
3. Change capture mode
4. Toggle visualisation
5. Quit

JPG files are saved to the `captures/` directory.

## Notes

`config.json` contains machine-specific screen coordinates and is intentionally not tracked by Git.

Use `config.example.json` as a starting point for a new machine.
