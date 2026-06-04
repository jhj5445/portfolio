import streamlit as st
import sys
import ssl
import urllib3

# SSL 경고 무시 및 SSL 기본 컨텍스트 변경
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

# curl_cffi SSL 검증 강제 해제 Monkey Patch (Yahoo Finance 차단 우회 및 SSL 인증서 검증 에러 해결)
try:
    import curl_cffi.requests as curl_requests
    original_request = curl_requests.Session.request
    
    def patched_request(self, method, url, *args, **kwargs):
        kwargs['verify'] = False # SSL 인증서 검증 무력화
        return original_request(self, method, url, *args, **kwargs)
        
    curl_requests.Session.request = patched_request
except Exception as e:
    pass

import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 기본 설정 및 모바일 우선 뷰포트 지원
st.set_page_config(
    page_title="모바일 ETF 리밸런싱 계산기",
    page_icon="📱",
    layout="centered", # 모바일 최적화를 위해 centered 레이아웃 선택
    initial_sidebar_state="collapsed" # 사이드바 기본 숨김
)

# 2. 고급 스타일링 (CSS 주입)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=Outfit:wght@400;600;700;800&display=swap');

/* 전체 앱 글꼴 및 배경색 */
html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Noto Sans KR', 'Outfit', sans-serif;
    background-color: #0f172a; /* Slate 900 다크블루 */
    color: #f8fafc;
}

/* 앱 타이틀 영역 스타일 */
.app-header {
    background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 24px;
    text-align: center;
    margin-bottom: 5px;
    margin-top: 10px;
}
.app-subtitle {
    font-size: 13px;
    color: #94a3b8;
    text-align: center;
    margin-bottom: 20px;
}

/* 카드 뉴스 스타일의 메트릭 카드 커스텀 */
div[data-testid="metric-container"] {
    background-color: #1e293b; /* Slate 800 */
    border-radius: 12px;
    padding: 12px 16px;
    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    border: 1px solid #334155;
    margin-bottom: 12px;
}

div[data-testid="stMetricValue"] {
    font-size: 20px !important;
    font-weight: 700 !important;
    color: #38bdf8 !important;
}

div[data-testid="stMetricLabel"] {
    font-size: 12px !important;
    color: #94a3b8 !important;
}

/* 탭 버튼 스타일링 */
button[data-baseweb="tab"] {
    font-size: 15px !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
    padding: 10px 12px !important;
    background-color: transparent !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #38bdf8 !important; /* 하늘색 강조 */
    border-bottom: 3px solid #38bdf8 !important;
}

/* 리밸런싱 액션 카드 스타일 */
.action-card {
    background-color: #1e293b;
    border-left: 5px solid #10b981; /* 기본 매수(초록색) */
    border-radius: 8px;
    padding: 14px;
    margin-bottom: 12px;
    border-top: 1px solid #334155;
    border-right: 1px solid #334155;
    border-bottom: 1px solid #334155;
}
.action-card.action-sell {
    border-left-color: #f43f5e; /* 매도(붉은색) */
}
.action-card.action-keep {
    border-left-color: #64748b; /* 유지(회색) */
}

.action-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 700;
    font-size: 15px;
    margin-bottom: 6px;
}
.badge-buy {
    background-color: #064e3b;
    color: #34d399;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
}
.badge-sell {
    background-color: #4c0519;
    color: #fb7185;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
}
.badge-keep {
    background-color: #334155;
    color: #94a3b8;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
}

.action-body {
    font-size: 13px;
    color: #cbd5e1;
    line-height: 1.5;
}

