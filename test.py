from playwright.sync_api import sync_playwright

# CDP WebSocket URL
cdp_ws_url = "ws://127.0.0.1:4002/devtools/browser/91d7ff24-7c83-4203-94d5-b11d20029d26"

def main():
    # Start Playwright
    with sync_playwright() as p:
        # Connect to the browser via CDP WebSocket URL
        browser = p.chromium.connect_over_cdp(cdp_ws_url)
        
        # Access the default context
        contexts = browser.contexts
        if not contexts:
            # Create a new context if none exist
            context = browser.new_context()
        else:
            # Use the existing context
            context = contexts[0]

        # Open a new page in the context
        page = context.new_page()

        # Perform browser navigation
        page.goto("https://google.com")
        print("Title of the page:", page.title())

        # Interact with the page (e.g., click a link)
        # page.click('text="More information..."')  # Uncomment for interaction

        # Take a screenshot
        page.screenshot(path="screenshot.png")
        print("Screenshot saved as 'screenshot.png'.")

        # Close the browser context
        context.close()

if __name__ == "__main__":
    main()

