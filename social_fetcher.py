"""
=============================================================================
 📱 SNS & Community Data Fetcher (Social Fetcher)
 - Reddit (PRAW): r/Investing, r/WallStreetBets Hot Posts
 - Telegram (Telethon): 공개 채널 메시지 수집
 - Truth Social (truthbrush): 특정 계정 포스트 수집
 - 통합 피드: 정규화 + 스팸 필터링
 - Gemini 배치 분석: 상위 5개 투자 영향 분석
=============================================================================
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# 1) Reddit (PRAW) — r/Investing, r/WallStreetBets
# ---------------------------------------------------------------------------
def get_reddit_hot_posts(
    client_id: str = "",
    client_secret: str = "",
    user_agent: str = "TradingDashboard/1.0",
    subreddits: List[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Reddit에서 투자 관련 서브레딧의 Hot 게시물을 수집합니다.
    PRAW 라이브러리 필요 (pip install praw)
    """
    if not client_id or not client_secret:
        print("[INFO] Reddit API 키가 설정되지 않았습니다. 빈 리스트 반환.")
        return []
    
    if subreddits is None:
        subreddits = ["investing", "wallstreetbets"]
    
    try:
        import praw
        
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        
        results = []
        for sub_name in subreddits:
            try:
                subreddit = reddit.subreddit(sub_name)
                for submission in subreddit.hot(limit=limit):
                    # 고정(sticky) 게시물 제외
                    if submission.stickied:
                        continue
                    
                    results.append({
                        "title": submission.title,
                        "url": f"https://reddit.com{submission.permalink}",
                        "domain": f"r/{sub_name}",
                        "platform": "reddit",
                        "platform_icon": "🟠",
                        "raw_score": submission.score,
                        "score_label": f"⬆️ {submission.score:,}",
                        "date": datetime.fromtimestamp(submission.created_utc).strftime("%Y-%m-%d %H:%M"),
                        "num_comments": submission.num_comments,
                    })
            except Exception as e:
                print(f"[WARNING] r/{sub_name} 수집 실패: {e}")
        
        # Score 기준 내림차순 정렬
        results.sort(key=lambda x: x["raw_score"], reverse=True)
        return results[:limit * 2]  # 상위 항목만 반환
        
    except ImportError:
        print("[WARNING] praw 라이브러리 미설치. Reddit 데이터 건너뜀.")
        return []
    except Exception as e:
        print(f"[ERROR] Reddit 데이터 수집 실패: {e}")
        return []


