import asyncio
import os
import subprocess
import zendriver as zd

os.environ["DISPLAY"] = ":1"  # set display for Xvfb


async def start_browser() -> zd.Browser:
    browser = await zd.start(
        # use wayland for rendering instead of default X11 backend
        verbose=True,
        browser_args=[
            "--disable-dev-shm-usage",
        ],
    )
    return browser


async def main() -> None:
    print(f"Zendriver Docker demo (zendriver {zd.__version__})")
    chrome_version = " ".join(
        (
            subprocess.run(
                ["google-chrome-stable", "--version"], stdout=subprocess.PIPE
            )
            .stdout.decode("utf-8")
            .split(" ")[:3]
        )
    )
    print(
        f"{chrome_version} {os.uname().machine} ({os.uname().sysname} {os.uname().release})\n"
    )

    print("Starting browser...")
    browser = await start_browser()
    print("Browser successfully started!")

    print("Visiting https://www.browserscan.net/bot-detection...")
    page = await browser.get("https://www.browserscan.net/bot-detection")
    print("Page loaded successfully!\n")

    await page.update_target()
    assert page.target
    print("Page title:", page.target.title)

    print(
        (
            "\nDemo complete.\n"
            "- Try using a VNC viewer to visit the Docker container's built-in VNC server at http://localhost:5910.\n"
            "- VNC allows for easy debugging and inspection of the browser window.\n"
            "- For some tasks which may not be fully possible to automate, it can also be used to manually interact with the browser.\n\n"
            "When you are done, press Ctrl+C to exit the demo."
        )
    )
    await asyncio.Future()  # wait forever


if __name__ == "__main__":
    asyncio.run(main())