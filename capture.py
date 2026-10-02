import json
from pathlib import Path

import mss
from PIL import Image
import pyperclipimg


CONFIG_FILE = "config.json"
OUTPUT_DIRECTORY = Path("captures")


def load_config():
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)


def take_screenshot():
    with mss.MSS() as sct:
        virtual_screen = sct.monitors[0]
        screenshot = sct.grab(virtual_screen)

    return screenshot, virtual_screen


def to_pil_image(image):
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


def capture(region, action):
    image, virtual_screen = take_screenshot()
    image = crop_region(image, virtual_screen, region)

    if action == "clipboard":
        copy_to_clipboard(image)
    elif action == "jpg":
        save_as_jpg(image)


def main():
    config = load_config()

    print("\n--- Screen Capture Setup ---")

    region = choose_region(config)

    if region is None:
        return

    action = choose_action()

    if action is None:
        return

    while True:
        print("\n--- Screen Capture ---")
        print(f"Region: {region['name']}")
        print(
            "Action: "
            + ("Copy to clipboard" if action == "clipboard" else "Save as JPG")
        )
        print()
        print("1. Capture")
        print("2. Change region")
        print("3. Change action")
        print("4. Quit")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            capture(region, action)

        elif choice == "2":
            new_region = choose_region(config)

            if new_region is not None:
                region = new_region

        elif choice == "3":
            new_action = choose_action()

            if new_action is not None:
                action = new_action

        elif choice == "4":
            print("Goodbye.")
            break

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
