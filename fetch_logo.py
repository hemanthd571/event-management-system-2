import urllib.request
import re
import os

html = urllib.request.urlopen('https://gmu.ac.in/').read().decode('utf-8', errors='ignore')
matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE)

logo_url = "https://gmu.ac.in/assets/imgs/gmulogo.png"
print(f"Downloading {logo_url}")
urllib.request.urlretrieve(logo_url, r'app\static\images\gmu_logo.png')
print("High-quality logo downloaded to app/static/images/gmu_logo.png")
