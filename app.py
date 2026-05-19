import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, date

# --- Streamlit 페이지 설정 ---
st.set_page_config(layout="wide", page_title="주식 종목 수익률 분석기")

# --- 한국 주식 종목명-티커 매핑 (수동 추가) ---
# 이 맵은 yfinance에서 사용되는 티커를 기준으로 합니다.
# 더 많은 종목을 종목명으로 검색하고 싶다면 여기에 직접 추가해야 합니다.
KOREAN_STOCK_TICKER_MAP = {
    "삼성전자": "005930.KS",
    "카카오": "035720.KS",
    "네이버": "035420.KS",
    "현대차": "005380.KS",
    "SK하이닉스": "000660.KS",
    "LG화학": "051910.KS",
    "셀트리온": "068270.KS",
    "POSCO홀딩스": "005490.KS",
    "삼성바이오로직스": "207940.KS",
    "기아": "000270.KS",
    "KB금융": "105560.KS",
    "신한지주": "055550.KS",
    "하나금융지주": "086790.KS",
    "LG전자": "066570.KS",
    "삼성SDI": "006400.KS",
    "엔씨소프트": "036570.KS", # 코스닥
    "에코프로비엠": "247540.KQ", # 코스닥
    "HLB": "085340.KQ", # 코스닥
    "카카오게임즈": "293490.KQ", # 코스닥
}
import streamlit as st
import yfinance as yf
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, date

# --- Streamlit 페이지 설정 ---
st.set_page_config(layout="wide", page_title="주식 종목 수익률 분석기")

# --- 한국 주식 리스트 동적 로드 및 캐싱 ---
@st.cache_data(ttl=86400) # 하루에 한 번만 업데이트
def get_krx_ticker_map():
    """
    KRX 상장 종목 리스트를 가져와서 {종목명: 티커} 딕셔너리를 생성합니다.
    KOSPI 200, KOSDAQ 150을 포함한 모든 상장사 정보를 포함합니다.
    """
    try:
        df = fdr.StockListing('KRX')
        # 종목명(Name)과 티커(Code) 매핑
        # KOSPI는 .KS, KOSDAQ은 .KQ 접미사를 붙여야 yfinance에서 인식합니다.
        ticker_map = {}
        for _, row in df.iterrows():
            market = row['Market']
            code = row['Code']
            name = row['Name']
            
            if market == 'KOSPI':
                ticker_map[name] = f"{code}.KS"
            elif market == 'KOSDAQ':
                ticker_map[name] = f"{code}.KQ"
        return ticker_map
    except Exception as e:
        st.warning(f"한국 주식 리스트를 불러오지 못했습니다: {e}")
        return {}

# 티커 맵 로드
krx_map = get_krx_ticker_map()

# --- 데이터 가져오기 및 캐싱 함수 ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker: str, start_date_str: str, end_date_str: str) -> pd.Series | None:
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="max")
        
        if data.empty:
            return None
        
        # 시간대 제거 및 날짜 필터링
        data.index = pd.to_datetime(data.index).tz_localize(None)
        start_date = pd.to_datetime(start_date_str)
        end_date = pd.to_datetime(end_date_str)
        
        filtered_data = data[(data.index >= start_date) & (data.index <= end_date)]
        
        if filtered_data.empty:
            return None
        return filtered_data['Close']
    except Exception as e:
        st.error(f"오류 발생: {e}")
        return None

# --- 수익률 계산 함수 ---
def calculate_annual_returns(data_series: pd.Series, current_year: int) -> pd.DataFrame:
    if data_series is None or data_series.empty:
        return pd.DataFrame()

    # 연도별 마지막 영업일 데이터 추출
    # resample('YE')는 연말 데이터를 가져오며, 계산 편의를 위해 연간 수익률을 구합니다.
    annual_data = data_series.resample('YE').last()
    
    returns = []
    years = annual_data.index.year.unique()
    
    for year in sorted(years, reverse=True):
        year_data = data_series[data_series.index.year == year]
        if len(year_data) < 2: continue
        
        ret = (year_data.iloc[-1] / year_data.iloc[0]) - 1
        # 소수점 한자리 포맷팅
        returns.append({'Year': int(year), 'Annual Return': f"{ret:.1%}", 'RawReturn': ret})
    
    return pd.DataFrame(returns)

