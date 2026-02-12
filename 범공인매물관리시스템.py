import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# [1. 시스템 설정]
st.set_page_config(
    page_title="범공인 Pro (v24.15)",
    layout="wide",
    initial_sidebar_state="expanded"
)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1bmTnLu-vMvlAGRSsCI4a8lk00U38covWl5Wfn9JZYVU/edit"
# 💡 [중요] 실제 구글 시트 탭 이름으로 수정 필요
SHEET_NAMES = ["시트1", "임대", "매매"] 

# [2. 스타일 설정]
st.markdown("""
    <style>
    .stButton button { min-height: 50px !important; font-size: 16px !important; font-weight: bold !important; }
    input[type=number] { min-height: 40px; }
    @media (max-width: 768px) { 
        .stDataEditor { font-size: 13px !important; }
        h1 { font-size: 24px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# [3. 데이터 로드 엔진]
# ttl=0설정으로 캐시를 너무 오래 잡지 않게 하여 시트 변경 시 즉시 반영 유도
@st.cache_data(ttl=600) 
def load_data(sheet_name):
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # worksheet에 따라 다른 데이터를 가져옴
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0)
    except Exception:
        # 탭 이름 오류 시 안전장치 (기본 탭 로드)
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        
    df.columns = df.columns.str.strip()
    
    # 매핑 테이블 (필요시 시트 컬럼명에 맞춰 조정)
    mapping = {
        "보증금(만원)": "보증금", "월차임(만원)": "월차임", "권리금_입금가(만원)": "권리금",
        "전용면적(평)": "면적", "매물 특징": "내용", "지역_번지": "번지",
        "관리비(만원)": "관리비", "해당층": "층", "매물 구분": "구분", "건물명": "건물명"
    }
    df = df.rename(columns=mapping)
    df = df.fillna("")
    
    # 숫자형 데이터 안전 변환
    numeric_cols = ["보증금", "월차임", "면적", "권리금", "관리비", "층"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # '선택' 컬럼 초기화
    if '선택' in df.columns: df = df.drop(columns=['선택'])
    df.insert(0, '선택', False)
    return df

# [4. 메인 실행 로직]
st.title("🏙️ 범공인 매물장 (Pro)")

# 사이드바: 시트 선택
with st.sidebar:
    st.header("📂 작업 공간 선택")
    # 시트를 바꾸면 자동으로 load_data가 새로운 sheet_name으로 실행됨
    selected_sheet = st.selectbox("데이터 시트", SHEET_NAMES)
    
    st.divider()
    
    # [수정된 초기화 버튼 로직]
    # 사이드바에 두어 언제든 접근 가능하게 함 (또는 메인 화면 하단 배치 가능)
    if st.button("🔄 데이터 및 필터 초기화", type="primary", use_container_width=True):
        st.cache_data.clear()   # 1. 데이터 캐시 삭제 (구글 시트 새로 읽기)
        st.session_state.clear() # 2. 필터 입력값(Session State) 전체 삭제
        st.rerun()              # 3. 앱 재시작 (모든 위젯 기본값 복구)

    st.caption("Developed by Gemini & Pro-Mode")

try:
    df_main = load_data(selected_sheet)

    # ---------------------------------------------------------
    # [스마트 기본값 계산]
    # ---------------------------------------------------------
    def get_max_val(col):
        if col in df_main.columns and not df_main.empty:
            return float(df_main[col].max())
        return 0.0

    # 데이터가 로드된 직후의 최대값 계산
    curr_max_dep = get_max_val("보증금") if get_max_val("보증금") > 0 else 10000.0
    curr_max_rent = get_max_val("월차임") if get_max_val("월차임") > 0 else 500.0
    curr_max_kwon = get_max_val("권리금") if get_max_val("권리금") > 0 else 5000.0
    curr_max_man = get_max_val("관리비") if get_max_val("관리비") > 0 else 50.0
    curr_max_area = get_max_val("면적") if get_max_val("면적") > 0 else 100.0
    curr_max_fl = get_max_val("층") if get_max_val("층") > 0 else 50.0

    # 절대 한계치 (1조 원)
    LIMIT_HUGE = 100000000.0 
    LIMIT_RENT = 1000000.0

    # ---------------------------------------------------------
    # [모듈 2: 최종 보수된 필터 엔진]
    # ---------------------------------------------------------
    with st.expander("🔍 정밀 검색 및 제어판 (열기/닫기)", expanded=True):
        # [A] 검색 및 지역
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
        with c1: 
            search_keyword = st.text_input("통합 검색", key='search_keyword', placeholder="키워드 입력")
        with c2: 
            exact_bunji = st.text_input("번지 정밀검색", key='exact_bunji', placeholder="예: 50-1")
        
        unique_gu = ["전체"] + sorted(df_main['지역_구'].unique().tolist())
        with c3: 
            selected_gu = st.selectbox("지역 (구)", unique_gu, key='selected_gu_box')
            
        if selected_gu == "전체":
            unique_dong = ["전체"] + sorted(df_main['지역_동'].unique().tolist())
        else:
            unique_dong = ["전체"] + sorted(df_main[df_main['지역_구'] == selected_gu]['지역_동'].unique().tolist())
        with c4: 
            selected_dong = st.selectbox("지역 (동)", unique_dong, key='selected_dong_box')

        st.divider()

        # [B] 수치 정밀 입력
        # value를 설정하여 초기값을 '현재 데이터의 최대값'으로 잡음
        # 초기화 버튼 클릭 시 session_state가 날아가므로, 다시 여기로 와서 value값(curr_max_...)으로 세팅됨
        r1_col1, r1_col2, r1_col3 = st.columns(3)

        with r1_col1:
            st.markdown("##### 💰 금액 조건 (단위: 만원)")
            c_d1, c_d2 = st.columns(2)
            min_dep = c_d1.number_input("보증금(최소)", step=1000.0, key='min_dep')
            max_dep = c_d2.number_input("보증금(최대)", value=curr_max_dep, max_value=LIMIT_HUGE, step=1000.0, key='max_dep')
            
            c_r1, c_r2 = st.columns(2)
            min_rent = c_r1.number_input("월세(최소)", step=100.0, key='min_rent')
            max_rent = c_r2.number_input("월세(최대)", value=curr_max_rent, max_value=LIMIT_RENT, step=100.0, key='max_rent')

        with r1_col2:
            st.markdown("##### 🔑 권리금/관리비")
            is_no_kwon = st.checkbox("무권리 매물만 보기", key='is_no_kwon')
            c_k1, c_k2 = st.columns(2)
            min_kwon = c_k1.number_input("권리금(최소)", step=500.0, key='min_kwon', disabled=is_no_kwon)
            max_kwon = c_k2.number_input("권리금(최대)", value=curr_max_kwon, max_value=LIMIT_HUGE, step=500.0, key='max_kwon', disabled=is_no_kwon)

            c_m1, c_m2 = st.columns(2)
            min_man = c_m1.number_input("관리비(최소)", step=5.0, key='min_man')
            max_man = c_m2.number_input("관리비(최대)", value=curr_max_man, max_value=LIMIT_RENT, step=5.0, key='max_man')

        with r1_col3:
            st.markdown("##### 📐 면적/층수")
            c_a1, c_a2 = st.columns(2)
            min_area = c_a1.number_input("면적(최소)", step=10.0, key='min_area')
            max_area = c_a2.number_input("면적(최대)", value=curr_max_area, max_value=LIMIT_HUGE, step=10.0, key='max_area')
            
            c_f1, c_f2 = st.columns(2)
            # [수정] 지하층 검색을 위해 min_value를 -20.0으로 확장
            min_fl = c_f1.number_input("층(최저)", value=-2.0, min_value=-20.0, step=1.0, key='min_fl')
            max_fl = c_f2.number_input("층(최고)", value=curr_max_fl if curr_max_fl > 0 else 50.0, max_value=100.0, step=1.0, key='max_fl')

    # [C] 필터링 로직 (변수에 직접 할당된 값 사용)
    df_filtered = df_main.copy()

    # 1. 지역 필터
    if selected_gu != "전체":
        df_filtered = df_filtered[df_filtered['지역_구'] == selected_gu]
    if selected_dong != "전체":
        df_filtered = df_filtered[df_filtered['지역_동'] == selected_dong]

    # 2. 번지수 정밀 타격
    if exact_bunji:
        df_filtered = df_filtered[df_filtered['번지'].astype(str).str.strip() == exact_bunji.strip()]

    # 3. 수치 범위 필터
    df_filtered = df_filtered[
        (df_filtered['보증금'] >= min_dep) & (df_filtered['보증금'] <= max_dep) &
        (df_filtered['월차임'] >= min_rent) & (df_filtered['월차임'] <= max_rent) &
        (df_filtered['면적'] >= min_area) & (df_filtered['면적'] <= max_area) &
        (df_filtered['관리비'] >= min_man) & (df_filtered['관리비'] <= max_man)
    ]
    
    if '층' in df_filtered.columns:
         df_filtered = df_filtered[
            (df_filtered['층'] >= min_fl) & (df_filtered['층'] <= max_fl)
         ]

    # 4. 권리금 로직
    if is_no_kwon:
        df_filtered = df_filtered[df_filtered['권리금'] == 0]
    else:
        df_filtered = df_filtered[
            (df_filtered['권리금'] >= min_kwon) & (df_filtered['권리금'] <= max_kwon)
        ]

    # 5. 키워드 검색 로직 (안전한 방식)
    if search_keyword:
        # 모든 행 False 마스크 생성
        keyword_mask = pd.Series([False] * len(df_filtered), index=df_filtered.index)
        
        # 존재하는 컬럼에 대해서만 OR 연산
        if '내용' in df_filtered.columns:
            keyword_mask |= df_filtered['내용'].astype(str).str.contains(search_keyword, case=False)
        if '건물명' in df_filtered.columns:
            keyword_mask |= df_filtered['건물명'].astype(str).str.contains(search_keyword, case=False)
        if '구분' in df_filtered.columns:
            keyword_mask |= df_filtered['구분'].astype(str).str.contains(search_keyword, case=False)
            
        df_filtered = df_filtered[keyword_mask]

    # 결과 출력
    st.info(f"📋 **{selected_sheet}** 탭 검색 결과: **{len(df_filtered)}**건 (전체 {len(df_main)}건)")
    
    # [수정] column_order 삭제 -> 모든 컬럼 표시
    st.data_editor(
        df_filtered,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "선택": st.column_config.CheckboxColumn(width="small"),
            "보증금": st.column_config.NumberColumn("보증금", format="%d만"),
            "월차임": st.column_config.NumberColumn("월세", format="%d만"),
            "권리금": st.column_config.NumberColumn("권리금", format="%d만"),
            "면적": st.column_config.NumberColumn("면적", format="%.1f평"),
            "층": st.column_config.NumberColumn("층", format="%d층"),
            "내용": st.column_config.TextColumn("특징", width="large"),
        },
        key="data_editor_key"
    )

except Exception as e:
    st.error(f"🚨 시스템 에러: {e}")
    st.write("잠시 후 다시 시도하거나, [초기화] 버튼을 눌러주세요.")
