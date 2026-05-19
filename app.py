import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, date

# --- Streamlit 페이지 설정 ---
st.set_page_config(layout="wide", page_title="주식 종목 수익률 분석기")

# --- 확장된 폴백(Fallback) 한국 주식 종목명-티커 매핑 ---
# FinanceDataReader가 실패할 경우를 대비하여 주요 종목들을 미리 정의합니다.
# KOSPI 200, KOSDAQ 150의 모든 종목을 포함하기는 어렵지만, 자주 검색되는 종목들을 포함합니다.
FALLBACK_KOREAN_STOCK_TICKER_MAP = {
    "삼성전자": "005930.KS", "카카오": "035720.KS", "네이버": "035420.KS",
    "현대차": "005380.KS", "SK하이닉스": "000660.KS", "LG화학": "051910.KS",
    "셀트리온": "068270.KS", "POSCO홀딩스": "005490.KS", "삼성바이오로직스": "207940.KS",
    "기아": "000270.KS", "KB금융": "105560.KS", "신한지주": "055550.KS",
    "하나금융지주": "086790.KS", "LG전자": "066570.KS", "삼성SDI": "006400.KS",
    "엔씨소프트": "036570.KS", "에코프로비엠": "247540.KQ", "HLB": "085340.KQ",
    "카카오게임즈": "293490.KQ", "두산에너빌리티": "034020.KS", "하이브": "352820.KS",
    "LG에너지솔루션": "373220.KS", "삼성물산": "028260.KS", "현대모비스": "012330.KS",
    "포스코퓨처엠": "003670.KS", "KT&G": "000050.KS", "한국전력": "015760.KS",
    "SK텔레콤": "017670.KS", "KT": "030200.KS", "LG생활건강": "051900.KS",
    "아모레퍼시픽": "090430.KS", "엔씨소프트": "036570.KS", "펄어비스": "263750.KQ",
    "카카오뱅크": "323410.KS", "크래프톤": "259960.KS", "SK이노베이션": "096770.KS",
    "롯데케미칼": "011170.KS", "고려아연": "010130.KS", "S-Oil": "010950.KS",
    "삼성화재": "000810.KS", "현대해상": "001450.KS", "DB손해보험": "005830.KS",
    "삼성생명": "032830.KS", "한화생명": "088350.KS", "신세계": "004170.KS",
    "이마트": "139480.KS", "롯데쇼핑": "023530.KS", "GS리테일": "007070.KS",
    "CJ제일제당": "097950.KS", "오리온": "271560.KS", "농심": "004370.KS",
    "삼양식품": "003230.KS", "하이트진로": "000080.KS", "롯데칠성": "005300.KS",
    "대한항공": "003490.KS", "아시아나항공": "020560.KS", "HMM": "011200.KS",
    "팬오션": "028670.KS", "현대건설": "000720.KS", "대우건설": "047040.KS",
    "삼성엔지니어링": "028050.KS", "GS건설": "006360.KS", "현대제철": "004020.KS",
    "포스코스틸리온": "058430.KS", "KG스틸": "016380.KS", "LG디스플레이": "034220.KS",
    "삼성전기": "009150.KS", "LG이노텍": "011070.KS", "SKC": "011790.KS",
    "한화솔루션": "009830.KS", "OCI": "010060.KS", "금호석유": "011780.KS",
    "롯데정밀화학": "004000.KS", "코오롱인더": "120110.KS", "효성첨단소재": "298050.KS",
    "효성티앤씨": "298020.KS", "F&F": "383220.KS", "휠라홀딩스": "081660.KS",
    "한섬": "020000.KS", "LF": "093050.KS", "신세계인터내셔날": "031430.KS",
    "제일기획": "030000.KS", "이노션": "214320.KS", "CJ ENM": "035760.KS",
    "스튜디오드래곤": "253450.KQ", "JYP Ent.": "035900.KQ", "YG엔터테인먼트": "122870.KQ",
    "SM엔터테인먼트": "041510.KQ", "에스엠": "041510.KQ",
    "펄어비스": "263750.KQ", "위메이드": "112040.KQ", "컴투스": "078340.KQ",
    "NHN": "035420.KQ",
    "카카오페이": "377300.KS", "카카오뱅크": "323410.KS",
    "두산밥캣": "241560.KS", "HD현대인프라코어": "042670.KS",
    "한국항공우주": "047810.KS", "한화에어로스페이스": "012450.KS", "LIG넥스원": "079550.KS",
    "풍산": "103140.KS", "LS": "006260.KS", "LS ELECTRIC": "000680.KS",
    "코웨이": "021240.KS", "SK바이오팜": "326030.KS",
    "삼성SDI": "006400.KS", "LG전자": "066570.KS", "LG이노텍": "011070.KS",
    "SK하이닉스": "000660.KS", "DB하이텍": "000990.KS", "키움증권": "039490.KS",
    "미래에셋증권": "006800.KS", "삼성증권": "016360.KS", "NH투자증권": "005940.KS",
    "한국금융지주": "071050.KS", "메리츠금융지주": "138040.KS", "메리츠증권": "008560.KS",
    "메리츠화재": "000060.KS", "현대글로비스": "086280.KS", "CJ대한통운": "000120.KS",
    "한진칼": "180640.KS", "GS": "078930.KS", "SK": "034730.KS",
    "LG": "003550.KS", "한화": "000880.KS", "두산": "000150.KS",
    "효성": "004800.KS", "코오롱": "002020.KS",
    "DL이앤씨": "375500.KS", "DL건설": "001880.KS",
    "현대미포조선": "010620.KS", "삼성중공업": "010140.KS", "한화오션": "042660.KS",
    "HD현대중공업": "329180.KS", "HD한국조선해양": "009540.KS",
    "현대엘리베이": "017800.KS", "현대로템": "064350.KS", "현대위아": "011210.KS",
    "현대오토에버": "307950.KS",
    "한온시스템": "012310.KS", "HL만도": "204320.KS",
    "넥센타이어": "002350.KS", "금호타이어": "073240.KS", "한국타이어앤테크놀로지": "000240.KS",
    "아모레G": "002790.KS", "LG생활건강우": "051905.KS", "아모레퍼시픽우": "090435.KS",
    "코스맥스": "192820.KQ", "한국콜마": "161890.KS", "클리오": "237880.KQ",
    "토니모리": "214420.KQ", "잇츠한불": "226320.KQ", "애경산업": "161000.KS",
    "제이콘텐트리": "036420.KS", "CJ CGV": "079160.KS", "쇼박스": "086980.KQ",
    "NEW": "160550.KQ", "덱스터스튜디오": "206560.KQ", "자이언트스텝": "289220.KQ",
    "알테오젠": "196170.KQ", "에이치엘비": "085340.KQ",
    "셀트리온제약": "068760.KQ", "SK바이오사이언스": "326030.KS",
    "한미약품": "128940.KS", "유한양행": "000100.KS", "종근당": "185750.KS",
    "GC녹십자": "006280.KS", "대웅제약": "069620.KS", "동아에스티": "170900.KS",
    "JW중외제약": "001060.KS", "일동제약": "249420.KS", "보령제약": "006390.KS",
    "한독": "002390.KS", "동국제약": "086450.KS", "휴젤": "145020.KQ",
    "메디톡스": "086900.KQ", "파마리서치": "214450.KQ",
    "원텍": "336570.KQ", "루닛": "328130.KQ", "뷰노": "338220.KQ",
    "제이엘케이": "322510.KQ", "딥노이드": "315640.KQ", "코난테크놀로지": "402030.KQ",
    "솔트룩스": "348600.KQ", "마인즈랩": "377480.KQ", "플리토": "300080.KQ",
    "비트컴퓨터": "032850.KQ", "인피니트헬스케어": "071200.KQ", "유비케어": "032620.KQ",
    "케어젠": "214370.KQ", "휴마시스": "205470.KQ", "씨젠": "096530.KQ",
    "랩지노믹스": "084650.KQ", "EDGC": "245620.KQ", "마크로젠": "038290.KQ",
    "디엔에이링크": "127120.KQ", "테라젠이텍스": "066700.KQ", "신테카바이오": "226330.KQ",
    "지놈앤컴퍼니": "314130.KQ", "큐라클": "365270.KQ", "오스코텍": "039200.KQ",
    "제넥신": "095700.KQ", "에이비엘바이오": "298380.KQ", "레고켐바이오": "141080.KQ",
    "앱클론": "174900.KQ", "티움바이오": "321550.KQ", "지아이이노베이션": "358570.KQ",
    "아이진": "185490.KQ", "올릭스": "226950.KQ", "펩트론": "087010.KQ",
    "인벤티지랩": "334230.KQ", "에스티팜": "237690.KQ",
    "HLB생명과학": "067630.KQ", "HLB테라퓨틱스": "115450.KQ", "HLB제약": "047920.KQ",
    "HLB글로벌": "003580.KQ",
    "에코프로": "086520.KQ", "엘앤에프": "066970.KQ", "천보": "278280.KQ",
    "코스모신소재": "005070.KQ", "코스모화학": "005420.KQ", "포스코DX": "022100.KQ",
    "솔브레인": "357780.KQ", "동진쎄미켐": "005290.KQ", "원익IPS": "240810.KQ",
    "주성엔지니어링": "036220.KQ", "AP시스템": "265520.KQ", "케이씨텍": "281820.KQ",
    "테스": "095610.KQ", "유진테크": "084370.KQ", "피에스케이": "319660.KQ",
    "원익QnC": "074600.KQ", "하나마이크론": "067310.KQ", "리노공업": "058470.KQ",
    "ISC": "095340.KQ", "티씨케이": "064760.KQ", "솔브레인홀딩스": "036830.KQ",
    "동화기업": "025900.KQ", "파크시스템스": "140860.KQ", "고영": "098460.KQ",
    "로보티즈": "108490.KQ", "레인보우로보틱스": "277810.KQ", "뉴로메카": "348340.KQ",
    "티로보틱스": "117730.KQ", "유진로봇": "056080.KQ", "에브리봇": "270660.KQ",
    "큐렉소": "060280.KQ", "인바디": "041830.KQ",
    "제이시스메디칼": "287410.KQ", "하이로닉": "149980.KQ",
    "비올": "335890.KQ", "루트로닉": "085370.KQ", "휴메딕스": "200670.KQ",
    "대원제약": "003220.KQ",
}

