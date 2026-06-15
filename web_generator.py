"""
web_generator.py — TechVerse Thailand
สร้างหน้า HTML จากข้อมูลข่าวแล้ว push ขึ้น GitHub Pages (TechVerseWeb)
"""
import os, json, base64, re, requests
from datetime import datetime, timezone

WEB_REPO = os.environ.get("WEB_REPO", "electric2008/TechVerseWeb")
GH_TOKEN = os.environ.get("GH_TOKEN", "")
SITE_URL = "https://electric2008.github.io/TechVerseWeb"
HEADERS  = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
    "Content-Type": "application/json",
}
BADGE_MAP = {
    "AI & ML":"b-ai","Startup & Tech Business":"b-start",
    "Smartphone & Gadget":"b-gadget","EV & Future Tech":"b-ev",
    "Cybersecurity":"b-cyber","Software & App":"b-soft",
}

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]","",text)
    text = re.sub(r"[\s_-]+","-",text)
    text = re.sub(r"^-+|-+$","",text)
    return text[:80] or "news"

def estimate_read_time(body):
    return max(2, round(len(body.split())/200))

def format_date_thai(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z","+00:00"))
        M = ["","มกราคม","กุมภาพันธ์","มีนาคม","เมษายน","พฤษภาคม","มิถุนายน",
             "กรกฎาคม","สิงหาคม","กันยายน","ตุลาคม","พฤศจิกายน","ธันวาคม"]
        return f"{dt.day} {M[dt.month]} {dt.year+543}"
    except:
        return iso

def body_to_html(body):
    lines = body.strip().split("\n")
    html = []
    for line in lines:
        line = line.strip()
        if not line: continue
        if line.startswith("## "):   html.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "): html.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("- "):  html.append(f"<ul><li>{line[2:]}</li></ul>")
        else: html.append(f"<p>{line}</p>")
    return "\n".join(html).replace("</ul>\n<ul>","\n")

def push_file(path, content, message):
    url = f"https://api.github.com/repos/{WEB_REPO}/contents/{path}"
    b64 = base64.b64encode(content.encode("utf-8")).decode()
    sha = None
    r = requests.get(url, headers=HEADERS, timeout=10)
    if r.status_code == 200:
        sha = r.json().get("sha")
    payload = {"message":message,"content":b64}
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=HEADERS, json=payload, timeout=15)
    return r.status_code in (200,201)

def read_template():
    url = f"https://api.github.com/repos/{WEB_REPO}/contents/news/template.html"
    r = requests.get(url, headers=HEADERS, timeout=10)
    if r.status_code == 200:
        return base64.b64decode(r.json()["content"]).decode("utf-8")
    return ""

def generate_article_page(article, written):
    try:
        title_th   = written.get("title_th", article.get("title",""))
        body_th    = written.get("body_th","")
        caption_fb = written.get("caption_fb","")
        hashtags   = written.get("hashtags",[])
        category   = article.get("category","Tech")
        source_url = article.get("url","")
        image      = article.get("image","")
        slug       = slugify(title_th) or slugify(article.get("title","news"))
        date_iso   = datetime.now(timezone.utc).isoformat()
        date_thai  = format_date_thai(date_iso)
        read_time  = estimate_read_time(body_th)
        badge_cls  = BADGE_MAP.get(category,"b-tech")
        excerpt    = caption_fb[:160] if caption_fb else body_th[:160]
        body_html  = body_to_html(body_th)
        tags_html  = "".join(f'<span class="tag">{t}</span>' for t in hashtags)
        hero_img   = f'<img class="hero-img" src="{image}" alt="{title_th}" loading="eager">' if image else ""
        template   = read_template()
        if not template:
            print("[⚠️] ไม่พบ template.html ใน TechVerseWeb repo")
            return None
        title_short = title_th[:40]+("..." if len(title_th)>40 else "")
        html = (template
            .replace("{{TITLE}}",title_th)
            .replace("{{TITLE_SHORT}}",title_short)
            .replace("{{EXCERPT}}",excerpt)
            .replace("{{IMAGE}}",image or "")
            .replace("{{CATEGORY}}",category)
            .replace("{{BADGE_CLASS}}",badge_cls)
            .replace("{{DATE}}",date_thai)
            .replace("{{READ_TIME}}",str(read_time))
            .replace("{{HERO_IMAGE}}",hero_img)
            .replace("{{BODY}}",body_html)
            .replace("{{SOURCE_TITLE}}",article.get("title",""))
            .replace("{{SOURCE_URL}}",source_url)
            .replace("{{TAGS}}",tags_html)
        )
        ok_html = push_file(f"news/{slug}.html", html, f"✨ เพิ่มข่าว: {title_th[:50]}")
        if not ok_html:
            print("[❌] push HTML ล้มเหลว")
            return None
        meta = {
            "slug":slug,"title":title_th,"excerpt":excerpt,
            "category":category,"date":date_iso,"image":image or "",
            "url":f"{SITE_URL}/news/{slug}.html",
            "source_url":source_url,"source":article.get("source",""),
        }
        push_file(f"news/{slug}.json", json.dumps(meta,ensure_ascii=False,indent=2), f"📋 meta: {slug}")
        print(f"[✅] สร้างหน้าเว็บสำเร็จ: {SITE_URL}/news/{slug}.html")
        return meta
    except Exception as e:
        print(f"[❌] generate_article_page error: {e}")
        return None

def get_article_url(slug):
    return f"{SITE_URL}/news/{slug}.html"
