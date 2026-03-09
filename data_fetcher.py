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
                        }
                        continue
                
                result[ticker_symbol] = {
                    "price": "N/A",
                    "change_pct": "N/A",
                    "name": display_name,
                }
                continue

            latest_close = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[-2]
            change_pct = ((latest_close - prev_close) / prev_close) * 100

            result[ticker_symbol] = {
                "price": round(float(latest_close), 2),
                "change_pct": round(float(change_pct), 2),
                "name": display_name,
            }

        except Exception as e:
            print(f"[WARNING] {ticker_symbol} 데이터 수집 실패: {e}")
            result[ticker_symbol] = {
                "price": "N/A",
                "change_pct": "N/A",
                "name": display_name,
            }

    return result


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
    
    try:
        # Streamlit Cloud 환경에서의 네트워크 지연 및 방화벽 차단을 방지하기 위해 Session과 헤더 사용
        session = requests.Session()
        response = session.get(endpoint, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 일부 GDELT API 응답이 text/html로 올 수 있는 경우 대비
        try:
            data = response.json()
        except json.JSONDecodeError:
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

    except requests.exceptions.Timeout:
        return "GDELT API Timeout Error: 서버 응답 지연"
    except Exception as e:
        error_msg = str(e)
        print(f"Error fetching GDELT data: {error_msg}")
        return f"GDELT Fetch Error: {error_msg}"

def analyze_news_with_gemini(news_list, api_key):
    """
    Gemini 1.5 Flash를 사용하여 뉴스의 투자 중요도를 필터링 (Superforecasting 원칙).
    실패 시 (오류 메시지 문자열)을 반환할 수 있도록 변경.
    """
    if not api_key:
        return "Error: API Key is missing."
        
    if not news_list:
        return []

    from google import genai
    client = genai.Client(api_key=api_key)
    
    # Batch Prompt 구성
    news_text = ""
    for idx, news in enumerate(news_list):
        news_text += f"[{idx}] Title: {news['title']}\n"
        
    prompt = f"""
    You are a hedge fund lead analyst and superforecasting expert. 
    Review the following news headlines. For each headline, evaluate the probability (0-100) that this news will cause a significant, tradable movement in broad asset prices (equities, bonds, commodities) within the next 1 week.
    Apply Philip Tetlock's Superforecasting principles: weight evidence precisely, remove political bias, ignore pure noise.
    
    Filter out any news that scores below 70. 
    
    Output strictly valid JSON with no markdown formatting or extra text. The JSON format must be a list of objects like this:
    [
      {{
        "index": <integer corresponding to the news item index>,
        "score": <integer 70-100>,
        "investment_angle": "<one sentence concise investment angle/insight>"
      }}
    ]
    
    Here are the news headlines:
    {news_text}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
        )
        text_resp = response.text.strip()
        
        # Clean potential markdown wrappers
        if text_resp.startswith("```json"):
            text_resp = text_resp[7:]
        if text_resp.startswith("```"):
            text_resp = text_resp[3:]
        if text_resp.endswith("```"):
            text_resp = text_resp[:-3]
            
        filtered_indices = json.loads(text_resp.strip())
        
        # Map back to original list
        analyzed_news = []
        for item in filtered_indices:
            idx = item.get("index")
            if 0 <= idx < len(news_list):
                original_news = news_list[idx]
                original_news["score"] = item.get("score", 0)
                original_news["investment_angle"] = item.get("investment_angle", "")
                analyzed_news.append(original_news)
                
        # Sort by score descending
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