# FinanceDataReader 임포트 시 발생할 수 있는 오류를 방지하기 위한 예외 처리
try:
    import FinanceDataReader as fdr
    HAS_FDR = True
except ImportError:
    HAS_FDR = False
    st.warning("`FinanceDataReader` 라이브러리를 로드할 수 없습니다. 한국 주식 종목명 검색은 제한적일 수 있습니다.")
except Exception as e:
    HAS_FDR = False
    st.error(f"`FinanceDataReader` 로드 중 예상치 못한 오류 발생: {e}. 한국 주식 종목명 검색은 제한적일 수 있습니다.")


@st.cache_data(ttl=86400)
def get_krx_ticker_map():
    """
    KRX 상장 종목 리스트를 가져와서 {종목명: 티커} 딕셔너리를 생성합니다.
    FinanceDataReader가 실패할 경우, 미리 정의된 폴백 맵을 사용합니다.
    """
    if not HAS_FDR:
        st.info("`FinanceDataReader`를 사용할 수 없어 미리 정의된 일부 한국 종목명으로만 검색 가능합니다.")
        return FALLBACK_KOREAN_STOCK_TICKER_MAP
    
    try:
        df = fdr.StockListing('KRX')
        ticker_map = {}
        for _, row in df.iterrows():
            code, name, market = row['Code'], row['Name'], row['Market']
            # yfinance 호환을 위해 시장 구분 접미사 추가
            suffix = ".KS" if market == 'KOSPI' else ".KQ"
            ticker_map[name] = f"{code}{suffix}"
        st.success("한국 주식 종목 리스트를 성공적으로 로드했습니다.")
        return ticker_map
    except Exception as e:
        st.error(f"종목 리스트 로드 중 오류: {e}. 미리 정의된 일부 한국 종목명으로만 검색 가능합니다. "
                 f"이 오류가 지속되면 `FinanceDataReader` 라이브러리 업데이트를 고려해 보세요.")
        return FALLBACK_KOREAN_STOCK_TICKER_MAP

