"""
=============================================================================
 🚀 AI 트레이딩 대시보드 (AI Trading Dashboard)
 - 헷지펀드 전문가용 트레이딩 대시보드
 - 실시간 시장 데이터 + VIX 위기 경보 + 공매도 분석
 -
 - 실행 방법: streamlit run dashboard.py
 - 호환: Streamlit 0.84+
=============================================================================
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime

# 로컬 모듈 임포트
from data_fetcher import (
    get_macro_data, 
    get_short_squeeze_data,
    get_correlation_data,
    get_money_flow_data,
    get_insider_trading_data,
    get_gdelt_news,
    analyze_news_with_gemini
)
from risk_analyzer import calculate_market_risk


# ===========================================================================
# 페이지 설정 (Streamlit 0.84+ 호환)
# ===========================================================================
st.set_page_config(
    page_title="AI Trading Dashboard",
    page_icon="🚀",
    layout="wide",
)


# ===========================================================================
# 커스텀 CSS 스타일 (다크 테마 강화)
# ===========================================================================
st.markdown("""
<style>
    /* 메인 배경 */
    .stApp, .reportview-container, .main {
        background-color: #0e1117;
        color: #fafafa;
    }

    /* 사이드바 */
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #0a0e18 0%, #141926 100%);
    }

    /* 메트릭 카드 스타일 */
    .metric-card {
        background: linear-gradient(135deg, #1a1f2e 0%, #252b3b 100%);
        border: 1px solid #2d3548;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        text-align: center;
        margin-bottom: 10px;
        min-height: 180px; /* 고정 최소 높이로 정렬 유지 */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .metric-card .label {
        color: #8892a4;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .metric-card .value {
        color: #ffffff;
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .metric-card .delta-up {
        color: #00d4aa;
        font-size: 0.95rem;
        font-weight: 600;
    }
    .metric-card .delta-down {
        color: #ff4444;
        font-size: 0.95rem;
        font-weight: 600;
    }
    .metric-card .delta-na {
        color: #888888;
        font-size: 0.95rem;
    }

    /* 알림 박스 강화 */
    .alert-box {
        border-radius: 10px;
        padding: 20px 24px;
        margin: 10px 0 20px 0;
        font-size: 1.05rem;
        line-height: 1.6;
    }
    .alert-safe {
        background-color: #0d3320;
        border-left: 5px solid #00d4aa;
        color: #a5f3d6;
    }
    .alert-warning {
        background-color: #3d2e00;
        border-left: 5px solid #ffaa00;
        color: #ffe0a0;
    }
    .alert-danger {
        background-color: #3d0a0a;
        border-left: 5px solid #ff4444;
        color: #ffaaaa;
    }
    .alert-unknown {
        background-color: #1a1f2e;
        border-left: 5px solid #888888;
        color: #c0c8d8;
    }

    .metric-card .time {
        font-size: 0.7rem;
        color: #6b7688;
        text-align: right;
        margin-top: 5px;
    }

    /* 구분선 */
    hr {
        border-color: #2d3548 !important;
    }

    /* 헤더 스타일 */
    h1, h2, h3, h4 {
        color: #e0e6f0 !important;
    }

    /* 테이블 스타일 */
    .dataframe {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# ===========================================================================
# 데이터 캐싱 (st.cache_data - 최신 호환)
# ===========================================================================
@st.cache_data(ttl=43200, show_spinner=True)
def load_macro_data(av_api_key=""):
    """매크로 시장 데이터 캐싱 로드 (12시간 갱신)"""
    return get_macro_data(av_api_key)


@st.cache_data(ttl=3600, show_spinner=True)
def load_short_squeeze_data(tickers_str):
    """공매도 데이터 캐싱 로드 (1시간 갱신)"""
    ticker_list = [t.strip() for t in tickers_str.split(",") if t.strip()]
    return get_short_squeeze_data(ticker_list)


@st.cache_data(ttl=86400, show_spinner=True)
def load_correlation_data(tickers):
    """상관관계 데이터 캐싱 (1일 갱신)"""
    return get_correlation_data(tickers)


@st.cache_data(ttl=3600, show_spinner=True)
def load_money_flow_data(tickers):
    """자금 흐름 데이터 캐싱 (1시간 갱신)"""
    return get_money_flow_data(tickers)


@st.cache_data(ttl=3600, show_spinner=True)
def load_insider_data(ticker):
    """내부자 거래 데이터 캐싱 (1시간 갱신)"""
    return get_insider_trading_data(ticker)


@st.cache_data(ttl=3600, show_spinner=True)
def load_ticker_history_data(ticker, period="1y"):
    """티커 시계열 데이터 캐싱 (1시간 갱신)"""
    from data_fetcher import get_ticker_history
    return get_ticker_history(ticker, period)


@st.cache_data(ttl=3600, show_spinner=True)
def load_liquidity_data():
    """TGA 및 연준 자산 데이터 캐싱 (1시간 갱신)"""
    from data_fetcher import get_tga_data, get_fred_liquidity_data
    return {
        "tga": get_tga_data(),
        "fed": get_fred_liquidity_data()
    }


@st.cache_data(ttl=43200, show_spinner=True)
def load_gemini_25_market_report(macro_data, news_data, liquidity_data, gemini_api_key):
    """Gemini 2.5 Flash 기반 투자 조언 캐싱 (12시간 갱신)"""
    from data_fetcher import get_ai_market_advice
    return get_ai_market_advice(macro_data, news_data, liquidity_data, gemini_api_key)


@st.cache_data(ttl=43200, show_spinner=True)
def load_intelligence_feed(api_key, bypass_cache=False):
    """GDELT 뉴스 수집 및 Gemini 필터링된 인텔리전스 피드 로드 (12시간 갱신)"""
    raw_news = get_gdelt_news(keywords=["Economy", "Interest Rate", "Crisis", "War"], max_results=30)
    
    # 에러 문자열이 반환된 경우 UI로 그대로 전달
    if isinstance(raw_news, str):
        return raw_news
        
    if not raw_news:
        return []
        
    analyzed_news = analyze_news_with_gemini(raw_news, api_key)
    return analyzed_news

# ===========================================================================
# 사이드바 (Sidebar) 메뉴 구성
# ===========================================================================
st.sidebar.markdown("# 🚀 AI Dashboard")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "📋 Navigation",
    options=["Overview", "Intelligence Feed", "M3 Short Squeeze", "M6 Correlation", "M8 Inst. Flow", "Insider Trading"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.markdown("#### ⚙️ Settings")
av_api_key = st.sidebar.text_input("Alpha Vantage API Key", type="password", help="yfinance 장애 시 매크로 데이터 백업용 (옵션)")

# Streamlit Secrets에서 Gemini API 키 확인 (클라우드 배포용)
gemini_api_key = ""
if "GEMINI_API_KEY" in st.secrets:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
else:
    # 로컬 테스트용 폴백 (secrets.toml 설정 전)
    gemini_api_key = st.sidebar.text_input("Gemini API Key (Local Setup)", type="password", help="secrets.toml이 없을 때 표시됩니다.")

auto_refresh = st.sidebar.checkbox("Auto Refresh (12hr)", value=True)
if st.sidebar.button("🔄 Force Clear Cache"):
    st.cache_data.clear()
    # Streamlit 버전에 따른 리런 처리 (1.27.0+ 에서는 st.rerun() 권장)
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()
show_debug = st.sidebar.checkbox("Debug Mode", value=False)
st.sidebar.markdown("---")
st.sidebar.text(f"🕐 Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
st.sidebar.text("Powered by yfinance & Streamlit")


# ===========================================================================
# 메인 화면 - 상단 헤더
# ===========================================================================
st.markdown(
    """
    <h1 style='text-align: center; color: #00d4aa; margin-bottom: 0;'>
        🚀 AI Trading Dashboard
    </h1>
    <p style='text-align: center; color: #6b7688; font-size: 1.1rem; margin-top: 4px;'>
        Hedge Fund Grade Market Intelligence System
    </p>
    """,
    unsafe_allow_html=True,
)
st.markdown("---")


# ===========================================================================
# 실제 데이터 로드
# ===========================================================================
from data_fetcher import get_us_market_status
macro_data = load_macro_data(av_api_key)
market_status = get_us_market_status()
liquidity_data = load_liquidity_data()


# ===========================================================================
# 커스텀 메트릭 위젯 렌더링 함수 (HTML 기반 - 0.84 호환)
# ===========================================================================
def render_metric_card(label, value, change_pct, timestamp="", market_status=None):
    """HTML 기반 메트릭 카드 렌더링"""
    if isinstance(change_pct, (int, float)):
        delta_class = "delta-up" if change_pct >= 0 else "delta-down"
        delta_str = f"{change_pct:+.2f}%"
    else:
        delta_class = "delta-na"
        delta_str = "N/A"

    if isinstance(value, (int, float)):
        value_str = f"${value:,.2f}" if label != "📈 VIX" else f"{value:.2f}"
    else:
        value_str = "N/A"

    time_html = f"<div class='time'>{timestamp}</div>" if timestamp else ""
    
    status_html = ""
    if market_status:
        status_html = f"<div style='font-size: 0.75rem; font-weight: bold; color: {market_status['color']}; margin-bottom: 4px;'>● {market_status['status']}</div>"

    html = f"""<div class="metric-card">
{status_html}
<div class="label">{label}</div>
<div class="value">{value_str}</div>
<div class="{delta_class}">{delta_str}</div>
{time_html}
</div>"""
    return html


# ===========================================================================
# 상단 메트릭 위젯 (5열 배치: S&P 500, QQQ, Gold, Brent, VIX)
# ===========================================================================
metric_keys = ["SPY", "QQQ", "GLD", "BNO", "^VIX"]
cols = st.columns(5)

for col, key in zip(cols, metric_keys):
    data = macro_data.get(key, {})
    name = data.get("name", key)
    price = data.get("price", "N/A")
    change = data.get("change_pct", "N/A")
    time_val = data.get("time", "")

    # US 지수(SPY, QQQ)와 VIX에만 장 상태 표시
    status_to_show = market_status if key in ["SPY", "QQQ", "^VIX"] else None

    with col:
        html = render_metric_card(f"📈 {name}", price, change, timestamp=time_val, market_status=status_to_show)
        st.markdown(html, unsafe_allow_html=True)
        # 차트 보기 버튼 추가 (상태 저장)
        if st.button(f"🔍 Chart: {name}", key=f"btn_{key}"):
            st.session_state['selected_ticker'] = key



# ===========================================================================
# 메인 콘텐츠 영역 (메뉴에 따라 분기)
# ===========================================================================

if menu == "Overview":
    # -------------------------------------------------------------------
    # 1) AI Market Advisor (Gemini 기반 종합 판단)
    # -------------------------------------------------------------------
    st.markdown("### 🤖 AI Market Advisor (종합 투자 전략)")
    
    # 지능형 피드 데이터 가져오기 (Gemini 조언용 컨텍스트)
    intelligence_data = load_intelligence_feed(gemini_api_key)
    
    with st.spinner("Gemini 2.5가 시장 데이터를 분석 중입니다..."):
        ai_advice = load_gemini_25_market_report(macro_data, intelligence_data, liquidity_data, gemini_api_key)
    
    # AI 어드바이스 박스 (스타일 적용)
    st.markdown(
        f"""
        <div style="background-color: #1e2538; padding: 20px; border-radius: 10px; border-left: 5px solid #00d4aa; margin-bottom: 25px; line-height: 1.6;">
            {ai_advice.replace('\n', '<br>')}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")
    
    # -------------------------------------------------------------------
    # 2-1) 유동성 지표 (Liquidity Metrics)
    # -------------------------------------------------------------------
    st.markdown("### 💧 US Liquidity & Macro Summary")
    l_col1, l_col2, l_col3 = st.columns(3)
    
    with l_col1:
        tga = liquidity_data.get("tga", {})
        tga_val = tga.get('latest_value', 'N/A')
        tga_disp = f"${tga_val:,.1f}B" if isinstance(tga_val, (int, float)) and tga_val > 0 else "N/A"
        st.metric("Treasury General Account (TGA)", tga_disp, help="미 재무부 현금 잔고 (유동성 흡수/방출 지표)")
        
    with l_col2:
        fed = liquidity_data.get("fed", {})
        fed_val = fed.get('latest_value', 'N/A')
        fed_disp = f"${fed_val:,.2f}T" if isinstance(fed_val, (int, float)) and fed_val > 0 else "N/A"
        st.metric("Fed Total Assets (WALCL)", fed_disp, help="연준 대차대조표 총 자산 (양적완화/긴축 지표)")
        
    with l_col3:
        vix_data = macro_data.get("^VIX", {})
        vix_price = vix_data.get("price", "N/A")
        st.metric("VIX Index (Fear Gauge)", f"{vix_price}", delta=f"{vix_data.get('change_pct', 0):+.2f}%")

    # -------------------------------------------------------------------
    # 2) 선택된 자산 차트 (인터랙션)
    # -------------------------------------------------------------------
    # 기본값 설정: 선택된 것이 없으면 VIX (^VIX) 디폴트
    target_ticker = st.session_state.get('selected_ticker', '^VIX')
    ticker_name = macro_data.get(target_ticker, {}).get("name", target_ticker)
    
    # 기간 선택 라디오 버튼
    timeframe_map = {
        "3개월": "3mo",
        "6개월": "6mo",
        "12개월": "1y",
        "3년": "3y"
    }
    
    # 라디오 버튼을 가로로 배치 (0.84버전에서는 horizontal=True 지원)
    selected_period_label = st.radio("조회 기간 선택:", options=list(timeframe_map.keys()), index=2)
    selected_period = timeframe_map[selected_period_label]
    
    st.markdown(f"#### 📊 {ticker_name} - Price History ({selected_period_label})")
    
    with st.spinner(f"Loading {ticker_name} chart..."):
        hist_df = load_ticker_history_data(target_ticker, period=selected_period)
        
    if not hist_df.empty:
        # 수익률 계산: (마지막 종가 - 첫 종가) / 첫 종가 * 100
        start_price = hist_df["Close"].iloc[0]
        end_price = hist_df["Close"].iloc[-1]
        perf = ((end_price - start_price) / start_price) * 100
        
        # 수익률 텍스트 스타일
        perf_color = "#00d4aa" if perf >= 0 else "#ff4444"
        perf_text = f"{perf:+.2f}%"
        
        # 제목 옆에 수익률 표시
        st.markdown(f"<h3 style='margin-top: -15px;'>해당 기간 수익률: <span style='color: {perf_color}; font-weight: bold;'>{perf_text}</span></h3>", unsafe_allow_html=True)

        fig_hist = px.line(hist_df, x=hist_df.index, y="Close", 
                           template="plotly_dark",
                           color_discrete_sequence=["#00d4aa"])
        fig_hist.update_layout(
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            hovermode="x unified",
            margin=dict(l=40, r=40, t=20, b=40),
            height=400
        )
        st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.error("차트 데이터를 불러올 수 없습니다.")

    # -------------------------------------------------------------------
    # 3) 유동성 트렌드 차트 (TGA & Fed Assets)
    # -------------------------------------------------------------------
    st.markdown("#### 🌊 Liquidity Trends (TGA & Fed Balance Sheet)")
    
    tga_hist = liquidity_data.get("tga", {}).get("history", [])
    fed_hist = liquidity_data.get("fed", {}).get("history", [])
    
    if tga_hist and fed_hist:
        tga_df = pd.DataFrame(tga_hist)
        fed_df = pd.DataFrame(fed_hist)
        
        c1, c2 = st.columns(2)
        
        with c1:
            fig_tga = px.area(tga_df, x="date", y="value", title="TGA Balance ($B)",
                             template="plotly_dark", color_discrete_sequence=["#ffaa00"])
            fig_tga.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=300)
            st.plotly_chart(fig_tga, use_container_width=True)
            
        with c2:
            fig_fed = px.line(fed_df, x="date", y="value", title="Fed Total Assets ($T)",
                             template="plotly_dark", color_discrete_sequence=["#00d4aa"])
            fig_fed.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=300)
            st.plotly_chart(fig_fed, use_container_width=True)
    
    st.markdown("---")

    st.markdown("---")
    # -------------------------------------------------------------------
    # Overview 탭: 버블 차트 + 시장 요약
    # -------------------------------------------------------------------
    st.markdown("### 📊 Market Overview — Sector Bubble Map")
    st.markdown(
        "<p style='color: #6b7688;'>각 버블의 크기는 시가총액, X축은 수익률, Y축은 변동성을 나타냅니다.</p>",
        unsafe_allow_html=True,
    )

    # 버블 차트용 데이터 (데모용 시뮬레이션)
    np.random.seed(42)
    sectors = [
        "Technology", "Healthcare", "Financials", "Energy",
        "Consumer Disc.", "Industrials", "Materials", "Utilities",
        "Real Estate", "Comm. Services",
    ]
    bubble_df = pd.DataFrame({
        "Sector": sectors,
        "Return (%)": np.random.uniform(-5, 15, len(sectors)).round(2),
        "Volatility (%)": np.random.uniform(5, 30, len(sectors)).round(2),
        "Market Cap ($B)": np.random.uniform(50, 500, len(sectors)).round(0),
        "Momentum Score": np.random.uniform(0.3, 1.0, len(sectors)).round(2),
    })

    # Plotly 버블 차트
    fig = px.scatter(
        bubble_df,
        x="Return (%)",
        y="Volatility (%)",
        size="Market Cap ($B)",
        color="Momentum Score",
        hover_name="Sector",
        size_max=60,
        color_continuous_scale="Turbo",
        title="",
    )
    fig.update_layout(
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font=dict(color="#c0c8d8", size=13),
        xaxis=dict(
            gridcolor="#1e2538",
            zerolinecolor="#2d3548",
            title_font=dict(size=14),
        ),
        yaxis=dict(
            gridcolor="#1e2538",
            zerolinecolor="#2d3548",
            title_font=dict(size=14),
        ),
        coloraxis_colorbar=dict(
            title="Momentum",
            tickfont=dict(color="#8892a4"),
            title_font=dict(color="#8892a4"),
        ),
        height=500,
        margin=dict(l=40, r=40, t=20, b=40),
    )
    fig.update_traces(
        marker=dict(line=dict(width=1, color="#2d3548")),
    )

    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------------
    # Sector Attractiveness Analysis (새로 추가된 기능)
    # -------------------------------------------------------------------
    st.markdown("#### ✨ Sector Attractiveness Insight")
    
    # 투자 매력도 스코어 계산 (Score = Return * Momentum / Volatility)
    # Volatility가 0에 가까운 경우를 방지
    attr_df = bubble_df.copy()
    attr_df["Attractiveness Score"] = (attr_df["Return (%)"] * attr_df["Momentum Score"]) / attr_df["Volatility (%)"].replace(0, 0.1)
    
    best_sector = attr_df.loc[attr_df["Attractiveness Score"].idxmax()]
    worst_sector = attr_df.loc[attr_df["Attractiveness Score"].idxmin()]
    
    st.markdown(
        f"""
        <div style='background-color: #1a1f2e; padding: 15px; border-radius: 8px; border-left: 4px solid #00d4aa; margin-bottom: 20px;'>
            <p style='margin: 0; font-size: 1.05rem;'>
                📈 <strong>가장 매력적인 섹터: <span style='color: #00d4aa;'>{best_sector['Sector']}</span></strong><br>
                <span style='color: #8892a4; font-size: 0.95rem;'>
                높은 수익률(<b>{best_sector['Return (%)']}%</b>)과 강한 모멘텀(<b>{best_sector['Momentum Score']}</b>)을 유지하면서도 
                상대적으로 안정적인 변동성(<b>{best_sector['Volatility (%)']}%</b>)을 보이고 있어 투자 매력도가 가장 높습니다.
                </span>
            </p>
            <hr style='margin: 10px 0; border: none; border-top: 1px solid #2d3548;'>
            <p style='margin: 0; font-size: 1.05rem;'>
                📉 <strong>주의가 필요한 섹터: <span style='color: #ff4444;'>{worst_sector['Sector']}</span></strong><br>
                <span style='color: #8892a4; font-size: 0.95rem;'>
                저조한 수익률(<b>{worst_sector['Return (%)']}%</b>)과 높은 변동성(<b>{worst_sector['Volatility (%)']}%</b>)으로 인해 
                리스크 대비 보상이 낮아 현재 투자 매력도가 가장 떨어지는 것으로 분석됩니다.
                </span>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # -------------------------------------------------------------------
    # 하단: 시장 데이터 요약 테이블
    # -------------------------------------------------------------------
    st.markdown("### 📋 Market Summary Table")

    summary_rows = []
    for key in metric_keys:
        d = macro_data.get(key, {})
        price = d.get("price", "N/A")
        change = d.get("change_pct", "N/A")
        if isinstance(change, (int, float)):
            status = "🟢 Up" if change > 0 else ("🔴 Down" if change < 0 else "⚪ Flat")
        else:
            status = "❓ N/A"
        summary_rows.append({
            "Asset": d.get("name", key),
            "Price": f"${price:,.2f}" if isinstance(price, (int, float)) else "N/A",
            "Change (%)": f"{change:+.2f}%" if isinstance(change, (int, float)) else "N/A",
            "Status": status,
        })

    summary_df = pd.DataFrame(summary_rows)
    st.table(summary_df)


elif menu == "Intelligence Feed":
    # -------------------------------------------------------------------
    # Intelligence Feed 탭 (GDELT + Gemini 요약)
    # -------------------------------------------------------------------
    st.markdown("### 🧠 Intelligence Feed (GDELT + Gemini 2.5 Flash)")
    st.markdown(
        "<p style='color: #6b7688;'>GDELT 실시간 뉴스에 «슈퍼포어캐스팅» 원칙을 적용하여 "
        "단기 시장 변동성을 촉발할 가능성이 높은 뉴스를 선별합니다.</p>",
        unsafe_allow_html=True,
    )
    
    if not gemini_api_key:
        st.warning("⚠️ 백엔드 환경에 **Gemini API Key**가 설정되지 않았습니다. (.streamlit/secrets.toml 또는 Streamlit Cloud Secrets에 `GEMINI_API_KEY`를 추가해주세요.)")
    else:
        # 수동 갱신 버튼
        col_btn, _ = st.columns([1, 4])
        with col_btn:
            if st.button("🔄 Refresh Feed"):
                load_intelligence_feed.clear()
        
        with st.spinner("Analyzing global intelligence (superforecasting in progress)..."):
            # Time-based bypass to force cloud to drop old empty cache right now
            force_refresh = datetime.now().strftime("%H")
            feed_data = load_intelligence_feed(gemini_api_key, bypass_cache=force_refresh)
            
        if isinstance(feed_data, str):
            st.error(f"🚨 인텔리전스 피드 로딩 오류: {feed_data}")
            st.info("API Key가 정확한지 확인하시거나 잠시 후 다시 시도해 주세요.")
        elif not feed_data:
            st.info("최근 24시간 내 유의미한 거시/지정학 이벤트가 감지되지 않았거나 데이터 수집 중 오류가 발생했습니다.")
        else:
            for item in feed_data:
                score = item.get("score", 0)
                
                # 점수 90 이상은 CRITICAL 표시
                is_critical = score >= 90
                
                border_color = "#ff4444" if is_critical else "#2d3548"
                bg_color = "#3d0a0a" if is_critical else "#1a1f2e"
                
                title_kr = item.get("title_kr")
                kr_line = f"<p style='margin-top: 6px; margin-bottom: 0; color: #ffcc00; font-size: 1.0rem; font-weight: 600;'>🇰🇷 {title_kr}</p>" if is_critical and title_kr else ""
                
                article_date = item.get("date", "")
                if not article_date or article_date == "Unknown":
                    date_display = "N/A"
                else:
                    date_display = article_date[:16] if len(article_date) > 16 else article_date
                
                html_card = f"""<div style='background-color: {bg_color}; padding: 15px; border-radius: 8px; border: 1px solid {border_color}; margin-bottom: 20px;'>
<div style='display: flex; justify-content: space-between; align-items: center;'>
<h4 style='margin: 0; color: #ffffff;'>{'🚨 <b>[CRITICAL]</b>' if is_critical else '📰'} <a href='{item.get("url", "#")}' style='color: #ffffff; text-decoration: none;' target='_blank'>{item.get("title", "No Title")}</a></h4>
<span style='background-color: {border_color}; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-weight: bold;'>Score: {score}</span>
</div>
{kr_line}
<p style='margin-top: 5px; color: #8892a4; font-size: 0.85rem;'>Source: {item.get("domain", "Unknown")} | Date: {date_display}</p>
<p style='margin-top: 10px; margin-bottom: 0px; font-size: 1.05rem;'><strong style='color: #00d4aa;'>💡 Investment Angle:</strong> {item.get("investment_angle", "N/A")}</p>
</div>"""
                st.markdown(html_card, unsafe_allow_html=True)


elif menu == "M3 Short Squeeze":
    # -------------------------------------------------------------------
    # M3 Short Squeeze 탭: 공매도 데이터 분석
    # -------------------------------------------------------------------
    st.markdown("### 🩳 M3 — Short Squeeze Monitor")
    st.markdown(
        "<p style='color: #6b7688;'>공매도 비율이 높은 종목을 모니터링합니다. "
        "Short Ratio가 높을수록 숏 스퀴즈 가능성이 높아집니다.</p>",
        unsafe_allow_html=True,
    )

    # 분석 대상 종목 (사용자 커스터마이즈 가능)
    default_tickers = "GME, AMC, TSLA, AAPL, MSFT"
    user_tickers = st.text_input(
        "분석할 티커 입력 (쉼표로 구분)",
        value=default_tickers,
    )

    ticker_list = [t.strip().upper() for t in user_tickers.split(",") if t.strip()]

    if ticker_list:
        squeeze_df = load_short_squeeze_data(user_tickers.upper())

        # 메인 데이터 테이블
        st.table(squeeze_df)

        # Short Ratio 바 차트
        st.markdown("#### 📊 Short Ratio Comparison")

        chart_df = squeeze_df[squeeze_df["Short Ratio"] != "N/A"].copy()
        if not chart_df.empty:
            chart_df["Short Ratio"] = pd.to_numeric(chart_df["Short Ratio"], errors="coerce")
            chart_df = chart_df.dropna(subset=["Short Ratio"])

            if not chart_df.empty:
                max_ratio_row = chart_df.loc[chart_df["Short Ratio"].idxmax()]
                st.markdown(
                    f"""
                    <div style='background-color: #1a1f2e; padding: 15px; border-radius: 8px; border-left: 4px solid #ff4444; margin-bottom: 20px;'>
                        <strong>⚠️ Short Squeeze Alert:</strong> 가장 위험이 높은 종목은 <b>{max_ratio_row['Ticker']}</b> (Short Ratio: {max_ratio_row['Short Ratio']}) 입니다.<br>
                        <span style='color: #8892a4; font-size: 0.9rem;'>* 일반적으로 Short Ratio가 10 이상이면 숏 스퀴즈 가능성이 매우 높고, 5~10 사이면 주의가 필요합니다.</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                fig_bar = px.bar(
                    chart_df.sort_values("Short Ratio", ascending=True),
                    x="Short Ratio",
                    y="Ticker",
                    orientation="h",
                    color="Short Ratio",
                    color_continuous_scale="Reds",
                )
                fig_bar.update_layout(
                    plot_bgcolor="#0e1117",
                    paper_bgcolor="#0e1117",
                    font=dict(color="#c0c8d8"),
                    xaxis=dict(gridcolor="#1e2538"),
                    yaxis=dict(gridcolor="#1e2538"),
                    height=350,
                    margin=dict(l=20, r=20, t=20, b=20),
                    showlegend=False,
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Short Ratio 데이터를 차트로 표시할 수 없습니다.")
        else:
            st.info("Short Ratio 데이터를 차트로 표시할 수 없습니다.")
    else:
        st.warning("분석할 티커를 하나 이상 입력해 주세요.")


elif menu == "M6 Correlation":
    # -------------------------------------------------------------------
    # M6 Correlation 탭: 자산 간 상관관계 히트맵 (데모)
    # -------------------------------------------------------------------
    st.markdown("### 🔗 M6 — Cross-Asset Correlation Matrix")
    st.markdown(
        "<p style='color: #6b7688;'>주요 자산 간 가격 상관관계를 시각화합니다. "
        "상관계수가 1에 가까울수록 동조화, -1에 가까울수록 역상관관계를 나타냅니다.</p>",
        unsafe_allow_html=True,
    )

    # 실제 자산 상관관계 (yfinance)
    assets = ["SPY", "QQQ", "GLD", "TLT", "BNO", "BTC-USD"]
    corr_df = load_correlation_data(assets)

    if corr_df.empty:
        st.error("상관관계 데이터를 불러오는 데 실패했습니다.")
    else:
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=corr_df.values,
            x=corr_df.columns.tolist(),
            y=corr_df.index.tolist(),
            colorscale="RdBu_r",
            zmin=-1,
            zmax=1,
            text=corr_df.values.round(2),
            texttemplate="%{text}",
            textfont=dict(size=14, color="#ffffff"),
            hovertemplate="<b>%{x}</b> vs <b>%{y}</b><br>Correlation: %{z:.2f}<extra></extra>",
        ))

        fig_heatmap.update_layout(
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font=dict(color="#c0c8d8", size=13),
            xaxis=dict(side="bottom"),
            height=500,
            margin=dict(l=20, r=20, t=20, b=20),
        )

        st.plotly_chart(fig_heatmap, use_container_width=True)


elif menu == "M8 Inst. Flow":
    # -------------------------------------------------------------------
    # M8 Inst. Flow 탭: 기관 자금 흐름 (데모)
    # -------------------------------------------------------------------
    st.markdown("### 🏦 M8 — Institutional Money Flow")
    st.markdown(
        "<p style='color: #6b7688;'>기관 투자자의 자금 흐름을 추적합니다. "
        "양수는 순유입, 음수는 순유출을 나타냅니다.</p>",
        unsafe_allow_html=True,
    )

    # 실제 기관 자금 흐름 프록시 (yfinance의 가격/거래량 기반)
    flow_tickers = ["SPY", "QQQ", "IWM", "DIA", "XLF", "XLK", "XLE", "XLV"]
    
    with st.spinner("Fetching Money Flow Data..."):
        flow_df = load_money_flow_data(flow_tickers)
    
    if flow_df.empty:
        st.error("자금 흐름 데이터를 불러오는 데 실패했습니다.")
    else:
        # 최근 30일(1mo) 순유입/유출 요약
        latest_flow = flow_df.groupby("ETF")["Net Flow ($M)"].sum().reset_index()
        latest_flow.columns = ["ETF", "30D Net Flow ($M)"]
        latest_flow = latest_flow.sort_values("30D Net Flow ($M)", ascending=False)
    
        col_left, col_right = st.columns(2)
    
        with col_left:
            st.markdown("#### 💰 30-Day Net Flow Summary")
            fig_flow = px.bar(
                latest_flow,
                x="ETF",
                y="30D Net Flow ($M)",
                color="30D Net Flow ($M)",
                color_continuous_scale=["#ff4444", "#ffaa00", "#00d4aa"],
                color_continuous_midpoint=0,
            )
            fig_flow.update_layout(
                plot_bgcolor="#0e1117",
                paper_bgcolor="#0e1117",
                font=dict(color="#c0c8d8"),
                xaxis=dict(gridcolor="#1e2538"),
                yaxis=dict(gridcolor="#1e2538"),
                height=400,
                margin=dict(l=20, r=20, t=20, b=20),
                showlegend=False,
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_flow, use_container_width=True)
    
        with col_right:
            st.markdown("#### 📈 Cumulative Flow Trend (SPY)")
            spy_flow = flow_df[flow_df["ETF"] == "SPY"].copy()
            spy_flow["Cumulative Flow ($M)"] = spy_flow["Net Flow ($M)"].cumsum()
    
            fig_line = px.area(
                spy_flow,
                x="Date",
                y="Cumulative Flow ($M)",
                color_discrete_sequence=["#00d4aa"],
            )
            fig_line.update_layout(
                plot_bgcolor="#0e1117",
                paper_bgcolor="#0e1117",
                font=dict(color="#c0c8d8"),
                xaxis=dict(gridcolor="#1e2538"),
                yaxis=dict(gridcolor="#1e2538"),
                height=400,
                margin=dict(l=20, r=20, t=20, b=20),
            )
            st.plotly_chart(fig_line, use_container_width=True)

    st.info(
        "📌 참고: 실제 기관 자금 흐름(13F 등)은 실시간 제공이 어려워, "
        "yfinance를 이용해 거래량과 가격 변동폭을 곱한 **Money Flow Proxy**로 대체 산출했습니다."
    )


elif menu == "Insider Trading":
    # -------------------------------------------------------------------
    # Insider Trading 탭: 내부자 순매수/해석 (새 기능)
    # -------------------------------------------------------------------
    st.markdown("### 🕵️ Insider Trading Tracker")
    st.markdown(
        "<p style='color: #6b7688;'>해당 기업의 경영진 또는 내부자들의 최근 주식 매수/매도 현황을 분석합니다. "
        "내부자의 대규모 순매수는 강력한 주가 상승 시그널이 될 수 있습니다.</p>",
        unsafe_allow_html=True,
    )

    insider_ticker = st.text_input("분석할 티커 입력", value="AAPL")
    
    if insider_ticker:
        insider_ticker = insider_ticker.strip().upper()
        with st.spinner(f"Fetching Insider Trading data for {insider_ticker}..."):
            insider_df = load_insider_data(insider_ticker)
            
        if insider_df.empty:
            st.warning(f"{insider_ticker}의 최근 내부자 거래 데이터가 없거나 수집할 수 없습니다.")
        else:
            # yfinance insider_transactions 컬럼 정리 (예: Start Date, Shares, Text)
            st.markdown(f"#### recent transactions for {insider_ticker}")
            st.dataframe(insider_df)
            
            # 주식 거래량(Shares) 숫자형 변환 후 매수/매도 필터링
            if "Shares" in insider_df.columns:
                insider_df["Shares_Num"] = pd.to_numeric(insider_df["Shares"], errors="coerce").fillna(0)
                
                # yfinance 데이터 특성상, 양수는 매수, 음수는 매도 (형식이 다를 수 있어 유의)
                buys = insider_df[insider_df["Shares_Num"] > 0]
                sells = insider_df[insider_df["Shares_Num"] < 0]
                
                total_buy = buys["Shares_Num"].sum()
                total_sell = abs(sells["Shares_Num"].sum())
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(
                        f"""
                        <div style='background-color: #0d3320; padding: 15px; border-radius: 8px; border-left: 4px solid #00d4aa; text-align: center;'>
                            <h5 style='margin:0; color:#00d4aa;'>🟢 Total Insider Buy Shares</h5>
                            <h2 style='margin:0; color:#fff;'>{total_buy:,.0f}</h2>
                        </div>
                        """, unsafe_allow_html=True
                    )
                with col2:
                    st.markdown(
                        f"""
                        <div style='background-color: #3d0a0a; padding: 15px; border-radius: 8px; border-left: 4px solid #ff4444; text-align: center;'>
                            <h5 style='margin:0; color:#ff4444;'>🔴 Total Insider Sell Shares</h5>
                            <h2 style='margin:0; color:#fff;'>{total_sell:,.0f}</h2>
                        </div>
                        """, unsafe_allow_html=True
                    )
            else:
                st.info("거래량(Shares) 정보를 분석할 수 없습니다.")


# ===========================================================================
# 디버그 패널 (Debug Mode ON일 때만 표시)
# ===========================================================================
    st.markdown("---")
    st.markdown("### 🔧 Debug Panel")

    with st.expander("Raw Macro Data"):
        st.json(macro_data)

    with st.expander("AI Advisor Content"):
        st.write(ai_advice)

    with st.expander("System Info"):
        st.code(f"""
Streamlit Version: {st.__version__}
Python Running: OK
Cache TTL: 3600s (1 hour)
Auto Refresh: {auto_refresh}
Current Menu: {menu}
        """)


# ===========================================================================
# 풋터
# ===========================================================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #4a5268; padding: 20px 0;'>
        <p style='margin-bottom: 4px;'>🚀 AI Trading Dashboard v1.0</p>
        <p style='font-size: 0.8rem;'>Data provided by Yahoo Finance via yfinance | 
        Built with Streamlit & Plotly</p>
    </div>
    """,
    unsafe_allow_html=True,
)
