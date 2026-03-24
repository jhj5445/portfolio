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

# ─────────────────────────────────────────────
# CSS 스타일링
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* 다크 배경 */
.stApp {
    background: linear-gradient(135deg, #0d0f1a 0%, #0f1623 50%, #0d1520 100%);
    min-height: 100vh;
}

/* 사이드바 */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0e1a 0%, #0f1829 100%);
    border-right: 1px solid rgba(99, 179, 237, 0.15);
}
[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stNumberInput > div > div > input,
[data-testid="stSidebar"] .stDateInput > div > div > input {
    background: rgba(15, 25, 50, 0.8);
    border: 1px solid rgba(99, 179, 237, 0.25);
    color: #e2e8f0;
    border-radius: 8px;
}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
    color: #94a3b8 !important;
    font-size: 0.85rem;
}

/* 헤더 */
.hero-header {
    background: linear-gradient(135deg, rgba(99,179,237,0.08) 0%, rgba(129,140,248,0.08) 50%, rgba(167,243,208,0.05) 100%);
    border: 1px solid rgba(99,179,237,0.2);
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(99,179,237,0.08) 0%, transparent 70%);
    pointer-events: none;
}
.hero-title {
    font-size: 2.2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #63b3ed, #818cf8, #a7f3d0);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 8px 0;
}
.hero-sub {
    color: #64748b;
    font-size: 1rem;
    margin: 0;
}

/* 전략 입력창 */
.stTextArea > div > div > textarea {
    background: rgba(10, 15, 35, 0.9) !important;
    border: 1px solid rgba(99, 179, 237, 0.3) !important;
    color: #e2e8f0 !important;
    border-radius: 12px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
    transition: border-color 0.2s ease;
}
.stTextArea > div > div > textarea:focus {
    border-color: rgba(99, 179, 237, 0.7) !important;
    box-shadow: 0 0 0 3px rgba(99, 179, 237, 0.1) !important;
}

/* 실행 버튼 */
.stButton > button {
    background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 14px 36px !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    letter-spacing: 0.5px !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 20px rgba(59, 130, 246, 0.35) !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 28px rgba(59, 130, 246, 0.5) !important;
}

/* 메트릭 카드 */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(15,25,50,0.9) 0%, rgba(20,30,60,0.9) 100%);
    border: 1px solid rgba(99,179,237,0.18);
    border-radius: 12px;
    padding: 20px !important;
    transition: border-color 0.2s ease;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(99,179,237,0.4);
}
[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-size: 0.8rem !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}
[data-testid="stMetricValue"] {
    color: #e2e8f0 !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricDelta"] {
    font-size: 0.85rem !important;
}

/* 섹션 제목 */
.section-title {
    color: #94a3b8;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin: 24px 0 14px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(99,179,237,0.1);
}

/* 알림/에러 박스 */
.stAlert {
    border-radius: 10px !important;
}

/* Expander */
.stExpander {
    background: rgba(10, 15, 30, 0.6) !important;
    border: 1px solid rgba(99,179,237,0.15) !important;
    border-radius: 10px !important;
}

