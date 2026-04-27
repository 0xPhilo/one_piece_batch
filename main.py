import requests
from bs4 import BeautifulSoup

url = "https://kusonime.com/one-piece-0001-1150-batch-subtitle-indonesia-4/"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

acefile_links = []

for a in soup.find_all("a", href=True):
    href = a["href"]
    if "acefile.co" in href and "opk" in href:
        acefile_links.append(href)

# print results
for link in acefile_links:
    print(link)

print(f"\nTotal Acefile links: {len(acefile_links)}")
with open("acefile_links.txt", "w") as f:
    for link in acefile_links:
        f.write(link + "\n")