# ---------------------------------------------------------------------------
# 2) Telegram (Telethon) — 공개 채널 메시지
# ---------------------------------------------------------------------------
def get_telegram_channel_posts(
    api_id: str = "",
    api_hash: str = "",
    string_session: str = "",
    channels: List[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Telegram 공개 채널에서 최근 메시지를 수집합니다.
    Telethon 라이브러리 필요 (pip install telethon)
    
    주의: Streamlit Cloud에서는 세션 파일 유지가 어려워
    첫 실행 시 인증코드 입력이 필요할 수 있습니다. (StringSession 사용 권장)
    """
    if not api_id or not api_hash:
        print("[INFO] Telegram API 키가 설정되지 않았습니다. 빈 리스트 반환.")
        return []
    
    if channels is None:
        channels = ["WallStreetBetsOfficial"]
    
    try:
        # Telethon은 async이므로 동기 래퍼 사용
        from telethon.sync import TelegramClient
        from telethon.sessions import StringSession
        
        results = []
        
        # StringSession이 있으면 우선 사용 (인증 코드 불필요)
        if string_session:
            client_instance = TelegramClient(StringSession(string_session), int(api_id), api_hash)
        else:
            session_path = "/tmp/telegram_session"
            client_instance = TelegramClient(session_path, int(api_id), api_hash)
            
        with client_instance as client:
            for channel_name in channels:
                try:
                    channel = client.get_entity(channel_name)
                    messages = client.get_messages(channel, limit=limit)
                    
                    for msg in messages:
                        if not msg.text or len(msg.text.strip()) < 10:
                            continue
                        
                        # 조회수 + 리액션 합산
                        views = msg.views or 0
                        reactions_count = 0
                        if hasattr(msg, 'reactions') and msg.reactions:
                            for r in msg.reactions.results:
                                reactions_count += r.count
                        
                        popularity = views + (reactions_count * 10)
                        
                        results.append({
                            "title": msg.text[:120] + ("..." if len(msg.text) > 120 else ""),
                            "url": f"https://t.me/{channel_name}/{msg.id}",
                            "domain": f"t.me/{channel_name}",
                            "platform": "telegram",
                            "platform_icon": "✈️",
                            "raw_score": popularity,
                            "score_label": f"👁️ {views:,}" if views else f"💬 {reactions_count}",
                            "date": msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else "",
                            "num_comments": reactions_count,
                        })
                except Exception as e:
                    print(f"[WARNING] Telegram 채널 '{channel_name}' 수집 실패: {e}")
        
        results.sort(key=lambda x: x["raw_score"], reverse=True)
        return results
        
    except ImportError:
        print("[WARNING] telethon 라이브러리 미설치. Telegram 데이터 건너뜀.")
        return []
    except Exception as e:
        print(f"[ERROR] Telegram 데이터 수집 실패: {e}")
        # 화면에 에러를 직관적으로 전달할 수 있도록 피드 형태로 오류 반환
        return [{
            "title": f"🚨 Telegram API 수집 오류: {str(e)}",
            "url": "#",
            "domain": "System",
            "platform": "telegram",
            "platform_icon": "⚠️",
            "raw_score": 0,
            "score_label": "ERROR",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }]


# ---------------------------------------------------------------------------
# 3) Truth Social (truthbrush) — 특정 계정 포스트
# ---------------------------------------------------------------------------
def get_truthsocial_posts(
    username: str = "",
    password: str = "",
    target_user: str = "realDonaldTrump",
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Truth Social에서 특정 계정의 최근 포스트를 수집합니다.
    truthbrush 라이브러리 필요 (pip install truthbrush)
    
    주의: Cloudflare 차단이 빈번하여 안정성이 낮습니다.
    """
    if not username or not password:
        print("[INFO] Truth Social 계정이 설정되지 않았습니다. 빈 리스트 반환.")
        return []
    
    try:
        from truthbrush import Api
        
        api = Api(username=username, password=password)
        results = []
        
        statuses = list(api.pull_statuses(target_user, limit=limit))
        
        for status in statuses:
            content = status.get("content", "")
            # HTML 태그 제거 (간단)
            import re
            clean_text = re.sub(r'<[^>]+>', '', content).strip()
            
            if len(clean_text) < 10:
                continue
            
            likes = status.get("likes_count", 0) or status.get("favourites_count", 0)
            reblogs = status.get("reblogs_count", 0)
            
            results.append({
                "title": clean_text[:120] + ("..." if len(clean_text) > 120 else ""),
                "url": status.get("url", f"https://truthsocial.com/@{target_user}"),
                "domain": f"truthsocial.com/@{target_user}",
                "platform": "truthsocial",
                "platform_icon": "🟦",
                "raw_score": likes + (reblogs * 2),
                "score_label": f"❤️ {likes:,}" if likes else "N/A",
                "date": status.get("created_at", "")[:16] if status.get("created_at") else "",
                "num_comments": status.get("replies_count", 0),
            })
        
        results.sort(key=lambda x: x["raw_score"], reverse=True)
        return results
        
    except ImportError:
        print("[WARNING] truthbrush 라이브러리 미설치. Truth Social 데이터 건너뜀.")
        return []
    except Exception as e:
        print(f"[ERROR] Truth Social 데이터 수집 실패: {e}")
        return []


# ---------------------------------------------------------------------------
# 4) 통합 피드: 정규화 + 스팸 필터링
# ---------------------------------------------------------------------------
def get_combined_social_feed(
    reddit_creds: Dict[str, str] = None,
    telegram_creds: Dict[str, str] = None,
    truthsocial_creds: Dict[str, str] = None,
) -> List[Dict[str, Any]]:
    """
    3개 플랫폼 데이터를 통합하고, 정규화된 점수로 정렬합니다.
    각 플랫폼 내에서 min-max 정규화 → 0~100 스케일 통일.
    """
    all_posts = []
    
    # Reddit 수집
    if reddit_creds:
        reddit_posts = get_reddit_hot_posts(
            client_id=reddit_creds.get("client_id", ""),
            client_secret=reddit_creds.get("client_secret", ""),
            user_agent=reddit_creds.get("user_agent", "TradingDashboard/1.0"),
        )
        all_posts.extend(reddit_posts)
    
    # Telegram 수집
    if telegram_creds:
        telegram_posts = get_telegram_channel_posts(
            api_id=telegram_creds.get("api_id", ""),
            api_hash=telegram_creds.get("api_hash", ""),
            string_session=telegram_creds.get("string_session", ""),
        )
        all_posts.extend(telegram_posts)
    
    # Truth Social 수집
    if truthsocial_creds:
        ts_posts = get_truthsocial_posts(
            username=truthsocial_creds.get("username", ""),
            password=truthsocial_creds.get("password", ""),
        )
        all_posts.extend(ts_posts)
    
    if not all_posts:
        return []
    
    # --- 스팸 필터링 ---
    filtered = []
    seen_titles = set()
    for post in all_posts:
        title = post.get("title", "")
        # 짧은 제목, 삭제된 게시물, 중복 제거
        if len(title) < 15:
            continue
        if any(kw in title.lower() for kw in ["[removed]", "[deleted]", "daily discussion"]):
            continue
        if title in seen_titles:
            continue
        seen_titles.add(title)
        filtered.append(post)
    
    # --- 플랫폼별 Min-Max 정규화 ---
    platforms = set(p["platform"] for p in filtered)
    for platform in platforms:
        platform_posts = [p for p in filtered if p["platform"] == platform]
        scores = [p["raw_score"] for p in platform_posts]
        
        if not scores:
            continue
        
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score if max_score != min_score else 1
        
        for post in platform_posts:
            post["normalized_score"] = round(
                ((post["raw_score"] - min_score) / score_range) * 100, 1
            )
    
    # 정규화 점수 기준 내림차순 정렬
    filtered.sort(key=lambda x: x.get("normalized_score", 0), reverse=True)
    
    # 수집 시간 기록
    for post in filtered:
        post["collected_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    return filtered


# ---------------------------------------------------------------------------
# 5) Gemini 배치 분석: 상위 게시물 투자 영향 분석
# ---------------------------------------------------------------------------
def analyze_social_with_gemini(
    posts: List[Dict[str, Any]],
    api_key: str,
    top_n: int = 5
) -> List[Dict[str, Any]]:
    """
    상위 N개 게시물을 하나의 배치로 묶어 Gemini 2.5 Flash에
    단 1회 API 호출로 투자 영향을 분석합니다.
    """
    if not api_key or not posts:
        return posts
    
    top_posts = posts[:top_n]
    
    # 배치 프롬프트 구성
    posts_text = ""
    for idx, post in enumerate(top_posts):
        platform = post.get("platform", "unknown")
        title = post.get("title", "No Title")
        score = post.get("normalized_score", 0)
        posts_text += f"[{idx}] ({platform}, Score: {score}) {title}\n"
    
    prompt = f"""You are a hedge fund analyst. Review these trending social media posts from investment communities.
For each post, provide a brief investment impact assessment in Korean (한국어).

IMPORTANT: Output strictly valid JSON. Format:
[
  {{
    "index": <integer>,
    "impact": "<one sentence investment impact in Korean>"
  }}
]

Posts:
{posts_text}"""
    
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
            }
        )
        
        text_resp = response.text.strip()
        analysis = json.loads(text_resp)
        
        # 분석 결과를 원본 포스트에 매핑
        for item in analysis:
            idx = item.get("index")
            if idx is not None and 0 <= idx < len(top_posts):
                top_posts[idx]["ai_impact"] = item.get("impact", "")
        
        print(f"[INFO] Gemini 소셜 분석 완료: {len(analysis)}건")
        return posts
        
    except Exception as e:
        print(f"[WARNING] Gemini 소셜 분석 실패: {e}")
        return posts


# ---------------------------------------------------------------------------
# 테스트용
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Social Fetcher Test ===")
    print("Testing with no credentials (should return empty lists)...")
    
    result = get_combined_social_feed()
    print(f"Combined feed (no creds): {len(result)} items")
    
    reddit = get_reddit_hot_posts()
    print(f"Reddit (no creds): {len(reddit)} items")
    
    telegram = get_telegram_channel_posts()
    print(f"Telegram (no creds): {len(telegram)} items")
    
    ts = get_truthsocial_posts()
    print(f"Truth Social (no creds): {len(ts)} items")
    
    print("\nAll functions gracefully returned empty lists. ✅")