/* 사이드바 브랜드 */
.sidebar-brand {
    text-align: center;
    padding: 16px 0 24px 0;
    border-bottom: 1px solid rgba(99,179,237,0.1);
    margin-bottom: 20px;
}
.sidebar-brand-title {
    font-size: 1.3rem;
    font-weight: 700;
    background: linear-gradient(135deg, #63b3ed, #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.sidebar-brand-sub {
    font-size: 0.72rem;
    color: #475569;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 시스템 프롬프트
# ─────────────────────────────────────────────
SYSTEM_INSTRUCTION = """
너는 파이썬 기반의 전문 퀀트 투자 개발자야.
사용자가 자연어로 투자 전략을 설명하면, 이를 바탕으로 pandas 백테스트 코드를 작성해.

[환경 및 전제조건]
1. 주가 데이터는 이미 `df`라는 pandas DataFrame 변수에 로드되어 있다. (데이터 다운로드 코드 작성 금지)
2. `df`의 주요 컬럼은 ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'] 이다.
3. 주가 분할 및 배당이 반영된 정확한 테스트를 위해, 모든 진입/청산 가격과 수익률 계산은 반드시 `Adj Close`(수정주가)를 기준으로 해라.
4. 복잡한 백테스트 라이브러리(Backtrader 등)는 절대 사용하지 말고, 오직 `pandas`와 `numpy`의 벡터화 연산만 사용해라.

[작성해야 할 코드의 구조]
아래 변수들이 `df`의 새로운 컬럼으로 최종 계산되도록 코드를 작성해라:
- `df['Signal']`: 매수 신호 1, 매도/관망 신호 0
- `df['Position']`: 미래 참조(Look-ahead Bias)를 막기 위해 반드시 `df['Signal'].shift(1)`을 사용하여 실제 보유 상태를 계산해라.
- `df['Strategy_Return']`: 매일의 전략 수익률 (`df['Adj Close'].pct_change()` * `df['Position']`)
- `df['Cumulative_Return']`: 누적 수익률 (`(1 + df['Strategy_Return']).cumprod()`)

[Look-ahead Bias 방지 - 매우 중요]
- 신호가 발생한 당일 종가로 바로 매수하지 않도록, 반드시 Position = Signal.shift(1) 을 사용해라.
- 이동평균선 등의 지표 계산 시 .rolling().mean() 등 과거 데이터만 사용해라.

[출력 형식 제한]
- 오직 파이썬 코드 블록(```python ... ```) 안에만 코드를 작성해라.
- `print()`나 `plt.show()` 같은 화면 출력 코드는 절대 작성하지 마라.
- 코드 외에 어떠한 설명도 붙이지 마라.
""".strip()


# ─────────────────────────────────────────────
# 유틸리티 함수
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def download_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    """yfinance로 수정주가 포함 OHLCV 데이터 다운로드 (최신 버전 멀티인덱스 호환)"""
    try:
        df = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
    except Exception:
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    # ── 멀티인덱스 컬럼 평탄화 ──────────────────────────────────────
    # 최신 yfinance는 (Price, Ticker) 구조의 MultiIndex를 반환
    # 예: ('Adj Close', 'TSLA'), ('Close', 'TSLA'), ...
    if isinstance(df.columns, pd.MultiIndex):
        lvl0_samples = set(df.columns.get_level_values(0))
        price_fields = {"Adj Close", "Close", "Open", "High", "Low", "Volume"}
        if lvl0_samples & price_fields:
            df.columns = df.columns.get_level_values(0)
        else:
            df.columns = df.columns.get_level_values(1)

    # 컬럼명 문자열 정규화
    df.columns = [str(c).strip() for c in df.columns]

    # ── Adj Close 없을 경우 Close로 대체 ────────────────────────────
    if "Adj Close" not in df.columns:
        if "Close" in df.columns:
            df["Adj Close"] = df["Close"]
        else:
            return pd.DataFrame()

    df = df.dropna(subset=["Adj Close"])
    return df


def call_gemini(api_key: str, strategy_text: str) -> str:
    """Gemini API를 호출하여 백테스트 코드를 생성 (google-genai SDK)"""
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=strategy_text,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
        ),
    )
    return response.text


def extract_python_code(text: str) -> str:
    """Gemini 응답에서 python 코드 블록만 추출"""
    pattern = r"```python\s*([\s\S]*?)```"
    matches = re.findall(pattern, text)
    if matches:
        return "\n\n".join(matches).strip()
    return text.strip()


def run_backtest(df: pd.DataFrame, code: str):
    """격리된 exec() 환경에서 백테스트 코드 실행"""
    allowed_globals = {
        "__builtins__": {
            "abs": abs, "all": all, "any": any, "bool": bool,
            "dict": dict, "enumerate": enumerate, "float": float,
            "int": int, "isinstance": isinstance, "len": len,
            "list": list, "map": map, "max": max, "min": min,
            "print": print, "range": range, "round": round,
            "set": set, "str": str, "sum": sum, "tuple": tuple,
            "zip": zip,
        },
        "pd": pd,
        "np": np,
    }
    local_vars = {"df": df.copy()}
    exec(code, allowed_globals, local_vars)
    return local_vars["df"]


