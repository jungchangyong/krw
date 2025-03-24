import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import threading
import schedule

# 페이지 설정: 모든 Streamlit 명령어보다 먼저 호출되어야 합니다.
st.set_page_config(
    page_title="정액 투자 시뮬레이터",
    page_icon="💰",
    layout="wide"
)

# === 암호 보호 기능 (업데이트) ===
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

# === 이후부터 기존 코드 내용 ===

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

# ===== 투자 대상 선택 =====
st.sidebar.markdown("<h3 style='text-align: center; color: #003b70;'>투자 대상 선택</h3>", unsafe_allow_html=True)
asset_option = st.sidebar.radio("투자 대상 선택", options=["달러 (USDKRW=X)", "직접 입력"])
if asset_option == "달러 (USDKRW=X)":
    asset_ticker = "USDKRW=X"
else:
    asset_ticker = st.sidebar.text_input("티커 입력 (예: AAPL, ^KS11, 005930.KS)", value="AAPL")
    if not asset_ticker:
        st.sidebar.warning("티커를 입력해주세요.")

# 해외 투자(달러 전환 적용) 여부 선택  
overseas_investment = False
# 미국 주식이나 달러로 거래되는 자산의 경우 환전 기능 적용
if asset_ticker not in ["USDKRW=X"] and asset_ticker.endswith((".KS", ".KQ", ".L", ".MI")) == False:
    overseas_investment = st.sidebar.checkbox("해외 투자 (달러 전환 적용)", value=False)

# ===== 가격 데이터 관련 함수 =====
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

# ===== 데이터 자동 업데이트 및 스케줄러 =====
def update_data():
    st.cache_data.clear()
    next_update = datetime.now() + timedelta(hours=1)
    st.session_state.next_update = next_update

def run_scheduler():
    schedule.every(1).hour.do(update_data)
    while True:
        schedule.run_pending()
        time.sleep(60)

if 'scheduler_started' not in st.session_state:
    st.session_state.scheduler_started = True
    st.session_state.next_update = datetime.now() + timedelta(hours=1)
    threading.Thread(target=run_scheduler, daemon=True).start()

