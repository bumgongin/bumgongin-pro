import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import urllib.parse

# [1. 시스템 설정]
st.set_page_config(
    page_title="범공인 Pro (v24.16)",
    layout="wide",
    initial_sidebar_state="expanded"
)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1bmTnLu-vMvlAGRSsCI4a8lk00U38covWl5Wfn9JZYVU/edit"

# 💡 [설정] 6개 시트 명칭 (정확도 필수)
SHEET_NAMES = ["임대", "임대(종료)", "매매", "매매(종료)", "임대브리핑", "매매브리핑"]

# [2. 스타일 설정]
st.markdown("""
    <style>
    .stButton button { min-height: 50px !important; font-size: 16px !important; font-weight: bold !important; }
    input[type=number] { min-height: 40px; }
    div[data-testid="stExpander"] details summary p { font-size: 1.1rem; font-weight: 600; }
    @media (max-width: 768px) { 
        .stDataEditor { font-size: 13px !important; }
        h1 { font-size: 24px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# [3. 데이터 로드 엔진 (정직한 로드 & 무결성 보장)]
@st.cache_data(ttl=600) 
def load_data(sheet_name):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = None
    
    # [1단계] 엄격한 시트 로드 (가짜 로드 금지)
    try:
        # 1. 원본 이름 시도
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0)
    except Exception:
        try:
            # 2. URL 인코딩 이름 시도 (한글 깨짐 방어)
            encoded_name = urllib.parse.quote(sheet_name)
            df = conn.read(spreadsheet=SHEET_URL, worksheet=encoded_name, ttl=0)
        except Exception:
            # 둘 다 실패 시 None 반환 (메인 로직에서 에러 처리)
            return None

    # [2단계] 데이터 컬럼 정제
    df.columns = df.columns.str.strip() # 앞뒤 공백 제거
    
    # [3단계] 컬럼 매핑 (실제 존재하는 컬럼만 변경)
    # 없는 컬럼을 억지로 만들지 않음
    mapping = {
        # 공통
        "지역_번지": "번지", "매물 특징": "내용", "해당층": "층", "매물 구분": "구분", 
        "건물명": "건물명", "관리비(만원)": "관리비",
        # 임대 관련
        "보증금(만원)": "보증금", "월차임(만원)": "월차임", "권리금_입금가(만원)": "권리금", "전용면적(평)": "면적",
        # 매매 관련
        "매매가(만원)": "매매가", "수익률(%)": "수익률", "대지면적(평)": "대지면적", "연면적(평)": "연면적"
    }
    df = df.rename(columns=mapping)
    
    # [4단계] 숫자형 변환 (존재하는 컬럼에 한해서만 수행)
    numeric_candidates = [
        "보증금", "월차임", "권리금", "관리비", "면적", "층", 
        "매매가", "수익률", "대지면적", "연면적"
    ]
    
    for col in numeric_candidates:
        if col in df.columns:
            # 문자가 섞여 있으면 NaN 처리 후 0으로 변환 (필터링을 위해)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 전체 데이터의 결측치는 빈 문자열로 처리 (검색 안전성)
    df = df.fillna("")

    # '선택' 컬럼 초기화
    if '선택' in df.columns: df = df.drop(columns=['선택'])
    df.insert(0, '선택', False)
    
    return df

# [4. 메인 실행 로직]
st.title("🏙️ 범공인 매물장 (Pro)")

# [A] 시트 관리
if 'current_sheet' not in st.session_state:
    st.session_state.current_sheet = SHEET_NAMES[0]

with st.sidebar:
    st.header("📂 작업 공간 선택")
    
    # 인덱스 안전 확보
    try:
        curr_idx = SHEET_NAMES.index(st.session_state.current_sheet)
    except:
        curr_idx = 0
        
    selected_sheet = st.selectbox("데이터 시트", SHEET_NAMES, index=curr_idx)
    
    # 시트 변경 감지
    if selected_sheet != st.session_state.current_sheet:
        st.session_state.current_sheet = selected_sheet
        st.cache_data.clear() # 데이터 갱신
        st.rerun() # 앱 리셋

    st.divider()
    
    # 초기화 버튼 (세션 및 캐시 완전 삭제)
    if st.button("🔄 검색 조건 초기화", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.session_state.clear()
        st.rerun()

    st.caption("Developed by Gemini & Pro-Mode")

# [B] 데이터 로드 실행
df_main = load_data(st.session_state.current_sheet)

# [C] 로드 실패 시 정직한 에러 출력 (Empty DataFrame 아님)
if df_main is None:
    st.error(f"🚨 **오류 발생:** '{st.session_state.current_sheet}' 시트를 찾을 수 없습니다.")
    st.info("💡 **해결 방법:** 구글 시트 하단의 탭 이름이 위 이름과 띄어쓰기까지 정확히 일치하는지 확인해주세요.")
    st.stop() # 이후 코드 실행 중단

# 현재 모드 판단 (매매 포함 여부)
is_sale_mode = "매매" in st.session_state.current_sheet

# ---------------------------------------------------------
# [모듈 2: 동적 필터 엔진 UI]
# ---------------------------------------------------------
# 없는 컬럼은 UI를 띄우지 않음으로써 사용자 혼란 방지
# ---------------------------------------------------------

# Helper: 최대값 가져오기 (컬럼 없으면 None 반환)
def get_max_if_exists(col):
    if col in df_main.columns and not df_main.empty:
        val = df_main[col].max()
        return float(val) if val > 0 else 100.0
    return None

# Helper: 세션값 가져오기 (Key가 없으면 Default 설정)
def sess(key, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]

with st.expander("🔍 정밀 검색 및 제어판 (열기/닫기)", expanded=True):
    # 1. 텍스트 검색
    c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
    with c1: st.text_input("통합 검색", key='search_keyword', placeholder="내용, 건물명, 번지 등")
    with c2: st.text_input("번지 정밀검색", key='exact_bunji', placeholder="예: 50-1")
    
    # 지역 선택 (컬럼이 있을 때만 활성화)
    unique_gu = ["전체"]
    if '지역_구' in df_main.columns:
        unique_gu += sorted(df_main['지역_구'].astype(str).unique().tolist())
    
    with c3: 
        sel_gu = st.selectbox("지역 (구)", unique_gu, key='selected_gu')
        
    unique_dong = ["전체"]
    if '지역_동' in df_main.columns:
        if sel_gu == "전체":
            unique_dong += sorted(df_main['지역_동'].astype(str).unique().tolist())
        else:
            unique_dong += sorted(df_main[df_main['지역_구'] == sel_gu]['지역_동'].astype(str).unique().tolist())
            
    with c4: 
        sel_dong = st.selectbox("지역 (동)", unique_dong, key='selected_dong')

    st.divider()

    # 2. 수치 필터 (매매 vs 임대 분기 + 컬럼 존재 여부 체크)
    r1, r2, r3 = st.columns(3)
    LIMIT_HUGE = 100000000.0 # 1조

    if is_sale_mode:
        # [매매 모드]
        with r1:
            st.markdown("##### 💰 매매가 (만원)")
            max_price = get_max_if_exists("매매가")
            if max_price is not None:
                c_a, c_b = st.columns(2)
                c_a.number_input("최소", step=1000.0, key='min_price', value=sess('min_price', 0.0))
                c_b.number_input("최대", step=1000.0, key='max_price', value=sess('max_price', max_price))
            else:
                st.caption("🚫 매매가 정보 없음")

        with r2:
            st.markdown("##### 📊 수익률(%)")
            max_yield = get_max_if_exists("수익률")
            if max_yield is not None:
                c_a, c_b = st.columns(2)
                c_a.number_input("최소", step=0.1, key='min_yield', value=sess('min_yield', 0.0))
                c_b.number_input("최대", step=0.1, key='max_yield', value=sess('max_yield', 20.0))
            else:
                st.caption("🚫 수익률 정보 없음")

        with r3:
            st.markdown("##### 📐 대지/연면적 (평)")
            max_land = get_max_if_exists("대지면적")
            max_total = get_max_if_exists("연면적")
            
            c_a, c_b = st.columns(2)
            if max_land is not None:
                c_a.number_input("대지 최소", step=1.0, key='min_land', value=sess('min_land', 0.0))
            else: c_a.caption("-")
                
            if max_total is not None:
                c_b.number_input("연면 최소", step=1.0, key='min_total', value=sess('min_total', 0.0))
            else: c_b.caption("-")

    else:
        # [임대 모드]
        with r1:
            st.markdown("##### 💰 보증금/월세 (만원)")
            max_dep = get_max_if_exists("보증금")
            max_rent = get_max_if_exists("월차임")
            
            c_a, c_b = st.columns(2)
            if max_dep is not None:
                c_a.number_input("보증금 최소", step=500.0, key='min_dep', value=sess('min_dep', 0.0))
            else: c_a.caption("보증금X")
                
            if max_rent is not None:
                c_b.number_input("월세 최소", step=10.0, key='min_rent', value=sess('min_rent', 0.0))
            else: c_b.caption("월세X")

        with r2:
            st.markdown("##### 🔑 권리금/관리비")
            is_no_kwon = st.checkbox("무권리만", key='is_no_kwon')
            max_kwon = get_max_if_exists("권리금")
            max_man = get_max_if_exists("관리비")
            
            c_a, c_b = st.columns(2)
            if max_kwon is not None:
                c_a.number_input("권리금 최소", step=100.0, key='min_kwon', disabled=is_no_kwon, value=sess('min_kwon', 0.0))
            else: c_a.caption("권리금X")
            
            if max_man is not None:
                c_b.number_input("관리비 최소", step=5.0, key='min_man', value=sess('min_man', 0.0))
            else: c_b.caption("관리비X")

        with r3:
            st.markdown("##### 📐 면적 (평)")
            max_area = get_max_if_exists("면적")
            if max_area is not None:
                c_a, c_b = st.columns(2)
                c_a.number_input("면적 최소", step=5.0, key='min_area', value=sess('min_area', 0.0))
                c_b.number_input("면적 최대", step=5.0, key='max_area', value=sess('max_area', max_area))
            else:
                st.caption("🚫 면적 정보 없음")

# ---------------------------------------------------------
# [필터링 로직: 존재하는 컬럼만 안전하게 필터링]
# ---------------------------------------------------------
df_filtered = df_main.copy()

# 1. 지역
if '지역_구' in df_filtered.columns and sel_gu != "전체":
    df_filtered = df_filtered[df_filtered['지역_구'] == sel_gu]
if '지역_동' in df_filtered.columns and sel_dong != "전체":
    df_filtered = df_filtered[df_filtered['지역_동'] == sel_dong]

# 2. 번지
if '번지' in df_filtered.columns and st.session_state.exact_bunji:
    df_filtered = df_filtered[df_filtered['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]

# 3. 수치 필터 (키 존재 여부 및 컬럼 존재 여부 동시 확인)
if is_sale_mode:
    if '매매가' in df_filtered.columns and 'min_price' in st.session_state:
        df_filtered = df_filtered[(df_filtered['매매가'] >= st.session_state.min_price) & (df_filtered['매매가'] <= st.session_state.max_price)]
    if '수익률' in df_filtered.columns and 'min_yield' in st.session_state:
        df_filtered = df_filtered[(df_filtered['수익률'] >= st.session_state.min_yield)] # 수익률은 최소값 이상만
    if '대지면적' in df_filtered.columns and 'min_land' in st.session_state:
        df_filtered = df_filtered[(df_filtered['대지면적'] >= st.session_state.min_land)]
    if '연면적' in df_filtered.columns and 'min_total' in st.session_state:
        df_filtered = df_filtered[(df_filtered['연면적'] >= st.session_state.min_total)]
else:
    if '보증금' in df_filtered.columns and 'min_dep' in st.session_state:
        df_filtered = df_filtered[(df_filtered['보증금'] >= st.session_state.min_dep) & (df_filtered['보증금'] <= st.session_state.max_dep)]
    if '월차임' in df_filtered.columns and 'min_rent' in st.session_state:
        df_filtered = df_filtered[(df_filtered['월차임'] >= st.session_state.min_rent)]
    if '면적' in df_filtered.columns and 'min_area' in st.session_state:
        df_filtered = df_filtered[(df_filtered['면적'] >= st.session_state.min_area) & (df_filtered['면적'] <= st.session_state.max_area)]
    if '관리비' in df_filtered.columns and 'min_man' in st.session_state:
        df_filtered = df_filtered[(df_filtered['관리비'] >= st.session_state.min_man)]
    if '권리금' in df_filtered.columns and 'min_kwon' in st.session_state:
        if st.session_state.is_no_kwon:
            df_filtered = df_filtered[df_filtered['권리금'] == 0]
        else:
            df_filtered = df_filtered[(df_filtered['권리금'] >= st.session_state.min_kwon)]

# ---------------------------------------------------------
# [핵심] 슈퍼 옴니 서치 (Super Omni Search)
# ---------------------------------------------------------
search_val = st.session_state.search_keyword.strip()
if search_val:
    # '선택' 컬럼 제외
    search_scope = df_filtered.drop(columns=['선택'], errors='ignore')
    
    # 전체 데이터를 문자로 변환 -> 검색
    mask = search_scope.fillna("").astype(str).apply(lambda x: ' '.join(x), axis=1).str.contains(search_val, case=False)
    df_filtered = df_filtered[mask]

# ---------------------------------------------------------
# [결과 출력]
# ---------------------------------------------------------
if len(df_filtered) == 0:
    st.warning("🔍 검색 결과가 없습니다.")
else:
    st.info(f"📋 **{st.session_state.current_sheet}** 검색 결과: **{len(df_filtered)}**건 (전체 {len(df_main)}건)")

# 리스트 잠금 (Read-only)
disabled_cols = [c for c in df_filtered.columns if c != '선택']

# 에디터 키 (시트별 유니크)
editor_key = f"editor_{st.session_state.current_sheet}"

# 동적 컬럼 설정 (있는 것만 보여줌)
col_cfg = {"선택": st.column_config.CheckboxColumn(width="small")}

# 존재하면 설정 추가, 없으면 무시
if "매매가" in df_filtered.columns: col_cfg["매매가"] = st.column_config.NumberColumn("매매가(만)", format="%d")
if "보증금" in df_filtered.columns: col_cfg["보증금"] = st.column_config.NumberColumn("보증금(만)", format="%d")
if "월차임" in df_filtered.columns: col_cfg["월차임"] = st.column_config.NumberColumn("월세(만)", format="%d")
if "권리금" in df_filtered.columns: col_cfg["권리금"] = st.column_config.NumberColumn("권리금(만)", format="%d")
if "면적" in df_filtered.columns: col_cfg["면적"] = st.column_config.NumberColumn("면적(평)", format="%.1f")
if "대지면적" in df_filtered.columns: col_cfg["대지면적"] = st.column_config.NumberColumn("대지(평)", format="%.1f")
if "연면적" in df_filtered.columns: col_cfg["연면적"] = st.column_config.NumberColumn("연면(평)", format="%.1f")
if "수익률" in df_filtered.columns: col_cfg["수익률"] = st.column_config.NumberColumn("수익률", format="%.2f%%")
if "내용" in df_filtered.columns: col_cfg["내용"] = st.column_config.TextColumn("특징", width="large")

st.data_editor(
    df_filtered,
    disabled=disabled_cols,
    use_container_width=True,
    hide_index=True,
    height=600,
    column_config=col_cfg,
    key=editor_key
)
