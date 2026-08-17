import requests
import datetime
import json
import os
import sys

def send_telegram_message(token, chat_id, message):
    """텔레그램 봇으로 메시지를 전송합니다."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True # 뉴스 링크 미리보기 때문에 알림이 길어지는 것 방지
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("텔레그램 메세지 전송 성공!")
    except Exception as e:
        print(f"텔레그램 메세지 전송 실패: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print("상세 내용:", e.response.text)

def fetch_daily_news():
    """
    뉴스토어 API를 활용하여 특정 키워드의 당일 뉴스를 가져옵니다.
    """
    # 환경변수에서 설정값 가져오기
    api_key = os.environ.get("NEWS_API_KEY")
    keyword = os.environ.get("KEYWORD", "인공지능")
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not api_key:
        print("오류: NEWS_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    url = "https://www.newstore.or.kr/api-newstore/v1/search/newsList.json"
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    payload = {
        "apiKey": api_key,
        "query": keyword,
        "from": today,
        "until": today,
        "sort": {"date": "desc"},
        "fields": ["title", "published_at", "provider_link_page"],
        "return_from": 0,
        "return_size": 20 # 알림이 너무 길어지지 않게 20개로 제한
    }
    
    headers = {"Content-Type": "application/json; charset=utf-8"}
    news_results = []
    total_hits = 0

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if "return_object" in data and "documents" in data["return_object"]:
            documents = data["return_object"]["documents"]
            total_hits = data["return_object"].get("total_hits", 0)
            
            for doc in documents:
                title = doc.get("title", "제목 없음")
                link = doc.get("provider_link_page", "링크 없음")
                news_results.append(f"• <a href='{link}'>{title}</a>")
                
    except requests.exceptions.RequestException as e:
        print(f"API 요청 중 오류가 발생했습니다: {e}")
        news_results.append(f"⚠️ API 데이터를 불러오지 못했습니다: {e}")

    # 텔레그램 메시지 포맷 만들기
    message_lines = [
        f"📅 <b>{today} '{keyword}' 관련 뉴스</b>",
        f"총 {total_hits}건의 뉴스가 검색되었습니다.\n"
    ]
    
    if news_results:
        message_lines.extend(news_results)
    else:
        message_lines.append("새로운 뉴스가 없습니다.")
        
    final_message = "\n".join(message_lines)
    
    # 텔레그램 전송
    if tg_token and tg_chat_id:
        if len(final_message) > 4000:
            final_message = final_message[:4000] + "\n... (글자수 제한으로 생략됨)"
        send_telegram_message(tg_token, tg_chat_id, final_message)
    else:
        print("텔레그램 토큰이 없어 메시지를 전송하지 않았습니다. 결과:")
        print(final_message)

if __name__ == "__main__":
    fetch_daily_news()
