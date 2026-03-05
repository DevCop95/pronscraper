import sys
sys.path.insert(0, '.')
from src.scraper import fetch_html, ALLOWED_URL
from bs4 import BeautifulSoup

html = fetch_html(ALLOWED_URL)
soup = BeautifulSoup(html, "html.parser")

comp = soup.select("div.competition")[0]
matches = comp.select("div.match") or comp.select("div.cmatch")
m = matches[0]

print("=== HTML COMPLETO DEL PRIMER PARTIDO ===")
print(m.prettify()[:3000])