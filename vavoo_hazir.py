import sys
import requests
import json
import re
import base64
import os

class VavooResolver:
    def __init__(self):
        self.domain = "vavoo.to"
        self.api_url = "https://www.vavoo.tv/api/app/ping"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "okhttp/4.11.0",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8"
        })

    def get_auth_signature(self):
        """Vavoo sunucusundan addonSig (imza) alır."""
        # GitHub Secrets üzerinden veya direkt koddaki tokenı al
        token = os.environ.get('VAVOO_TOKEN', "tosFwQCJMS8qrW_AjLoHPQ41646J5dRNha6ZWHnijoYQQQoADQoXYSo7ki7O5-CsgN4CH0uRk6EEoJ0728ar9scCRQW3ZkbfrPfeCXW2VgopSW2FWDqPOoVYIuVPAOnXCZ5g")
        
        payload = {
            "token": token,
            "reason": "app-blur",
            "locale": "tr",
            "metadata": {
                "device": {"brand": "google", "model": "Nexus", "name": "21081111RG"},
                "os": {"name": "android", "version": "13"},
                "app": {"platform": "android", "version": "3.1.20"}
            },
            "appFocusTime": 1500,
            "hasAddon": True
        }
        
        try:
            resp = self.session.post(self.api_url, json=payload, timeout=15)
            if resp.status_code == 200:
                return resp.json().get("addonSig")
            else:
                print(f"⚠️ İmza Hatası: {resp.status_code}", file=sys.stderr)
                return None
        except Exception as e:
            print(f"❌ Bağlantı Hatası: {e}", file=sys.stderr)
            return None

    def fetch_group(self, group, signature):
        """Katalogdan belirli bir ülkenin kanallarını çeker."""
        channels = []
        cursor = 0
        headers = {"mediahubmx-signature": signature}
        
        while True:
            payload = {
                "language": "tr", "region": "TR", "catalogId": "iptv", "id": "iptv",
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
            except:
                break
        return channels

    def resolve_url(self, ch):
        """URL'yi oynatılabilir formata çevirir (Base64 dahil)."""
        url = ch.get("url", "")
        if url and not url.startswith("http"):
            try:
                url = base64.b64decode(url).decode('utf-8')
            except: pass
        
        if "vavoo.to" in url and "/play/" in url:
            url = url.replace("/play/", "/vavoo-iptv/play/")
        return url

# ====================== ÇALIŞTIRMA ======================
if __name__ == "__main__":
    resolver = VavooResolver()
    
    if "--full-m3u" in sys.argv:
        sig = resolver.get_auth_signature()
        if not sig:
            print("❌ İmza alınamadığı için devam edilemiyor.")
            sys.exit(1)
            
        # İstediğin ülkeleri buraya ekleyebilirsin
        target_groups = ["Turkey", "Germany"]
        all_data = []
        
        for g in target_groups:
            print(f"🔄 {g} kanalları çekiliyor...")
            all_data.extend(resolver.fetch_group(g, sig))
            
        if all_data:
            with open("vavoo_full.m3u", "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for ch in all_data:
                    name = ch.get("name", "Kanal").strip()
                    url = resolver.resolve_url(ch)
                    group = ch.get("group", "Genel")
                    f.write(f'#EXTINF:-1 group-title="{group}",{name}\n{url}\n')
            print(f"✅ Bitti! {len(all_data)} kanal kaydedildi.")
        else:
            print("⚠️ Hiç kanal bulunamadı.")
          
