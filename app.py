import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from google import genai
from google.genai import types
from github import Github
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
# 0. 페이지 설정 및 CSS
# ─────────────────────────────────────────────
st.set_page_config(page_title="AI Quant-Tester", page_icon="📈", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Roboto:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'Roboto', 'Google Sans', sans-serif; }
.stApp { background: #f8f9fa; }
.hero-header { background: #ffffff; border-radius: 16px; padding: 28px 36px; margin-bottom: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); position: relative; overflow: hidden; }
.hero-header::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #4285F4 25%, #EA4335 25% 50%, #FBBC05 50% 75%, #34A853 75%); }
.section-title { color: #5f6368; font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px; border-bottom: 2px solid #4285F4; display: inline-block; margin: 20px 0 12px 0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 1. 세션 상태 초기화 (저장/삭제 시 데이터 증발 방지)
# ─────────────────────────────────────────────
if "single_res" not in st.session_state: st.session_state.single_res = None
if "port_res" not in st.session_state: st.session_state.port_res = None
if "custom_code_val" not in st.session_state: st.session_state.custom_code_val = ""

# ─────────────────────────────────────────────
# 2. GitHub 저장소 엔진 (PyGithub)
# ─────────────────────────────────────────────
GITHUB_TOKEN = st.secrets["github"]["token"]
GITHUB_REPO = st.secrets["github"]["repo"]
GITHUB_BRANCH = st.secrets["github"]["branch"]
STRATEGIES_DIR = "strategies"

def get_github_repo():
    return Github(GITHUB_TOKEN).get_repo(GITHUB_REPO)

def load_strategies():
    try:
        repo = get_github_repo()
        strategies = []
        try: contents = repo.get_contents(STRATEGIES_DIR, ref=GITHUB_BRANCH)
        except: return []
        for content in contents:
            if content.name.endswith(".json"):
                data = json.loads(content.decoded_content.decode("utf-8"))
                data["_sha"] = content.sha
                strategies.append(data)
        return sorted(strategies, key=lambda x: x.get("saved_at", ""), reverse=True)
    except Exception as e:
        st.error(f"GitHub 로드 실패: {e}")
        return []

def add_strategy(name, memo, code, strat_type, strategy_text=""):
    try:
        repo = get_github_repo()
        strat_id = str(uuid.uuid4())
        filename = f"{STRATEGIES_DIR}/{strat_id}.json"
        new_data = {
            "id": strat_id, "name": name, "memo": memo, "type": strat_type,
            "code": code, "strategy_text": strategy_text,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        repo.create_file(path=filename, message=f"Add: {name}", content=json.dumps(new_data, ensure_ascii=False, indent=4), branch=GITHUB_BRANCH)
        st.success(f"🚀 '{name}' 전략 저장 성공 (GitHub)")
    except Exception as e: st.error(f"저장 실패: {e}")

def delete_strategy(strat_id):
    try:
        repo = get_github_repo()
        contents = repo.get_contents(STRATEGIES_DIR, ref=GITHUB_BRANCH)
        for content in contents:
            if content.name == f"{strat_id}.json":
                repo.delete_file(path=content.path, message=f"Delete: {strat_id}", sha=content.sha, branch=GITHUB_BRANCH)
                st.success("삭제 완료")
                return
    except Exception as e: st.error(f"삭제 실패: {e}")

# ─────────────────────────────────────────────
# 3. 데이터 엔진 및 지표 카탈로그
# ─────────────────────────────────────────────
FRED_INDICATORS = {
    "경기 사이클": {"USSLIND": "미국 경기선행지수", "NAPM": "ISM 제조업 PMI"},
    "금리 및 스프레드": {"DFF": "미국 기준금리", "T10Y2Y": "장단기 금리차"},
    "물가 / 인플레이션": {"CPIAUCSL": "소비자물가지수 (CPI)", "T10YIE": "10년 기대인플레"},
    "고용 시장": {"UNRATE": "실업률", "ICSA": "신규 실업수당 청구"}
}

@st.cache_data(ttl=3600, show_spinner=False)
def download_data(ticker, start, end):
    try:
        df = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [str(c).strip() for c in df.columns]
        df.index = pd.to_datetime(df.index).tz_localize(None)
        if "Adj Close" not in df.columns: df["Adj Close"] = df["Close"]
        return df.dropna(subset=["Adj Close"])
    except: return None

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fred_data(series_id, api_key, start_date="2000-01-01"):
    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {"series_id": series_id, "api_key": api_key, "file_type": "json", "observation_start": start_date}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        obs = data["observations"]
        df = pd.DataFrame([{"date": pd.to_datetime(d["date"]), "value": float(d["value"])} for d in obs if d["value"] != "."])
        df.set_index("date", inplace=True)
        df.index = df.index.tz_localize(None)
        return df["value"]
    except: return pd.Series(dtype=float)

@st.cache_data(ttl=86400, show_spinner=False)
def get_universe_tickers(universe):
    if universe == "NASDAQ-100":
        return sorted(["AAPL","MSFT","AMZN","NVDA","META","GOOGL","GOOG","TSLA","AVGO","PEP","COST","CSCO","ADBE","TXN"]) # 샘플
    else:
        return sorted(["AAPL","MSFT","JNJ","V","PG","MA","HD","CVX","ABBV","PEP","KO","BAC"]) # 샘플

@st.cache_data(ttl=3600, show_spinner=False)
def download_universe(tickers, start, end):
    try:
        raw = yf.download(tickers, start=start, end=end, auto_adjust=False, progress=False)
        prices_df = raw.xs("Adj Close", axis=1, level=0) if isinstance(raw.columns, pd.MultiIndex) else raw["Adj Close"]
        prices_df.index = pd.to_datetime(prices_df.index).tz_localize(None)
        return prices_df.ffill().dropna(axis=1, thresh=len(prices_df)*0.5)
    except: return None

# ─────────────────────────────────────────────
# 4. 백테스트 계산기
# ─────────────────────────────────────────────
def get_rebal_dates(price_index, freq):
    rule = {"주간": "W-FRI", "월간": "ME", "분기": "QE", "연간": "YE"}
    resampled = pd.Series(1, index=price_index).resample(rule[freq]).last().index
    snapped = [price_index[price_index <= d][-1] for d in resampled if len(price_index[price_index <= d]) > 0]
    return pd.DatetimeIndex(sorted(set(snapped)))

def calc_portfolio_returns(prices_df, holdings_df, cost_rate=0.002):
    daily_ret = prices_df.pct_change()
    port_daily = pd.Series(0.0, index=daily_ret.index)
    sorted_rebal = holdings_df.index.sort_values()
    
    for i, date in enumerate(sorted_rebal):
        end = sorted_rebal[i+1] if i+1 < len(sorted_rebal) else daily_ret.index[-1] + pd.Timedelta(days=1)
        held = holdings_df.loc[date][holdings_df.loc[date] == 1].index.tolist()
        if not held: continue
        
        # 비용 계산 (교체 비율 기반)
        if i == 0: cost = cost_rate
        else:
            prev_held = set(holdings_df.loc[sorted_rebal[i-1]][holdings_df.loc[sorted_rebal[i-1]] == 1].index)
            change = len(set(held) - prev_held) + len(prev_held - set(held))
            cost = (change / len(held)) * cost_rate
            
        mask = (daily_ret.index >= date) & (daily_ret.index < end)
        period_rets = daily_ret.loc[mask, held].mean(axis=1)
        if not period_rets.empty:
            port_daily.loc[mask] = period_rets.values
            port_daily.loc[period_rets.index[0]] -= cost
    return port_daily

def calc_metrics(returns, bnh, capital):
    returns = returns.dropna()
    if returns.empty: return None
    cum = (1 + returns).cumprod()
    years = max((cum.index[-1] - cum.index[0]).days / 365.25, 0.01)
    cagr = cum.iloc[-1]**(1/years) - 1
    mdd = ((cum - cum.cummax()) / cum.cummax()).min()
    return {"cagr": cagr, "mdd": mdd, "sharpe": (returns.mean()/returns.std()*np.sqrt(252)) if returns.std()>0 else 0,
            "cum": cum, "bnh": bnh, "final": capital * cum.iloc[-1]}

# ─────────────────────────────────────────────
# 5. AI 엔진 (Gemini) + 리트라이 로직
# ─────────────────────────────────────────────
SYSTEM_SINGLE = "너는 퀀트 개발자야. df['Signal'](매수=1, 관망=0), df['Position']=df['Signal'].shift(1), df['Strategy_Return'], df['Cumulative_Return'] 컬럼을 필수로 생성해. 코드만 출력해."
SYSTEM_PORTFOLIO = "너는 포트폴리오 퀀트야. prices_df, returns_df, rebal_dates, n_stocks를 사용해 holdings_df(index=rebal_dates, columns=종목, values=0or1)를 생성해. 코드만 출력해."

def call_gemini_retry(msg, system_prompt):
    keys = [k.strip() for k in st.secrets["gemini"]["api_keys"].split(",")]
    last_err = ""
    for attempt in range(3):
        for key in keys:
            try:
                client = genai.Client(api_key=key)
                full_msg = f"{msg}\n\n[ERROR FROM PREVIOUS ATTEMPT]\n{last_err}" if last_err else msg
                res = client.models.generate_content(model="gemini-3-flash-preview", contents=full_msg, config=types.GenerateContentConfig(system_instruction=system_prompt))
                return re.findall(r"```python\s*([\s\S]*?)```", res.text)[0].strip()
            except Exception as e:
                last_err = str(e)
                continue
    return None

# ─────────────────────────────────────────────
# 6. 메인 화면 & 탭 로직
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔑 API & 설정")
    fred_key = st.secrets.get("fred", {}).get("api_key", "")
    ticker = st.text_input("단일 종목 코드", value="AAPL").upper()
    universe = st.selectbox("유니버스", ["NASDAQ-100", "S&P 500"])
    n_stocks = st.slider("보유 종목 수", 5, 30, 10)
    rebal_freq = st.selectbox("리밸런싱 주기", ["월간", "분기", "주간"])
    col_s, col_e = st.columns(2)
    s_date = col_s.date_input("시작", date.today() - timedelta(days=365*5))
    e_date = col_e.date_input("종료", date.today())
    capital = st.number_input("초기 자본 ($)", value=10000)

st.markdown('<div class="hero-header"><h1 style="margin:0;">📈 AI Quant-Tester</h1><p style="color:gray;">자연어 전략 → GitHub 저장소 연동형 백테스트</p></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 단일 종목", "🌍 포트폴리오", "🌐 매크로", "✍️ 코드 & 저장소"])

# ────── TAB 1: 단일 종목 ──────
with tab1:
    strategy_single = st.text_area("단일 종목 전략 설명", placeholder="예: RSI가 30 이하일 때 매수하고 70 이상일 때 매도...", height=120)
    if st.button("🚀 단일 백테스트 실행", key="run_s"):
        with st.spinner("AI가 코드를 짜고 백테스트 중..."):
            df = download_data(ticker, s_date, e_date)
            code = call_gemini_retry(strategy_single, SYSTEM_SINGLE)
            if code:
                try:
                    sandbox = {"pd": pd, "np": np, "math": math, "yf": yf, "plt": plt}
                    local = {"df": df.copy()}
                    exec(code, sandbox, local)
                    bnh = (df["Adj Close"] / df["Adj Close"].iloc[0]).dropna()
                    metrics = calc_metrics(local["df"]["Strategy_Return"], bnh, capital)
                    st.session_state.single_res = {"metrics": metrics, "code": code, "text": strategy_single}
                except: st.error(traceback.format_exc())

    if st.session_state.single_res:
        sr = st.session_state.single_res
        m = sr["metrics"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("CAGR", f"{m['cagr']*100:.2f}%")
        c2.metric("MDD", f"{m['mdd']*100:.2f}%")
        c3.metric("Sharpe", f"{m['sharpe']:.2f}")
        c4.metric("최종 자산", f"${m['final']:,.0f}")
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
        fig.add_trace(go.Scatter(x=m["cum"].index, y=(m["cum"]-1)*100, name="전략"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m["bnh"].index, y=(m["bnh"]-1)*100, name="B&H", line=dict(dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=m["cum"].index, y=m["cum"].pct_change(), name="Daily", mode='markers', marker=dict(size=2)), row=2, col=1)
        fig.update_layout(height=500, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("💾 이 전략을 GitHub에 저장"):
            cn, cm = st.columns([1, 2]); name = cn.text_input("전략명", key="sn1"); memo = cm.text_input("메모", key="sm1")
            if st.button("GitHub 저장", key="btns1"):
                if name: add_strategy(name, memo, sr["code"], "single", sr["text"]); st.rerun()

# ────── TAB 2: 포트폴리오 ──────
with tab2:
    strategy_port = st.text_area("포트폴리오 종목 선택 전략", placeholder="예: 최근 6개월 수익률이 높은 상위 10개 종목을 매월 리밸런싱...", height=120)
    if st.button("🚀 포트폴리오 백테스트 실행", key="run_p"):
        with st.spinner("유니버스 데이터 로드 및 AI 연산 중..."):
            tickers = get_universe_tickers(universe)
            prices_df = download_universe(tickers, s_date, e_date)
            returns_df = prices_df.pct_change()
            rebal_dates = get_rebal_dates(prices_df.index, rebal_freq)
            
            code = call_gemini_retry(strategy_port, SYSTEM_PORTFOLIO)
            if code:
                try:
                    sandbox = {"pd": pd, "np": np, "math": math, "yf": yf, "plt": plt}
                    local = {"prices_df": prices_df, "returns_df": returns_df, "rebal_dates": rebal_dates, "n_stocks": n_stocks}
                    exec(code, sandbox, local)
                    
                    # 정규화 및 수익률 계산
                    h_df = local["holdings_df"]
                    p_ret = calc_portfolio_returns(prices_df, h_df)
                    benchmark_df = download_data("SPY" if universe=="S&P 500" else "QQQ", s_date, e_date)
                    bnh = (benchmark_df["Adj Close"] / benchmark_df["Adj Close"].iloc[0]).dropna()
                    
                    common_idx = p_ret.index.intersection(bnh.index)
                    metrics = calc_metrics(p_ret.loc[common_idx], bnh.loc[common_idx], capital)
                    st.session_state.port_res = {"metrics": metrics, "code": code, "text": strategy_port}
                except: st.error(traceback.format_exc())

    if st.session_state.port_res:
        pr = st.session_state.port_res; m = pr["metrics"]
        st.metric("Portfolio CAGR", f"{m['cagr']*100:.2f}%", delta=f"MDD {m['mdd']*100:.2f}%")
        
        fig_p = make_subplots(rows=1, cols=1)
        fig_p.add_trace(go.Scatter(x=m["cum"].index, y=(m["cum"]-1)*100, name="AI 포트폴리오"))
        fig_p.add_trace(go.Scatter(x=m["bnh"].index, y=(m["bnh"]-1)*100, name="Benchmark", line=dict(dash='dot')))
        fig_p.update_layout(height=400, template="plotly_dark")
        st.plotly_chart(fig_p, use_container_width=True)

        with st.expander("💾 이 포트폴리오 전략 저장"):
            cn, cm = st.columns([1, 2]); name = cn.text_input("전략명", key="pn2"); memo = cm.text_input("메모", key="pm2")
            if st.button("GitHub 저장", key="btns2"):
                if name: add_strategy(name, memo, pr["code"], "portfolio", pr["text"]); st.rerun()

# ────── TAB 3: 매크로 대시보드 ──────
with tab3:
    st.markdown('<p class="section-title">📡 FRED 매크로 지표 시각화</p>', unsafe_allow_html=True)
    if not fred_key: st.warning("FRED API Key가 필요합니다.")
    else:
        cat = st.selectbox("카테고리", list(FRED_INDICATORS.keys()))
        inds = st.multiselect("지표 선택", list(FRED_INDICATORS[cat].keys()), default=list(FRED_INDICATORS[cat].keys())[:1])
        
        if st.button("📊 지표 불러오기"):
            fig_m = make_subplots(rows=len(inds), cols=1, shared_xaxes=True)
            for i, tid in enumerate(inds):
                s = fetch_fred_data(tid, fred_key, s_date)
                fig_m.add_trace(go.Scatter(x=s.index, y=s.values, name=FRED_INDICATORS[cat][tid]), row=i+1, col=1)
            fig_m.update_layout(height=200*len(inds), template="plotly_dark", showlegend=False)
            st.plotly_chart(fig_m, use_container_width=True)

# ────── TAB 4: 코드 & 저장소 ──────
with tab4:
    sub_a, sub_b = st.tabs(["✍️ 직접 코드 실행", "📚 저장된 전략 (GitHub)"])
    with sub_a:
        c_code = st.text_area("파이썬 코드", height=300, value=st.session_state.custom_code_val)
        if st.button("🚀 실행"):
            try:
                sandbox = {"pd": pd, "np": np, "math": math, "yf": yf, "plt": plt, "st": st, "go": go}
                exec(c_code, sandbox, sandbox)
            except: st.error(traceback.format_exc())
        
        with st.expander("💾 저장하기"):
            cn, cm = st.columns([1, 2]); name = cn.text_input("이름", key="cn4"); memo = cm.text_input("메모", key="cm4")
            if st.button("저장", key="btns4"):
                if name: add_strategy(name, memo, c_code, "free"); st.rerun()

    with sub_b:
        strats = load_strategies()
        for s in strats:
            with st.expander(f"📁 {s['name']} ({s['type']}) - {s['saved_at']}"):
                st.write(s['memo'])
                col1, col2 = st.columns(2)
                if col1.button("🔄 에디터로 불러오기", key=f"ld_{s['id']}"):
                    st.session_state.custom_code_val = s['code']; st.rerun()
                if col2.button("🗑️ 삭제", key=f"del_{s['id']}"):
                    delete_strategy(s['id']); st.rerun()
                st.code(s['code'])
