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
        # 최소한의 폴백 데이터
        ticker_map = {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS"}
    return ticker_map

krx_map = get_comprehensive_ticker_map()
krx_map_lower = {k.lower(): v for k, v in krx_map.items()}

@st.cache_data(ttl=3600)
def fetch_stock_data(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        # yfinance에서 회사명 가져오기
        company_name = stock.info.get('longName', ticker)
        data = stock.history(period="max")
        if data.empty:
            return None, None
        # 시간대 정보 제거하여 연산 오류 방지
        data.index = pd.to_datetime(data.index).tz_localize(None)
        return company_name, data['Close']
    except:
        return None, None

def calculate_annual_returns(prices: pd.Series):
    """연도별 수익률 계산 (소수점 한자리)"""
    if prices is None or prices.empty:
        return pd.DataFrame()
    
    # 연도별 첫 가격과 마지막 가격 추출
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

# --- 3. UI 메인 섹션 ---
st.title("📈 스마트 종목 분석기")

# 입력창을 상단에 고정
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
        # 헤더 포맷: 회사명(티커)
        ticker_only = target_ticker.split('.')[0]
        st.header(f"📊 {company_name} ({ticker_only})")
        
        perf_df = calculate_annual_returns(prices)
        current_year = date.today().year
        
        # 올해(YTD) 수익률 섹션
        ytd_row = perf_df[perf_df['Year'] == current_year]
        if not ytd_row.empty:
            ytd_val = ytd_row.iloc[0]['Return']
            
            # [중복 방지] value에만 값을 넣거나, delta에는 화살표 표시용으로만 사용합니다.
            st.metric(
                label=f"{current_year} YTD Performance", 
                value=f"{ytd_val:.1%}",
                delta=None  # 중복을 피하기 위해 delta를 None으로 설정하거나 보조 지표로만 활용
            )
        
        st.divider()
        
        # 전체 연도별 테이블 섹션
        st.subheader("📅 Yearly Returns History")
        
        if not perf_df.empty:
            # 출력용 데이터프레임 가공
            display_df = perf_df.copy()
            display_df['Return'] = display_df['Return'].map('{:.1%}'.format)
            
            # 올해 데이터 행 강조 스타일링
            def highlight_current_year(row):
                return ['background-color: #f0f2f6; font-weight: bold'] * len(row) if row.Year == current_year else [''] * len(row)

            st.dataframe(
                display_df.style.apply(highlight_current_year, axis=1),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.error(f"'{user_input}'의 데이터를 불러올 수 없습니다. 티커를 확인해 주세요.")

st.caption(f"Last Updated: {date.today()}")
