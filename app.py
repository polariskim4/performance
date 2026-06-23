import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, date

# --- 1. 페이지 설정 및 초기화 ---
st.set_page_config(layout="wide", page_title="주식 수익률 분석기")

# --- 2. 데이터 로드 로직 (캐싱 적용) ---
@st.cache_data(ttl=86400)
def get_comprehensive_ticker_map():
    ticker_map = {}
    try:
        import FinanceDataReader as fdr
        df_krx = fdr.StockListing('KRX')
        for _, row in df_krx.iterrows():
            code, name, market = row['Code'], row['Name'], row['Market']
            suffix = ".KS" if market == 'KOSPI' else ".KQ"
            ticker_map[name] = f"{code}{suffix}"
    except Exception:
        ticker_map = {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS"}
    return ticker_map

krx_map = get_comprehensive_ticker_map()
krx_map_lower = {k.lower(): v for k, v in krx_map.items()}

@st.cache_data(ttl=3600)
def fetch_stock_data(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        company_name = stock.info.get('longName', ticker)
        data = stock.history(period="max")
        if data.empty:
            return None, None
        data.index = pd.to_datetime(data.index).tz_localize(None)
        return company_name, data['Close']
    except:
        return None, None

def calculate_annual_returns(prices: pd.Series):
    """연도별 수익률 계산 (소수점 한자리)"""
    if prices is None or prices.empty:
        return pd.DataFrame()

    df = prices.to_frame(name='Close')
    df['Year'] = df.index.year

    annual_data = []
    for year, group in df.groupby('Year'):
        if len(group) < 2: continue
        start_price = group['Close'].iloc[0]
        end_price = group['Close'].iloc[-1]
        returns = (end_price / start_price) - 1
        annual_data.append({"Year": year, "Return": returns})

    return pd.DataFrame(annual_data).sort_values("Year", ascending=False)

def calculate_period_returns(prices: pd.Series):
    """
    1Y, 2Y, 3Y, 5Y, 10Y, 20Y 기간별 연평균 수익률(CAGR) 계산
    - 기준: 오늘 기준으로 N년 전 종가 → 최근 종가
    - 데이터가 부족한 기간은 N/A 처리
    """
    if prices is None or prices.empty:
        return pd.DataFrame()

    today = pd.Timestamp(date.today())
    latest_price = prices.iloc[-1]
    latest_date = prices.index[-1]

    periods = [
        ("1Y",  1),
        ("2Y",  2),
        ("3Y",  3),
        ("5Y",  5),
        ("10Y", 10),
        ("20Y", 20),
    ]

    rows = []
    for label, years in periods:
        target_date = latest_date - pd.DateOffset(years=years)

        # target_date 이전 데이터 중 가장 가까운 날짜 찾기
        past_prices = prices[prices.index <= target_date]
        if past_prices.empty:
            rows.append({"기간": label, "연평균 수익률 (CAGR)": None, "총 수익률": None})
            continue

        past_price = past_prices.iloc[-1]
        past_date = past_prices.index[-1]

        # 실제 경과 연수 (정확한 CAGR 계산)
        actual_years = (latest_date - past_date).days / 365.25
        if actual_years < 0.5:
            rows.append({"기간": label, "연평균 수익률 (CAGR)": None, "총 수익률": None})
            continue

        total_return = (latest_price / past_price) - 1
        cagr = (latest_price / past_price) ** (1 / actual_years) - 1

        rows.append({
            "기간": label,
            "연평균 수익률 (CAGR)": cagr,
            "총 수익률": total_return,
        })

    return pd.DataFrame(rows)

# --- 3. UI 메인 섹션 ---
st.title("📈 스마트 종목 분석기")

user_input = st.text_input("종목명 또는 티커를 입력하세요", value="삼성전자").strip()

# 검색 로직
target_ticker = None
if user_input.lower() in krx_map_lower:
    target_ticker = krx_map_lower[user_input.lower()]
elif user_input.isdigit() and len(user_input) == 6:
    target_ticker = f"{user_input}.KS"
else:
    target_ticker = user_input.upper()

if target_ticker:
    company_name, prices = fetch_stock_data(target_ticker)

    if prices is not None:
        ticker_only = target_ticker.split('.')[0]
        st.header(f"📊 {company_name} ({ticker_only})")

        perf_df = calculate_annual_returns(prices)
        current_year = date.today().year

        # ── 섹션 1: YTD ──────────────────────────────────────────
        ytd_row = perf_df[perf_df['Year'] == current_year]
        if not ytd_row.empty:
            ytd_val = ytd_row.iloc[0]['Return']
            st.metric(
                label=f"{current_year} YTD Performance",
                value=f"{ytd_val:.1%}",
                delta=None
            )

        st.divider()

        # ── 섹션 2: 연도별 수익률 ────────────────────────────────
        st.subheader("📅 Yearly Returns History")

        if not perf_df.empty:
            display_df = perf_df.copy()
            display_df['Return'] = display_df['Return'].map('{:.1%}'.format)

            def highlight_current_year(row):
                return (
                    ['background-color: #f0f2f6; font-weight: bold'] * len(row)
                    if row.Year == current_year
                    else [''] * len(row)
                )

            st.dataframe(
                display_df.style.apply(highlight_current_year, axis=1),
                use_container_width=True,
                hide_index=True,
            )

        st.divider()

        # ── 섹션 3: 기간별 평균 수익률 ───────────────────────────
        st.subheader("📆 Period Average Returns (CAGR)")

        period_df = calculate_period_returns(prices)

        if not period_df.empty:
            # 표시용 포맷 적용
            display_period = period_df.copy()

            def fmt_pct(val):
                return f"{val:.2%}" if pd.notna(val) else "N/A"

            def color_return(val):
                """양수 → 초록, 음수 → 빨강, N/A → 회색"""
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    return "color: gray"
                return "color: #0a8c4a; font-weight: bold" if val >= 0 else "color: #d63031; font-weight: bold"

            display_period["연평균 수익률 (CAGR)"] = display_period["연평균 수익률 (CAGR)"].apply(fmt_pct)
            display_period["총 수익률"] = display_period["총 수익률"].apply(fmt_pct)

            # 스타일 적용 전 원본 값이 필요하므로 포맷 전 복사본으로 스타일 생성
            raw_period = period_df.copy()

            def style_period_row(row):
                cagr_val = raw_period.loc[row.name, "연평균 수익률 (CAGR)"]
                total_val = raw_period.loc[row.name, "총 수익률"]
                styles = ["font-weight: bold"]  # 기간 열
                for v in [cagr_val, total_val]:
                    if v is None or (isinstance(v, float) and pd.isna(v)):
                        styles.append("color: gray")
                    elif v >= 0:
                        styles.append("color: #0a8c4a; font-weight: bold")
                    else:
                        styles.append("color: #d63031; font-weight: bold")
                return styles

            st.dataframe(
                display_period.style.apply(style_period_row, axis=1),
                use_container_width=True,
                hide_index=True,
            )

            # 데이터 기준일 안내
            data_start = prices.index[0].strftime("%Y-%m-%d")
            st.caption(f"※ CAGR = 연평균 복리 수익률 | 데이터 시작일: {data_start} | 기간 부족 시 N/A 표시")

    else:
        st.error(f"'{user_input}'의 데이터를 불러올 수 없습니다. 티커를 확인해 주세요.")

st.caption(f"Last Updated: {date.today()}")
