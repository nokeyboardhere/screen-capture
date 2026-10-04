import json
import multiprocessing
import tkinter as tk
from pathlib import Path

from pynput import keyboard


CONFIG_FILE = "config.json"
OUTPUT_DIRECTORY = Path("captures")
OVERLAY_COLOR = "#ff3b30"


def load_config():
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)


def take_screenshot():
    import mss

    with mss.MSS() as sct:
        virtual_screen = sct.monitors[0]
        screenshot = sct.grab(virtual_screen)

    return screenshot, virtual_screen


def to_pil_image(image):
    from PIL import Image

    return Image.frombytes(
        "RGB",
        image.size,
        image.bgra,
        "raw",
        "BGRX",
    )


def crop_region(image, virtual_screen, region):
    top_left = region["top_left"]
    bottom_right = region["bottom_right"]

    x1 = top_left[0] - virtual_screen["left"]
    y1 = top_left[1] - virtual_screen["top"]
    x2 = bottom_right[0] - virtual_screen["left"]
    y2 = bottom_right[1] - virtual_screen["top"]

    return to_pil_image(image).crop((x1, y1, x2, y2))


def copy_to_clipboard(image):
    import pyperclipimg

    pyperclipimg.copy(image)
    print("Screenshot copied to clipboard.")


def save_as_jpg(image):
    OUTPUT_DIRECTORY.mkdir(exist_ok=True)

    filename = input("Enter filename (without .jpg): ").strip()

    if not filename:
        print("Filename cannot be empty.")
        return

    path = OUTPUT_DIRECTORY / f"{filename}.jpg"

    image.save(path, "JPEG")
    print(f"Screenshot saved to {path}")


