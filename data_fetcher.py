"""
=============================================================================
 데이터 수집 모듈 (Data Fetcher)
 - yfinance를 활용한 매크로 시장 데이터 및 공매도 데이터 수집
 - 모든 함수에 강력한 예외 처리(try-except) 적용
=============================================================================
"""

import yfinance as yf
import pandas as pd
from typing import Dict, List, Any
import requests
import json
import urllib.parse
from datetime import datetime, timedelta
import re


# ---------------------------------------------------------------------------
# 1) 매크로 시장 데이터 수집
# ---------------------------------------------------------------------------
def get_macro_data(av_api_key: str = "") -> Dict[str, Dict[str, Any]]:
    """
    SPY, QQQ, GLD(금), USO(원유), ^VIX(VIX 지수)의
    최근 영업일 종가와 전일 대비 등락률(%)을 딕셔너리 형태로 반환합니다.
    """
    tickers_info = {
        "SPY": "S&P 500",
        "QQQ": "QQQ",
        "GLD": "Gold",
        "BNO": "Brent Oil",  # BNO는 Brent 원유 ETF
        "^VIX": "VIX",
    }

    result = {}

    for ticker_symbol, display_name in tickers_info.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="5d")

            if hist.empty or len(hist) < 2:
                # Alpha Vantage Fallback
                if av_api_key and ticker_symbol != "^VIX":
                    av_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker_symbol}&apikey={av_api_key}"
                    resp = requests.get(av_url, timeout=5)
                    data = resp.json()
                    if "Global Quote" in data and data["Global Quote"]:
                        quote = data["Global Quote"]
                        latest_close = float(quote.get("05. price", 0))
                        change_pct_str = quote.get("10. change percent", "0%")
                        change_pct = float(change_pct_str.replace('%', ''))
                        
                        result[ticker_symbol] = {
                            "price": round(latest_close, 2),
                            "change_pct": round(change_pct, 2),
                            "name": display_name,
                            "time": quote.get("07. latest trading day", "N/A")
                        }
                        continue
                
                result[ticker_symbol] = {
                    "price": "N/A",
                    "change_pct": "N/A",
                    "name": display_name,
                    "time": "N/A"
                }
                continue

            latest_close = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[-2]
            change_pct = ((latest_close - prev_close) / prev_close) * 100
            
            # 마지막 거래 시간 (날짜) 추출
            last_date = hist.index[-1].strftime('%Y-%m-%d')

            result[ticker_symbol] = {
                "price": round(float(latest_close), 2),
                "change_pct": round(float(change_pct), 2),
                "name": display_name,
                "time": last_date
            }

        except Exception as e:
            print(f"[WARNING] {ticker_symbol} 데이터 수집 실패: {e}")
            result[ticker_symbol] = {
                "price": "N/A",
                "change_pct": "N/A",
                "name": display_name,
                "time": "N/A"
            }

    return result


def get_us_market_status() -> Dict[str, str]:
    """
    현재 뉴욕(ET) 시간 기준 시장 상태를 반환합니다.
    - Market Open: 09:30 ~ 16:00
    - Before Market: 04:00 ~ 09:30
    - After Market: 16:00 ~ 20:00
    - Market Closed: 그 외 및 주말
    """
    # KST to ET (KST는 UTC+9, ET는 UTC-5/UTC-4)
    # 3월 9일은 서머타임 기간(3월 둘째 일요일~11월 첫째 일요일) -> UTC-4
    # 단순화를 위해 현재 UTC 기준으로 계산
    now_utc = datetime.utcnow()
    # 서머타임 적용 여부 (대략적)
    # 서머타임(EDT) = UTC - 4, 표준시(EST) = UTC - 5
    # 2026년 서머타임: 3월 8일 ~ 11월 1일
    et_offset = -4 if (datetime(2026, 3, 8) <= now_utc <= datetime(2026, 11, 1)) else -5
    now_et = now_utc + timedelta(hours=et_offset)
    
    current_time = now_et.time()
    is_weekend = now_et.weekday() >= 5
    
    if is_weekend:
        return {"status": "Market Closed", "color": "#8892a4"}
        
    if datetime.strptime("09:30", "%H:%M").time() <= current_time <= datetime.strptime("16:00", "%H:%M").time():
        return {"status": "Market Open", "color": "#00d4aa"}
    elif datetime.strptime("04:00", "%H:%M").time() <= current_time < datetime.strptime("09:30", "%H:%M").time():
        return {"status": "Before Market", "color": "#ffaa00"}
    elif datetime.strptime("16:00", "%H:%M").time() < current_time <= datetime.strptime("20:00", "%H:%M").time():
        return {"status": "After Market", "color": "#ffaa00"}
    else:
        return {"status": "Market Closed", "color": "#8892a4"}