# 앱 헤더
st.title("정액 투자 시뮬레이터")
st.markdown("<div class='small-text'>실시간 가격 기준 성과 예측</div>", unsafe_allow_html=True)
st.markdown(f"<div class='small-text'>마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 다음 업데이트: {st.session_state.next_update.strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)

st.markdown("<div class='warning-text'>⚠️ 현재는 2003년 12월 데이터부터 제공됩니다. 이전 데이터 선택 시 자동으로 시작일이 조정됩니다.</div>", unsafe_allow_html=True)

# 간단한 시뮬레이션 설명
with st.expander("💡 시뮬레이션 설명"):
    desc = f"""
    **정액 투자 시뮬레이션**은 매월 동일한 원화 금액으로 **{asset_ticker}**를(을) 구매하고 일정기간 유지 후,
    유지기간 종료 시점에 약정 이자율을 일괄 적용하여 투자 자산으로 전환한 후, 전환 기간 동안 별도의 복리 이자율이 매년 적용되는 시뮬레이션입니다.
    """
    if overseas_investment:
        desc += """
        <br>**해외 투자**의 경우 매월 투자금액(원화)을 해당 시점의 USDKRW 환율로 달러로 환전한 후 주식을 구매합니다.
        """
    desc += """
    <br><br>### 주요 특징:
    - **납입 기간:** 정해진 기간 동안 매월 정액으로 구매
    - **유지 기간:** 자산을 일정 기간 보유 후 약정 이자율 적용 (일괄)
    - **전환(적립) 기간:** 유지 종료 후 전환되어 별도의 복리 이자율이 매년 적용됨
    - **가격 변동 효과:** 매입 시점의 가격과 최종 만기 가격을 비교하여 성과 예측
    <br><br>**데이터 제한:** Yahoo Finance에서 제공하는 데이터(2003년 12월 이후)만 사용됩니다.
    """
    st.markdown(desc, unsafe_allow_html=True)

# ===== 사이드바 설정 =====
st.sidebar.markdown("<h3 style='text-align: center; color: #003b70;'>적립 설정</h3>", unsafe_allow_html=True)
st.sidebar.markdown("<div class='sidebar-content'>", unsafe_allow_html=True)

time_range = st.sidebar.selectbox(
    "전체 운용 기간",
    ["1일", "1주일", "1개월", "6개월", "1년", "3년", "5년", "7년", "10년", "15년", "20년"],
    index=4
)

interval_option = st.sidebar.selectbox(
    "납입 간격",
    ["1일", "1주", "1개월", "1년"],
    index=2
)

today_date = datetime.today().date()
if "date_input" not in st.session_state:
    st.session_state["date_input"] = today_date
selected_date = st.sidebar.date_input("기준 날짜 선택 (만기일)", key="date_input")

investment_per_period = st.sidebar.number_input(
    "매 기간 납입 원화 금액",
    value=1000000,
    step=100000,
    format="%d"
)

st.sidebar.markdown("<div style='font-size: 0.8rem; color: #856404; margin-top: 5px;'>* 데이터는 2003년 12월부터 제공됩니다</div>", unsafe_allow_html=True)

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

st.sidebar.markdown("</div>", unsafe_allow_html=True)

# ===== 운용 기간 데이터 불러오기 =====
months_total = int(round(total_period_years * 12))
end_date = pd.to_datetime(selected_date)
start_date = end_date - pd.DateOffset(months=months_total)
start_str = start_date.strftime("%Y-%m-%d")

min_data_date = pd.to_datetime("2003-12-01")

with st.spinner("기간 데이터 불러오는 중입니다..."):
    price_data = get_price_data_range(asset_ticker, start=start_str, end=(end_date + pd.DateOffset(days=1)).strftime("%Y-%m-%d"))

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

# 해외 투자 시, 환율 데이터도 함께 불러옴 (원/달러)
if overseas_investment:
    usdkrw_data = get_price_data_range("USDKRW=X", start=start_str, end=(end_date + pd.DateOffset(days=1)).strftime("%Y-%m-%d"))
    usdkrw_data = usdkrw_data.reindex(all_dates, method='ffill')

months_purchase = int(round(purchase_period_years * 12))
purchase_end_date = start_date + pd.DateOffset(months=months_purchase)
purchase_dates = pd.date_range(start=start_date, end=purchase_end_date, freq=freq, tz=price_data.index.tz, inclusive='left')
purchase_data = price_data.reindex(purchase_dates, method='ffill')
if overseas_investment:
    usdkrw_purchase = usdkrw_data.reindex(purchase_dates, method='ffill')

months_holding = int(round(holding_period_years * 12))
holding_end_date = purchase_end_date + pd.DateOffset(months=months_holding)

num_investments = len(purchase_dates)
st.sidebar.markdown(f"<div class='small-text'>총 납입 횟수: {num_investments}회</div>", unsafe_allow_html=True)

if sampled_data.empty or purchase_data.empty:
    st.error("운용 기간과 납입 간격이 호환되지 않습니다. 운용 기간이 충분한지, 납입 간격을 조정해주세요.")
    st.stop()

# ===== 매입 시점 누적 평균 가격 및 총 구매 수량 계산 =====
total_investment_purchase = investment_per_period * num_investments

if overseas_investment:
    # 해외 투자 시 효과적 매입 가격(원화) = (해당일 USDKRW 환율 * 주식 가격(USD))
    effective_purchase_prices = usdkrw_purchase['Close'] * purchase_data['Close']
    cumulative_effective_prices = []
    cumulative_reciprocal = 0.0
    for i, price in enumerate(effective_purchase_prices):
        cumulative_reciprocal += 1 / price
        cumulative_effective_price = (i + 1) / cumulative_reciprocal
        cumulative_effective_prices.append(cumulative_effective_price)
    total_units_purchase = (investment_per_period / effective_purchase_prices).sum()
else:
    cumulative_effective_prices = []
    cumulative_reciprocal = 0.0
    for i, price in enumerate(purchase_data['Close']):
        cumulative_reciprocal += 1 / price
        cumulative_effective_price = (i + 1) / cumulative_reciprocal
        cumulative_effective_prices.append(cumulative_effective_price)
    total_units_purchase = (investment_per_period / purchase_data['Close']).sum()

final_effective_price_purchase = total_investment_purchase / total_units_purchase

# ===== 최종 수익률 계산 =====
final_units_after_contract = total_units_purchase * (1 + interest_rate_percent/100)
if conversion_period_years > 0:
    final_units_final = final_units_after_contract * ((1 + compound_interest_rate_percent/100) ** conversion_period_years)
else:
    final_units_final = final_units_after_contract

base_price = sampled_data.iloc[-1]['Close']
if overseas_investment:
    latest_exchange_rate = get_latest_price("USDKRW=X")
    if latest_exchange_rate is None:
        latest_exchange_rate = 1
    base_effective_price = base_price * latest_exchange_rate
    final_holding_value = final_units_final * base_effective_price
else:
    final_holding_value = final_units_final * base_price

profit_rate = ((final_holding_value - total_investment_purchase) / total_investment_purchase) * 100

latest_price = get_latest_price(asset_ticker)
if latest_price is None:
    latest_price = base_price

if overseas_investment:
    latest_exchange_rate = get_latest_price("USDKRW=X")
    if latest_exchange_rate is None:
        latest_exchange_rate = 1
    current_effective_price = latest_price * latest_exchange_rate
else:
    current_effective_price = latest_price

try:
    st.subheader("📊 투자 시뮬레이션 결과")
    
    st.markdown("<div class='highlight-box'>", unsafe_allow_html=True)
    col_summary1, col_summary2, col_summary3, col_summary4 = st.columns(4)
    with col_summary1:
        st.metric("총 납입 원화", f"{total_investment_purchase:,.0f}원")
    with col_summary2:
        st.metric("만기 시 자산 가치", f"{final_holding_value:,.0f}원")
    with col_summary3:
        st.metric("예상 수익률", f"{profit_rate:.2f}%", delta=f"{profit_rate:.2f}%")
    with col_summary4:
        st.metric("평균 매입 가격", f"{final_effective_price_purchase:.2f}원")
    st.markdown("</div>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📈 투자 성과 상세", "💵 가격 정보"])
    
    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("납입 시 총 구매 수량", f"{total_units_purchase:,.2f}")
        with col2:
            st.metric("약정 이자율", f"{interest_rate_percent:.2f}%")
        with col3:
            st.metric("전환 복리 이자율", f"{compound_interest_rate_percent:.2f}%")
        with col4:
            st.metric("만기 시 총 구매 수량", f"{final_units_final:,.2f}", 
                     delta=f"{final_units_final - total_units_purchase:.2f}")
        st.markdown(f"<div class='small-text'>납입 기간: {purchase_period_years:.2f}년 | 유지 기간: {holding_period_years:.2f}년 | 전환(적립) 기간: {conversion_period_years:.2f}년</div>", unsafe_allow_html=True)
    
    with tab2:
        col5, col6, col7 = st.columns(3)
        with col5:
            st.metric("현재 가격", f"{current_effective_price:.2f}원")
        with col6:
            st.metric("기준 날짜 가격", f"{base_price * (latest_exchange_rate if overseas_investment else 1):.2f}원")
        with col7:
            st.metric("평균 매입 가격", f"{final_effective_price_purchase:.2f}원")
        
        actual_start_date = price_data.index.min().strftime("%Y년 %m월 %d일")
        st.markdown(f"<div class='small-text'>* 실제 사용된 데이터 시작일: {actual_start_date}</div>", unsafe_allow_html=True)
    
    st.subheader("📉 가격 추이 및 누적 매입 평균")
    # 해외 투자 시 효과적 가격(원화)로 변환하여 그래프에 표시
    if overseas_investment:
        effective_price_series = sampled_data['Close'] * usdkrw_data['Close']
    else:
        effective_price_series = sampled_data['Close']
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=all_dates,
        y=effective_price_series,
        mode='lines',
        name='실제 가격',
        line=dict(width=2, color='#003b70')
    ))
    fig.add_trace(go.Scatter(
        x=purchase_dates,
        y=cumulative_effective_prices,
        mode='lines',
        name='누적 매입 평균 가격',
        line=dict(dash='dot', width=2, color='#28a745')
    ))
    
    y_min = min(effective_price_series.min(), min(cumulative_effective_prices) if cumulative_effective_prices else effective_price_series.min()) * 0.95
    y_max = max(effective_price_series.max(), max(cumulative_effective_prices) if cumulative_effective_prices else effective_price_series.max()) * 1.05
    
    fig.add_shape(
        type="rect",
        x0=start_date,
        y0=y_min,
        x1=purchase_end_date,
        y1=y_max,
        fillcolor="#e6f2ff",
        opacity=0.3,
        layer="below",
        line_width=0
    )
    fig.add_shape(
        type="rect",
        x0=purchase_end_date,
        y0=y_min,
        x1=holding_end_date,
        y1=y_max,
        fillcolor="#fff2e6",
        opacity=0.3,
        layer="below",
        line_width=0
    )
    fig.add_shape(
        type="rect",
        x0=holding_end_date,
        y0=y_min,
        x1=end_date,
        y1=y_max,
        fillcolor="#e6ffe6",
        opacity=0.3,
        layer="below",
        line_width=0
    )
    
    fig.add_shape(
        type='line',
        x0=purchase_end_date,
        y0=y_min,
        x1=purchase_end_date,
        y1=y_max,
        line=dict(color='#ffa94d', width=2, dash='dash')
    )
    fig.add_annotation(
        x=purchase_end_date,
        y=y_max * 0.98,
        text="납입 종료",
        showarrow=True,
        arrowhead=1,
        ax=40,
        ay=-40,
        font=dict(size=12, color="#ff8c00")
    )
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
        text="유지 종료 & 이자적용 & 전환 시작",
        showarrow=True,
        arrowhead=1,
        ax=40,
        ay=-40,
        font=dict(size=12, color="#dc3545")
    )
    
    fig.add_trace(go.Scatter(
        x=[purchase_end_date, end_date],
        y=[final_effective_price_purchase, final_effective_price_purchase],
        mode='lines',
        name='최종 평균 매입 가격 (납입 기준)',
        line=dict(dash='dash', width=2, color='#dc3545')
    ))
    
    fig.update_layout(
        title=f'정액 투자 시뮬레이션 (납입: {purchase_period_years:.2f}년, 유지: {holding_period_years:.2f}년, 전환: {conversion_period_years:.2f}년, 총: {total_period_years:.2f}년)',
        xaxis_title='날짜',
        yaxis_title='가격 (원)',
        hovermode='x unified',
        height=500,
        font=dict(family="Malgun Gothic, NanumGothic, sans-serif", size=14),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        plot_bgcolor='white'
    )
    fig.update_xaxes(tickformat="%Y년 %m월", tickangle=-45, gridcolor='#f0f0f0')
    fig.update_yaxes(gridcolor='#f0f0f0')
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"가격 데이터 처리 중 오류 발생: {str(e)}")
    st.write(f"오류 상세: {e}")

