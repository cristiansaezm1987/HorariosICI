import sys
import asyncio
from playwright.async_api import async_playwright

async def capture_token():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        token_captured = []

        async def on_request(request):
            headers = request.headers
            auth_header = headers.get('authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token_captured.append(auth_header.split('Bearer ')[1])

        page.on("request", on_request)

        try:
            await page.goto("https://smp.uautonoma.cl/auth/login")
        except Exception:
            pass
        
        # Wait up to 120 seconds
        for _ in range(120):
            if token_captured:
                break
            await asyncio.sleep(1)
            
        await browser.close()
        
        if token_captured:
            print(token_captured[0])
            sys.exit(0)
        else:
            sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(capture_token())
    except Exception:
        sys.exit(1)
