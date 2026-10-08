import json
import tkinter as tk

import mouse
from pynput import keyboard


CONFIG_FILE = "config.json"
OVERLAY_COLOR = "#ff3b30"


def load_config():
    try:
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {"regions": []}


def save_config(config):
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)


def get_region_coordinates(region_number):
    input(
        f"Place the mouse at the top-left corner of region "
        f"{region_number} and press Enter: "
    )
    top_left = mouse.get_position()

    input(
        f"Place the mouse at the bottom-right corner of region "
        f"{region_number} and press Enter: "
    )
    bottom_right = mouse.get_position()

    if bottom_right[0] <= top_left[0] or bottom_right[1] <= top_left[1]:
        print("Invalid region: bottom-right must be below and to the right.")
        return None

    return {
        "top_left": list(top_left),
        "bottom_right": list(bottom_right),
    }


def choose_region(config):
    regions = config["regions"]

    if not regions:
        print("No regions configured.")
        return None

    for number, region in enumerate(regions, start=1):
        print(f"{number}. {region['name']}")

    try:
        choice = int(input("Choose a region: "))
        return regions[choice - 1]
    except (ValueError, IndexError):
        print("Invalid choice.")
        return None


def add_region(config):
    name = input("Region name: ").strip()

    if not name:
        print("Region name cannot be empty.")
        return

    region_number = len(config["regions"]) + 1
    coordinates = get_region_coordinates(region_number)

    if coordinates is None:
        return

    coordinates["name"] = name
    config["regions"].append(coordinates)
    save_config(config)

    print(f"Region '{name}' added.")


def edit_region(config):
    region = choose_region(config)

    if region is None:
        return

    new_name = input(
        f"Region name [{region['name']}]: "
    ).strip()

    if new_name:
        region["name"] = new_name

    coordinates = get_region_coordinates(region["name"])

    if coordinates is None:
        return

    region["top_left"] = coordinates["top_left"]
    region["bottom_right"] = coordinates["bottom_right"]

    save_config(config)

    print(f"Region '{region['name']}' updated.")


def delete_region(config):
    region = choose_region(config)

    if region is None:
        return

    confirmation = input(
        f"Delete region '{region['name']}'? [y/N]: "
    ).strip().lower()

    if confirmation == "y":
        config["regions"].remove(region)
        save_config(config)
        print("Region deleted.")
    else:
        print("Nothing deleted.")


def visualise_region(config):
    region = choose_region(config)

    if region is None:
        return

    top_left = region["top_left"]
    bottom_right = region["bottom_right"]

    x = top_left[0]
    y = top_left[1]
    width = bottom_right[0] - top_left[0]
    height = bottom_right[1] - top_left[1]

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

    canvas.create_rectangle(
        3,
        3,
        width - 3,
        height - 3,
        outline=OVERLAY_COLOR,
        width=5,
    )

    root.geometry(f"{width}x{height}+{x}+{y}")

    def close_overlay(event=None):
        root.destroy()

    root.bind("<Return>", close_overlay)
    root.bind("<Escape>", close_overlay)

    root.after(100, root.focus_force)
    root.after(500, root.focus_force)
    root.after(1000, root.focus_force)
    root.mainloop()


def adjust_region(config):
    region = choose_region(config)

    if region is None:
        return

    original_top_left = region["top_left"].copy()
    original_bottom_right = region["bottom_right"].copy()
    cancelled = False

    print("\n--- Adjust region ---")
    print("Arrow keys: move region 1 pixel")
    print("W / S: increase / decrease height")
    print("A / D: decrease / increase width")
    print("Enter: save")
    print("Esc: cancel")

    def show_status():
        x = region["top_left"][0]
        y = region["top_left"][1]

        width = region["bottom_right"][0] - x
        height = region["bottom_right"][1] - y

        print(
            f"\rPosition: X {x}, Y {y} | "
            f"Size: {width} x {height}",
            end="",
            flush=True,
        )

    def move(dx, dy):
        region["top_left"][0] += dx
        region["top_left"][1] += dy
        region["bottom_right"][0] += dx
        region["bottom_right"][1] += dy

        show_status()

    def resize(dw, dh):
        new_width = (
            region["bottom_right"][0]
            - region["top_left"][0]
            + dw
        )

        new_height = (
            region["bottom_right"][1]
            - region["top_left"][1]
            + dh
        )

        if new_width < 1 or new_height < 1:
            return

        region["bottom_right"][0] += dw
        region["bottom_right"][1] += dh

        show_status()

    def on_press(key):
        nonlocal cancelled

        if key == keyboard.Key.enter:
            return False

        if key == keyboard.Key.esc:
            cancelled = True
            return False

        if key == keyboard.Key.up:
            move(0, -1)

        elif key == keyboard.Key.down:
            move(0, 1)

        elif key == keyboard.Key.left:
            move(-1, 0)

        elif key == keyboard.Key.right:
            move(1, 0)

        elif key == keyboard.KeyCode.from_char("w"):
            resize(0, 1)

        elif key == keyboard.KeyCode.from_char("s"):
            resize(0, -1)

        elif key == keyboard.KeyCode.from_char("a"):
            resize(-1, 0)

        elif key == keyboard.KeyCode.from_char("d"):
            resize(1, 0)

    print()
    show_status()

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

    if cancelled:
        region["top_left"] = original_top_left
        region["bottom_right"] = original_bottom_right
        print("\nAdjustment cancelled.")
        return

    save_config(config)
    print("\nAdjustment saved.")


def list_regions(config):
    if not config["regions"]:
        print("No regions configured.")
        return

    print("\nConfigured regions:")

    for number, region in enumerate(config["regions"], start=1):
        print(
            f"{number}. {region['name']} "
            f"{region['top_left']} -> {region['bottom_right']}"
        )


def main():
    config = load_config()

    while True:
        print("\n--- Screen Capture Configuration ---")
        print("1. Add region")
        print("2. Edit region")
        print("3. Delete region")
        print("4. Visualise region")
        print("5. Adjust region")
        print("6. List regions")
        print("7. Quit")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            add_region(config)
        elif choice == "2":
            edit_region(config)
        elif choice == "3":
            delete_region(config)
        elif choice == "4":
            visualise_region(config)
        elif choice == "5":
            adjust_region(config)
        elif choice == "6":
            list_regions(config)
        elif choice == "7":
            print("Goodbye.")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
