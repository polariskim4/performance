3.11
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, date

# FinanceDataReader 임포트 시 발생할 수 있는 오류를 방지하기 위한 예외 처리
try:
    import FinanceDataReader as fdr
    HAS_FDR = True
except ImportError:
    HAS_FDR = False

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="주식 수익률 분석기")

@st.cache_data(ttl=86400)
def get_krx_ticker_map():
    """KRX 상장사 리스트를 가져와 {종목명: 티커} 맵을 반환"""
    if not HAS_FDR:
        # 라이브러리 로드 실패 시 기본값 제공
        return {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS"}
    
    try:
        df = fdr.StockListing('KRX')
        ticker_map = {}
        for _, row in df.iterrows():
            code, name, market = row['Code'], row['Name'], row['Market']
            # yfinance 호환을 위해 시장 구분 접미사 추가
            suffix = ".KS" if market == 'KOSPI' else ".KQ"
            ticker_map[name] = f"{code}{suffix}"
        return ticker_map
    except Exception as e:
        st.error(f"종목 리스트 로드 중 오류: {e}")
        return {"삼성전자": "005930.KS"}

# 데이터 로드
krx_map = get_krx_ticker_map()

@st.cache_data(ttl=3600)
def fetch_data(ticker: str):
    """주가 데이터를 가져오고 전처리"""
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="max")
        if data.empty:
            return None
        # 타임존 제거 (비교 오류 방지)
        data.index = pd.to_datetime(data.index).tz_localize(None)
        return data['Close']
    except Exception:
        return None

def get_performance_df(data: pd.Series):
    """연도별 수익률 계산 (소수점 한자리)"""
    current_year = date.today().year
    # 연도별로 그룹화하여 첫날과 마지막날 가격 비교
    annual_groups = data.groupby(data.index.year)
    
    results = []
    for year, year_data in annual_groups:
        if len(year_data) < 2: continue
        
        start_price = year_data.iloc[0]
        end_price = year_data.iloc[-1]
        ret = (end_price / start_price) - 1
        
        results.append({
            "Year": year,
            "Return": ret,
            "Display": f"{ret:.1%}"
        })
    
    # 최신순 정렬
    df = pd.DataFrame(results).sort_values("Year", ascending=False)
    return df

# --- UI 레이아웃 ---
st.title("📈 주식 수익률 분석기")

user_input = st.text_input("종목명 또는 티커 입력", value="삼성전자").strip()

# 입력값 처리
target_ticker = krx_map.get(user_input, user_input.upper())

if target_ticker:
    prices = fetch_data(target_ticker)
    
    if prices is not None:
        perf_df = get_performance_df(prices)
        current_year = date.today().year
        
        # 1. 상단 YTD 메트릭
        ytd_data = perf_df[perf_df['Year'] == current_year]
        if not ytd_data.empty:
            ytd_val = ytd_data.iloc[0]['Return']
            st.metric(f"{current_year} YTD 수익률", f"{ytd_val:.1%}", delta=f"{ytd_val:.1%}")
        
        st.divider()
        
        # 2. 전체 연도별 수익률 테이블
        st.subheader("📅 연도별 수익률 상세")
        
        def style_rows(row):
            # 올해 데이터는 음영 처리
            if row['Year'] == current_year:
                return ['background-color: #e6f7ff; font-weight: bold'] * len(row)
            return [''] * len(row)

        display_df = perf_df[['Year', 'Display']].rename(columns={"Display": "Annual Return"})
        st.dataframe(
            display_df.style.apply(style_rows, axis=1),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.error("데이터를 찾을 수 없습니다. 티커나 종목명을 확인해주세요.")
