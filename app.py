import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from google import genai
from google.genai import types
import re
import traceback
import math
from datetime import date, timedelta, datetime
import requests
import json
import uuid
from pathlib import Path
import matplotlib.pyplot as plt

# ─────────────────────────────────────────────
# 전략 저장소 (JSON)
# ─────────────────────────────────────────────
STRATEGIES_FILE = Path(__file__).parent / "strategies.json"


def load_strategies() -> list:
    """저장된 전략 목록을 JSON 파일에서 불러옵니다."""
    if STRATEGIES_FILE.exists():
        try:
            return json.loads(STRATEGIES_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_strategies(strategies: list):
    """전략 목록을 JSON 파일에 저장합니다."""
    STRATEGIES_FILE.write_text(
        json.dumps(strategies, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_strategy(name: str, memo: str, code: str, strat_type: str,
                 strategy_text: str = "") -> None:
    """전략 1개를 strategies.json에 추가합니다."""
    strategies = load_strategies()
    strategies.append({
        "id": str(uuid.uuid4()),
        "name": name,
        "memo": memo,
        "type": strat_type,        # 'single' | 'portfolio'
        "code": code,
        "strategy_text": strategy_text,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    save_strategies(strategies)


def delete_strategy(strategy_id: str) -> None:
    """ID로 전략 1개를 strategies.json에서 삭제합니다."""
    strategies = load_strategies()
    strategies = [s for s in strategies if s["id"] != strategy_id]
    save_strategies(strategies)


# ─────────────────────────────────────────────
# FRED 지표 카탈로그
# ─────────────────────────────────────────────
FRED_INDICATORS = {
    "경기 사이클": {
        "USSLIND": "미국 경기선행지수 (US Leading Economic Index)",
        "USALOLITONOSTSAM": "OECD 경기선행지수",
        "NAPM": "ISM 제조업 구매관리자지수 (PMI)",
        "NMFCI": "시카고 연은 금융환경지수 (NFCI)"
    },
    "금리 및 스프레드": {
        "DFF": "미국 기준금리 (Fed Funds Rate)",
        "T10Y2Y": "장단기 금리차 (10년 - 2년)",
        "DGS10": "미국 10년물 국채 금리",
        "BAMLH0A0HYM2": "하이일드 채권 스프레드"
    },
    "물가 / 인플레이션": {
        "CPIAUCSL": "소비자물가지수 (CPI)",
        "CPILFESL": "근원 소비자물가지수 (Core CPI)",
        "PCEPI": "개인소비지출 (PCE)",
        "T10YIE": "10년 기대인플레이션"
    },
    "고용 시장": {
        "PAYEMS": "비농업 고용자수 (Nonfarm Payrolls)",
        "UNRATE": "실업률 (Unemployment Rate)",
        "ICSA": "신규 실업수당 청구건수"
    },
    "통화량 및 실물경기": {
        "M2SL": "M2 통화량",
        "WALCL": "연준 총 자산규모",
        "RSXFS": "미국 소매판매액"
    }
}


# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Quant-Tester",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

TRANSACTION_COST = 0.002  # 0.2% per trade side

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Roboto:wght@300;400;500&display=swap');

/* ── Google 색상 팔레트 ──────────────────────
   Blue  #4285F4 · Red   #EA4335
   Yellow#FBBC05 · Green #34A853
   ──────────────────────────────────────────── */

html, body, [class*="css"] {
    font-family: 'Roboto', 'Google Sans', sans-serif;
}

/* 전체 배경 */
.stApp {
    background: #f8f9fa;
    min-height: 100vh;
}

/* 사이드바 */
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e8eaed;
    box-shadow: 2px 0 8px rgba(0,0,0,0.04);
}
[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stNumberInput > div > div > input,
[data-testid="stSidebar"] .stDateInput > div > div > input {
    background: #f8f9fa;
    border: 1px solid #dadce0;
    color: #202124;
    border-radius: 8px;
    font-size: 0.9rem;
}
[data-testid="stSidebar"] .stTextInput > div > div > input:focus,
[data-testid="stSidebar"] .stNumberInput > div > div > input:focus {
    border-color: #4285F4 !important;
    box-shadow: 0 0 0 2px rgba(66,133,244,0.15) !important;
}
[data-testid="stSidebar"] label {
    color: #5f6368 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
}

/* 히어로 헤더 */
.hero-header {
    background: #ffffff;
    border: none;
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 24px;
    box-shadow: 0 1px 3px rgba(60,64,67,0.1), 0 4px 12px rgba(60,64,67,0.06);
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, #4285F4 25%, #EA4335 25% 50%, #FBBC05 50% 75%, #34A853 75%);
}
.hero-title {
    font-size: 2rem; font-weight: 700;
    color: #202124;
    margin: 8px 0 6px 0;
    font-family: 'Google Sans', 'Roboto', sans-serif;
    letter-spacing: -0.5px;
}
.hero-sub {
    color: #5f6368;
    font-size: 0.95rem;
    margin: 0;
}

/* 텍스트 에어리어 */
.stTextArea > div > div > textarea {
    background: #ffffff !important;
    border: 1px solid #dadce0 !important;
    color: #202124 !important;
    border-radius: 12px !important;
    font-family: 'Roboto', sans-serif !important;
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.stTextArea > div > div > textarea:focus {
    border-color: #4285F4 !important;
    box-shadow: 0 0 0 2px rgba(66,133,244,0.15) !important;
}

/* 버튼 — Google Blue */
.stButton > button {
    background: #4285F4 !important;
    color: white !important;
    border: none !important;
    border-radius: 24px !important;
    padding: 12px 32px !important;
    font-weight: 500 !important;
    font-size: 0.95rem !important;
    width: 100% !important;
    letter-spacing: 0.25px !important;
    box-shadow: 0 1px 3px rgba(66,133,244,0.3), 0 4px 8px rgba(66,133,244,0.15) !important;
    transition: all 0.2s ease !important;
    font-family: 'Google Sans', 'Roboto', sans-serif !important;
}
.stButton > button:hover {
    background: #1a73e8 !important;
    box-shadow: 0 2px 6px rgba(26,115,232,0.4), 0 6px 16px rgba(26,115,232,0.2) !important;
    transform: translateY(-1px) !important;
}

/* 메트릭 카드 */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e8eaed;
    border-radius: 12px;
    padding: 20px !important;
    box-shadow: 0 1px 3px rgba(60,64,67,0.08);
    transition: box-shadow 0.2s ease, border-color 0.2s ease;
}
[data-testid="stMetric"]:hover {
    box-shadow: 0 2px 8px rgba(60,64,67,0.15);
    border-color: #4285F4;
}
[data-testid="stMetricLabel"] {
    color: #5f6368 !important;
    font-size: 0.76rem !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 500 !important;
}
[data-testid="stMetricValue"] {
    color: #202124 !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricDelta"] { font-size: 0.82rem !important; }
[data-testid="stMetricDelta"] > div[data-testid="stMetricDeltaIcon-Up"] { color: #34A853 !important; }
[data-testid="stMetricDelta"] > div[data-testid="stMetricDeltaIcon-Down"] { color: #EA4335 !important; }

/* 섹션 제목 */
.section-title {
    color: #5f6368;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin: 20px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 2px solid #4285F4;
    display: inline-block;
}

/* 수수료 뱃지 */
.cost-badge {
    background: #fef7e0;
    border: 1px solid #FBBC05;
    border-radius: 8px;
    padding: 8px 12px;
    color: #b37600;
    font-size: 0.82rem;
    font-weight: 500;
    margin-top: 8px;
}

/* Expander */
.stExpander {
    background: #ffffff !important;
    border: 1px solid #e8eaed !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 3px rgba(60,64,67,0.06) !important;
}

/* 성공/에러 알림 */
.stSuccess { border-left: 4px solid #34A853 !important; background: #e6f4ea !important; }
.stError   { border-left: 4px solid #EA4335 !important; background: #fce8e6 !important; }
.stInfo    { border-left: 4px solid #4285F4 !important; background: #e8f0fe !important; }
.stWarning { border-left: 4px solid #FBBC05 !important; background: #fef7e0 !important; }

/* 사이드바 브랜드 */
.sidebar-brand {
    text-align: center;
    padding: 14px 0 20px 0;
    border-bottom: 1px solid #e8eaed;
    margin-bottom: 18px;
}
.sidebar-brand-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #202124;
    font-family: 'Google Sans', sans-serif;
    letter-spacing: -0.3px;
}
.sidebar-brand-title span.g-b { color: #4285F4; }
.sidebar-brand-title span.g-r { color: #EA4335; }
.sidebar-brand-title span.g-y { color: #FBBC05; }
.sidebar-brand-title span.g-g { color: #34A853; }
.sidebar-brand-sub { font-size: 0.7rem; color: #9aa0a6; margin-top: 3px; }

/* 탭 스타일 */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 2px solid #e8eaed;
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    color: #5f6368 !important;
    font-weight: 500;
    padding: 12px 24px;
    border-radius: 0;
    font-size: 0.9rem;
}
.stTabs [aria-selected="true"] {
    color: #4285F4 !important;
    border-bottom: 2px solid #4285F4;
    background: transparent !important;
}

/* 데이터프레임 */
.stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid #e8eaed; }

/* 일반 텍스트 */
p, li, span { color: #3c4043; }
h1, h2, h3 { color: #202124; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 시스템 프롬프트
# ─────────────────────────────────────────────
SYSTEM_SINGLE = """
너는 파이썬 기반의 전문 퀀트 투자 개발자야.
사용자가 자연어로 투자 전략을 설명하면, 이를 실행 가능한 pandas 백테스트 코드로 변환해.

[환경]
- `df`: pandas DataFrame (인덱스=날짜, 컬럼=['Open','High','Low','Close','Adj Close','Volume'])
- 데이터 다운로드 코드 작성 금지. 오직 pandas, numpy만 사용.

[출력 컬럼 (필수)]
- df['Signal']: 매수=1, 관망=0
- df['Position']: 반드시 df['Signal'].shift(1) 사용 (Look-ahead Bias 방지)
- df['Strategy_Return']: df['Adj Close'].pct_change() * df['Position']
- df['Cumulative_Return']: (1 + df['Strategy_Return']).cumprod()

[출력 형식]
- 오직 ```python ... ``` 코드 블록만 출력. 설명 없음. print/plt.show 금지.
""".strip()

SYSTEM_PORTFOLIO = """
너는 파이썬 기반의 전문 포트폴리오 퀀트 투자 개발자야.
사용자가 자연어로 종목 선택 전략을 설명하면, 이를 pandas 코드로 변환해.

[환경 - 이미 정의된 변수들]
- prices_df: DataFrame (인덱스=날짜, 컬럼=종목코드, 값=Adj Close 수정주가)
- returns_df: DataFrame (prices_df.pct_change() 일간 수익률)
- rebal_dates: pd.DatetimeIndex (리밸런싱 날짜 목록)
- n_stocks: int (매 리밸런싱 시 보유할 종목 수)
- 데이터 다운로드/import 코드 작성 금지. 오직 pandas, numpy만 사용.

[출력 - 필수 생성 변수]
holdings_df: DataFrame
  - index = rebal_dates
  - columns = prices_df.columns (종목코드)
  - values = 1 (보유) 또는 0 (미보유)
  - 각 행에서 1의 합계 == n_stocks (정확히)

[Look-ahead Bias 방지 - 매우 중요]
각 rebal_date에서 반드시 해당 날짜 이전 데이터만 사용:
  prices_df.loc[:rebal_date] 또는 returns_df.loc[:rebal_date]

[출력 형식]
- 오직 ```python ... ``` 코드 블록만 출력. 설명 없음. print/plt.show 금지.
""".strip()


# ── 하드코딩 폴백 (Wikipedia 접근 불가 시 사용) ────────────────────────
_NASDAQ100 = sorted([
    "AAPL","ABNB","ADBE","ADI","ADP","ADSK","AEP","AMAT","AMD","AMGN",
    "AMZN","ANSS","ARM","ASML","AVGO","AXON","AZN","BIIB","BKR","CCEP",
    "CDNS","CDW","CEG","CHTR","CMCSA","COST","CPRT","CRWD","CSCO","CSGP",
    "CSX","CTAS","CTSH","DDOG","DLTR","DXCM","EA","EXC","FANG","FAST",
    "FTNT","GEHC","GFS","GILD","GOOG","GOOGL","HON","IDXX","ILMN","INTC",
    "INTU","ISRG","KDP","KHC","KLAC","LIN","LRCX","LULU","MAR","MCHP",
    "MDB","MDLZ","META","MNST","MRNA","MRVL","MSFT","MU","NFLX","NVDA",
    "NXPI","ODFL","ON","ORLY","PANW","PAYX","PCAR","PDD","PEP","PYPL",
    "QCOM","REGN","ROP","ROST","SBUX","SIRI","SMCI","SNPS","SPLK","TEAM",
    "TMUS","TSLA","TTD","TTWO","TXN","VRSK","VRTX","WBA","WBD","WDAY",
    "XEL","ZS",
])

_SP500_SAMPLE = sorted([
    "A","AAL","AAP","AAPL","ABBV","ABC","ABMD","ABT","ACN","ADBE","ADI","ADM",
    "ADP","ADSK","AEE","AEP","AES","AFL","AIG","AIZ","AJG","AKAM","ALB","ALGN",
    "ALL","ALLE","AMAT","AMCR","AMD","AME","AMGN","AMP","AMT","AMZN","ANET",
    "ANSS","AON","AOS","APD","APH","APTV","ARE","ATO","AVB","AVGO","AVY","AWK",
    "AXP","AZO","BA","BAC","BALL","BAX","BBWI","BBY","BDX","BEN","BF-B","BIIB",
    "BIO","BK","BKNG","BKR","BLK","BMY","BR","BRK-B","BRO","BSX","BWA","BXP",
    "C","CAG","CAH","CARR","CAT","CB","CBOE","CBRE","CCI","CCL","CDNS","CDW",
    "CE","CEG","CF","CFG","CHD","CHRW","CHTR","CI","CINF","CL","CLX","CMA","CMCSA",
    "CME","CMG","CMI","CMS","CNC","CNP","COF","COO","COP","COST","CPB","CPRT",
    "CPT","CRL","CRM","CSCO","CSGP","CSX","CTAS","CTLT","CTSH","CTVA","CVS","CVX",
    "D","DAL","DAY","DD","DE","DECK","DFS","DG","DGX","DHI","DHR","DIS","DLTR",
    "DOC","DOV","DOW","DPZ","DRI","DTE","DUK","DVA","DVN","DXC","DXCM",
    "EA","EBAY","ECL","ED","EFX","EG","EIX","EL","ELV","EMN","EMR","ENPH",
    "EOG","EPAM","EQIX","EQR","EQT","ES","ESS","ETN","ETR","EVRG","EW","EXC","EXPD","EXPE",
    "F","FANG","FAST","FCX","FDS","FDX","FE","FFIV","FI","FICO","FIS","FITB",
    "FLT","FMC","FOX","FOXA","FRT","FSLR","FTNT","FTV",
    "GD","GE","GEHC","GEN","GEV","GILD","GIS","GL","GLW","GM","GNRC","GOOG","GOOGL",
    "GPC","GPN","GRMN","GS","GWW",
    "HAL","HAS","HBAN","HCA","HD","HES","HIG","HII","HLT","HOLX","HON","HPE","HPQ",
    "HRL","HSIC","HST","HSY","HUBB","HUM","HWM",
    "IBM","ICE","IDXX","IEX","IFF","ILMN","INCY","INTC","INTU","INVH","IP","IPG",
    "IQV","IR","IRM","ISRG","IT","ITW","IVZ",
    "J","JBHT","JBL","JCI","JKHY","JNJ","JNPR","JPM",
    "K","KDP","KEY","KEYS","KHC","KIM","KLAC","KMB","KMI","KMX","KO","KR",
    "L","LDOS","LEN","LH","LHX","LIN","LKQ","LLY","LMT","LNT","LOW","LRCX","LULU","LUV","LVS","LW","LYB","LYV",
    "MA","MAA","MAR","MAS","MCD","MCHP","MCK","MCO","MDLZ","MDT","MET","META","MGM",
    "MHK","MKC","MKTX","MLM","MMC","MMM","MNST","MO","MOH","MOS","MPC","MPWR","MRK",
    "MRNA","MRO","MS","MSCI","MSFT","MSI","MTB","MTCH","MTD","MU","NCLH","NDAQ",
    "NEE","NEM","NFLX","NI","NKE","NOC","NOW","NRG","NSC","NTAP","NTRS","NUE","NVDA","NVR","NWS","NWSA",
    "O","ODFL","OKE","OMC","ON","ORCL","ORLY","OXY",
    "PANW","PARA","PAYC","PAYX","PCAR","PCG","PEG","PEP","PFE","PFG","PG","PGR",
    "PH","PHM","PKG","PLD","PM","PNC","PNR","PNW","PODD","POOL","PPG","PPL",
    "PRU","PSA","PSX","PTC","PWR","PXD","PYPL",
    "QCOM","QRVO",
    "RCL","REG","REGN","RF","RJF","RL","RMD","ROK","ROL","ROP","ROST","RSG","RTX",
    "SBAC","SBUX","SCHW","SEDG","SEE","SHW","SJM","SLB","SNA","SNPS","SO","SPG",
    "SPGI","SRE","STE","STLD","STT","STX","STZ","SWK","SWKS","SYF","SYK","SYY",
    "T","TAP","TDG","TDY","TECH","TEL","TER","TFC","TFX","TGT","TJX","TMO","TMUS",
    "TPR","TRGP","TRMB","TROW","TRV","TSCO","TSLA","TSN","TT","TTWO","TXN","TXT","TYL",
    "UAL","UDR","UHS","ULTA","UNH","UNP","UPS","URI","USB",
    "V","VFC","VICI","VLO","VLTO","VMC","VRSK","VRSN","VRTX","VTR","VTRS",
    "WAB","WAT","WBA","WBD","WDC","WEC","WELL","WFC","WHR","WM","WMB","WMT",
    "WRB","WST","WTW","WY",
    "XEL","XOM","XYL",
    "YUM",
    "ZBH","ZBRA","ZTS",
])


@st.cache_data(ttl=3600 * 24, show_spinner=False)
def get_universe_tickers(universe: str) -> list:
    """지수 구성종목 티커 수집 (Wikipedia → 실패 시 하드코딩 폴백)"""
    try:
        if universe == "NASDAQ-100":
            tables = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
            for t in tables:
                for col in ["Ticker", "Symbol", "Ticker symbol"]:
                    if col in t.columns:
                        raw = t[col].dropna().astype(str).str.strip().tolist()
                        tickers = [x.replace(".", "-") for x in raw
                                   if (len(x) <= 6 and x.isalpha()) or "-" in x]
                        if len(tickers) > 50:
                            return sorted(tickers)
        elif universe == "S&P 500":
            tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
            raw = tables[0]["Symbol"].dropna().astype(str).str.strip().tolist()
            return sorted([x.replace(".", "-") for x in raw])
    except Exception:
        pass

    # Wikipedia 접근 실패 → 하드코딩 폴백
    if universe == "NASDAQ-100":
        return _NASDAQ100
    else:
        return _SP500_SAMPLE



def get_rebal_dates(price_index: pd.DatetimeIndex, freq: str) -> pd.DatetimeIndex:
    """리밸런싱 날짜 생성 (실제 거래일 기준으로 스냅)"""
    freq_rule = {
        "주간": "W-FRI",
        "월간": "ME",
        "분기": "QE",
        "반기": "QE",   # 분기의 격월 → 아래서 필터
        "연간": "YE",
    }
    dummy = pd.Series(1, index=price_index)
    resampled = dummy.resample(freq_rule[freq]).last().index
    if freq == "반기":
        resampled = resampled[::2]  # 분기 중 격월만 사용

    # 실제 거래일로 스냅 (해당 날짜 이하 가장 가까운 날)
    snapped = []
    for d in resampled:
        past = price_index[price_index <= d]
        if len(past) > 0:
            snapped.append(past[-1])
    return pd.DatetimeIndex(sorted(set(snapped)))


# ─────────────────────────────────────────────
# 데이터 다운로드 (yfinance + FRED)
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600 * 24, show_spinner=False)
def fetch_fred_data(series_id: str, api_key: str, start_date: str = "2000-01-01") -> pd.Series:
    """FRED API에서 특정 시리즈의 시계열 데이터를 가져옵니다."""
    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start_date,
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "observations" not in data:
            return pd.Series(dtype=float)
            
        obs = data["observations"]
        # "." 으로 표시되는 결측치 필터링
        df = pd.DataFrame([{"date": pd.to_datetime(d["date"]), "value": float(d["value"])} 
                          for d in obs if d["value"] != "."])
        if df.empty:
            return pd.Series(dtype=float)
            
        df.set_index("date", inplace=True)
        return df["value"]
        
    except Exception as e:
        return pd.Series(dtype=float) # 에러는 UI에서 처리


@st.cache_data(show_spinner=False)
def download_single(ticker: str, start: str, end: str) -> pd.DataFrame:
    """단일 종목 다운로드 (최신 yfinance 멀티인덱스 호환)"""
    try:
        df = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        lvl0 = set(df.columns.get_level_values(0))
        price_fields = {"Adj Close", "Close", "Open", "High", "Low", "Volume"}
        df.columns = df.columns.get_level_values(0) if lvl0 & price_fields else df.columns.get_level_values(1)
    df.columns = [str(c).strip() for c in df.columns]
    if "Adj Close" not in df.columns:
        if "Close" in df.columns:
            df["Adj Close"] = df["Close"]
        else:
            return pd.DataFrame()
    return df.dropna(subset=["Adj Close"])


@st.cache_data(ttl=3600 * 12, show_spinner=False)
def download_universe(tickers_csv: str, start: str, end: str):
    """
    유니버스 전체 배치 다운로드.
    tickers_csv: 캐시 키용 (콤마 구분 정렬 문자열)
    반환: (prices_df, returns_df) or (None, None)
    """
    tickers = tickers_csv.split(",")
    try:
        raw = yf.download(tickers, start=start, end=end, auto_adjust=False,
                          progress=False, group_by="ticker")
    except Exception:
        return None, None
    if raw is None or raw.empty:
        return None, None

    # MultiIndex (ticker, price) → Adj Close pivot 추출
    if isinstance(raw.columns, pd.MultiIndex):
        try:
            prices_df = raw.xs("Adj Close", axis=1, level=1)
        except KeyError:
            try:
                prices_df = raw.xs("Close", axis=1, level=1)
            except KeyError:
                return None, None
    else:
        # 단일 티커 예외처리
        prices_df = raw[["Adj Close"]].rename(columns={"Adj Close": tickers[0]})

    prices_df = prices_df.dropna(axis=1, how="all")         # 완전히 빈 종목 제거
    # 전체 기간의 50% 미만 데이터가 있는 종목 제거 (신규 상장 등)
    min_rows = int(len(prices_df) * 0.5)
    prices_df = prices_df.dropna(axis=1, thresh=min_rows)
    prices_df = prices_df.ffill()                             # 결측 거래일 앞값 채우기
    prices_df = prices_df.dropna(how="all")                  # 모든 컬럼 NaN인 행만 제거
    returns_df = prices_df.pct_change()
    return prices_df, returns_df


# ─────────────────────────────────────────────
# Gemini API (Key 자동 로테이션)
# ─────────────────────────────────────────────
_RATE_LIMIT_SIGNALS = ("429", "Quota", "RESOURCE_EXHAUSTED", "Resource exhausted", "rate limit")


def call_gemini(api_keys_list: list, user_message: str, system_prompt: str) -> str:
    """
    API 키 리스트를 순환하며 Gemini를 호출합니다.
    429 / Quota 오류 발생 시 다음 키로 자동 전환합니다.
    """
    last_error = None
    for idx, key in enumerate(api_keys_list):
        try:
            client = genai.Client(api_key=key.strip())
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=user_message,
                config=types.GenerateContentConfig(system_instruction=system_prompt),
            )
            return response.text
        except Exception as e:
            last_error = e
            err_str = str(e)
            is_rate_limit = any(sig in err_str for sig in _RATE_LIMIT_SIGNALS)
            if is_rate_limit and idx < len(api_keys_list) - 1:
                # Rate Limit → 다음 키로 전환
                continue
            # 그 외 오류이거나 마지막 키면 루프 종료
            break
    raise last_error


def extract_code(text: str) -> str:
    matches = re.findall(r"```python\s*([\s\S]*?)```", text)
    return "\n\n".join(matches).strip() if matches else text.strip()


def _clean_code(code: str) -> str:
    """
    Gemini에서 import문이 생성되는 경우 자동 제거.
    pd, np, math는 샌드박스에 이미 주입되어 있음.
    """
    cleaned = []
    for line in code.split("\n"):
        s = line.strip()
        if s.startswith("import ") or (s.startswith("from ") and " import " in s):
            # import문은 주석으로 체인지하고 무시 (필요 모듈은 샌드박스에서 직접 주입됨)
            cleaned.append(f"# [auto-removed] {line}")
        else:
            cleaned.append(line)
    return "\n".join(cleaned)


# ─────────────────────────────────────────────
# 코드 실행 (샌드박스)
# ─────────────────────────────────────────────
def _make_sandbox():
    return {
        "__builtins__": {
            # 기본 빌트인
            "abs": abs, "all": all, "any": any, "bool": bool,
            "dict": dict, "enumerate": enumerate, "float": float,
            "int": int, "isinstance": isinstance, "len": len,
            "list": list, "map": map, "max": max, "min": min,
            "print": print, "range": range, "round": round,
            "set": set, "sorted": sorted, "str": str, "sum": sum,
            "tuple": tuple, "type": type, "zip": zip,
            # Gemini가 import문을 사용할 경우 대비 (±안전: _clean_code가 제거하지만 알승이 대비)
            "__import__": __import__,
        },
        "pd": pd,
        "np": np,
        "math": math,
    }


def run_single_code(df: pd.DataFrame, code: str) -> pd.DataFrame:
    code = _clean_code(code)
    local_vars = {"df": df.copy()}
    exec(code, _make_sandbox(), local_vars)
    return local_vars["df"]


def run_portfolio_code(prices_df, returns_df, rebal_dates, n_stocks, code, macro_df=None) -> pd.DataFrame:
    code = _clean_code(code)

    # macro_df를 안전한 래퍼로 감싸 (없는 콜럼 접근 시 빈 Series 반환)
    class _SafeMacro(pd.DataFrame):
        def __missing__(self, key):
            return pd.Series(dtype=float, name=key)

    _macro_safe = None
    if macro_df is not None:
        _macro_safe = _SafeMacro(macro_df)

    local_vars = {
        "prices_df": prices_df.copy(),
        "returns_df": returns_df.copy(),
        "rebal_dates": rebal_dates,
        "n_stocks": n_stocks,
        "macro_df": _macro_safe,
    }
    exec(code, _make_sandbox(), local_vars)
    return local_vars["holdings_df"]


# ─────────────────────────────────────────────
# holdings_df 검증 및 정규화
# ─────────────────────────────────────────────
def normalize_holdings(holdings_df: pd.DataFrame, prices_df: pd.DataFrame,
                        rebal_dates: pd.DatetimeIndex, n_stocks: int) -> pd.DataFrame:
    """각 행에서 정확히 n_stocks 종목만 선택되도록 정규화"""
    valid_cols = [c for c in holdings_df.columns if c in prices_df.columns]
    result = pd.DataFrame(0, index=rebal_dates, columns=prices_df.columns)
    for d in rebal_dates:
        if d not in holdings_df.index:
            continue
        row = holdings_df.loc[d, valid_cols].fillna(0)
        top_n = row.nlargest(n_stocks).index
        result.loc[d, top_n] = 1
    return result


# ─────────────────────────────────────────────
# 포트폴리오 수익률 계산 (수수료 포함)
# ─────────────────────────────────────────────
def calc_portfolio_returns(prices_df: pd.DataFrame, holdings_df: pd.DataFrame,
                            transaction_cost: float = TRANSACTION_COST) -> pd.Series:
    daily_ret = prices_df.pct_change()
    sorted_rebal = holdings_df.index.sort_values()
    portfolio_daily = pd.Series(0.0, index=daily_ret.index)

    for i, rebal_date in enumerate(sorted_rebal):
        end_date = (sorted_rebal[i + 1] if i + 1 < len(sorted_rebal)
                    else daily_ret.index[-1] + pd.Timedelta(days=1))

        row = holdings_df.loc[rebal_date]
        held = [t for t in row[row == 1].index if t in daily_ret.columns]
        if not held:
            continue
        n = len(held)

        # 수수료 계산
        if i == 0:
            cost = transaction_cost  # 최초 매수
        else:
            prev_row = holdings_df.loc[sorted_rebal[i - 1]]
            prev_held = set(prev_row[prev_row == 1].index)
            curr_held = set(held)
            bought = len(curr_held - prev_held)
            sold = len(prev_held - curr_held)
            # 변경된 종목 비율 × 0.2% (매수측 + 매도측)
            cost = (bought + sold) / n * transaction_cost

        # 기간 수익률 계산
        period_mask = (daily_ret.index >= rebal_date) & (daily_ret.index < end_date)
        if not period_mask.any():
            continue

        period_rets = daily_ret.loc[period_mask, held].mean(axis=1)
        portfolio_daily.loc[period_mask] = period_rets.values

        # 첫날 수수료 차감
        first_day = daily_ret.index[period_mask][0]
        portfolio_daily[first_day] -= cost

    return portfolio_daily


# ─────────────────────────────────────────────
# 성과 지표 계산 (공통)
# ─────────────────────────────────────────────
def calc_metrics(daily_returns: pd.Series, bnh_series: pd.Series,
                 initial_capital: float) -> dict:
    daily_returns = daily_returns.dropna()
    cum = (1 + daily_returns).cumprod()
    if cum.empty or len(cum) < 2:
        return None

    n_days = (cum.index[-1] - cum.index[0]).days
    n_years = max(n_days / 365.25, 0.01)

    total_return = cum.iloc[-1] - 1
    cagr = cum.iloc[-1] ** (1 / n_years) - 1

    roll_max = cum.cummax()
    drawdown = (cum - roll_max) / roll_max
    mdd = drawdown.min()

    trade_rets = daily_returns[daily_returns != 0]
    win_rate = (trade_rets > 0).sum() / len(trade_rets) if len(trade_rets) > 0 else 0
    sharpe = (daily_returns.mean() / daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0

    final_value = initial_capital * cum.iloc[-1]

    n_years_bnh = max((bnh_series.index[-1] - bnh_series.index[0]).days / 365.25, 0.01)
    bnh_cagr = bnh_series.iloc[-1] ** (1 / n_years_bnh) - 1

    return {
        "cagr": cagr, "total_return": total_return, "mdd": mdd,
        "win_rate": win_rate, "sharpe": sharpe, "final_value": final_value,
        "bnh_cagr": bnh_cagr, "bnh_total": bnh_series.iloc[-1] - 1,
        "cum_series": cum, "bnh_series": bnh_series,
        "drawdown_series": drawdown, "n_trades": len(trade_rets),
    }


# ─────────────────────────────────────────────
# 차트 생성 (공통)
# ─────────────────────────────────────────────
def build_chart(metrics: dict, label: str) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.68, 0.32], vertical_spacing=0.04,
        subplot_titles=("📈 누적 수익률 비교", "📉 전략 드로우다운"),
    )
    cum = metrics["cum_series"]
    bnh = metrics["bnh_series"]
    dd = metrics["drawdown_series"]

    fig.add_trace(go.Scatter(
        x=cum.index, y=(cum - 1) * 100, name="AI 전략",
        line=dict(color="#63b3ed", width=2.5),
        fill="tozeroy", fillcolor="rgba(99,179,237,0.07)",
        hovertemplate="%{y:.2f}%<extra>AI 전략</extra>",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=bnh.index, y=(bnh - 1) * 100, name=f"Buy & Hold ({label})",
        line=dict(color="#f6c90e", width=1.8, dash="dot"),
        hovertemplate="%{y:.2f}%<extra>Buy & Hold</extra>",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=dd.index, y=dd * 100, name="드로우다운",
        line=dict(color="#fc8181", width=1.5),
        fill="tozeroy", fillcolor="rgba(252,129,129,0.12)",
        hovertemplate="%{y:.2f}%<extra>MDD</extra>",
    ), row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(color="#94a3b8", size=12),
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(gridcolor="rgba(99,179,237,0.08)", ticksuffix="%",
                   tickfont=dict(color="#64748b")),
        yaxis2=dict(gridcolor="rgba(252,129,129,0.08)", ticksuffix="%",
                    tickfont=dict(color="#64748b")),
        xaxis2=dict(tickfont=dict(color="#64748b")),
        hovermode="x unified", height=520, font=dict(family="Inter"),
    )
    fig.update_annotations(font=dict(color="#94a3b8", size=12))
    return fig


def render_metrics(metrics: dict, initial_capital: float):
    """성과 지표 카드 렌더링 (공통)"""
    cagr_val = metrics["cagr"] * 100
    bnh_cagr_val = metrics["bnh_cagr"] * 100

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("CAGR", f"{cagr_val:.2f}%",
                  delta=f"vs B&H {cagr_val - bnh_cagr_val:+.2f}%p")
    with m2:
        st.metric("총 수익률", f"{metrics['total_return'] * 100:.2f}%")
    with m3:
        st.metric("최대 낙폭 (MDD)", f"{metrics['mdd'] * 100:.2f}%")
    with m4:
        st.metric("승률", f"{metrics['win_rate'] * 100:.1f}%")
    with m5:
        st.metric("샤프비율", f"{metrics['sharpe']:.2f}")

    st.markdown("")
    m6, m7, m8, m9 = st.columns(4)
    with m6:
        st.metric("최종 자산", f"${metrics['final_value']:,.0f}")
    with m7:
        st.metric("초기 자본금", f"${initial_capital:,}")
    with m8:
        st.metric("매매 활성일", f"{metrics['n_trades']:,}일")
    with m9:
        st.metric("B&H 총 수익률", f"{metrics['bnh_total'] * 100:.2f}%")


# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="sidebar-brand-title">📈 AI Quant-Tester</div>
        <div class="sidebar-brand-sub">자연어 → 백테스트 플랫폼</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p class="section-title">🔑 API 설정</p>', unsafe_allow_html=True)
    # Streamlit Secrets에서 API 키 자동 로드
    _raw = st.secrets.get("GEMINI_API_KEYS", "")
    api_keys_list = [k.strip() for k in _raw.split(",") if k.strip()]
    if api_keys_list:
        st.success(f"🔑 Gemini API Key **{len(api_keys_list)}개** 로드됨")
    else:
        st.error("⛔ `GEMINI_API_KEYS` 시크릿 설정이 필요합니다.")
        
    fred_api_key = st.text_input("FRED API Key", value=st.secrets.get("FRED_API_KEY", ""),
                                 type="password", placeholder="FRED API 키 입력")

    st.markdown('<p class="section-title">📊 단일 종목 설정</p>', unsafe_allow_html=True)
    ticker = st.text_input("종목 코드 (Ticker)", value="AAPL",
                           placeholder="예: AAPL, TSLA, 005930.KS",
                           help="Yahoo Finance 기준 코드. 한국주식: 종목코드.KS").strip().upper()

    st.markdown('<p class="section-title">🌍 포트폴리오 설정</p>', unsafe_allow_html=True)
    universe = st.selectbox("유니버스", ["NASDAQ-100", "S&P 500"])
    n_stocks = st.slider("보유 종목 수", min_value=5, max_value=50, value=10, step=5)
    rebal_freq = st.selectbox("리밸런싱 주기", ["월간", "분기", "반기", "연간", "주간"])
    st.markdown(
        '<div class="cost-badge">💸 거래 수수료: 0.2% / 편도 적용</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<p class="section-title">📅 공통 설정</p>', unsafe_allow_html=True)
    col_s, col_e = st.columns(2)
    with col_s:
        start_date = st.date_input("시작일",
                                   value=date.today() - timedelta(days=365 * 5),
                                   max_value=date.today() - timedelta(days=30))
    with col_e:
        end_date = st.date_input("종료일", value=date.today(), max_value=date.today())

    initial_capital = st.number_input("초기 자본금 ($)", min_value=1000,
                                      max_value=100_000_000, value=10_000,
                                      step=1000, format="%d")
    st.markdown("---")
    st.markdown("<small style='color:#374151;'>⚠️ 교육 목적 제공. 투자 손실에 대한 책임은 본인에게 있습니다.</small>",
                unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 메인 화면
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
    <h1 class="hero-title">📈 AI Quant-Tester</h1>
    <p class="hero-sub">자연어로 투자 전략을 설명하면, AI가 백테스트 코드를 작성하고 즉시 실행합니다.</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 단일 종목 백테스트", "🌍 포트폴리오 유니버스 백테스트", "🌐 매크로 대시보드", "✍️ 직접 코드 & 전략 저장소"])


# ══════════════════════════════════════════════
# TAB 1 — 단일 종목
# ══════════════════════════════════════════════
with tab1:
    st.markdown('<p class="section-title">💡 투자 전략 입력</p>', unsafe_allow_html=True)

    single_examples = [
        "20일 이동평균선이 60일선을 상향 돌파하면 매수하고, 하향 이탈하면 매도해 줘.",
        "RSI 14일이 30 이하로 과매도 구간 진입 시 매수하고, 70 이상에서 매도해 줘.",
        "주가가 52주 신고가를 갱신하면 매수하고, 20일선 아래로 떨어지면 청산해 줘.",
        "볼린저밴드 하단 터치 시 매수하고, 상단 터치 시 매도해 줘.",
        "MACD 시그널선 골든크로스 발생 시 매수, 데드크로스 시 매도해 줘.",
    ]

    def _on_ex1_change():
        sel = st.session_state["ex1_sel"]
        st.session_state["strat_single"] = "" if sel == "직접 입력하기" else sel

    st.selectbox("예시 전략 불러오기", ["직접 입력하기"] + single_examples,
                 key="ex1_sel", on_change=_on_ex1_change)

    if "strat_single" not in st.session_state:
        st.session_state["strat_single"] = ""

    strategy_single = st.text_area(
        "전략 설명", height=120,
        placeholder="예: 20일 이동평균선이 60일선을 상향 돌파하면 매수하고, 하향 이탈하면 매도해 줘.",
        label_visibility="collapsed", key="strat_single",
    )
    run1 = st.button("🚀  백테스트 실행", key="run1", use_container_width=True)

    if run1:
        errs = []
        if not api_keys_list: errs.append("⛔ **GEMINI_API_KEYS** 시크릿이 설정되지 않았습니다.")
        if not ticker: errs.append("⛔ **종목 코드**를 입력해 주세요.")
        if not strategy_single.strip(): errs.append("⛔ **투자 전략**을 입력해 주세요.")
        if start_date >= end_date: errs.append("⛔ **종료일**이 시작일보다 이후여야 합니다.")
        for e in errs:
            st.error(e)
        if errs:
            st.stop()

        with st.spinner(f"📡 {ticker} 데이터 다운로드 중..."):
            df = download_single(ticker, str(start_date), str(end_date))
        if df is None or df.empty:
            st.error(f"❌ **{ticker}** 데이터를 불러올 수 없습니다. 종목 코드를 확인하세요.")
            st.stop()
        st.success(f"✅ {ticker} 데이터 로드 완료 ({len(df):,}일)")

        with st.spinner("🤖 Gemini가 백테스트 코드를 생성 중..."):
            try:
                raw = call_gemini(api_keys_list, strategy_single, SYSTEM_SINGLE)
                code1 = extract_code(raw)
            except Exception as e:
                st.error(f"❌ Gemini API 오류: {e}")
                st.stop()

        with st.spinner("⚡ 백테스트 실행 중..."):
            try:
                result_df = run_single_code(df, code1)
            except Exception:
                st.error("❌ 코드 실행 오류가 발생했습니다.")
                with st.expander("🔍 오류 상세", expanded=True):
                    st.code(traceback.format_exc(), language="text")
                with st.expander("🤖 생성 코드"):
                    st.code(code1, language="python")
                st.info("💡 오류 메시지를 전략 텍스트 뒤에 붙여넣고 다시 실행하면 AI가 자동 수정합니다.")
                st.stop()

        req = ["Signal", "Position", "Strategy_Return", "Cumulative_Return"]
        missing = [c for c in req if c not in result_df.columns]
        if missing:
            st.error(f"❌ 필수 컬럼 없음: {missing}")
            with st.expander("🤖 생성 코드"):
                st.code(code1, language="python")
            st.stop()

        bnh = (df["Adj Close"] / df["Adj Close"].iloc[0]).dropna()
        metrics = calc_metrics(result_df["Strategy_Return"], bnh, initial_capital)
        if not metrics:
            st.error("❌ 성과 계산 실패 — 매매 신호가 생성되지 않았을 수 있습니다.")
            st.stop()

        st.markdown("---")
        st.markdown("## 📊 백테스트 결과")
        st.markdown('<p class="section-title">🏆 핵심 성과 지표</p>', unsafe_allow_html=True)
        render_metrics(metrics, initial_capital)
        st.markdown('<p class="section-title">📈 성과 차트</p>', unsafe_allow_html=True)
        st.plotly_chart(build_chart(metrics, ticker), use_container_width=True)
        with st.expander("🤖 Gemini 생성 코드 보기"):
            st.code(code1, language="python")
        with st.expander("📋 데이터 미리보기 (최근 10행)"):
            cols = [c for c in ["Adj Close", "Signal", "Position", "Strategy_Return", "Cumulative_Return"]
                    if c in result_df.columns]
            st.dataframe(result_df[cols].tail(10), use_container_width=True)
            
        with st.expander("💾 이 전략 및 코드 저장하기", expanded=False):
            s_name = st.text_input("전략 이름", key="s_save_name")
            s_memo = st.text_input("메모 (선택)", key="s_save_memo")
            if st.button("저장", key="btn_save_single"):
                if s_name:
                    add_strategy(s_name, s_memo, code1, "single", strategy_single)
                    st.success("🎉 전략이 JSON에 저장되었습니다! 탭 4에서 확인하세요.")
                else:
                    st.error("전략 이름을 입력하세요.")


# ══════════════════════════════════════════════
# TAB 2 — 포트폴리오 유니버스
# ══════════════════════════════════════════════
with tab2:
    st.markdown(f"""
    **현재 설정:** `{universe}` 유니버스 · 상위 **{n_stocks}개** 종목 보유 · **{rebal_freq}** 리밸런싱 · 수수료 **0.2%**
    """)

    portfolio_examples = [
        "최근 6개월 수익률(모멘텀)이 가장 높은 상위 {n}개 종목을 선택해줘.",
        "최근 20일 변동성(일간 수익률 표준편차)이 가장 낮은 {n}개 종목을 선택해줘.",
        "최근 1개월 수익률이 플러스이면서, 52주 신고가 대비 낙폭이 가장 작은 {n}개 종목을 선택해줘.",
        "최근 3개월 수익률 상위 50% 종목 중, 최근 1개월 변동성이 가장 낮은 {n}개를 선택해줘.",
        "최근 12개월 수익률에서 최근 1개월 수익률을 뺀 값(12-1 모멘텀)이 가장 높은 {n}개 종목을 선택해줘.",
    ]
    # n_stocks를 실제 숫자로 치환
    port_ex_display = [ex.format(n=n_stocks) for ex in portfolio_examples]

    st.markdown('<p class="section-title">💡 종목 선택 전략 입력</p>', unsafe_allow_html=True)

    def _on_ex2_change():
        sel = st.session_state["ex2_sel"]
        if sel == "직접 입력하기":
            st.session_state["strat_port"] = ""
        else:
            # 선택된 예시를 n_stocks 숫자로 치환하여 textarea에 반영
            idx = port_ex_display.index(sel)
            st.session_state["strat_port"] = portfolio_examples[idx].format(n=n_stocks)

    st.selectbox("예시 전략 불러오기", ["직접 입력하기"] + port_ex_display,
                 key="ex2_sel", on_change=_on_ex2_change)

    if "strat_port" not in st.session_state:
        st.session_state["strat_port"] = ""

    strategy_port = st.text_area(
        "전략 설명 (종목 선택 기준)", height=120,
        placeholder=f"예: 최근 6개월 수익률(모멘텀)이 가장 높은 상위 {n_stocks}개 종목을 매월 말 리밸런싱해줘.",
        label_visibility="collapsed", key="strat_port",
    )

    # 벤치마크 선택
    benchmark_map = {"NASDAQ-100": "QQQ", "S&P 500": "SPY"}
    benchmark_ticker = benchmark_map[universe]

    # ── 매크로 데이터 연동 (옵션) ──
    with st.expander("🌐 매크로 데이터 연동 (FRED) — 선택 사항", expanded=False):
        use_macro = st.checkbox("매크로 데이터를 전략에 활용하기 (macro_df 변수로 주입)", value=False)
        if use_macro:
            if not fred_api_key:
                st.warning("⚠️ 사이드바에 FRED API Key를 먼저 입력하세요.")
            st.markdown("**사용할 FRED 지표 선택:**")
            macro_cat_sel = st.selectbox("카테고리", list(FRED_INDICATORS.keys()), key="tab2_macro_cat")
            avail = FRED_INDICATORS[macro_cat_sel]
            macro_sel_ids = st.multiselect(
                "지표 선택",
                list(avail.keys()),
                format_func=lambda x: f"{x} — {avail[x]}",
                default=list(avail.keys())[:2],
                key="tab2_macro_ids",
            )
            st.caption("선택한 지표들이 `macro_df` DataFrame으로 Gemini 코드 내에서 사용 가능해집니다.")
            st.code("""
# Gemini가 생성하는 코드에서 직접 ↓ 이렇게 사용 가능
if macro_df is not None and 'DFF' in macro_df.columns:
    fed = macro_df['DFF'].loc[:rebal_date].dropna()
    rate_change = fed.diff(3).iloc[-1]  # 3개월 금리 변화량
    regime = 'expansion' if rate_change < 0.25 else 'depression'
            """, language="python")
        else:
            macro_sel_ids = []

    run2 = st.button("🚀  포트폴리오 백테스트 실행", key="run2", use_container_width=True)

    if run2:
        errs = []
        if not api_keys_list: errs.append("⛔ **GEMINI_API_KEYS** 시크릿이 설정되지 않았습니다.")
        if not strategy_port.strip(): errs.append("⛔ **종목 선택 전략**을 입력해 주세요.")
        if start_date >= end_date: errs.append("⛔ **종료일**이 시작일보다 이후여야 합니다.")
        for e in errs:
            st.error(e)
        if errs:
            st.stop()

        # ── Step 1: 티커 목록 수집 ─────────────────
        with st.spinner(f"📋 {universe} 구성 종목 목록 수집 중..."):
            tickers_list = get_universe_tickers(universe)

        if not tickers_list:
            st.error(f"❌ {universe} 티커 목록을 가져올 수 없습니다. 인터넷 연결을 확인하세요.")
            st.stop()
        st.info(f"📋 {universe}: **{len(tickers_list)}개** 종목 확인")

        # ── Step 2: 유니버스 데이터 다운로드 ─────────
        est_time = "약 30~60초" if len(tickers_list) > 200 else "약 10~30초"
        with st.spinner(f"📡 {len(tickers_list)}개 종목 데이터 다운로드 중... ({est_time}, 최초 1회)"):
            tickers_csv = ",".join(sorted(tickers_list))
            prices_df, returns_df = download_universe(tickers_csv, str(start_date), str(end_date))

        if prices_df is None or prices_df.empty:
            st.error("❌ 유니버스 데이터 다운로드에 실패했습니다.")
            st.stop()

        n_downloaded = len(prices_df.columns)
        st.success(f"✅ 데이터 로드 완료: **{n_downloaded}개** 종목, **{len(prices_df):,}일**")

        # ── Step 3: 리밸런싱 날짜 생성 ───────────────
        rebal_dates = get_rebal_dates(prices_df.index, rebal_freq)
        if len(rebal_dates) < 2:
            st.error("❌ 백테스트 기간이 너무 짧습니다. 기간을 늘려주세요.")
            st.stop()
        st.info(f"📅 리밸런싱 횟수: **{len(rebal_dates)}회** ({rebal_freq})")

        # ── Step 3.5: 매크로 데이터 Fetch (연동 체크 시) ──
        macro_df = None
        macro_context = ""
        if use_macro and macro_sel_ids and fred_api_key:
            with st.spinner("🌐 FRED 매크로 지표 로드 중..."):
                _macro_raw = {}
                for sid in macro_sel_ids:
                    s = fetch_fred_data(sid, fred_api_key, start_date=str(start_date))
                    if not s.empty:
                        _macro_raw[sid] = s
                if _macro_raw:
                    macro_df = pd.DataFrame(_macro_raw).ffill().dropna(how="all")
                    _cols = list(macro_df.columns)
                    _desc = ", ".join([
                        f"{k} ({v})"
                        for cat in FRED_INDICATORS.values()
                        for k, v in cat.items() if k in macro_df.columns
                    ])
                    macro_context = (
                        f"\n\n[매크로 데이터 - macro_df 변수로 사용 가능]"
                        f"\n- 젬럼: {_cols}  (이 목록에 없는 콜럼은 절대 접근 금지)"
                        f"\n- 설명: {_desc}"
                        f"\n- 접근 시 반드시: `if 'COL' in macro_df.columns:` 확인 후 사용"
                        f"\n- Look-ahead Bias 방지: macro_df.loc[:rebal_date] 사용"
                    )
                    st.success(f"✅ 매크로 데이터 로드 완료: {_cols}")

        # ── Step 4: Gemini 코드 생성 ─────────────────
        gemini_msg = f"""[전략]
{strategy_port}

[유니버스 정보]
- 유니버스: {universe} (총 {n_downloaded}개 종목)
- 사용 가능 종목 예시: {', '.join(prices_df.columns[:15].tolist())} ... 등
- 보유 종목 수(n_stocks): {n_stocks}
- 리밸런싱 주기: {rebal_freq} (총 {len(rebal_dates)}회)
- 기간: {start_date} ~ {end_date}{macro_context}"""

        with st.spinner("🤖 Gemini가 종목 선택 코드를 생성 중..."):
            try:
                raw2 = call_gemini(api_keys_list, gemini_msg, SYSTEM_PORTFOLIO)
                code2 = extract_code(raw2)
            except Exception as e:
                st.error(f"❌ Gemini API 오류: {e}")
                st.stop()

        # ── Step 5: 코드 실행 → holdings_df 생성 ─────
        with st.spinner("⚡ 종목 선택 로직 실행 중..."):
            try:
                raw_holdings = run_portfolio_code(
                    prices_df, returns_df, rebal_dates, n_stocks, code2,
                    macro_df=macro_df,      # FRED 매크로 데이터 (None이면 미사용)
                )
                holdings_df = normalize_holdings(raw_holdings, prices_df, rebal_dates, n_stocks)
            except Exception:
                st.error("❌ 종목 선택 코드 실행 중 오류가 발생했습니다.")
                with st.expander("🔍 오류 상세", expanded=True):
                    st.code(traceback.format_exc(), language="text")
                with st.expander("🤖 생성 코드"):
                    st.code(code2, language="python")
                st.info("💡 오류 메시지를 전략 텍스트 뒤에 붙여넣고 다시 실행하면 AI가 자동 수정합니다.")
                st.stop()

        # ── Step 6: 포트폴리오 수익률 계산 ───────────
        with st.spinner("📊 포트폴리오 수익률 계산 중..."):
            port_returns = calc_portfolio_returns(prices_df, holdings_df, TRANSACTION_COST)

            # 벤치마크 (QQQ / SPY)
            with st.spinner(f"📡 벤치마크 ({benchmark_ticker}) 데이터 로드 중..."):
                bnh_df = download_single(benchmark_ticker, str(start_date), str(end_date))
            if bnh_df is not None and not bnh_df.empty:
                bnh_series = (bnh_df["Adj Close"] / bnh_df["Adj Close"].iloc[0]).dropna()
                # 인덱스 정렬 (포트폴리오와 맞추기)
                common_idx = port_returns.index.intersection(bnh_series.index)
                port_returns = port_returns.loc[common_idx]
                bnh_series = bnh_series.loc[common_idx]
                bnh_series = bnh_series / bnh_series.iloc[0]  # 같은 시작점
            else:
                bnh_series = pd.Series(1.0, index=port_returns.index)

            metrics2 = calc_metrics(port_returns, bnh_series, initial_capital)

        if not metrics2:
            st.error("❌ 성과 계산 실패 — 매매 신호가 생성되지 않았을 수 있습니다.")
            st.stop()

        # ── 결과 대시보드 ─────────────────────────────
        st.markdown("---")
        st.markdown("## 📊 포트폴리오 백테스트 결과")

        st.markdown('<p class="section-title">🏆 핵심 성과 지표</p>', unsafe_allow_html=True)
        render_metrics(metrics2, initial_capital)

        st.markdown('<p class="section-title">📈 성과 차트</p>', unsafe_allow_html=True)
        st.plotly_chart(build_chart(metrics2, benchmark_ticker), use_container_width=True)

        # 리밸런싱 종목 히스토리
        with st.expander("📋 리밸런싱 종목 히스토리 (최근 5회)", expanded=False):
            history = []
            for d in holdings_df.index[-5:]:
                row = holdings_df.loc[d]
                held = sorted(row[row == 1].index.tolist())
                history.append({"날짜": d.strftime("%Y-%m-%d"), "보유 종목": ", ".join(held)})
            st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)

        with st.expander("🤖 Gemini 생성 코드 보기"):
            st.code(code2, language="python")

        with st.expander("💾 이 전략 및 코드 저장하기", expanded=False):
            p_name = st.text_input("전략 이름", key="p_save_name")
            p_memo = st.text_input("메모 (선택)", key="p_save_memo")
            if st.button("저장", key="btn_save_port"):
                if p_name:
                    add_strategy(p_name, p_memo, code2, "portfolio", strategy_port)
                    st.success("🎉 전략이 JSON에 저장되었습니다! 탭 4에서 확인하세요.")
                else:
                    st.error("전략 이름을 입력하세요.")


# ══════════════════════════════════════════════
# TAB 3 — 매크로 대시보드
# ══════════════════════════════════════════════
with tab3:
    st.markdown('<p class="section-title">📡 FRED 매크로 지표 확인 및 국면 분석</p>', unsafe_allow_html=True)
    
    if not fred_api_key:
        st.warning("⚠️ 사이드바에 **FRED API Key**를 입력해야 매크로 데이터를 불러올 수 있습니다.")
        
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.markdown("#### 1. 지표 조회")
        selected_category = st.selectbox("카테고리 선택", list(FRED_INDICATORS.keys()))
        
        indicators_in_cat = FRED_INDICATORS[selected_category]
        selected_indicators = st.multiselect(
            "조회할 지표 선택 (다중 선택 가능)",
            options=list(indicators_in_cat.keys()),
            format_func=lambda x: f"{x} - {indicators_in_cat[x]}",
            default=list(indicators_in_cat.keys())[:2] if indicators_in_cat else []
        )
        
        load_macro = st.button("📊 데이터 조회 및 시각화", use_container_width=True)
        
    with c2:
        st.info("""
        **💡 핵심 매크로 지표 가이드**
        - **경기선행지수 (USSLIND)**: 향후 3~6개월 뒤의 경기 방향성을 예고합니다.
        - **장단기 금리차 (T10Y2Y)**: 0 이하면 장단기 금리 역전으로, 역사적으로 경기 침체의 강력한 선행 신호입니다.
        - **하이일드 스프레드 (BAMLH0A0HYM2)**: 기업들의 신용 위험을 나타냅니다. 스프레드 급등 시 위험자산 회피(Risk-off) 신호입니다.
        - **기준금리 (DFF)**: 연준의 유동성 공급/축소 사이클을 나타내며, 금리 하락 전환 시 회복기(Recovery)로 전환되는 경향이 있습니다.
        """)

    if load_macro:
        if not fred_api_key:
            st.error("⛔ FRED API Key를 먼저 입력해 주세요.")
        elif not selected_indicators:
            st.warning("⚠️ 조회할 지표를 최소 1개 이상 선택해 주세요.")
        else:
            with st.spinner("🌐 FRED API에서 데이터를 로드 중입니다..."):
                macro_data = {}
                for ind in selected_indicators:
                    s = fetch_fred_data(ind, fred_api_key, start_date=str(start_date))
                    if not s.empty:
                        macro_data[ind] = s
                
                if macro_data:
                    macro_df = pd.DataFrame(macro_data).ffill().dropna(how='all')
                    
                    st.markdown("### 📈 매크로 지표 추이")
                    fig = make_subplots(rows=len(macro_data), cols=1, shared_xaxes=True, vertical_spacing=0.08)
                    
                    for i, col in enumerate(macro_df.columns):
                        series_name = FRED_INDICATORS[selected_category].get(col, col)
                        fig.add_trace(go.Scatter(
                            x=macro_df.index, y=macro_df[col],
                            name=series_name,
                            mode='lines',
                            line=dict(width=2)
                        ), row=i+1, col=1)
                        fig.update_yaxes(title_text=col, title_font=dict(size=10), row=i+1, col=1)
                        
                    fig.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        height=300 * len(macro_data),
                        hovermode="x unified",
                        showlegend=False,
                        margin=dict(l=10, r=10, t=30, b=10)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander("관련 데이터 원본 보기"):
                        st.dataframe(macro_df.sort_index(ascending=False), use_container_width=True)
                else:
                    st.error("❌ 선택한 지표의 데이터를 가져오지 못했습니다. API Key나 날짜 설정을 확인해주세요.")


# ══════════════════════════════════════════════
# TAB 4 — 직접 코드 실행 & 전략 저장소
# ══════════════════════════════════════════════
with tab4:
    sub_a, sub_b = st.tabs(["✍️ 직접 코드 실행", "📚 저장된 전략 (JSON)"])

    # ── Sub A: 직접 코드 실행 ──
    with sub_a:
        st.markdown('<p class="section-title">💡 파이썬 코드 자유 실행</p>', unsafe_allow_html=True)
        st.info("데이터 다운로드부터 성과 계산까지 자유롭게 코딩하세요. 최종적으로 `df` 변수에 변환 데이터(인덱스=날짜, 컬럼에 `Cumulative_Return` 포함)를 남겨두면 차트로 그려집니다.")

        default_code = """# 예시: AAPL 데이터를 직접 다운받아 누적 수익률 계산
import yfinance as yf
raw = yf.download('AAPL', start='2020-01-01', auto_adjust=False)

# MultiIndex 호환 처리 및 데이터 추출
if isinstance(raw.columns, pd.MultiIndex):
    df = raw.xs('AAPL', axis=1, level=1).copy()
else:
    df = raw.copy()

df['Adj Close'] = df['Adj Close'] if 'Adj Close' in df.columns else df['Close']
df = df.dropna(subset=['Adj Close'])

df['Signal'] = (df['Close'] > df['Close'].rolling(20).mean()).astype(int)
df['Position'] = df['Signal'].shift(1).fillna(0)
df['Strategy_Return'] = df['Adj Close'].pct_change() * df['Position']
df['Cumulative_Return'] = (1 + df['Strategy_Return']).cumprod()"""

        custom_code = st.text_area(
            "파이썬 완성형 코드 입력", height=400, key="custom_free",
            value=st.session_state.get("custom_code_free_val", default_code),
            help="데이터 연동부터 백테스트, 시각화까지 자유롭게 작성하세요. `fig` 인스턴스 혹은 `plt.show()` 호출 시 자동으로 렌더링 됩니다."
        )
        
        run_custom = st.button("🚀 직접 코드 실행", key="btn_custom_free", use_container_width=True)

        if run_custom:
            with st.spinner("⚡ 코드 실행 중..."):
                try:
                    # 빈 샌드박스로 시작
                    local_vars = {}
                    
                    # plt.show() 호출 시 streamlit에서 잡도록 오버라이딩
                    original_show = plt.show
                    def st_show(*args, **kwargs):
                        st.pyplot(plt.gcf())
                    plt.show = st_show
                    
                    # 추가 라이브러리 임포트 (GMM, HMM 등은 없으면 안되므로 샌드박스 개방)
                    import sklearn
                    import hmmlearn
                    try: from fredapi import Fred
                    except ImportError: Fred = None

                    _sand_box = {
                        "__builtins__": __builtins__,
                        "pd": pd, "np": np, "math": math, "yf": yf, "plt": plt,
                        "sklearn": sklearn, "hmmlearn": hmmlearn, "Fred": Fred
                    }
                    
                    exec(custom_code, _sand_box, local_vars)
                    
                    # 실행 후 plt.show 복구
                    plt.show = original_show
                    
                except ImportError as ie:
                    st.error(f"❌ 필요한 모듈이 설치되어 있지 않습니다: {ie}")
                    st.info("터미널에서 `pip install hmmlearn fredapi scikit-learn` 등을 실행해 주세요.")
                    plt.show = original_show
                    st.stop()
                except Exception:
                    st.error("❌ 코드 실행 오류가 발생했습니다.")
                    st.code(traceback.format_exc(), language="text")
                    plt.show = original_show
                    st.stop()
                
            st.success("✅ 백테스트 실행 완료")
            
            # 1. 만약 코드 내에서 fig 변수가 정의되었다면 우선 출력
            fig_rendered = False
            if "fig" in local_vars and hasattr(local_vars["fig"], "savefig"):
                st.plotly_chart(local_vars["fig"], use_container_width=True) if isinstance(local_vars["fig"], go.Figure) else st.pyplot(local_vars["fig"])
                fig_rendered = True
            
            # 2. 호환성 지원: df['Cumulative_Return'] 형태로 리턴값을 남겨놓은 구 버전 코드의 경우
            if "df" in local_vars and isinstance(local_vars["df"], pd.DataFrame):
                result_df = local_vars["df"]
                if "Cumulative_Return" in result_df.columns and not fig_rendered:
                    fig = make_subplots(rows=1, cols=1, subplot_titles=("📈 전략 누적 수익률",))
                    cum = result_df["Cumulative_Return"]
                    
                    fig.add_trace(go.Scatter(
                        x=cum.index, y=(cum - 1) * 100, name="AI 전략",
                        line=dict(color="#63b3ed", width=2.5),
                        fill="tozeroy", fillcolor="rgba(99,179,237,0.07)",
                        hovertemplate="%{y:.2f}%<extra>전략 수익률</extra>",
                    ))
                    fig.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                    xanchor="right", x=1, font=dict(color="#94a3b8", size=12),
                                    bgcolor="rgba(0,0,0,0)"),
                        margin=dict(l=10, r=10, t=40, b=10),
                        yaxis=dict(gridcolor="rgba(99,179,237,0.08)", ticksuffix="%", tickfont=dict(color="#64748b")),
                        hovermode="x unified", height=400, font=dict(family="Inter"),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
            with st.expander("💾 이 백테스트 코드 저장하기", expanded=False):
                c_name = st.text_input("전략 이름", key="c_save_name_c")
                c_memo = st.text_input("메모 (선택)", key="c_save_memo_c")
                if st.button("저장", key="btn_save_custom_c"):
                    if c_name:
                        add_strategy(c_name, c_memo, custom_code, "free")
                        st.success("🎉 전략이 저장되었습니다!")
                    else:
                        st.error("전략 이름을 입력하세요.")

    # ── Sub B: 저장된 전략 보기 ──
    with sub_b:
        st.markdown('<p class="section-title">📚 JSON 전략 라이브러리</p>', unsafe_allow_html=True)
        saved = load_strategies()
        if not saved:
            st.info("아직 저장된 전략이 없습니다.")
        else:
            for item in reversed(saved):
                if item["type"] == "free": badge_color = "#9aa0a6"
                elif item["type"] == "single": badge_color = "#4285F4"
                else: badge_color = "#34A853"
                st.markdown(f"""
                <div style="padding:16px; border:1px solid #e8eaed; border-radius:8px; margin-bottom:12px; background:#fff;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h3 style="margin:0; font-size:1.1rem;">{item['name']}</h3>
                        <span style="background:{badge_color}; color:white; padding:4px 8px; border-radius:12px; font-size:0.75rem;">{item['type'].upper()}</span>
                    </div>
                    <p style="color:#5f6368; font-size:0.85rem; margin-top:4px;">저장일: {item['saved_at']} | 메모: {item.get('memo', '-')}</p>
                </div>
                """, unsafe_allow_html=True)

                if item.get("strategy_text"):
                    st.caption(f"자연어 전략: {item['strategy_text']}")
                with st.expander("파이썬 코드 보기"):
                    st.code(item["code"], language="python")

                c_run, c_del, _ = st.columns([2, 1, 7])
                with c_run:
                    if st.button("🔄 에디터로 불러오기", key=f"load_{item['id']}"):
                        st.session_state["custom_code_free_val"] = item["code"]
                        st.success("코드를 불러왔습니다. '직접 코드 실행' 탭을 확인하세요.")
                with c_del:
                    if st.button("🗑️ 삭제", key=f"del_{item['id']}"):
                        delete_strategy(item["id"])
                        st.rerun()