def calc_metrics(df: pd.DataFrame, initial_capital: float):
    """성과 지표 계산: CAGR, MDD, 승률, 샤프비율"""
    cum = df["Cumulative_Return"].dropna()
    daily_ret = df["Strategy_Return"].dropna()

    if cum.empty or len(cum) < 2:
        return None

    # 총 기간(연수)
    n_days = (cum.index[-1] - cum.index[0]).days
    n_years = n_days / 365.25 if n_days > 0 else 1

    # CAGR
    total_return = cum.iloc[-1] - 1
    cagr = (cum.iloc[-1] ** (1 / n_years) - 1) if n_years > 0 else total_return

    # MDD
    roll_max = cum.cummax()
    drawdown = (cum - roll_max) / roll_max
    mdd = drawdown.min()

    # 승률
    trade_returns = daily_ret[daily_ret != 0]
    win_rate = (trade_returns > 0).sum() / len(trade_returns) if len(trade_returns) > 0 else 0

    # 샤프비율 (무위험수익률 0% 가정)
    sharpe = (daily_ret.mean() / daily_ret.std() * np.sqrt(252)) if daily_ret.std() > 0 else 0

    # B&H 누적수익률
    bnh = (df["Adj Close"] / df["Adj Close"].iloc[0]).dropna()

    # 최종 자산
    final_value = initial_capital * cum.iloc[-1]

    return {
        "cagr": cagr,
        "total_return": total_return,
        "mdd": mdd,
        "win_rate": win_rate,
        "sharpe": sharpe,
        "final_value": final_value,
        "cum_series": cum,
        "bnh_series": bnh,
        "drawdown_series": drawdown,
        "n_trades": len(trade_returns),
    }


