import requests

def get_manifest(server_url: str):
    url = f"{server_url}/firmware/manifest"
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    return resp.json()