def get_tga_data() -> Dict[str, Any]:
    """미 재무부 일반 계정(TGA) 잔고 데이터를 가져옵니다."""
    try:
        # TGA Balance: Operating Cash Balance (Treasury General Account)
        # Endpoint: https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance
        url = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance?sort=-record_date&page[size]=100"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        
        # 'Treasury General Account (TGA) Closing Balance' 항목만 필터링
        tga_rows = [d for d in data.get("data", []) if "Treasury General Account (TGA) Closing Balance" in d.get("account_type", "")]
        
        if tga_rows:
            latest = tga_rows[0]
            # 최근 30개 데이터로 리스트 생성 (차트용)
            history = [{"date": d["record_date"], "value": float(d["close_today_bal"]) / 1000} for d in tga_rows[:30]] # $B 단위
            history.reverse()
            return {
                "latest_value": float(latest["close_today_bal"]) / 1000, # $B
                "date": latest["record_date"],
                "history": history
            }
    except Exception as e:
        print(f"Error fetching TGA data: {e}")
    return {"latest_value": 0, "date": "N/A", "history": []}


def get_fred_liquidity_data() -> Dict[str, Any]:
    """연준 총 자산(WALCL) 데이터를 가져옵니다 (FRED CSV 활용)."""
    try:
        # WALCL: Assets: Total Assets: Less Eliminations from Consolidation: Wednesday Level
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=WALCL"
        df = pd.read_csv(url)
        if not df.empty:
            # FRED CSV의 컬럼명은 'observation_date'와 'WALCL'입니다.
            date_col = 'observation_date' if 'observation_date' in df.columns else 'DATE'
            df[date_col] = pd.to_datetime(df[date_col])
            latest_val = float(df['WALCL'].iloc[-1]) / 1000000 # $T 단위 시각화
            latest_date = df[date_col].iloc[-1].strftime('%Y-%m-%d')
            
            # 최근 30개 데이터 (주간 데이터)
            recent = df.tail(30)
            history = [{"date": row[date_col].strftime('%Y-%m-%d'), "value": float(row['WALCL']) / 1000000} for _, row in recent.iterrows()]
            
            return {
                "latest_value": round(latest_val, 2),
                "date": latest_date,
                "history": history
            }
    except Exception as e:
        print(f"Error fetching Fed Assets: {e}")
    return {"latest_value": 0, "date": "N/A", "history": []}


def get_ai_market_advice(macro_data, news_data, liquidity_data, gemini_api_key):
    """모든 시장 데이터를 종합하여 Gemini로부터 투자 전략 리포트를 생성합니다."""
    if not gemini_api_key:
        return "Gemini API Key가 설정되지 않았습니다."
        
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=gemini_api_key)
        
        # 컨텍스트 요약
        macro_summary = "\n".join([f"- {v['name']}: ${v['price']} ({v['change_pct']}%)" for k, v in macro_data.items()])
        
        # 뉴스 데이터 요약 (리스트인 경우만 처리, 에러 문자열인 경우 빈 요약)
        news_summary = ""
        if isinstance(news_data, list):
            critical_news = [n for n in news_data if isinstance(n, dict) and n.get('score', 0) >= 90]
            if critical_news:
                news_summary = "CRITICAL NEWS:\n" + "\n".join([f"- {n['title']} (Score: {n['score']})" for n in critical_news[:3]])
        elif isinstance(news_data, str) and news_data.startswith("GDELT"):
             news_summary = f"Note: News data fetch issue ({news_data[:50]}...)"
        
        liq_summary = f"TGA: ${liquidity_data['tga']['latest_value']}B, Fed Assets: ${liquidity_data['fed']['latest_value']}T"
        
        prompt = f"""
        당신은 헤지펀드 수석 전략가입니다. 다음 실시간 시장 데이터를 바탕으로 투자 포트폴리오 전략을 제시하세요.
        
        [시장 지표]
        {macro_summary}
        
        [유동성 지표]
        {liq_summary}
        
        [주요 뉴스 개요]
        {news_summary}
        
        지침:
        1. 현재 시장의 위험 수준을 평가하세요.
        2. 포트폴리오 비중 확대(Overweight) 또는 축소(Underweight) 의견을 명확히 하세요.
        3. 추천 자산군(주식, 채권, 금, 원유 등)과 이유를 설명하세요.
        4. 한국어로 친절하면서도 전문적인 톤으로 답변하세요.
        5. 답변은 마크다운 형식을 사용하고, 짧고 강렬하게 핵심만 짚어주세요.
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        error_msg = str(e).upper()
        # gRPC 또는 JSON 에러 메시지에서 429 관련 키워드 확인
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "QUOTA" in error_msg:
            return """⚠️ **AI Advisor 할당량 초과 (Rate Limit)**
            
