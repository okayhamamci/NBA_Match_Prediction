import asyncio
import os
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import time

SEASONS = list(range(2010,2024))
DATA_DIR = "data"
STANDINGS_DIR = os.path.join(DATA_DIR, "standings")
SCORES_DIR = os.path.join(DATA_DIR, "scores")

async def get_html(url, selector, sleep=5, retries=3):
    html = None
    for i in range(1, retries+1):
        time.sleep(sleep * i)

        try:
            async with async_playwright() as p:
                browser = await p.firefox.launch()
                page = await browser.new_page()
                await page.goto(url)
                print(await page.title())
                html = await page.inner_html(selector)
        except PlaywrightTimeout:
            print("Tiemout error occured in this url: " + url)
            continue
        else:
            break #Succesfully Scrapped (to not stay in the loop)
    return html

async def main():
    season = 2011
    url = f"https://www.basketball-reference.com/leagues/NBA_{season}_games.html"   
    print(url)
    html = await get_html(url, "#content .filter")
    
asyncio.run(main())