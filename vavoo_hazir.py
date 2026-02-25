import sys
import requests
import json
import re
import base64
import os
import time

class VavooResolver:
    def __init__(self):
        # Domain ve API uç noktasını güncelledik
        self.domain = "vavoo.to"
        self.api_url = "https://www.vavoo.tv/api/app/ping"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "okhttp/4.11.0",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "X-App-Id": "tv.vavoo.app"
        })

    def get_auth_signature(self):
        # Güncel bir token denemesi (Eski olanı override eder)
        # Eğer bu da 500 verirse, GitHub Secrets'a yeni bir token girmelisin.
        token = os.environ.get('VAVOO_TOKEN', "tosFwQCJMS8qrW_AjLoHPQ41646J5dRNha6ZWHnijoYQQQoADQoXYSo7ki7O5-CsgN4CH0uRk6EEoJ0728ar9scCRQW3ZkbfrPfeCXW2VgopSW2FWDqPOoVYIuVPAOnXCZ5g")
        
        payload = {
            "token": token,
            "reason": "app-blur",
            "locale": "de",
            "metadata": {
                "device": {
                    "type": "Handset",
                    "brand": "Samsung",
                    "model": "SM-S918B",
                    "name": "S23 Ultra",
                    "uniqueId": "a8f3b2c1d0e9f8a7"
                },
                "os": {"name": "android", "version": "14"},
                "app": {
                    "platform": "android", 
                    "version": "3.1.20",
                    "signatures": ["6e8a975e3cbf07d5de823a760d4c2547f86c1403105020adee5de67ac510999e"]
                }
            },
            "appFocusTime": 5400,
            "hasAddon": True,
            "playerActive": False,
            "package": "tv.vavoo.app",
            "version": "3.1.20"
        }
        
        try:
            # 500 hatasını aşmak için ufak bir gecikme
            time.sleep(3)
            resp = self.session.post(self.api_url, json=payload, timeout=20)
            
            if resp.status_code == 200:
                sig = resp.json().get("addonSig")
                if sig: return sig
                print("⚠️ İmza verisi boş döndü.")
            else:
                print(f"⚠️ Sunucu Hatası ({resp.status_code}): {resp.text[:100]}")
            return None
        except Exception as e:
            print(f"❌ Bağlantı Hatası: {e}")
            return None

    def fetch_group(self, group, signature):
        channels = []
        cursor = 0
        headers = {"mediahubmx-signature": signature}
        
        while True:
            payload = {
                "language": "de", "region": "AT", "catalogId": "iptv", "id": "iptv",
                "filter": {"group": group}, "cursor": cursor
            }
            try:
                url = f"https://{self.domain}/mediahubmx-catalog.json"
                resp = self.session.post(url, json=payload, headers=headers, timeout=15)
                data = resp.json()
                items = data.get("items", [])
                channels.extend(items)
                cursor = data.get("nextCursor")
                if not cursor: break
            except: break
        return channels

    def resolve_url(self, ch):
        url = ch.get("url", "")
        if url and not url.startswith("http"):
            try: url = base64.b64decode(url).decode('utf-8')
            except: pass
        if "vavoo.to" in url and "/play/" in url:
            url = url.replace("/play/", "/vavoo-iptv/play/")
        return url

if __name__ == "__main__":
    resolver = VavooResolver()
    if "--full-m3u" in sys.argv:
        sig = resolver.get_auth_signature()
        if not sig: sys.exit(1)
            
        all_data = []
        # Önce sadece Türkiye'yi çekelim ki hız kazanalım
        for g in ["Turkey", "Germany"]:
            print(f"🔄 {g} çekiliyor...")
            all_data.extend(resolver.fetch_group(g, sig))
            
        if all_data:
            with open("vavoo_full.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for ch in all_data:
                    url = resolver.resolve_url(ch)
                    f.write(f'#EXTINF:-1 group-title="{ch.get("group")}",{ch.get("name")}\n{url}\n')
            print(f"✅ Başarılı: {len(all_data)} kanal kaydedildi.")
            
