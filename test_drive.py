import requests

API_KEY = "AIzaSyCsvGvldjqSMfkzVYUQCG-Mp7_NEinDMyk"
url = f"https://generativelanguage.googleapis.com/v1/models?key={API_KEY}"

print(requests.get(url).json())