# --- UI 부분 ---
st.title("📈 주식 종목 수익률 분석기")

user_input = st.text_input(
    "종목 티커 또는 종목명을 입력하세요", 
    "삼성전자",
    help="예: AAPL, TSLA, 삼성전자, SK하이닉스, 에코프로비엠"
).strip()

# 입력값 처리 (종목명 -> 티커 변환)
target_ticker = user_input
if user_input in krx_map:
    target_ticker = krx_map[user_input]
    st.info(f"🔍 '{user_input}' 종목을 찾았습니다. (티커: {target_ticker})")
else:
    target_ticker = user_input.upper()

if target_ticker:
    today = date.today()
    all_data = get_stock_data(target_ticker, "1900-01-01", today.strftime('%Y-%m-%d'))

    if all_data is not None:
        current_year = today.year
        df_returns = calculate_annual_returns(all_data, current_year)
        
        # YTD 메트릭 (최상단)
        ytd_row = df_returns[df_returns['Year'] == current_year]
        if not ytd_row.empty:
            ytd_val = ytd_row.iloc[0]['RawReturn']
            st.metric(f"{current_year} YTD 수익률", f"{ytd_val:.1%}", delta=f"{ytd_val:.1%}")

        st.markdown("---")
        st.subheader("📅 연도별 수익률 현황")

        # 테이블 스타일링 및 음영 처리
        def highlight_first_row(row):
            if row['Year'] == current_year:
                return ['background-color: #f0f2f6; font-weight: bold'] * len(row)
            return [''] * len(row)

        if not df_returns.empty:
            # 표시용 데이터프레임 (RawReturn 제외)
            display_df = df_returns[['Year', 'Annual Return']]
            st.dataframe(
                display_df.style.apply(highlight_first_row, axis=1),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.error("데이터를 불러올 수 없습니다. 티커나 종목명을 다시 확인해주세요.")

st.caption("Data provided by yfinance & FinanceDataReader")

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
        
        # 인덱스를 datetime 형식으로 변환하고 시간대(timezone) 정보를 제거하여 비교 오류를 방지합니다.
        data.index = pd.to_datetime(data.index).tz_localize(None)
        
        start_date = pd.to_datetime(start_date_str)
        end_date = pd.to_datetime(end_date_str)
        
        data = data[(data.index >= start_date) & (data.index >= end_date)] # start_date와 end_date 모두 포함
        
        if data.empty:
            return None
        # yfinance.history()에서는 'Close'가 이미 수정 종가 역할을 합니다.
        return data['Close']
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
def calculate_annual_returns(data_series: pd.Series, current_year: int) -> pd.DataFrame:
    """
    주어진 수정 종가 데이터 시리즈에서 각 연도의 연간 수익률을 계산합니다.
    현재 연도는 제외하고 과거 연도만 계산합니다.
    결과를 'Year'와 'Annual Return' (백분율 형식, 소수점 한 자리) 컬럼을 가진 DataFrame으로 반환합니다.
    """
    if data_series is None or data_series.empty:
        return pd.DataFrame()

    annual_returns_dict = {}
    
    # 현재 연도를 제외한 과거 데이터만 사용
    historical_data = data_series[data_series.index.year < current_year]

    grouped_by_year = historical_data.groupby(historical_data.index.year)

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
    
    # 'Annual Return' 컬럼을 백분율 문자열로 포맷팅합니다. (소수점 한 자리)
    returns_df['Annual Return'] = returns_df['Annual Return'].map('{:.1%}'.format)
    
    return returns_df

# --- Streamlit 앱 본문 ---
st.title("📈 주식 종목 수익률 분석기")
st.markdown("특정 종목의 YTD (Year-to-Date) 수익률과 과거 연간 수익률을 확인하세요.")

# 사용자로부터 종목 티커 또는 종목명을 입력받습니다.
user_input = st.text_input(
    "종목 티커 또는 종목명을 입력하세요 (예: AAPL, 005930.KS, 삼성전자)", 
    "AAPL", # 기본값 설정
    help="한국 주식은 종목명(예: 삼성전자)으로 검색하거나, 티커 뒤에 '.KS' (코스피) 또는 '.KQ' (코스닥)를 붙여주세요 (예: 005930.KS)"
)

# 사용자 입력 처리: 종목명 -> 티커 매핑
processed_ticker = user_input # 일단 사용자 입력 그대로 사용
is_korean_name_search = False

# 한국 종목명 매핑 확인 (대소문자 구분 없이)
found_mapping = False
for name, ticker in KOREAN_STOCK_TICKER_MAP.items():
    if user_input.upper() == name.upper(): # 사용자 입력과 맵의 키를 모두 대문자로 변환하여 비교
        processed_ticker = ticker
        is_korean_name_search = True
        st.info(f"'{user_input}' (으)로 검색하여 티커 '{processed_ticker}'의 데이터를 가져옵니다.")
        found_mapping = True
        break # 매핑을 찾았으면 루프 종료

if not found_mapping: # 매핑을 찾지 못했다면, 사용자 입력을 티커로 간주하고 대문자로 변환
    processed_ticker = user_input.upper()


if processed_ticker:
    today = date.today()
    current_year = today.year
    
    # 가능한 한 가장 오래된 데이터부터 오늘까지의 데이터를 가져오기 위한 날짜 범위 설정
    very_early_date_str = datetime(1900, 1, 1).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')

    # 필요한 모든 데이터를 한 번에 가져옵니다.
    all_data = get_stock_data(processed_ticker, very_early_date_str, today_str)

    if all_data is not None and not all_data.empty:
        st.subheader(f"📊 **{processed_ticker}** 수익률 분석")

        # --- YTD 수익률 계산 및 표시 ---
        st.markdown("#### 올해 YTD (Year-to-Date) 수익률")
        
        # 현재 연도 데이터만 필터링합니다.
        current_year_data = all_data[all_data.index.year == current_year]
        
        current_ytd_return_value = None
        if not current_year_data.empty:
            ytd_return = calculate_ytd_return(current_year_data)
            if ytd_return is not None:
                current_ytd_return_value = ytd_return
                # st.metric을 사용하여 YTD 수익률을 표시합니다. 소수점 한 자리로 포맷팅.
                st.metric(label=f"{current_year} YTD 수익률", value=f"{ytd_return:.1%}", delta=ytd_return, delta_color="normal")
            else:
                st.info("현재 연도 YTD 수익률을 계산할 데이터가 부족합니다 (예: 아직 거래일이 하루뿐인 경우).")
        else:
            st.info("현재 연도 YTD 수익률을 계산할 데이터가 없습니다.")

        st.markdown("---") # 구분선

        # --- 과거 연간 수익률 계산 및 표시 ---
        st.markdown("#### 연간 수익률 (YTD 포함)")
        
        # 과거 연간 수익률 계산 (현재 연도 제외)
        annual_returns_df = calculate_annual_returns(all_data, current_year)

        # 현재 연도 YTD 수익률을 맨 위에 음영 처리하여 추가
        if current_ytd_return_value is not None:
            ytd_row = pd.DataFrame([{'Year': current_year, 'Annual Return': f"{current_ytd_return_value:.1%}"}])
            annual_returns_df = pd.concat([ytd_row, annual_returns_df]).reset_index(drop=True)
        
        if not annual_returns_df.empty:
            # 음영 처리를 위한 스타일링 함수
            def highlight_current_year_row(row):
                if row['Year'] == current_year:
                    return ['background-color: #e6f7ff'] * len(row) # 연한 파란색 배경
                return [''] * len(row)

            st.dataframe(annual_returns_df.style.apply(highlight_current_year_row, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info("연간 수익률을 계산할 데이터가 없습니다.")

    elif all_data is None:
        st.error(f"'{processed_ticker}'에 대한 데이터를 찾을 수 없거나, 데이터를 가져오는 중 오류가 발생했습니다. 티커를 확인해주세요.")
    else: # all_data가 비어 있지만 None이 아닌 경우 (예: 티커는 존재하지만 지정된 날짜 범위에 데이터가 없는 경우)
        st.warning(f"'{processed_ticker}'에 대한 데이터를 찾을 수 없습니다. 올바른 티커인지 확인해주세요.")

st.markdown("---")
st.markdown("Powered by `yfinance` and `Streamlit`")