/* 추가 정보 박스 */
.info-box {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 10px;
    font-size: 12px;
    color: #94a3b8;
    margin-top: 10px;
}
</style>
""", unsafe_allow_html=True)

# 3. yfinance 주가 캐싱 함수
@st.cache_data(ttl=3600)  # 1시간 동안 가격 데이터 캐싱
def fetch_ticker_data(ticker_symbol):
    """
    주어진 티커 기호를 이용해 주가 및 한글/영문 이름을 조회합니다.
    한국 ETF/주식의 경우 6자리 숫자만 들어오면 자동으로 '.KS'를 붙여서 조회합니다.
    """
    ticker_clean = ticker_symbol.strip()
    
    # 6자리 숫자인 경우 자동 .KS 보정
    if len(ticker_clean) == 6 and ticker_clean.isdigit():
        ticker_clean = f"{ticker_clean}.KS"
        
    try:
        t = yf.Ticker(ticker_clean)
        # 캐싱된 빠른 조회를 위해 fast_info 사용 또는 history 호출
        hist = t.history(period="1d")
        if hist.empty:
            return None
        
        current_price = int(hist['Close'].iloc[-1])
        
        # 종목명 획득 시도 (한글명 획득 불가시 shortName이나 입력 코드 사용)
        info = t.info
        name = info.get('shortName', ticker_symbol)
        
        # 국내 대형 ETF의 경우 잘 알려진 매핑 정보 보완
        kr_etf_map = {
            '069500.KS': 'KODEX 200',
            '379800.KS': 'TIGER 미국나스닥100',
            '133690.KS': 'TIGER 미국S&P500',
            '360750.KS': 'TIGER 미국테크TOP10 INDXX',
            '273130.KS': 'KODEX 종합채권(AA-이상)액티브',
            '251340.KS': 'KODEX 미국채울트라30년선물(H)',
            '305080.KS': 'TIGER 200TR',
            '453810.KS': 'ACE 미국S&P500',
            '454580.KS': 'KODEX CD금리액티브(합성)'
        }
        if ticker_clean in kr_etf_map:
            name = kr_etf_map[ticker_clean]
            
        return {
            'ticker': ticker_clean,
            'name': name,
            'price': current_price
        }
    except Exception as e:
        return None

# 4. 세션 상태 초기화 (Session State)
if 'portfolio' not in st.session_state:
    # 기본 포트폴리오 템플릿
    st.session_state.portfolio = pd.DataFrame([
        {'종목명': 'KODEX 200', '티커': '069500.KS', '현재가': 35600, '보유수량': 10, '목표비중': 40},
        {'종목명': 'TIGER 미국나스닥100', '티커': '379800.KS', '현재가': 15400, '보유수량': 40, '목표비중': 60}
    ])

if 'cash' not in st.session_state:
    st.session_state.cash = 1000000  # 가용 예수금 기본값 100만원

# 5. UI 타이틀
st.markdown('<div class="app-header">📱 ETF 리밸런싱 계산기</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">모바일 최적화 자산배분 플래너 (KODEX, TIGER 등 국내 ETF)</div>', unsafe_allow_html=True)

# 6. 실시간 주가 새로고침 트리거
def refresh_prices():
    updated_portfolio = st.session_state.portfolio.copy()
    for index, row in updated_portfolio.iterrows():
        res = fetch_ticker_data(row['티커'])
        if res:
            updated_portfolio.at[index, '현재가'] = res['price']
            # 기존 종목명이 티커 번호와 같거나 비어있던 경우 한글/영문명 자동 보정
            if row['종목명'] == row['티커'] or row['종목명'].strip() == "":
                updated_portfolio.at[index, '종목명'] = res['name']
    st.session_state.portfolio = updated_portfolio
    st.success("🔄 현재 주가 데이터를 업데이트했습니다!")

# 7. 데이터 전처리 및 계산 로직 호출을 위한 함수화
def get_metrics_and_calculations():
    df = st.session_state.portfolio.copy()
    cash = st.session_state.cash
    
    # 평가금액 계산
    df['평가금액'] = df['현재가'] * df['보유수량']
    total_etf_value = df['평가금액'].sum()
    total_asset = total_etf_value + cash
    
    # 현재 비중 (%)
    if total_asset > 0:
        df['현재비중'] = (df['평가금액'] / total_asset) * 100
    else:
        df['현재비중'] = 0.0
        
    # 목표 비중의 합
    total_target_pct = df['목표비중'].sum()
    
    return df, cash, total_etf_value, total_asset, total_target_pct

# 8. 핵심 연산 및 상단 요약 영역 (Summary Cards)
df_calc, current_cash, total_etfs, total_wealth, target_sum = get_metrics_and_calculations()

# 상단 요약 정보 카드 (2x1 또는 3x1로 좁은 화면에서도 깨지지 않게 2개 컬럼 배치)
col1, col2 = st.columns(2)
with col1:
    st.metric(
        label="💸 총 자산 가치 (평가금 + 예수금)", 
        value=f"{total_wealth:,.0f} 원", 
        delta=f"ETF: {total_etfs:,.0f} 원"
    )
with col2:
    status_emoji = "🎯" if abs(target_sum - 100.0) < 0.01 else "⚠️"
    status_text = "정상" if abs(target_sum - 100.0) < 0.01 else "조정 필요"
    st.metric(
        label=f"{status_emoji} 설정 비중 합계", 
        value=f"{target_sum:.1f} %", 
        delta=status_text if abs(target_sum - 100.0) < 0.01 else f"100% 대비 {target_sum - 100.0:+.1f}%"
    )

# 비중 경고 배너
if abs(target_sum - 100.0) > 0.01:
    st.warning(f"⚠️ 목표 비중의 합이 **{target_sum:.1f}%**입니다. 리밸런싱의 정확한 계산을 위해 100%로 맞추어 주세요.")

st.write("---")

# 9. 탭 인터페이스 (모바일 스크롤 최소화 전략)
tab1, tab2, tab3 = st.tabs(["🔹 자산 입력 (Inputs)", "📊 비중 차트 (Charts)", "📋 리밸런싱 가이드 (Actions)"])

# ==========================================
# 🔹 [Tab 1] 자산 입력 및 포트폴리오 에디터
# ==========================================
with tab1:
    # 1) 가용 예수금 설정
    new_cash = st.number_input(
        "💵 가용 예수금 (원)", 
        min_value=0, 
        value=int(st.session_state.cash), 
        step=50000,
        format="%d",
        help="포트폴리오 리밸런싱에 사용할 계좌 내 현금 예수금입니다."
    )
    if new_cash != st.session_state.cash:
        st.session_state.cash = new_cash
        st.rerun()

    st.markdown("#### 📈 포트폴리오 종목 관리")
    
    # 2) 신규 종목 추가 UI (단일 로우 모바일 레이아웃)
    add_col1, add_col2 = st.columns([2, 1])
    with add_col1:
        new_ticker = st.text_input(
            "종목코드/티커 추가", 
            placeholder="예: 379800 또는 069500",
            label_visibility="collapsed"
        )
    with add_col2:
        add_btn = st.button("➕ 추가", use_container_width=True)

    if add_btn and new_ticker:
        with st.spinner("주가 조회 중..."):
            res = fetch_ticker_data(new_ticker)
            if res:
                # 이미 종목 리스트에 존재하는지 체크
                if res['ticker'] in st.session_state.portfolio['티커'].values:
                    st.error("이미 포트폴리오에 존재하는 종목입니다.")
                else:
                    new_row = {
                        '종목명': res['name'],
                        '티커': res['ticker'],
                        '현재가': res['price'],
                        '보유수량': 0,
                        '목표비중': 0
                    }
                    st.session_state.portfolio = pd.concat([
                        st.session_state.portfolio, 
                        pd.DataFrame([new_row])
                    ], ignore_index=True)
                    st.success(f"✅ {res['name']} ({res['ticker']}) 추가 완료!")
                    st.rerun()
            else:
                st.error("티커 조회에 실패했습니다. 올바른 종목코드인지 확인해주세요.")

    # 3) st.data_editor 테이블 편집 영역
    st.markdown("##### ✏️ 보유 수량 및 목표 비중 수정")
    
    # 편집 가능 컬럼 지정 및 설정
    edited_df = st.data_editor(
        st.session_state.portfolio,
        column_config={
            "종목명": st.column_config.TextColumn("종목명", width="medium"),
            "티커": st.column_config.TextColumn("티커 (조회용)", disabled=True, width="small"),
            "현재가": st.column_config.NumberColumn("현재가 (원)", format="%d원", width="small"),
            "보유수량": st.column_config.NumberColumn("보유수량 (주)", min_value=0, step=1, format="%d", width="small"),
            "목표비중": st.column_config.NumberColumn("목표(%)", min_value=0, max_value=100, step=5, format="%d%%", width="small"),
        },
        hide_index=True,
        use_container_width=True,
        num_rows="fixed" # 행 추가는 상단 폼에서, 수정만 테이블에서 수행하도록 고정
    )
    
    # 세션 상태 업데이트 (수정사항 즉시 반영)
    if not edited_df.equals(st.session_state.portfolio):
        st.session_state.portfolio = edited_df
        st.rerun()

    # 4) 종목 삭제 및 주가 새로고침 액션 버튼
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("🔄 주가 새로고침", use_container_width=True, help="yfinance에서 현재가를 다시 불러옵니다."):
            refresh_prices()
            st.rerun()
    with btn_col2:
        # 삭제 대상 선택 UI
        delete_target = st.selectbox(
            "삭제할 종목 선택", 
            options=["선택 안 함"] + list(st.session_state.portfolio['종목명'].values),
            label_visibility="collapsed"
        )
        if delete_target != "선택 안 함":
            if st.button("🗑️ 선택 종목 삭제", use_container_width=True, type="secondary"):
                st.session_state.portfolio = st.session_state.portfolio[st.session_state.portfolio['종목명'] != delete_target].reset_index(drop=True)
                st.success(f"{delete_target} 종목이 삭제되었습니다.")
                st.rerun()

    st.markdown("""
    <div class="info-box">
    💡 <b>Tip:</b> 스마트폰 터치로 테이블의 '보유수량'과 '목표(%)' 칸을 직접 수정할 수 있습니다.<br>
    한국 ETF는 6자리 숫자만 넣고 <b>➕ 추가</b>를 누르면 가격 정보와 종목명이 자동으로 조회됩니다.
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# 📊 [Tab 2] 비중 차트
# ==========================================
with tab2:
    st.markdown("#### 📊 현재 vs 목표 비중 비교")
    
    if len(df_calc) > 0:
        # 모바일 가로 폭을 감안하여 1개의 Donut 차트에 현재/목표 비중을 번갈아 보거나, 두 링을 중첩 혹은 사이드바이사이드로 그립니다.
        # 모바일 세로형 스크롤 레이아웃에 맞게 2개의 Donut 차트를 위아래로 깔끔하게 배치합니다.
        
        # 1. 현재 포트폴리오 실제 비중 (예수금 포함)
        current_data = []
        for _, row in df_calc.iterrows():
            if row['평가금액'] > 0:
                current_data.append({'자산': row['종목명'], '비중': row['현재비중']})
        if current_cash > 0:
            current_data.append({'자산': '현금(예수금)', '비중': (current_cash / total_wealth) * 100})
            
        df_current_pie = pd.DataFrame(current_data)
        
        # 2. 목표 포트폴리오 비중
        df_target_pie = df_calc[['종목명', '목표비중']].copy().rename(columns={'종목명': '자산', '목표비중': '비중'})
        if target_sum < 100.0:
            df_target_pie = pd.concat([df_target_pie, pd.DataFrame([{'자산': '현금(미배분)', '비중': 100.0 - target_sum}])], ignore_index=True)
        
        # 차트 그리기
        fig_curr = px.pie(
            df_current_pie, 
            values='비중', 
            names='자산', 
            hole=0.5,
            title="현재 자산 비중 (실제)",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_curr.update_traces(textinfo='percent+label', textposition='inside')
        fig_curr.update_layout(
            showlegend=False, 
            margin=dict(t=40, b=10, l=10, r=10),
            height=280,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#fafafa')
        )
        st.plotly_chart(fig_curr, use_container_width=True)
        
        fig_targ = px.pie(
            df_target_pie, 
            values='비중', 
            names='자산', 
            hole=0.5,
            title="목표 자산 비중 (설정)",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_targ.update_traces(textinfo='percent+label', textposition='inside')
        fig_targ.update_layout(
            showlegend=False, 
            margin=dict(t=40, b=10, l=10, r=10),
            height=280,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#fafafa')
        )
        st.plotly_chart(fig_targ, use_container_width=True)

        # 막대그래프로도 비교 직관적으로 제공
        st.markdown("##### 📊 자산별 비중 비교 (현재 vs 목표)")
        compare_df = pd.DataFrame({
            '자산': df_calc['종목명'].tolist() + (['현금'] if current_cash > 0 else []),
            '현재비중': df_calc['현재비중'].tolist() + ([current_cash / total_wealth * 100] if current_cash > 0 else []),
            '목표비중': df_calc['목표비중'].tolist() + ([100 - target_sum] if current_cash > 0 else [])
        })
        
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=compare_df['자산'],
            x=compare_df['현재비중'],
            name='현재 비중',
            orientation='h',
            marker_color='#818cf8'
        ))
        fig_bar.add_trace(go.Bar(
            y=compare_df['자산'],
            x=compare_df['목표비중'],
            name='목표 비중',
            orientation='h',
            marker_color='#38bdf8'
        ))
        
        fig_bar.update_layout(
            barmode='group',
            height=250,
            margin=dict(t=10, b=10, l=10, r=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#fafafa', size=11),
            xaxis=dict(title="비중 (%)", gridcolor='#334155'),
            yaxis=dict(gridcolor='rgba(0,0,0,0)')
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("비중 차트를 그릴 데이터가 없습니다. 먼저 종목을 추가해 주세요.")


# ==========================================
# 📋 [Tab 3] 리밸런싱 가이드
# ==========================================
with tab3:
    st.markdown("#### 🛒 리밸런싱 주문 가이드")
    
    if len(df_calc) == 0:
        st.info("포트폴리오에 종목이 없습니다. 먼저 종목을 설정해 주세요.")
    elif abs(target_sum - 100.0) > 0.01:
        st.error("⚠️ 리밸런싱 계산을 위해 자산 입력 탭에서 **목표 비중 합계를 100%**로 맞추어 주세요.")
    else:
        # 리밸런싱 가이드 연산 시작
        action_plans = []
        total_required_cash = 0  # 총 거래 필요 금액
        
        # 1. 목표 수량 및 변동 수량 계산
        df_calc['목표금액'] = total_wealth * (df_calc['목표비중'] / 100.0)
        df_calc['목표수량'] = (df_calc['목표금액'] / df_calc['현재가']).apply(np.floor).astype(int) # 소수점 이하 절사 (주 단위 매매)
        df_calc['조정수량'] = df_calc['목표수량'] - df_calc['보유수량']
        
        for index, row in df_calc.iterrows():
            diff_q = row['조정수량']
            price = row['현재가']
            etf_name = row['종목명']
            ticker_name = row['티커']
            
            trade_value = abs(diff_q * price)
            
            if diff_q > 0:
                action_plans.append({
                    'type': 'buy',
                    'text': f"🛒 **{diff_q}주 추가 매수**",
                    'class': 'action-card',
                    'badge': '<span class="badge-buy">추가 매수</span>',
                    'etf': f"{etf_name} ({ticker_name.split('.')[0]})",
                    'details': f"현재 {row['보유수량']}주 ➔ 목표 {row['목표수량']}주<br>예상 거래 금액: <b>{trade_value:,.0f} 원</b> (현재가: {price:,.0f}원)"
                })
                total_required_cash += trade_value
            elif diff_q < 0:
                action_plans.append({
                    'type': 'sell',
                    'text': f"✂️ **{abs(diff_q)}주 매도**",
                    'class': 'action-card action-sell',
                    'badge': '<span class="badge-sell">축소 매도</span>',
                    'etf': f"{etf_name} ({ticker_name.split('.')[0]})",
                    'details': f"현재 {row['보유수량']}주 ➔ 목표 {row['목표수량']}주<br>예상 확보 금액: <b>{trade_value:,.0f} 원</b> (현재가: {price:,.0f}원)"
                })
                total_required_cash -= trade_value  # 매도는 현금 유입
            else:
                action_plans.append({
                    'type': 'keep',
                    'text': "🔍 **변동 없음 (유지)**",
                    'class': 'action-card action-keep',
                    'badge': '<span class="badge-keep">비중 유지</span>',
                    'etf': f"{etf_name} ({ticker_name.split('.')[0]})",
                    'details': f"현재 {row['보유수량']}주 ➔ 목표 {row['목표수량']}주<br>현재가: {price:,.0f}원"
                })

        # 최종 예상 예수금 계산
        final_used_etfs_value = (df_calc['목표수량'] * df_calc['현재가']).sum()
        final_estimated_cash = total_wealth - final_used_etfs_value
        
        # 리밸런싱 결과 요약
        st.markdown(f"""
        <div style="background-color: #1e293b; border-radius: 8px; padding: 15px; margin-bottom: 20px; border: 1px solid #334155;">
            <div style="font-size: 13px; color: #94a3b8; margin-bottom: 4px;">리밸런싱 매매 요약</div>
            <div style="font-size: 16px; font-weight: 700; margin-bottom: 8px;">
                최종 예상 예수금 잔고: <span style="color: #38bdf8; font-size: 18px;">{final_estimated_cash:,.0f} 원</span>
            </div>
            <div style="font-size: 12px; color: #cbd5e1;">
                • 리밸런싱 전 예수금: {current_cash:,.0f} 원<br>
                • 최종 포트폴리오 가치: {final_used_etfs_value:,.0f} 원 ({df_calc['목표비중'].sum()}% 배분)<br>
                • <b>소수점 절사(1주 미만 매수 불가)</b>로 인해 예수금 잔액 <b>{final_estimated_cash:,.0f}원</b>이 남습니다.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 거래 대상 목록 카드 출력
        st.markdown("##### 📋 주문 가이드 리스트")
        
        for plan in action_plans:
            st.markdown(f"""
            <div class="{plan['class']}">
                <div class="action-header">
                    <span>{plan['etf']}</span>
                    {plan['badge']}
                </div>
                <div style="font-weight: 600; font-size: 14px; color: #fff; margin-bottom: 6px;">
                    {plan['text']}
                </div>
                <div class="action-body">
                    {plan['details']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        st.success("🎉 리밸런싱 결과가 계산되었습니다! 모바일 MTS 앱을 실행하여 주문을 넣어주세요.")
