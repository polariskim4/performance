import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, date

# --- Streamlit 페이지 설정 ---
# 페이지 레이아웃을 'wide'로 설정하여 넓게 사용하고, 페이지 제목을 설정합니다.
st.set_page_config(layout="wide", page_title="주식 종목 수익률 분석기")

# --- 데이터 가져오기 및 캐싱 함수 ---
@st.cache_data(ttl=3600) # 데이터를 1시간 동안 캐시하여 API 호출을 줄이고 성능을 향상시킵니다.
def get_stock_data(ticker: str, start_date_str: str, end_date_str: str) -> pd.Series | None:
    """
    지정된 티커의 과거 주식 데이터를 가져옵니다.
    가능한 모든 이력을 가져온 후, 지정된 날짜 범위로 필터링합니다.
    """
    try:
        stock = yf.Ticker(ticker)
        # 'period="max"'를 사용하여 해당 종목의 모든 이력 데이터를 가져옵니다.
        data = stock.history(period="max")
        
        if data.empty:
            return None
        
        # 인덱스를 datetime 형식으로 변환하고, 지정된 날짜 범위로 데이터를 필터링합니다.
        data.index = pd.to_datetime(data.index)
        
        start_date = pd.to_datetime(start_date_str)
        end_date = pd.to_datetime(end_date_str)
        
        data = data[(data.index >= start_date) & (data.index <= end_date)]
        
        if data.empty:
            return None
        return data['Adj Close'] # 수정 종가(Adj Close)만 반환합니다.
    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다. 티커 '{ticker}'를 확인하거나 잠시 후 다시 시도해주세요. 오류: {e}")
        return None

# --- YTD (Year-to-Date) 수익률 계산 함수 ---
def calculate_ytd_return(data_series: pd.Series) -> float | None:
    """
    주어진 수정 종가 데이터 시리즈에서 YTD (Year-to-Date) 수익률을 계산합니다.
    데이터 시리즈는 해당 연도의 시작부터 현재까지의 데이터를 포함해야 합니다.
    """
    if data_series is None or data_series.empty:
        return None

    # 해당 연도의 첫 거래일 가격
    start_price = data_series.iloc[0]
    # 해당 연도의 마지막 거래일 (가장 최근) 가격
    end_price = data_series.iloc[-1]

    if start_price == 0: # 0으로 나누는 오류 방지
        return None

    ytd_return = (end_price / start_price) - 1
    return ytd_return

# --- 연간 수익률 계산 함수 ---
def calculate_annual_returns(data_series: pd.Series) -> pd.DataFrame:
    """
    주어진 수정 종가 데이터 시리즈에서 각 연도의 연간 수익률을 계산합니다.
    결과를 'Year'와 'Annual Return' (백분율 형식) 컬럼을 가진 DataFrame으로 반환합니다.
    """
    if data_series is None or data_series.empty:
        return pd.DataFrame()

    annual_returns_dict = {}
    
    # 데이터를 연도별로 그룹화합니다.
    grouped_by_year = data_series.groupby(data_series.index.year)

    for year, year_data in grouped_by_year:
        # 연간 수익률을 계산하려면 최소 두 개 이상의 거래일 데이터가 필요합니다.
        if len(year_data) < 2:
            continue

        # 해당 연도의 첫 거래일 가격과 마지막 거래일 가격을 가져옵니다.
        start_price = year_data.iloc[0]
        end_price = year_data.iloc[-1]

        if start_price == 0: # 0으로 나누는 오류 방지
            continue

        annual_return = (end_price / start_price) - 1
        annual_returns_dict[year] = annual_return
    
    # 결과를 DataFrame으로 변환합니다.
    returns_df = pd.DataFrame(list(annual_returns_dict.items()), columns=['Year', 'Annual Return'])
    
    # 연도를 기준으로 내림차순 정렬합니다.
    returns_df = returns_df.sort_values(by='Year', ascending=False)
    
    # 'Annual Return' 컬럼을 백분율 문자열로 포맷팅합니다.
    returns_df['Annual Return'] = returns_df['Annual Return'].map('{:.2%}'.format)
    
    return returns_df

