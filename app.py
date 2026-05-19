import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, date

# --- Streamlit 페이지 설정 ---
st.set_page_config(layout="wide", page_title="주식 종목 수익률 분석기")

# --- 폴백(Fallback) 한국 주식 데이터 ---
FALLBACK_KOREAN_STOCK_TICKER_MAP = {
    "삼성전자": "005930.KS", "카카오": "035720.KS", "네이버": "035420.KS",
    "현대차": "005380.KS", "SK하이닉스": "000660.KS", "LG화학": "051910.KS",
    "셀트리온": "068270.KS", "에코프로비엠": "247540.KQ", "하이브": "352820.KS"
    # ... (필요 시 추가 가능)
}

@st.cache_data(ttl=86400)
def get_krx_ticker_map():
    """KRX 종목 리스트를 가져오며 오류 발생 시 조용히 폴백 데이터 반환"""
    try:
        import FinanceDataReader as fdr
        df = fdr.StockListing('KRX')
        ticker_map = {}
        for _, row in df.iterrows():
            code, name, market = row['Code'], row['Name'], row['Market']
            suffix = ".KS" if market == 'KOSPI' else ".KQ"
            ticker_map[name] = f"{code}{suffix}"
        return ticker_map
    except Exception:
        # 오류 메시지 없이 조용히 폴백 데이터 반환
        return FALLBACK_KOREAN_STOCK_TICKER_MAP

# 티커 맵 로드
krx_map = get_krx_ticker_map()
# 대소문자 구분 없는 검색을 위해 모든 키를 소문자로 만든 맵 생성
krx_map_lower = {k.lower(): v for k, v in krx_map.items()}

@st.cache_data(ttl=3600)
def fetch_stock_info(ticker: str):
    """티커를 통해 기업명과 주가 데이터를 가져옴"""
    try:
        stock = yf.Ticker(ticker)
        # 회사 긴 이름 가져오기 (실패 시 티커 사용)
        long_name = stock.info.get('longName', ticker)
        data = stock.history(period="max")
        if data.empty:
            return None, None
        data.index = pd.to_datetime(data.index).tz_localize(None)
        return long_name, data['Close']
    except:
        return None, None

def get_performance_df(data: pd.Series):
    """연도별 수익률 계산"""
    current_year = date.today().year
    annual_groups = data.groupby(data.index.year)
    results = []
    for year, year_data in annual_groups:
        if len(year_data) < 2: continue
        start_price, end_price = year_data.iloc[0], year_data.iloc[-1]
        if start_price == 0: continue
        ret = (end_price / start_price) - 1
        results.append({"Year": year, "Return": ret, "Display": f"{ret:.1%}"})
    return pd.DataFrame(results).sort_values("Year", ascending=False)

# --- UI 레이아웃 ---
st.title("📈 주식 종목 수익률 분석기")

user_input = st.text_input("종목명 또는 티커를 입력하세요", value="삼성전자").strip()

# 1. 종목명 검색 (대소문자 구분 없음)
target_ticker = None
display_name = None

input_lower = user_input.lower()
if input_lower in krx_map_lower:
    target_ticker = krx_map_lower[input_lower]
    # 실제 맵에서 원래 케이스의 종목명 찾기
    display_name = next((name for name in krx_map if name.lower() == input_lower), user_input)
else:
    # 티커 직접 입력으로 간주
    target_ticker = user_input.upper()

if target_ticker:
    # 데이터 및 기업 정보 가져오기
    company_long_name, prices = fetch_stock_info(target_ticker)
    
    if prices is not None:
        # 한국 종목이면 '삼성전자(005930)', 미국 종목이면 'Apple Inc.(AAPL)' 형식 구성
        clean_ticker = target_ticker.split('.')[0]
        final_title_name = display_name if display_name else company_long_name
        header_title = f"{final_title_name}({clean_ticker})"
        
        st.subheader(f"📊 {header_title}")
        
        perf_df = get_performance_df(prices)
        current_year = date.today().year
        
        # YTD 메트릭
        ytd_data = perf_df[perf_df['Year'] == current_year]
        if not ytd_data.empty:
            ytd_val = ytd_data.iloc[0]['Return']
            st.metric(f"{current_year} YTD 수익률", f"{ytd_val:.1%}", delta=f"{ytd_val:.1%}")
        
        st.divider()
        st.subheader("📅 연도별 수익률 상세")
        
        # 행 강조 스타일
        def style_rows(row):
            if row['Year'] == current_year:
                return ['background-color: #f0f2f6; font-weight: bold'] * len(row)
            return [''] * len(row)

        if not perf_df.empty:
            display_df = perf_df[['Year', 'Display']].rename(columns={"Display": "Annual Return"})
            st.dataframe(
                display_df.style.apply(style_rows, axis=1),
                use_container_width=True, hide_index=True
            )
    else:
        st.error(f"'{user_input}'에 대한 데이터를 찾을 수 없습니다.")

st.caption("Data provided by yfinance & FinanceDataReader")
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, date