def build_chart(metrics: dict, ticker: str) -> go.Figure:
    """Plotly 인터랙티브 차트 생성 (누적수익률 + 드로우다운)"""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.68, 0.32],
        vertical_spacing=0.04,
        subplot_titles=("📈 누적 수익률 비교", "📉 전략 드로우다운"),
    )

    cum = metrics["cum_series"]
    bnh = metrics["bnh_series"]
    dd = metrics["drawdown_series"]

    fig.add_trace(
        go.Scatter(
            x=cum.index, y=(cum - 1) * 100,
            name="AI 전략",
            line=dict(color="#63b3ed", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(99,179,237,0.07)",
            hovertemplate="%{y:.2f}%<extra>AI 전략</extra>",
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=bnh.index, y=(bnh - 1) * 100,
            name=f"Buy & Hold ({ticker})",
            line=dict(color="#f6c90e", width=1.8, dash="dot"),
            hovertemplate="%{y:.2f}%<extra>Buy & Hold</extra>",
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=dd.index, y=dd * 100,
            name="드로우다운",
            line=dict(color="#fc8181", width=1.5),
            fill="tozeroy",
            fillcolor="rgba(252,129,129,0.12)",
            hovertemplate="%{y:.2f}%<extra>MDD</extra>",
        ),
        row=2, col=1,
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(10,14,30,0.0)",
        plot_bgcolor="rgba(10,14,30,0.0)",
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            font=dict(color="#94a3b8", size=12),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(
            gridcolor="rgba(99,179,237,0.08)",
            ticksuffix="%",
            tickfont=dict(color="#64748b"),
        ),
        yaxis2=dict(
            gridcolor="rgba(252,129,129,0.08)",
            ticksuffix="%",
            tickfont=dict(color="#64748b"),
        ),
        xaxis2=dict(tickfont=dict(color="#64748b")),
        hovermode="x unified",
        height=520,
        font=dict(family="Inter"),
    )
    fig.update_annotations(font=dict(color="#94a3b8", size=12))
    return fig


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
    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        placeholder="AIza...",
        help="Google AI Studio에서 발급받은 API 키를 입력하세요.",
    )

    st.markdown('<p class="section-title">📊 종목 설정</p>', unsafe_allow_html=True)
    ticker = st.text_input(
        "종목 코드 (Ticker)",
        value="AAPL",
        placeholder="예: AAPL, TSLA, 005930.KS",
        help="Yahoo Finance 기준 종목 코드를 입력하세요. 한국 주식은 종목코드.KS 형식 사용.",
    ).strip().upper()

    st.markdown('<p class="section-title">📅 테스트 기간</p>', unsafe_allow_html=True)
    col_s, col_e = st.columns(2)
    with col_s:
        start_date = st.date_input(
            "시작일",
            value=date.today() - timedelta(days=365 * 5),
            max_value=date.today() - timedelta(days=30),
        )
    with col_e:
        end_date = st.date_input(
            "종료일",
            value=date.today(),
            max_value=date.today(),
        )

    st.markdown('<p class="section-title">💰 자본금 설정</p>', unsafe_allow_html=True)
    initial_capital = st.number_input(
        "초기 자본금 ($)",
        min_value=1000,
        max_value=100_000_000,
        value=10_000,
        step=1000,
        format="%d",
    )

    st.markdown("---")
    st.markdown(
        "<small style='color:#374151;'>⚠️ 본 서비스는 교육 목적으로 제공됩니다. "
        "투자 결과에 대한 책임은 사용자 본인에게 있습니다.</small>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# 메인 화면
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
    <h1 class="hero-title">📈 AI Quant-Tester</h1>
    <p class="hero-sub">자연어로 투자 전략을 설명하면, AI가 백테스트 코드를 작성하고 즉시 실행합니다.</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<p class="section-title">💡 투자 전략 입력</p>', unsafe_allow_html=True)
strategy_examples = [
    "20일 이동평균선이 60일선을 상향 돌파하면 매수하고, 하향 이탈하면 매도해 줘.",
    "RSI가 30 이하로 과매도 구간에 진입하면 매수하고, 70 이상에서 매도해 줘.",
    "주가가 52주 신고가를 갱신하면 매수 진입하고, 20일 이동평균선 아래로 떨어지면 청산해 줘.",
    "볼린저밴드 하단 터치 시 매수하고, 상단 터치 시 매도해 줘.",
]
example_idx = st.selectbox(
    "💡 예시 전략 불러오기",
    options=["직접 입력하기"] + strategy_examples,
    index=0,
)

default_text = "" if example_idx == "직접 입력하기" else example_idx
strategy_text = st.text_area(
    "전략 설명",
    value=default_text,
    height=130,
    placeholder="예: 20일 이동평균선이 60일 이동평균선을 상향 돌파하면 매수하고, 하향 이탈하면 매도해 줘.",
    label_visibility="collapsed",
)

run_btn = st.button("🚀  백테스트 실행", use_container_width=True)

# ─────────────────────────────────────────────
# 실행 로직
# ─────────────────────────────────────────────
if run_btn:
    errors = []
    if not api_key:
        errors.append("⛔ 사이드바에서 **Gemini API Key**를 입력해 주세요.")
    if not ticker:
        errors.append("⛔ **종목 코드**를 입력해 주세요.")
    if not strategy_text.strip():
        errors.append("⛔ **투자 전략**을 입력해 주세요.")
    if start_date >= end_date:
        errors.append("⛔ **종료일**이 시작일보다 이후여야 합니다.")

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    # ── 1. 데이터 다운로드 ──────────────────────
    with st.spinner(f"📡 {ticker} 데이터를 다운로드 중..."):
        df = download_data(ticker, str(start_date), str(end_date))

    if df is None or df.empty:
        st.error(
            f"❌ **{ticker}** 데이터를 불러올 수 없습니다. "
            "종목 코드가 올바른지 확인하세요. (예: AAPL, TSLA, 005930.KS)"
        )
        st.stop()

    st.success(f"✅ {ticker} 데이터 로드 완료 ({len(df):,}일, {start_date} ~ {end_date})")

    # ── 2. Gemini 코드 생성 ─────────────────────
    with st.spinner("🤖 Gemini가 백테스트 코드를 생성 중..."):
        try:
            raw_response = call_gemini(api_key, strategy_text)
            generated_code = extract_python_code(raw_response)
        except Exception as e:
            st.error(f"❌ Gemini API 오류: {e}")
            st.stop()

    # ── 3. 코드 실행 (exec 샌드박스) ───────────
    with st.spinner("⚡ 백테스트 실행 중..."):
        try:
            result_df = run_backtest(df, generated_code)
        except Exception as e:
            st.error("❌ 백테스트 코드 실행 중 오류가 발생했습니다.")
            with st.expander("🔍 오류 상세 보기", expanded=True):
                st.code(traceback.format_exc(), language="text")
            with st.expander("🤖 Gemini가 생성한 코드", expanded=False):
                st.code(generated_code, language="python")
            st.info(
                "💡 **Self-Correction 힌트:** 위 오류 메시지를 복사하여 전략 프롬프트 뒤에 붙여넣고 "
                "다시 실행하면 AI가 스스로 오류를 수정합니다."
            )
            st.stop()

    required_cols = ["Signal", "Position", "Strategy_Return", "Cumulative_Return"]
    missing = [c for c in required_cols if c not in result_df.columns]
    if missing:
        st.error(f"❌ 생성된 코드에 필수 컬럼이 없습니다: {missing}")
        with st.expander("🤖 생성 코드 확인"):
            st.code(generated_code, language="python")
        st.stop()

    # ── 4. 성과 지표 계산 ──────────────────────
    metrics = calc_metrics(result_df, initial_capital)
    if metrics is None:
        st.error("❌ 성과 계산에 실패했습니다. 전략이 매매 신호를 생성하지 못했을 수 있습니다.")
        st.stop()

    # ─────────────────────────────────────────────
    # 결과 대시보드
    # ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📊 백테스트 결과")

    st.markdown('<p class="section-title">🏆 핵심 성과 지표</p>', unsafe_allow_html=True)
    m1, m2, m3, m4, m5 = st.columns(5)

    cagr_val = metrics["cagr"] * 100
    total_ret = metrics["total_return"] * 100
    mdd_val = metrics["mdd"] * 100
    win_val = metrics["win_rate"] * 100
    sharpe_val = metrics["sharpe"]

    bnh = metrics["bnh_series"]
    n_years_bnh = (bnh.index[-1] - bnh.index[0]).days / 365.25
    bnh_cagr = (bnh.iloc[-1] ** (1 / n_years_bnh) - 1) * 100 if n_years_bnh > 0 else 0

    with m1:
        st.metric("CAGR", f"{cagr_val:.2f}%", delta=f"vs B&H {cagr_val - bnh_cagr:+.2f}%p")
    with m2:
        st.metric("총 수익률", f"{total_ret:.2f}%")
    with m3:
        st.metric("최대 낙폭 (MDD)", f"{mdd_val:.2f}%")
    with m4:
        st.metric("승률", f"{win_val:.1f}%")
    with m5:
        st.metric("샤프비율", f"{sharpe_val:.2f}")

    st.markdown("")
    m6, m7, m8, m9 = st.columns(4)
    with m6:
        st.metric("최종 자산", f"${metrics['final_value']:,.0f}")
    with m7:
        st.metric("초기 자본금", f"${initial_capital:,}")
    with m8:
        st.metric("총 매매 횟수", f"{metrics['n_trades']:,}일")
    with m9:
        bnh_total = (bnh.iloc[-1] - 1) * 100
        st.metric("B&H 총 수익률", f"{bnh_total:.2f}%")

    st.markdown('<p class="section-title">📈 성과 차트</p>', unsafe_allow_html=True)
    fig = build_chart(metrics, ticker)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("🤖 Gemini가 생성한 백테스트 코드 보기", expanded=False):
        st.code(generated_code, language="python")

    with st.expander("📋 처리된 데이터 미리보기 (최근 10행)", expanded=False):
        display_cols = [c for c in ["Adj Close", "Signal", "Position", "Strategy_Return", "Cumulative_Return"] if c in result_df.columns]
        st.dataframe(
            result_df[display_cols].tail(10).style.format({
                "Adj Close": "{:.2f}",
                "Signal": "{:.0f}",
                "Position": "{:.0f}",
                "Strategy_Return": "{:.4f}",
                "Cumulative_Return": "{:.4f}",
            }),
            use_container_width=True,
        )