현재 Gemini API의 무료 티어 사용량이 한도에 도달했습니다. 잠시 후(약 1~5분 뒤) 다시 시도해 주세요. 
(무료 티어 모델은 분당/일일 호출 횟수가 제한되어 있습니다.)"""
        return f"AI Advisor 호출 중 오류 발생: {str(e)}"


def get_ticker_history(ticker_symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    주어진 티커의 시계열 역사 데이터를 가져옵니다.
    차트 렌더링용으로 사용됩니다.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period=period)
        return hist
    except Exception as e:
        print(f"Error fetching history for {ticker_symbol}: {e}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# 2) 공매도 (Short Squeeze) 데이터 수집
# ---------------------------------------------------------------------------
def get_short_squeeze_data(
    tickers: List[str] = None,
) -> pd.DataFrame:
    """
    주어진 티커 리스트의 공매도 관련 지표를 yfinance의 info에서 추출하여
    Pandas DataFrame으로 반환합니다.

    Args:
        tickers: 분석할 종목 티커 리스트 (기본값: GME, AMC, TSLA, AAPL, MSFT)

    Returns:
        DataFrame with columns:
            - Ticker: 종목 티커
            - Name: 종목명
            - Short Ratio: 공매도 비율 (Days to Cover)
            - Short % of Float: 유통주식 대비 공매도 비율
            - Current Price: 현재가
            - Market Cap: 시가총액
    """
    if tickers is None:
        tickers = ["GME", "AMC", "TSLA", "AAPL", "MSFT"]

    rows = []

    for ticker_symbol in tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info

            # 공매도 관련 데이터 추출 (없으면 'N/A')
            short_ratio = info.get("shortRatio", "N/A")
            short_pct_float = info.get("shortPercentOfFloat", "N/A")
            company_name = info.get("shortName", ticker_symbol)
            current_price = info.get("currentPrice", info.get("regularMarketPrice", "N/A"))
            market_cap = info.get("marketCap", "N/A")

            # Short % of Float를 퍼센트로 변환
            if isinstance(short_pct_float, (int, float)):
                short_pct_float = round(short_pct_float * 100, 2)

            # 시가총액을 읽기 쉬운 형식으로 변환
            if isinstance(market_cap, (int, float)):
                if market_cap >= 1e12:
                    market_cap_str = f"${market_cap / 1e12:.1f}T"
                elif market_cap >= 1e9:
                    market_cap_str = f"${market_cap / 1e9:.1f}B"
                elif market_cap >= 1e6:
                    market_cap_str = f"${market_cap / 1e6:.1f}M"
                else:
                    market_cap_str = f"${market_cap:,.0f}"
            else:
                market_cap_str = "N/A"

            rows.append({
                "Ticker": ticker_symbol,
                "Name": company_name,
                "Short Ratio": short_ratio,
                "Short % of Float": short_pct_float,
                "Current Price": current_price,
                "Market Cap": market_cap_str,
            })

        except Exception as e:
            # 개별 티커 에러 시 N/A로 채우고 계속 진행
            print(f"[WARNING] {ticker_symbol} 공매도 데이터 수집 실패: {e}")
            rows.append({
                "Ticker": ticker_symbol,
                "Name": ticker_symbol,
                "Short Ratio": "N/A",
                "Short % of Float": "N/A",
                "Current Price": "N/A",
                "Market Cap": "N/A",
            })

    df = pd.DataFrame(rows)
    return df


# ---------------------------------------------------------------------------
# 3) 상관관계 데이터 수집 (Cross-Asset Correlation)
# ---------------------------------------------------------------------------
def get_correlation_data(tickers: List[str] = None, period: str = "1y") -> pd.DataFrame:
    """
    주어진 자산들의 과거 가격 데이터를 바탕으로 수익률 상관관계를 계산합니다.
    """
    if tickers is None:
        tickers = ["SPY", "QQQ", "GLD", "TLT", "BNO", "BTC-USD"]

    try:
        data = yf.download(tickers, period=period, progress=False)["Close"]
        # 결측치 제거 및 수익률 계산
        returns = data.pct_change().dropna()
        # 상관관계 행렬 계산
        corr_matrix = returns.corr().round(2)
        
        # 컬럼 순서를 입력한 티커 순서에 맞게 조정 (다운로드 실패한 티커 제외)
        valid_tickers = [t for t in tickers if t in corr_matrix.columns]
        corr_matrix = corr_matrix.loc[valid_tickers, valid_tickers]
        
        return corr_matrix
    except Exception as e:
        print(f"[WARNING] 상관관계 데이터 수집 실패: {e}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# 4) 자금 흐름 데이터 수집 (Money Flow Proxy)
# ---------------------------------------------------------------------------
def get_money_flow_data(tickers: List[str] = None, period: str = "1mo") -> pd.DataFrame:
    """
    ETF 가격과 거래량을 바탕으로 일별 자금 흐름 대리 지표를 계산합니다.
    Net Flow Proxy = (Close - Open) * Volume / 1_000_000 (Million USD 단위)
    """
    if tickers is None:
        tickers = ["SPY", "QQQ", "IWM", "DIA", "XLF", "XLK", "XLE", "XLV"]

    rows = []
    for ticker_symbol in tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period=period)
            
            if hist.empty:
                continue
                
            for date, row in hist.iterrows():
                # 간단한 자금 흐름 프록시 계산
                net_flow = (row["Close"] - row["Open"]) * row["Volume"] / 1_000_000
                rows.append({
                    "Date": date.date(),
                    "ETF": ticker_symbol,
                    "Net Flow ($M)": round(net_flow, 1)
                })
        except Exception as e:
            print(f"[WARNING] {ticker_symbol} 자금 흐름 데이터 수집 실패: {e}")

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 5) 내부자 거래 데이터 수집 (Insider Trading)
# ---------------------------------------------------------------------------
def get_insider_trading_data(ticker_symbol: str) -> pd.DataFrame:
    """
    종목의 최근 내부자 거래(매수/매도) 내역을 수집합니다.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        insider = ticker.insider_transactions
        
        if insider is None or insider.empty:
            return pd.DataFrame()
            
        return insider.copy()
    except Exception as e:
        print(f"[WARNING] {ticker_symbol} 내부자 거래 데이터 수집 실패: {e}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# 6) GDELT & Gemini Intelligence Feed 관련
# ---------------------------------------------------------------------------

def get_gdelt_news(keywords=["Economy", "Interest Rate", "Crisis"], max_results=20):
    """
    Query the GDELT 2.0 DOC API for recent news containing specific keywords.
    """
    endpoint = "https://api.gdeltproject.org/api/v2/doc/doc"
    query_str = " OR ".join(f'"{kw}"' for kw in keywords)
    query_str += ' sourcelang:eng'
    
    params = {
        "query": query_str,
        "mode": "artlist",
        "maxrecords": max_results,
        "format": "json",
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }
    
    def fetch_yahoo_rss_fallback():
        """GDELT Rate Limit (429) 시 Yahoo Finance RSS를 대안으로 사용"""
        print("[INFO] GDELT API 차단 감지. Yahoo Finance RSS Fallback 작동...")
        import xml.etree.ElementTree as ET
        rss_url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=SPY,QQQ,TLT,GLD,USO&region=US&lang=en-US"
        try:
            rss_resp = requests.get(rss_url, headers=headers, timeout=10)
            if rss_resp.status_code == 200:
                root = ET.fromstring(rss_resp.content)
                fallback_results = []
                items = list(root.findall('./channel/item'))
                for item in items[:max_results]:
                    title = item.find('title').text if item.find('title') is not None else "No Title"
                    link = item.find('link').text if item.find('link') is not None else "#"
                    pubDate = item.find('pubDate').text if item.find('pubDate') is not None else "Unknown Date"
                    fallback_results.append({
                        "title": title,
                        "url": link,
                        "domain": "finance.yahoo.com",
                        "date": pubDate
                    })
                return fallback_results
        except Exception as e:
            print(f"[WARNING] Yahoo RSS Fallback 실패: {e}")
        return None
    
    try:
        # Streamlit Cloud 환경에서의 네트워크 지연 및 방화벽 차단을 방지하기 위해 Session과 헤더 사용
        session = requests.Session()
        response = session.get(endpoint, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 일부 GDELT API 응답이 text/html로 올 수 있는 경우 대비
        try:
            data = response.json()
        except json.JSONDecodeError:
            print("[WARNING] GDELT returned 200 but failed to parse JSON (likely a block/captcha page). Falling back...")
            fallback = fetch_yahoo_rss_fallback()
            if fallback:
                return fallback
            return f"GDELT API Format Error: 서버가 JSON 형식이 아닌 데이터를 반환했습니다. (응답 코드: {response.status_code})"
            
        articles = data.get("articles", [])
        
        results = []
        seen_urls = set()
        
        for art in articles:
            url = art.get("url")
            if not url or url in seen_urls:
                continue
                
            seen_urls.add(url)
            
            results.append({
                "title": art.get("title", "No Title"),
                "url": url,
                "domain": art.get("domain", "Unknown"),
                "seendate": art.get("seendate", "")
            })
            
        return results

    except requests.exceptions.HTTPError as e:
        if response.status_code == 429:
            fallback = fetch_yahoo_rss_fallback()
            if fallback:
                return fallback
        return f"GDELT API HTTP Error: {response.status_code}"
    except requests.exceptions.Timeout:
        fallback = fetch_yahoo_rss_fallback()
        if fallback:
            return fallback
        return "GDELT API Timeout Error: 서버 응답 지연"
    except Exception as e:
        error_msg = str(e)
        print(f"Error fetching GDELT data: {error_msg}")
        return f"GDELT Fetch Error: {error_msg}"

def analyze_news_with_gemini(news_list, api_key):
    """
    Gemini 2.5 Flash를 사용하여 뉴스의 투자 중요도를 필터링 (Superforecasting 원칙).
    실패 시 (오류 메시지 문자열)을 반환할 수 있도록 변경.
    """
    if not api_key:
        return "Error: API Key is missing."
        
    if not news_list or not isinstance(news_list, list):
        return []

    from google import genai
    client = genai.Client(api_key=api_key)
    
    # Batch Prompt 구성
    news_text = ""
    for idx, news in enumerate(news_list):
        if isinstance(news, dict):
            news_text += f"[{idx}] Title: {news.get('title', 'No Title')}\n"
        
    prompt = f"""
    You are a hedge fund lead analyst and superforecasting expert. 
    Review the following news headlines. For each headline, evaluate the probability (0-100) that this news will cause a significant, tradable movement in broad asset prices (equities, bonds, commodities) within the next 1 week.
    Apply Philip Tetlock's Superforecasting principles: weight evidence precisely, remove political bias, ignore pure noise.
    
    Filter out any news that scores below 70. 
    
    IMPORTANT: For any headline that scores 90 or above (CRITICAL), you MUST also provide a Korean translation of the headline in the "title_kr" field. For items below 90, set "title_kr" to null.
    
    Output strictly valid JSON with no markdown formatting or extra text. The JSON format must be a list of objects like this:
    [
      {{
        "index": <integer corresponding to the news item index>,
        "score": <integer 70-100>,
        "investment_angle": "<one sentence concise investment angle/insight>",
        "title_kr": "<Korean translation of headline if score >= 90, else null>"
      }}
    ]
    
    Here are the news headlines:
    {news_text}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
            }
        )
        
        text_resp = response.text.strip()
        analysis_results = json.loads(text_resp)
        
        # 원본 뉴스 리스트와 결합
        analyzed_news = []
        for res in analysis_results:
            idx = res.get("index")
            if idx is not None and 0 <= idx < len(news_list):
                original = news_list[idx]
                analyzed_news.append({
                    "title": original["title"],
                    "url": original["url"],
                    "domain": original["domain"],
                    "date": original.get("date", original.get("seendate", "Unknown")),
                    "score": res.get("score", 0),
                    "investment_angle": res.get("investment_angle", "No insight provided."),
                    "title_kr": res.get("title_kr", None)
                })
        
        # Score 기준 내림차순 정렬
        return sorted(analyzed_news, key=lambda x: x["score"], reverse=True)
        
    except Exception as e:
        error_msg = str(e)
        print(f"Gemini Analysis Error: {error_msg}")
        return f"Gemini API Error: {error_msg}"


# ---------------------------------------------------------------------------
# 테스트용 메인 실행
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print(" 매크로 데이터 수집 테스트")
    print("=" * 60)
    macro = get_macro_data()
    for symbol, data in macro.items():
        print(f"  {data['name']:>12s} | Price: {data['price']} | Change: {data['change_pct']}%")

    print()
    print("=" * 60)
    print(" 공매도 데이터 수집 테스트")
    print("=" * 60)
    squeeze_df = get_short_squeeze_data()
    print(squeeze_df.to_string(index=False))