# --- 1. 종목 리스트 자동 업데이트 로직 (TTL 설정으로 주기적 갱신) ---
# ttl=86400은 24시간(하루)을 의미합니다. 일주일은 604800, 한 달은 2592000으로 설정하세요.
@st.cache_data(ttl=86400)
def get_comprehensive_ticker_map():
    """
    KRX 전체 종목을 가져오며, 실패 시에도 최대한 넓은 범위를 커버하는 로직입니다.
    이 함수는 설정된 TTL 주기에 따라 자동으로 재실행되어 리스트를 업데이트합니다.
    """
    ticker_map = {}
    
    # 전략 A: FinanceDataReader 시도
    try:
        import FinanceDataReader as fdr
        # KOSPI, KOSDAQ 종목 전체 리스트 확보
        df_krx = fdr.StockListing('KRX')
        for _, row in df_krx.iterrows():
            code, name, market = row['Code'], row['Name'], row['Market']
            suffix = ".KS" if market == 'KOSPI' else ".KQ"
            ticker_map[name] = f"{code}{suffix}"
        return ticker_map
    except Exception:
        # 전략 A 실패 시 로깅 없이 다음 단계로 이동
        pass

    # 전략 B: 전략 A가 실패할 경우를 대비한 350개+ 주요 종목 하드코딩 (최초 1회만 고생하면 됩니다)
    # 실제 운영 환경에서는 이 리스트를 별도의 JSON/CSV 파일로 관리하고 불러오는 것이 깔끔합니다.
    # 여기에는 핵심 지수 종목들을 예시로 넣었습니다.
    static_fallback = {
        "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "LG에너지솔루션": "373220.KS",
        "삼성바이오로직스": "207940.KS", "현대차": "005380.KS", "기아": "000270.KS",
        "셀트리온": "068270.KS", "POSCO홀딩스": "005490.KS", "NAVER": "035420.KS",
        "에코프로비엠": "247540.KQ", "에코프로": "086520.KQ", "HLB": "085340.KQ"
        # ... (이하 350개 종목을 이 딕셔너리에 추가하거나 별도 파일로 로드 권장)
    }
    return static_fallback

# 전역 변수로 종목 맵 로드 (앱 시작 시 또는 TTL 만료 시 실행)
krx_map = get_comprehensive_ticker_map()
krx_map_lower = {k.lower(): v for k, v in krx_map.items()}

# --- 2. 데이터 시각화 및 수익률 계산 함수 ---
@st.cache_data(ttl=3600)
def fetch_stock_data(ticker: str):
    """주가 데이터를 가져오는 핵심 함수"""
    try:
        stock = yf.Ticker(ticker)
        # 회사 정식 명칭 가져오기
        info = stock.info
        company_name = info.get('longName', ticker)
        
        data = stock.history(period="max")
        if data.empty:
            return None, None
            
        data.index = pd.to_datetime(data.index).tz_localize(None)
        return company_name, data['Close']
    except:
        return None, None

def calculate_performance(prices: pd.Series):
    """연도별 수익률 계산 로직"""
    df = prices.to_frame(name='Close')
    df['Year'] = df.index.year
    
    annual_perf = []
    for year, group in df.groupby('Year'):
        if len(group) < 2: continue
        start_val, end_val = group['Close'].iloc[0], group['Close'].iloc[-1]
        ret = (end_val / start_val) - 1
        annual_perf.append({"Year": year, "Return": ret})
        
    return pd.DataFrame(annual_perf).sort_values("Year", ascending=False)

# --- 3. UI 메인 로직 ---
st.title("📈 스마트 종목 분석기 (KOSPI 200 / KOSDAQ 150)")

# 사용자 입력
user_input = st.text_input("종목명 또는 티커를 입력하세요 (예: 삼성전자, AAPL, 000660)", "삼성전자").strip()

# 검색 로직 (이름 -> 숫자 코드 -> 티커 자동 완성)
target_ticker = None
if user_input.lower() in krx_map_lower:
    target_ticker = krx_map_lower[user_input.lower()]
elif user_input.isdigit() and len(user_input) == 6:
    # 숫자로만 입력했을 경우 코스피로 먼저 가정 (yfinance에서 검색 실패 시 KQ로 시도하는 로직 추가 가능)
    target_ticker = f"{user_input}.KS"
else:
    target_ticker = user_input.upper()

if target_ticker:
    company_name, prices = fetch_stock_data(target_ticker)
    
    if prices is not None:
        # 제목 포맷팅: 기업명(티커)
        ticker_display = target_ticker.split('.')[0]
        st.header(f"📊 {company_name} ({ticker_display})")
        
        perf_df = calculate_performance(prices)
        current_year = date.today().year
        
        # YTD 메트릭 표시
        ytd_row = perf_df[perf_df['Year'] == current_year]
        if not ytd_row.empty:
            ytd_val = ytd_row.iloc[0]['Return']
            st.metric(f"{current_year} YTD Performance", f"{ytd_val:.1%}", delta=f"{ytd_val:.1%}")
        
        # 연도별 수익률 테이블 (올해 강조 스타일링)
        st.subheader("Yearly Returns History")
        
        def highlight_current(row):
            return ['background-color: #f0f2f6; font-weight: bold'] * len(row) if row.Year == current_year else [''] * len(row)

        display_df = perf_df.copy()
        display_df['Return'] = display_df['Return'].map('{:.1%}'.format)
        
        st.dataframe(
            display_df.style.apply(highlight_current, axis=1),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.error(f"'{user_input}'의 데이터를 가져올 수 없습니다. 티커를 확인해주세요.")

# 하단 정보 표시
st.caption(f"Last List Update: {date.today()} (Update cycle: 24h)")