def choose_region(config):
    regions = config["regions"]

    if not regions:
        print("No regions configured.")
        return None

    print("\nAvailable regions:")

    for number, region in enumerate(regions, start=1):
        print(f"{number}. {region['name']}")

    choice = input("\nChoose a region: ").strip()

    try:
        return regions[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice.")
        return None


def choose_action():
    print("\nAvailable actions:")
    print("1. Copy to clipboard")
    print("2. Save as JPG")

    choice = input("\nChoose an action: ").strip()

    if choice == "1":
        return "clipboard"

    if choice == "2":
        return "jpg"

    print("Invalid choice.")
    return None


def choose_visualisation():
    choice = input("\nVisualise region? [y/N]: ").strip().lower()
    return choice in ("y", "yes")


def get_overlay_geometry(region):
    top_left = region["top_left"]
    bottom_right = region["bottom_right"]

    x = top_left[0]
    y = top_left[1]
    width = bottom_right[0] - top_left[0]
    height = bottom_right[1] - top_left[1]

    return x, y, width, height


def run_overlay(connection):
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.wm_attributes("-transparentcolor", "black")

    canvas = tk.Canvas(
        root,
        bg="black",
        highlightthickness=0,
    )
    canvas.pack(fill="both", expand=True)

    def update_overlay(region):
        x, y, width, height = get_overlay_geometry(region)

        root.geometry(f"{width}x{height}+{x}+{y}")

        canvas.delete("border")
        canvas.create_rectangle(
            3,
            3,
            width - 3,
            height - 3,
            outline=OVERLAY_COLOR,
            width=5,
            tags="border",
        )

    def check_commands():
        while connection.poll():
            command = connection.recv()

            if command[0] == "update":
                update_overlay(command[1])

            elif command[0] == "hide":
                root.withdraw()
                connection.send(("hidden",))

            if command[0] == "show":
                root.deiconify()
                connection.send(("shown",))

            elif command[0] == "close":
                root.destroy()
                return

        root.after(50, check_commands)

    root.after(0, check_commands)
    root.mainloop()


class OverlayController:
    def __init__(self):
        self.process = None
        self.connection = None

    def start(self, region):
        parent_connection, child_connection = multiprocessing.Pipe()

        self.connection = parent_connection
        self.process = multiprocessing.Process(
            target=run_overlay,
            args=(child_connection,),
            daemon=True,
        )

        self.process.start()
        self.update(region)

    def update(self, region):
        if self.connection is not None:
            self.connection.send(("update", region))

    def hide(self):
        if self.connection is None:
            return

        self.connection.send(("hide",))

        while self.connection.recv() != ("hidden",):
            pass


    def show(self, region):
        if self.connection is None:
            return

        self.connection.send(("update", region))
        self.connection.send(("show",))

        while self.connection.recv() != ("shown",):
            pass

    def stop(self):
        if self.connection is not None:
            try:
                self.connection.send(("close",))
            except (BrokenPipeError, EOFError):
                pass

        if self.process is not None:
            self.process.join(timeout=1)

            if self.process.is_alive():
                self.process.terminate()

        self.connection = None
        self.process = None


def capture(region, action, overlay=None, visualise=False):
    if visualise:
        overlay.hide()

    try:
        image, virtual_screen = take_screenshot()
        image = crop_region(image, virtual_screen, region)

        if action == "clipboard":
            copy_to_clipboard(image)
        elif action == "jpg":
            save_as_jpg(image)
    finally:
        if visualise:
            overlay.show(region)


def fine_tune_region(region, overlay):
    offset_x = 0
    offset_y = 0
    original_region = region.copy()

    def move(dx, dy):
        nonlocal offset_x, offset_y

        offset_x += dx
        offset_y += dy

        region["top_left"][0] += dx
        region["top_left"][1] += dy
        region["bottom_right"][0] += dx
        region["bottom_right"][1] += dy

        overlay.update(region)

        print(
            f"\rOffset: X {offset_x:+d}, Y {offset_y:+d}",
            end="",
            flush=True,
        )

    def reset():
        nonlocal offset_x, offset_y

        region["top_left"] = original_region["top_left"].copy()
        region["bottom_right"] = original_region["bottom_right"].copy()

        offset_x = 0
        offset_y = 0

        overlay.update(region)

        print("\rOffset: X +0, Y +0", end="", flush=True)

    print("\n--- Fine-tune region ---")
    print("Arrow keys: move 1 pixel")
    print("Shift + arrow: move 10 pixels")
    print("R: reset")
    print("Enter: accept")
    print("Esc: cancel")

    current_keys = set()
    finished = False
    cancelled = False

    def on_press(key):
        nonlocal finished, cancelled

        current_keys.add(key)

        if key == keyboard.Key.enter:
            finished = True
            return False

        if key == keyboard.Key.esc:
            cancelled = True
            return False

        step = 10 if (
            keyboard.Key.shift in current_keys
            or keyboard.Key.shift_l in current_keys
            or keyboard.Key.shift_r in current_keys
        ) else 1

        if key == keyboard.Key.up:
            move(0, -step)
        elif key == keyboard.Key.down:
            move(0, step)
        elif key == keyboard.Key.left:
            move(-step, 0)
        elif key == keyboard.Key.right:
            move(step, 0)
        elif key == keyboard.KeyCode.from_char("r"):
            reset()

    def on_release(key):
        current_keys.discard(key)

    with keyboard.Listener(
        on_press=on_press,
        on_release=on_release,
    ) as listener:
        listener.join()

    if cancelled:
        region["top_left"] = original_region["top_left"]
        region["bottom_right"] = original_region["bottom_right"]
        overlay.update(region)
        print("\nCancelled.")
    else:
        print("\nAdjustment accepted.")

    return region


def main():
    config = load_config()
    overlay = OverlayController()

    print("\n--- Screen Capture Setup ---")

    region = choose_region(config)

    if region is None:
        return

    action = choose_action()

    if action is None:
        return

    visualise = choose_visualisation()

    if visualise:
        overlay.start(region)

    try:
        while True:
            print("\n--- Screen Capture ---")
            print(f"Region: {region['name']}")
            print(
                "Action: "
                + (
                    "Copy to clipboard"
                    if action == "clipboard"
                    else "Save as JPG"
                )
            )
            print(f"Visualisation: {'On' if visualise else 'Off'}")
            print()
            print("1. Capture")
            print("2. Change region")
            print("3. Change action")
            print("4. Toggle visualisation")
            print("5. Fine-tune region")
            print("6. Quit")

            choice = input("\nChoose an option: ").strip()

            if choice == "1":
                capture(region, action, overlay, visualise)

            elif choice == "2":
                new_region = choose_region(config)

                if new_region is not None:
                    region = new_region

                    if visualise:
                        overlay.update(region)

            elif choice == "3":
                new_action = choose_action()

                if new_action is not None:
                    action = new_action

            elif choice == "4":
                visualise = not visualise

                if visualise:
                    overlay.start(region)
                else:
                    overlay.stop()

            elif choice == "5":
                if visualise:
                    fine_tune_region(region, overlay)
                else:
                    print("Turn on visualisation first.")
                    
            elif choice == "6":
                print("Goodbye.")
                break

            else:
                print("Invalid choice.")

    finally:
        overlay.stop()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
