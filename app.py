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
from datetime import date, timedelta

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
# 데이터 다운로드
# ─────────────────────────────────────────────
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

    prices_df = prices_df.dropna(axis=1, how="all")   # 데이터 없는 종목 제거
    prices_df = prices_df.ffill()                       # 결측 거래일 앞값 채우기
    prices_df = prices_df.dropna()                      # 남은 NaN 행 제거
    returns_df = prices_df.pct_change()
    return prices_df, returns_df


# ─────────────────────────────────────────────
# Gemini API
# ─────────────────────────────────────────────
def call_gemini(api_key: str, user_message: str, system_prompt: str) -> str:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=user_message,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )
    return response.text


def extract_code(text: str) -> str:
    matches = re.findall(r"```python\s*([\s\S]*?)```", text)
    return "\n\n".join(matches).strip() if matches else text.strip()


# ─────────────────────────────────────────────
# 코드 실행 (샌드박스)
# ─────────────────────────────────────────────
def _make_sandbox():
    return {
        "__builtins__": {
            "abs": abs, "all": all, "any": any, "bool": bool,
            "dict": dict, "enumerate": enumerate, "float": float,
            "int": int, "isinstance": isinstance, "len": len,
            "list": list, "map": map, "max": max, "min": min,
            "print": print, "range": range, "round": round,
            "set": set, "sorted": sorted, "str": str, "sum": sum,
            "tuple": tuple, "type": type, "zip": zip,
        },
        "pd": pd,
        "np": np,
        "math": math,
    }


def run_single_code(df: pd.DataFrame, code: str) -> pd.DataFrame:
    local_vars = {"df": df.copy()}
    exec(code, _make_sandbox(), local_vars)
    return local_vars["df"]


def run_portfolio_code(prices_df, returns_df, rebal_dates, n_stocks, code) -> pd.DataFrame:
    local_vars = {
        "prices_df": prices_df.copy(),
        "returns_df": returns_df.copy(),
        "rebal_dates": rebal_dates,
        "n_stocks": n_stocks,
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
    api_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...",
                            help="Google AI Studio에서 발급받은 API 키")

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

tab1, tab2 = st.tabs(["📊 단일 종목 백테스트", "🌍 포트폴리오 유니버스 백테스트"])


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
        if not api_key: errs.append("⛔ **Gemini API Key**를 입력해 주세요.")
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
                raw = call_gemini(api_key, strategy_single, SYSTEM_SINGLE)
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

    run2 = st.button("🚀  포트폴리오 백테스트 실행", key="run2", use_container_width=True)

    if run2:
        errs = []
        if not api_key: errs.append("⛔ **Gemini API Key**를 입력해 주세요.")
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

        # ── Step 4: Gemini 코드 생성 ─────────────────
        gemini_msg = f"""[전략]
{strategy_port}

[유니버스 정보]
- 유니버스: {universe} (총 {n_downloaded}개 종목)
- 사용 가능 종목 예시: {', '.join(prices_df.columns[:15].tolist())} ... 등
- 보유 종목 수(n_stocks): {n_stocks}
- 리밸런싱 주기: {rebal_freq} (총 {len(rebal_dates)}회)
- 기간: {start_date} ~ {end_date}"""

        with st.spinner("🤖 Gemini가 종목 선택 코드를 생성 중..."):
            try:
                raw2 = call_gemini(api_key, gemini_msg, SYSTEM_PORTFOLIO)
                code2 = extract_code(raw2)
            except Exception as e:
                st.error(f"❌ Gemini API 오류: {e}")
                st.stop()

        # ── Step 5: 코드 실행 → holdings_df 생성 ─────
        with st.spinner("⚡ 종목 선택 로직 실행 중..."):
            try:
                raw_holdings = run_portfolio_code(
                    prices_df, returns_df, rebal_dates, n_stocks, code2
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
