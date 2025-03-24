import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import threading
import schedule
import json

# ========================#
# 1. 페이지 및 인증 설정  #
# ========================#
st.set_page_config(
    page_title="정액 투자 시뮬레이터",
    page_icon="💰",
    layout="wide"
)

# --- 암호 보호 ---
PASSWORD = "secret123"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    placeholder = st.empty()
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            user_password = placeholder.text_input("페이지 접근을 위한 암호를 입력하세요", type="password")
    if user_password:
        if user_password != PASSWORD:
            placeholder.error("암호가 틀렸습니다. 페이지에 접근할 수 없습니다.")
            st.stop()
        else:
            st.session_state["authenticated"] = True
            placeholder.empty()
            st.success("접속 성공!")
    else:
        st.info("암호를 입력하세요.")
        st.stop()

# ========================#
# 2. 스타일 및 CSS         #
# ========================#
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .st-emotion-cache-16txtl3 h1 { 
        color: #003b70; 
        text-align: center; 
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .st-emotion-cache-16txtl3 h2, .st-emotion-cache-16txtl3 h3 { 
        color: #003b70; 
    }
    .stMetric { 
        background-color: white; 
        padding: 20px; 
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); 
        margin-bottom: 1rem;
    }
    .highlight-box {
        background-color: #e6f2ff;
        border-left: 4px solid #003b70;
        padding: 15px;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .sidebar-content {
        padding: 15px 0;
    }
    .footer {
        text-align: center;
        color: #6c757d;
        padding: 20px 0;
        font-size: 0.8rem;
    }
    .small-text {
        font-size: 0.8rem;
        color: #6c757d;
    }
    .warning-text {
        font-size: 0.9rem;
        color: #856404;
        background-color: #fff3cd;
        border-left: 4px solid #ffeeba;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# ========================#
# 3. 사이드바: 입력 및 설정 #
# ========================#
st.sidebar.markdown("<h3 style='text-align: center; color: #003b70;'>투자 대상 선택</h3>", unsafe_allow_html=True)
asset_option = st.sidebar.radio("투자 대상 선택", options=["달러 (USDKRW=X)", "직접 입력"])
if asset_option == "달러 (USDKRW=X)":
    asset_ticker = "USDKRW=X"
else:
    asset_ticker = st.sidebar.text_input("티커 입력 (예: AAPL, ^KS11, 005930.KS)", value="AAPL")
    if not asset_ticker:
        st.sidebar.warning("티커를 입력해주세요.")

# 해외 투자(달러 전환 적용) 여부  
overseas_investment = False
if asset_ticker not in ["USDKRW=X"] and not asset_ticker.endswith((".KS", ".KQ", ".L", ".MI")):
    overseas_investment = st.sidebar.checkbox("해외 투자 (달러 전환 적용)", value=False)

# --- 시뮬레이션 기본 설정 ---
st.sidebar.markdown("<h3 style='text-align: center; color: #003b70;'>시뮬레이션 설정</h3>", unsafe_allow_html=True)
# 전체 운용 기간 선택
time_range = st.sidebar.selectbox(
    "전체 운용 기간",
    ["1일", "1주일", "1개월", "6개월", "1년", "3년", "5년", "7년", "10년", "15년", "20년"],
    index=4
)
# 납입 간격
interval_option = st.sidebar.selectbox(
    "납입 간격",
    ["1일", "1주", "1개월", "1년"],
    index=2
)

# 기준 날짜 (만기일)
today_date = datetime.today().date()
if "date_input" not in st.session_state:
    st.session_state["date_input"] = today_date
selected_date = st.sidebar.date_input("기준 날짜 선택 (만기일)", key="date_input")

# 투자금액 및 기간
investment_per_period = st.sidebar.number_input(
    "매 기간 납입 원화 금액",
    value=1000000,
    step=100000,
    format="%d"
)

total_years_map = {
    "1일": 1/365,
    "1주일": 1/52,
    "1개월": 1/12,
    "6개월": 0.5,
    "1년": 1,
    "3년": 3,
    "5년": 5,
    "7년": 7,
    "10년": 10,
    "15년": 15,
    "20년": 20
}
total_period_years = total_years_map[time_range]

if total_period_years < 1:
    purchase_period_years = total_period_years
else:
    purchase_period_years = st.sidebar.number_input(
        "납입 기간 (년)",
        min_value=0.0,
        max_value=float(total_period_years),
        value=float(total_period_years/2),
        step=0.5
    )

holding_period_years = st.sidebar.number_input(
    "유지 기간 (년)",
    min_value=0.0,
    max_value=float(total_period_years - purchase_period_years),
    value=0.0,
    step=0.5
)

conversion_period_years = total_period_years - (purchase_period_years + holding_period_years)
if conversion_period_years < 0:
    st.error("납입 기간과 유지 기간의 합이 전체 운용 기간을 초과합니다. 값을 다시 확인해주세요.")
    st.stop()

interest_rate_percent = st.sidebar.number_input(
    "유지 종료 시점 약정 이자율 (%)",
    value=0.0,
    step=0.1,
    format="%.2f"
)
st.sidebar.markdown("<div class='small-text'>* 유지 기간 종료 시 보유 자산에 1회 적용</div>", unsafe_allow_html=True)

compound_interest_rate_percent = st.sidebar.number_input(
    "전환 후 복리 이자율 (%)",
    value=0.0,
    step=0.1,
    format="%.2f"
)
st.sidebar.markdown("<div class='small-text'>* 전환(적립) 기간 동안 매년 복리로 적용</div>", unsafe_allow_html=True)

# 리스크 시나리오 조정 (낙관/보수)
risk_adjustment = st.sidebar.number_input(
    "리스크 조정치 (%) (낙관: +, 보수: -)",
    value=1.0,
    step=0.1,
    format="%.2f"
)

st.sidebar.markdown("<hr>", unsafe_allow_html=True)

# --- 설정 저장/불러오기 ---
st.sidebar.markdown("<h3 style='text-align: center; color: #003b70;'>설정 저장/불러오기</h3>", unsafe_allow_html=True)
def get_config_dict():
    return {
        "asset_option": asset_option,
        "asset_ticker": asset_ticker,
        "overseas_investment": overseas_investment,
        "time_range": time_range,
        "interval_option": interval_option,
        "selected_date": selected_date.strftime("%Y-%m-%d"),
        "investment_per_period": investment_per_period,
        "purchase_period_years": purchase_period_years,
        "holding_period_years": holding_period_years,
        "interest_rate_percent": interest_rate_percent,
        "compound_interest_rate_percent": compound_interest_rate_percent,
        "risk_adjustment": risk_adjustment
    }

config_json = json.dumps(get_config_dict(), ensure_ascii=False, indent=4)
st.sidebar.download_button("현재 설정 다운로드", data=config_json, file_name="investment_config.json", mime="application/json")

uploaded_file = st.sidebar.file_uploader("설정 파일 업로드", type=["json"])
if uploaded_file is not None:
    try:
        uploaded_config = json.load(uploaded_file)
        st.session_state["uploaded_config"] = uploaded_config
        st.sidebar.success("설정 파일이 성공적으로 불러와졌습니다. (페이지 새로고침 후 반영)")
    except Exception as e:
        st.sidebar.error(f"설정 파일 로드 오류: {e}")

# ========================#
# 4. 캐싱 및 데이터 함수   #
# ========================#
@st.cache_data(ttl=3600)
def get_price_data_range(ticker_symbol, start, end):
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(start=start, end=end)
    return hist

@st.cache_data(ttl=300)
def get_latest_price(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    latest_data = ticker.history(period="1d")
    if not latest_data.empty:
        return latest_data['Close'].iloc[-1]
    else:
        return None

# ========================#
# 5. 데이터 자동 업데이트  #
# ========================#
def update_data():
    st.cache_data.clear()
    st.session_state.next_update = datetime.now() + timedelta(hours=1)

def run_scheduler():
    schedule.every(1).hour.do(update_data)
    while True:
        schedule.run_pending()
        time.sleep(60)

if 'scheduler_started' not in st.session_state:
    st.session_state.scheduler_started = True
    st.session_state.next_update = datetime.now() + timedelta(hours=1)
    threading.Thread(target=run_scheduler, daemon=True).start()

# ===================================#
# 6. 시뮬레이션 계산 함수 (모듈화)       #
# ===================================#
def run_simulation(investment_amt, interest_rate, compound_rate):
    months_total = int(round(total_period_years * 12))
    end_date = pd.to_datetime(selected_date)
    start_date = end_date - pd.DateOffset(months=months_total)
    start_str = start_date.strftime("%Y-%m-%d")
    min_data_date = pd.to_datetime("2003-12-01")
    
    with st.spinner("기간 데이터 불러오는 중입니다..."):
        price_data = get_price_data_range(asset_ticker, start=start_str, end=(end_date + pd.DateOffset(days=1)).strftime("%Y-%m-%d"))
    
    if price_data.empty:
        st.error("가격 데이터를 불러올 수 없습니다.")
        st.stop()
    
    if price_data.index.tz is not None:
        tz_info = price_data.index.tz
        if start_date.tzinfo is None:
            start_date = start_date.tz_localize(tz_info)
        if end_date.tzinfo is None:
            end_date = end_date.tz_localize(tz_info)
    
    data_min_date = price_data.index.min()
    if start_date < data_min_date:
        st.warning(f"선택한 운용 기간이 데이터 범위를 벗어납니다. 적립 시작일을 {data_min_date.strftime('%Y년 %m월 %d일')}로 조정합니다.")
        start_date = data_min_date

    if interval_option == "1일":
        freq = "D"
    elif interval_option == "1주":
        freq = "W"
    elif interval_option == "1개월":
        freq = "MS"
    elif interval_option == "1년":
        freq = "AS"
    
    all_dates = pd.date_range(start=start_date, end=end_date, freq=freq, tz=price_data.index.tz)
    sampled_data = price_data.reindex(all_dates, method='ffill')
    
    if overseas_investment:
        usdkrw_data = get_price_data_range("USDKRW=X", start=start_str, end=(end_date + pd.DateOffset(days=1)).strftime("%Y-%m-%d"))
        usdkrw_data = usdkrw_data.reindex(all_dates, method='ffill')
    
    months_purchase = int(round(purchase_period_years * 12))
    purchase_end_date = start_date + pd.DateOffset(months=months_purchase)
    purchase_dates = pd.date_range(start=start_date, end=purchase_end_date, freq=freq, tz=price_data.index.tz, inclusive='left')
    purchase_data = price_data.reindex(purchase_dates, method='ffill')
    if overseas_investment:
        usdkrw_purchase = usdkrw_data.reindex(purchase_dates, method='ffill')
    
    total_investment_purchase = investment_amt * len(purchase_dates)
    cumulative_effective_prices = []
    cumulative_reciprocal = 0.0
    
    if overseas_investment:
        effective_purchase_prices = usdkrw_purchase['Close'] * purchase_data['Close']
        for i, price in enumerate(effective_purchase_prices):
            cumulative_reciprocal += 1 / price
            cumulative_effective_prices.append((i + 1) / cumulative_reciprocal)
        total_units_purchase = (investment_amt / effective_purchase_prices).sum()
    else:
        for i, price in enumerate(purchase_data['Close']):
            cumulative_reciprocal += 1 / price
            cumulative_effective_prices.append((i + 1) / cumulative_reciprocal)
        total_units_purchase = (investment_amt / purchase_data['Close']).sum()
    
    final_effective_price_purchase = total_investment_purchase / total_units_purchase
    
    final_units_after_contract = total_units_purchase * (1 + interest_rate/100)
    if conversion_period_years > 0:
        final_units_final = final_units_after_contract * ((1 + compound_rate/100) ** conversion_period_years)
    else:
        final_units_final = final_units_after_contract
    
    base_price = sampled_data.iloc[-1]['Close']
    if overseas_investment:
        latest_exchange_rate = get_latest_price("USDKRW=X") or 1
        base_effective_price = base_price * latest_exchange_rate
        final_holding_value = final_units_final * base_effective_price
    else:
        final_holding_value = final_units_final * base_price
    
    profit_rate = ((final_holding_value - total_investment_purchase) / total_investment_purchase) * 100

    latest_price = get_latest_price(asset_ticker) or base_price
    if overseas_investment:
        latest_exchange_rate = get_latest_price("USDKRW=X") or 1
        current_effective_price = latest_price * latest_exchange_rate
    else:
        current_effective_price = latest_price
    
    results = {
        "total_investment_purchase": total_investment_purchase,
        "final_holding_value": final_holding_value,
        "profit_rate": profit_rate,
        "final_effective_price_purchase": final_effective_price_purchase,
        "total_units_purchase": total_units_purchase,
        "base_price": base_price,
        "current_effective_price": current_effective_price,
        "sampled_dates": all_dates,
        "effective_price_series": (sampled_data['Close'] * (usdkrw_data['Close'] if overseas_investment else 1)).values,
        "cumulative_effective_prices": cumulative_effective_prices,
        "purchase_dates": purchase_dates,
        "start_date": start_date,
        "purchase_end_date": purchase_end_date,
        "holding_end_date": purchase_end_date + pd.DateOffset(months=int(round(holding_period_years*12))),
        "end_date": end_date
    }
    return results

# ===================================#
# 7. 메인 영역: 시뮬레이션 및 탭 구성     #
# ===================================#
st.title("정액 투자 시뮬레이터")
st.markdown("<div class='small-text'>실시간 가격 기준 성과 예측</div>", unsafe_allow_html=True)
st.markdown(f"<div class='small-text'>마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 다음 업데이트: {st.session_state.next_update.strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)
st.markdown("<div class='warning-text'>⚠️ 현재는 2003년 12월 데이터부터 제공됩니다. 이전 데이터 선택 시 자동으로 시작일이 조정됩니다.</div>", unsafe_allow_html=True)

sim_base = run_simulation(investment_per_period, interest_rate_percent, compound_interest_rate_percent)
sim_optimistic = run_simulation(investment_per_period, interest_rate_percent + risk_adjustment, compound_interest_rate_percent + risk_adjustment)
sim_pessimistic = run_simulation(investment_per_period, interest_rate_percent - risk_adjustment, compound_interest_rate_percent - risk_adjustment)

tabs = st.tabs(["📊 투자 성과", "📈 가격 및 차트", "🎯 목표 달성 역산"])

with tabs[0]:
    st.subheader("투자 성과 결과")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 납입 원화 (기본)", f"{sim_base['total_investment_purchase']:,.0f}원")
    with col2:
        st.metric("만기 자산 가치 (기본)", f"{sim_base['final_holding_value']:,.0f}원")
    with col3:
        st.metric("예상 수익률 (기본)", f"{sim_base['profit_rate']:.2f}%", delta=f"{sim_base['profit_rate']:.2f}%")
    with col4:
        st.metric("평균 매입 가격 (기본)", f"{sim_base['final_effective_price_purchase']:.2f}원")
    
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class='small-text'>리스크 시나리오 비교 (낙관 / 보수)</div>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("만기 자산 가치 (낙관)", f"{sim_optimistic['final_holding_value']:,.0f}원")
        st.metric("예상 수익률 (낙관)", f"{sim_optimistic['profit_rate']:.2f}%")
    with col_b:
        st.metric("만기 자산 가치 (보수)", f"{sim_pessimistic['final_holding_value']:,.0f}원")
        st.metric("예상 수익률 (보수)", f"{sim_pessimistic['profit_rate']:.2f}%")
    st.markdown(f"<div class='small-text'>납입 기간: {purchase_period_years:.2f}년 | 유지 기간: {holding_period_years:.2f}년 | 전환 기간: {conversion_period_years:.2f}년</div>", unsafe_allow_html=True)

with tabs[1]:
    st.subheader("가격 추이 및 누적 매입 평균")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sim_base["sampled_dates"],
        y=sim_base["effective_price_series"],
        mode='lines',
        name='실제 가격',
        line=dict(width=2, color='#003b70')
    ))
    fig.add_trace(go.Scatter(
        x=sim_base["purchase_dates"],
        y=sim_base["cumulative_effective_prices"],
        mode='lines',
        name='누적 매입 평균 가격',
        line=dict(dash='dot', width=2, color='#28a745')
    ))
    y_min = min(min(sim_base["effective_price_series"]), min(sim_base["cumulative_effective_prices"])) * 0.95
    y_max = max(max(sim_base["effective_price_series"]), max(sim_base["cumulative_effective_prices"])) * 1.05

    fig.add_shape(
        type="rect",
        x0=sim_base["start_date"],
        y0=y_min,
        x1=sim_base["purchase_end_date"],
        y1=y_max,
        fillcolor="#e6f2ff",
        opacity=0.3,
        layer="below",
        line_width=0
    )
    fig.add_shape(
        type="rect",
        x0=sim_base["purchase_end_date"],
        y0=y_min,
        x1=sim_base["purchase_end_date"] + pd.DateOffset(months=int(round(holding_period_years*12))),
        y1=y_max,
        fillcolor="#fff2e6",
        opacity=0.3,
        layer="below",
        line_width=0
    )
    fig.add_shape(
        type="rect",
        x0=sim_base["purchase_end_date"] + pd.DateOffset(months=int(round(holding_period_years*12))),
        y0=y_min,
        x1=sim_base["end_date"],
        y1=y_max,
        fillcolor="#e6ffe6",
        opacity=0.3,
        layer="below",
        line_width=0
    )
    fig.add_shape(
        type='line',
        x0=sim_base["purchase_end_date"],
        y0=y_min,
        x1=sim_base["purchase_end_date"],
        y1=y_max,
        line=dict(color='#ffa94d', width=2, dash='dash')
    )
    fig.add_annotation(
        x=sim_base["purchase_end_date"],
        y=y_max * 0.98,
        text="납입 종료",
        showarrow=True,
        arrowhead=1,
        ax=40,
        ay=-40,
        font=dict(size=12, color="#ff8c00")
    )
    holding_end_date = sim_base["purchase_end_date"] + pd.DateOffset(months=int(round(holding_period_years*12)))
    fig.add_shape(
        type='line',
        x0=holding_end_date,
        y0=y_min,
        x1=holding_end_date,
        y1=y_max,
        line=dict(color='#dc3545', width=2, dash='dash')
    )
    fig.add_annotation(
        x=holding_end_date,
        y=y_max * 0.95,
        text="유지 종료 & 전환 시작",
        showarrow=True,
        arrowhead=1,
        ax=40,
        ay=-40,
        font=dict(size=12, color="#dc3545")
    )
    fig.add_trace(go.Scatter(
        x=[sim_base["purchase_end_date"], sim_base["end_date"]],
        y=[sim_base["final_effective_price_purchase"], sim_base["final_effective_price_purchase"]],
        mode='lines',
        name='최종 평균 매입 가격 (납입 기준)',
        line=dict(dash='dash', width=2, color='#dc3545')
    ))
    fig.update_layout(
        xaxis=dict(
            title='날짜',
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1년", step="year", stepmode="backward"),
                    dict(count=3, label="3년", step="year", stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(visible=True),
            tickformat="%Y년 %m월"
        ),
        yaxis=dict(title='가격 (원)', range=[y_min, y_max]),
        hovermode='x unified',
        height=500,
        plot_bgcolor='white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    col_price1, col_price2, col_price3 = st.columns(3)
    with col_price1:
        st.metric("현재 가격", f"{sim_base['current_effective_price']:.2f}원")
    with col_price2:
        st.metric("기준 날짜 가격", f"{sim_base['base_price'] * (get_latest_price('USDKRW=X') if overseas_investment else 1):.2f}원")
    with col_price3:
        st.metric("최종 평균 매입 가격", f"{sim_base['final_effective_price_purchase']:.2f}원")
    actual_start_date = sim_base["start_date"].strftime("%Y년 %m월 %d일")
    st.markdown(f"<div class='small-text'>* 실제 사용된 데이터 시작일: {actual_start_date}</div>", unsafe_allow_html=True)

with tabs[2]:
    st.subheader("목표 달성 역산")
    st.markdown("원하는 만기 자산 가치를 입력하면, 해당 목표 달성을 위해 필요한 매 기간 납입 금액을 계산합니다.")
    target_value = st.number_input("목표 만기 자산 가치 (원)", value=100000000, step=1000000, format="%d")
    
    def find_required_investment(target, low=1000, high=10000000, tol=1e3, max_iter=30):
        iteration = 0
        result = None
        while iteration < max_iter:
            mid = (low + high) / 2
            sim = run_simulation(mid, interest_rate_percent, compound_interest_rate_percent)
            final_val = sim["final_holding_value"]
            if abs(final_val - target) < tol:
                result = mid
                break
            if final_val < target:
                low = mid
            else:
                high = mid
            iteration += 1
        if result is None:
            result = mid
        return result, final_val, iteration

    if st.button("계산 실행"):
        req_investment, sim_final, iterations = find_required_investment(target_value)
        st.success(f"목표 {target_value:,.0f}원을 달성하기 위해서는 매 기간 약 {req_investment:,.0f}원의 투자 필요 (최종 시뮬레이션: {sim_final:,.0f}원, {iterations}회 반복)")
    st.markdown("<div class='small-text'>※ 단, 과거 데이터를 기반으로 한 단순 역산이므로 참고용으로만 활용해주세요.</div>", unsafe_allow_html=True)

with st.expander("❓ 자주 묻는 질문"):
    st.markdown(f"""
    **Q: 정액 투자 방식의 장점은 무엇인가요?**  
    A: 일정 금액을 정기적으로 투자하여 가격 변동에 따른 리스크를 분산시킬 수 있습니다.
    
    **Q: 약정 이자는 어떻게 적용되나요?**  
    A: 유지 기간 종료 시점에 보유 자산에 약정 이자율이 일괄 적용되고, 이후 전환(적립) 기간 동안 복리 이자율이 매년 적용됩니다.
    
    **Q: 목표 달성 역산은 어떻게 활용되나요?**  
    A: 원하는 만기 자산 가치를 입력하면, 해당 목표 달성을 위해 필요한 매 기간 투자액을 산출합니다.
    
    **Q: 2003년 12월 이전 데이터는 사용할 수 없나요?**  
    A: 현재 시뮬레이터는 Yahoo Finance 데이터를 사용하며, 2003년 12월부터의 데이터만 제공됩니다.
    """)

st.markdown("<div class='footer'>© 2025 정액 투자 시뮬레이터 | 데이터 출처: Yahoo Finance (2003년 12월부터 제공, 1시간마다 자동 업데이트)<br>이 시뮬레이터는 참고용으로만 사용하시기 바랍니다.</div>", unsafe_allow_html=True)
