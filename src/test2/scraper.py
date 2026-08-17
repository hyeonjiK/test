import requests
from bs4 import BeautifulSoup
import feedparser
import datetime
import os

def extract_news_from_url(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return [f"Error fetching {url}: {e}"]

    # 1. RSS 피드인지 먼저 확인 (feedparser로 시도)
    feed = feedparser.parse(response.content)
    if feed.entries:
        results = []
        for entry in feed.entries:
            title = entry.get('title', 'No Title')
            if 'ai' not in title.lower():
                continue
            link = entry.get('link', url)
            results.append(f"- [{title}]({link})")
            if len(results) >= 5:
                break
        return results

    # 2. RSS가 아니면 HTML 파싱
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # RSS 대체 링크 찾기
    rss_link = soup.find('link', type='application/rss+xml')
    if rss_link and rss_link.get('href'):
        rss_href = rss_link['href']
        if not rss_href.startswith('http'):
            from urllib.parse import urljoin
            rss_href = urljoin(url, rss_href)
        return extract_news_from_url(rss_href)

    # 3. 일반 HTML에서 제목처럼 보이는 링크 추출 (단순화된 휴리스틱)
    results = []
    seen_titles = set()
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        if len(text) > 30 and 'ai' in text.lower(): # 제목은 보통 30자 이상, 'ai' 포함
            if text not in seen_titles:
                seen_titles.add(text)
                link = a['href']
                if not link.startswith('http'):
                    from urllib.parse import urljoin
                    link = urljoin(url, link)
                results.append(f"- [{text}]({link})")
                if len(results) >= 5:
                    break
    
    if not results:
        results.append("- 기사를 찾을 수 없습니다.")
    
    return results

def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Telegram message sent successfully.")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def main():
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not TOKEN or not CHAT_ID:
        print("Error: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID is not set in environment variables.")
        return

    urls_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'urls.txt')
    
    if not os.path.exists(urls_file):
        print("urls.txt 파일을 찾을 수 없습니다.")
        return

    with open(urls_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    message_lines = [f"## 📰 일일 뉴스 업데이트 ({datetime.date.today()})\n"]
    
    for url in urls:
        message_lines.append(f"### 🔗 {url}")
        news_items = extract_news_from_url(url)
        for item in news_items:
            message_lines.append(item)
        message_lines.append("\n")

    # Safely chunk by message lines to avoid breaking Markdown links
    current_chunk = ""
    for line in message_lines:
        if len(current_chunk) + len(line) + 1 > 4000:
            send_telegram_message(TOKEN, CHAT_ID, current_chunk)
            current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"
            
    if current_chunk.strip():
        send_telegram_message(TOKEN, CHAT_ID, current_chunk)

if __name__ == "__main__":
    main()
