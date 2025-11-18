from playwright.sync_api import sync_playwright
import json
import time

class HeaderCapture:
    def __init__(self):
        self.captured_headers = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
    def capture(self, wallet_address, headless=False):
        print("Starting browser to capture authentication headers...")
        print("This will open Jupiter Portfolio and automatically capture the required tokens.")
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context()
        
        captured = False
        
        def handle_request(route, request):
            nonlocal captured
            url = request.url
            
            if "portfolio-api-jup.sonar.watch/v1/transactions/fetch" in url and not captured:
                headers = request.headers
                auth = headers.get("authorization")
                turnstile = headers.get("x-turnstile-token")
                
                if auth and turnstile:
                    self.captured_headers = {
                        "authorization": auth,
                        "x-turnstile-token": turnstile,
                        "accept": headers.get("accept", "application/json")
                    }
                    captured = True
                    print(f"✓ Headers captured successfully!")
                    print(f"  Authorization: {auth[:20]}...")
                    print(f"  Turnstile: {turnstile[:20]}...")
            
            route.continue_()
        
        self.context.route("**/*", handle_request)
        self.page = self.context.new_page()
        
        portfolio_url = f"https://jup.ag/portfolio/{wallet_address}"
        print(f"\nNavigating to: {portfolio_url}")
        self.page.goto(portfolio_url, wait_until="networkidle", timeout=60000)
        
        print("\nWaiting for page to load...")
        time.sleep(3)
        
        if not captured:
            print("\nHeaders not captured yet. Clicking 'Load more' button...")
            try:
                load_more_button = self.page.locator("button:has-text('Load more'), div:has-text('Load more')").first
                if load_more_button.is_visible(timeout=5000):
                    load_more_button.click()
                    print("Clicked 'Load more' button, waiting for API request...")
                    time.sleep(5)
            except Exception as e:
                print(f"Could not find 'Load more' button: {e}")
        
        if not captured:
            print("\n⚠ Could not automatically capture headers.")
            print("Please manually scroll down or click 'Load more' in the browser window...")
            print("The script will wait for up to 30 seconds...")
            
            for i in range(30):
                if captured:
                    break
                time.sleep(1)
        
        if not captured:
            self.close()
            raise Exception("Failed to capture authentication headers. Please try again.")
        
        return self.captured_headers
    
    def close(self):
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def save_headers(self, filename="captured_headers.json"):
        if self.captured_headers:
            with open(filename, 'w') as f:
                json.dump(self.captured_headers, f, indent=2)
            print(f"\n✓ Headers saved to {filename}")
    
    @staticmethod
    def load_headers(filename="captured_headers.json"):
        try:
            with open(filename, 'r') as f:
                headers = json.load(f)
                print(f"✓ Headers loaded from {filename}")
                return headers
        except FileNotFoundError:
            return None