# --- Streamlit 앱 본문 ---
st.title("📈 주식 종목 수익률 분석기")
st.markdown("특정 종목의 YTD (Year-to-Date) 수익률과 과거 연간 수익률을 확인하세요.")

# 사용자로부터 종목 티커를 입력받습니다.
ticker_input = st.text_input(
    "종목 티커를 입력하세요 (예: AAPL, MSFT, TSLA, 005930.KS)", 
    "AAPL", # 기본값 설정
    help="한국 주식은 '.KS' (코스피) 또는 '.KQ' (코스닥)를 티커 뒤에 붙여주세요 (예: 삼성전자 005930.KS)"
).upper() # 입력값을 대문자로 변환

if ticker_input:
    today = date.today()
    current_year = today.year
    
    # 가능한 한 가장 오래된 데이터부터 오늘까지의 데이터를 가져오기 위한 날짜 범위 설정
    # yfinance는 실제 상장일 이후의 데이터만 반환합니다.
    very_early_date_str = datetime(1900, 1, 1).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')

    # 필요한 모든 데이터를 한 번에 가져옵니다.
    all_data = get_stock_data(ticker_input, very_early_date_str, today_str)

    if all_data is not None and not all_data.empty:
        st.subheader(f"📊 **{ticker_input}** 수익률 분석")

        # --- YTD 수익률 계산 및 표시 ---
        st.markdown("#### 올해 YTD (Year-to-Date) 수익률")
        
        # 현재 연도 데이터만 필터링합니다.
        current_year_data = all_data[all_data.index.year == current_year]
        
        if not current_year_data.empty:
            ytd_return = calculate_ytd_return(current_year_data)
            if ytd_return is not None:
                # st.metric을 사용하여 YTD 수익률을 표시합니다. delta_color="normal"로 양수는 초록색, 음수는 빨간색으로 표시됩니다.
                st.metric(label=f"{current_year} YTD 수익률", value=f"{ytd_return:.2%}", delta=ytd_return, delta_color="normal")
            else:
                st.info("현재 연도 YTD 수익률을 계산할 데이터가 부족합니다 (예: 아직 거래일이 하루뿐인 경우).")
        else:
            st.info("현재 연도 YTD 수익률을 계산할 데이터가 없습니다.")

        st.markdown("---") # 구분선

        # --- 과거 연간 수익률 계산 및 표시 ---
        st.markdown("#### 과거 연간 수익률")
        
        # 현재 연도는 YTD 수익률로 다루므로, 과거 연간 수익률에서는 제외합니다.
        historical_data = all_data[all_data.index.year < current_year]
        
        if not historical_data.empty:
            annual_returns_df = calculate_annual_returns(historical_data)
            if not annual_returns_df.empty:
                # DataFrame으로 연간 수익률을 표시합니다.
                st.dataframe(annual_returns_df, use_container_width=True, hide_index=True)
            else:
                st.info("과거 연간 수익률을 계산할 데이터가 부족합니다.")
        else:
            st.info("과거 연간 수익률을 계산할 데이터가 없습니다.")

    elif all_data is None:
        st.error(f"'{ticker_input}'에 대한 데이터를 찾을 수 없거나, 데이터를 가져오는 중 오류가 발생했습니다. 티커를 확인해주세요.")
    else: # all_data가 비어 있지만 None이 아닌 경우 (예: 티커는 존재하지만 지정된 날짜 범위에 데이터가 없는 경우)
        st.warning(f"'{ticker_input}'에 대한 데이터를 찾을 수 없습니다. 올바른 티커인지 확인해주세요.")

st.markdown("---")
st.markdown("Powered by `yfinance` and `Streamlit`")

