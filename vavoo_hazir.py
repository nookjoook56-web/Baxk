import sys
import requests
import json
import re
import base64
import os
import time

class VavooResolver:
    def __init__(self):
        self.domain = "vavoo.to"
        self.api_url = "https://www.vavoo.tv/api/app/ping"
        self.session = requests.Session()
        # Header'ları tam olarak bir Android cihaz gibi taklit ediyoruz
        self.session.headers.update({
            "User-Agent": "okhttp/4.11.0",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Accept-Encoding": "gzip",
            "X-App-Id": "tv.vavoo.app"
        })

    def get_auth_signature(self):
        """400 Hatasını aşmak için optimize edilmiş imza alma fonksiyonu."""
        token = os.environ.get('VAVOO_TOKEN', "tosFwQCJMS8qrW_AjLoHPQ41646J5dRNha6ZWHnijoYQQQoADQoXYSo7ki7O5-CsgN4CH0uRk6EEoJ0728ar9scCRQW3ZkbfrPfeCXW2VgopSW2FWDqPOoVYIuVPAOnXCZ5g")
        
        # 400 hatasına neden olan eksik alanlar eklendi
        payload = {
            "token": token,
            "reason": "app-blur",
            "locale": "de",
            "metadata": {
                "device": {
                    "type": "Handset",
                    "brand": "google",
                    "model": "Nexus",
                    "name": "21081111RG",
                    "uniqueId": "d10e5d99ab665233" # Rastgele bir ID
                },
                "os": {"name": "android", "version": "13"},
                "app": {"platform": "android", "version": "3.1.20"}
            },
            "appFocusTime": 2500,
            "hasAddon": True,
            "playerActive": False,
            "package": "tv.vavoo.app",
            "version": "3.1.20",
            "firstAppStart": int(time.time() * 1000)
        }
        
        try:
            # Önce kısa bir bekleme (Bot tespitini zorlaştırmak için)
            time.sleep(2)
            resp = self.session.post(self.api_url, json=payload, timeout=20)
            
            if resp.status_code == 200:
                return resp.json().get("addonSig")
            else:
                print(f"⚠️ Sunucu Yanıtı ({resp.status_code}): {resp.text}", file=sys.stderr)
                return None
        except Exception as e:
            print(f"❌ Kritik Hata: {e}", file=sys.stderr)
            return None

    def fetch_group(self, group, signature):
        channels = []
        cursor = 0
        headers = {"mediahubmx-signature": signature}
        
        while True:
            payload = {
                "language": "de", "region": "AT", "catalogId": "iptv", "id": "iptv",
                "filter": {"group": group}, "cursor": cursor, "clientVersion": "3.0.2"
            }
            try:
                url = f"https://{self.domain}/mediahubmx-catalog.json"
                resp = self.session.post(url, json=payload, headers=headers, timeout=15)
                data = resp.json()
                items = data.get("items", [])
                channels.extend(items)
                
                cursor = data.get("nextCursor")
                if not cursor: break
            except:
                break
        return channels

    def resolve_url(self, ch):
        url = ch.get("url", "")
        if url and not url.startswith("http"):
            try:
                url = base64.b64decode(url).decode('utf-8')
            except: pass
        if "vavoo.to" in url and "/play/" in url:
            url = url.replace("/play/", "/vavoo-iptv/play/")
        return url

if __name__ == "__main__":
    resolver = VavooResolver()
    if "--full-m3u" in sys.argv:
        sig = resolver.get_auth_signature()
        if not sig:
            sys.exit(1)
            
        target_groups = ["Turkey", "Germany"]
        all_data = []
        for g in target_groups:
            print(f"🔄 {g} çekiliyor...")
            all_data.extend(resolver.fetch_group(g, sig))
            
        if all_data:
            with open("vavoo_full.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for ch in all_data:
                    name = ch.get("name", "Kanal").strip()
                    url = resolver.resolve_url(ch)
                    group = ch.get("group", "Genel")
                    f.write(f'#EXTINF:-1 group-title="{group}",{name}\n{url}\n')
            print(f"✅ Başarılı: {len(all_data)} kanal kaydedildi.")
