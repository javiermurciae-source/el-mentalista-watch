#!/usr/bin/env python3
import urllib.request
import re
import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

BASE_URL = "https://cuevana3l.pro"
SERIE_SLUG = "el-mentalista"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

XOR_KEY = "a45f04ce-2394-47c3-b718-0ecd97ce51d6"
SERVERS_MAP = {
    "1": "https://morencius.com/v/",
    "2": "https://filemoon.sx/e/",
    "3": "https://martinshop.xyz/e/",
    "4": "https://dood.li/e/"
}

def fetch_html(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=12) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception:
            if i == retries - 1:
                return None
            time.sleep(0.5)
    return None

def decode_server(raw_url):
    try:
        if "token=" in raw_url:
            token = raw_url.split("token=")[1].split("&")[0]
            prefix = token[0]
            b64_part = token[1:]
            decoded = base64.b64decode(b64_part).decode("latin1")
            decrypted = "".join(chr(ord(c) ^ ord(XOR_KEY[i % len(XOR_KEY)])) for i, c in enumerate(decoded))
            return SERVERS_MAP.get(prefix, "") + decrypted
        elif "v=" in raw_url:
            v = raw_url.split("v=")[1].split("&")[0]
            return base64.b64decode(v).decode("utf-8")
    except Exception:
        pass
    return raw_url

def scrape_episode(season_num, ep_num, ep_url):
    html = fetch_html(ep_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    
    # Title & overview
    title_el = soup.find("h2")
    ep_title = title_el.get_text(strip=True) if title_el else f"Episodio {ep_num}"
    
    # Backdrop / info overview
    overview = ""
    info_div = soup.select_one(".backdrop-info")
    if info_div:
        p_el = info_div.find("p")
        if p_el:
            overview = p_el.get_text(strip=True)
    
    # Image
    img_el = soup.select_one(".backdrop-image img") or soup.select_one(".backdrop-info img")
    poster = img_el["src"] if img_el and img_el.has_attr("src") else ""

    servers = []
    tabs = soup.find_all("li", class_="tab-video-item")
    for tab in tabs:
        lang_div = tab.find("div", class_="tab-item-name")
        lang = lang_div.get_text(" ", strip=True) if lang_div else "Latino"
        
        items = tab.find_all("li", attrs={"data-server": True})
        for item in items:
            span = item.find("span")
            server_name = span.get_text(strip=True) if span else "Servidor"
            raw_url = item["data-server"]
            embed_url = decode_server(raw_url)
            servers.append({
                "language": lang,
                "server": server_name,
                "embed_url": embed_url,
                "raw_url": raw_url
            })

    return {
        "season": season_num,
        "episode": ep_num,
        "title": ep_title,
        "overview": overview,
        "poster": poster,
        "url": ep_url,
        "servers": servers
    }

def main():
    print(f"[*] Obteniendo temporadas de {SERIE_SLUG}...")
    main_url = f"{BASE_URL}/serie/{SERIE_SLUG}"
    html = fetch_html(main_url)
    if not html:
        print("[!] Error al cargar página principal.")
        return

    season_links = re.findall(rf'href=[\"\x27]({BASE_URL}/serie/{SERIE_SLUG}/temporada-(\d+))[\"\x27]', html)
    seasons = sorted(list(set(season_links)), key=lambda x: int(x[1]))
    print(f"[+] Encontradas {len(seasons)} temporadas.")

    all_episodes_tasks = []
    for s_url, s_num in seasons:
        s_html = fetch_html(s_url)
        if not s_html:
            continue
        ep_urls = sorted(list(set(re.findall(rf'href=[\"\x27]({BASE_URL}/serie/{SERIE_SLUG}/episodio-{s_num}x(\d+))[\"\x27]', s_html))), key=lambda x: int(x[1]))
        print(f"  - Temporada {s_num}: {len(ep_urls)} episodios encontrados.")
        for ep_url, ep_num in ep_urls:
            all_episodes_tasks.append((int(s_num), int(ep_num), ep_url))

    print(f"[*] Scrapeando {len(all_episodes_tasks)} episodios con 12 hilos concurrentes...")
    episodes_data = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        future_to_ep = {
            executor.submit(scrape_episode, s_num, ep_num, ep_url): (s_num, ep_num)
            for s_num, ep_num, ep_url in all_episodes_tasks
        }
        done_count = 0
        for future in as_completed(future_to_ep):
            s_num, ep_num = future_to_ep[future]
            try:
                data = future.result()
                if data:
                    episodes_data.append(data)
                done_count += 1
                if done_count % 15 == 0 or done_count == len(all_episodes_tasks):
                    print(f"  -> Progreso: {done_count}/{len(all_episodes_tasks)} completados")
            except Exception as e:
                print(f"  [x] Error T{s_num}E{ep_num}: {e}")

    episodes_data.sort(key=lambda x: (x["season"], x["episode"]))

    output_path = "/data/data/com.termux.launcher.nix/files/home/el_mentalista_app/episodes.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(episodes_data, f, ensure_ascii=False, indent=2)

    print(f"[✅] ¡Completado con éxito! {len(episodes_data)} episodios guardados en {output_path}")

if __name__ == "__main__":
    main()