# 티커 맵 로드
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
    except Exception as e:
        st.error(f"'{ticker}'에 대한 데이터를 가져오는 중 오류가 발생했습니다: {e}")
        return None

def get_performance_df(data: pd.Series):
    """연도별 수익률 계산 (소수점 한자리)"""
    current_year = date.today().year
    
    annual_groups = data.groupby(data.index.year)
    
    results = []
    for year, year_data in annual_groups:
        if len(year_data) < 2: continue # 최소 2일 데이터 필요
        
        start_price = year_data.iloc[0]
        end_price = year_data.iloc[-1]
        
        if start_price == 0: continue # 0으로 나누는 오류 방지
        
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
st.title("📈 주식 종목 수익률 분석기")
st.markdown("특정 종목의 YTD (Year-to-Date) 수익률과 과거 연간 수익률을 확인하세요.")

user_input = st.text_input(
    "종목명 또는 티커를 입력하세요 (예: AAPL, 삼성전자, 005930.KS)", 
    value="삼성전자"
).strip()

# 입력값 처리: 종목명 -> 티커 변환
target_ticker = krx_map.get(user_input, user_input.upper())

if target_ticker:
    # 사용자에게 어떤 티커로 검색하는지 명확히 알려줍니다.
    if user_input != target_ticker:
        st.info(f"'{user_input}' (으)로 검색하여 티커 '{target_ticker}'의 데이터를 가져옵니다.")
    
    prices = fetch_data(target_ticker)
    
    if prices is not None and not prices.empty:
        perf_df = get_performance_df(prices)
        current_year = date.today().year
        
        # 1. 상단 YTD 메트릭
        ytd_data = perf_df[perf_df['Year'] == current_year]
        if not ytd_data.empty:
            ytd_val = ytd_data.iloc[0]['Return']
            st.subheader(f"📊 **{target_ticker}** 수익률 분석")
            st.metric(f"{current_year} YTD 수익률", f"{ytd_val:.1%}", delta=f"{ytd_val:.1%}")
        else:
            st.info(f"'{target_ticker}'의 {current_year}년 YTD 수익률을 계산할 데이터가 부족합니다.")
        
        st.divider()
        
        # 2. 전체 연도별 수익률 테이블
        st.subheader("📅 연도별 수익률 상세")
        
        def style_rows(row):
            # 올해 데이터는 음영 처리
            if row['Year'] == current_year:
                return ['background-color: #e6f7ff; font-weight: bold'] * len(row)
            return [''] * len(row)

        if not perf_df.empty:
            display_df = perf_df[['Year', 'Display']].rename(columns={"Display": "Annual Return"})
            st.dataframe(
                display_df.style.apply(style_rows, axis=1),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info(f"'{target_ticker}'에 대한 연간 수익률 데이터를 찾을 수 없습니다.")
    else:
        st.error(f"'{target_ticker}'에 대한 주가 데이터를 찾을 수 없거나, 데이터를 가져오는 중 오류가 발생했습니다. 티커나 종목명을 확인해주세요.")

st.caption("Data provided by yfinance & FinanceDataReader (if available)")