with st.expander("❓ 자주 묻는 질문"):
    st.markdown(f"""
    **Q: 정액 투자 방식의 장점은 무엇인가요?**  
    A: 일정 금액을 정기적으로 투자하여 가격 변동에 따른 리스크를 분산시킬 수 있습니다.
    
    **Q: 약정 이자는 어떻게 적용되나요?**  
    A: 유지 기간 종료 시점에 보유 자산에 약정 이자율이 일괄 적용되고, 이후 전환(적립) 기간 동안 별도의 복리 이자율이 매년 적용됩니다.
    
    **Q: 중도 해지가 가능한가요?**  
    A: 실제 상품의 중도 해지 조건은 상담을 통해 확인하시기 바랍니다. 이 시뮬레이터는 만기 시 예상 수익을 보여줍니다.
    
    **Q: 2003년 12월 이전 데이터는 사용할 수 없나요?**  
    A: 현재 시뮬레이터는 Yahoo Finance의 데이터를 사용하며, 2003년 12월부터의 데이터만 제공됩니다.
    """)

st.markdown("<div class='footer'>© 2025 정액 투자 시뮬레이터 | 데이터 출처: Yahoo Finance (2003년 12월부터 제공, 1시간마다 자동 업데이트)<br>이 시뮬레이터는 참고용으로만 사용하시기 바랍니다. 실제 투자 결과는 다를 수 있습니다.</div>", unsafe_allow_html=True)
