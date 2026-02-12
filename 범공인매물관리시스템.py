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
@st.cache_data(ttl=60)
def load_data(sheet_name):
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0)
    except:
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        
    df.columns = df.columns.str.strip()
    mapping = {
        "보증금(만원)": "보증금", "월차임(만원)": "월차임", "권리금_입금가(만원)": "권리금",
        "전용면적(평)": "면적", "매물 특징": "내용", "지역_번지": "번지",
        "관리비(만원)": "관리비", "해당층": "층", "매물 구분": "구분", "건물명": "건물명"
    }
    df = df.rename(columns=mapping)
    df = df.fillna("")
    
    numeric_cols = ["보증금", "월차임", "면적", "권리금", "관리비", "층"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if '선택' in df.columns: df = df.drop(columns=['선택'])
    df.insert(0, '선택', False)
    return df

# [4. 메인 실행 로직]
st.title("🏙️ 범공인 매물장 (Pro)")

with st.sidebar:
    st.header("📂 작업 공간 선택")
    selected_sheet = st.selectbox("데이터 시트", SHEET_NAMES)
    st.divider()
    st.caption("Developed by Gemini")

try:
    df_main = load_data(selected_sheet)

    # ---------------------------------------------------------
    # [핵심 로직 1] 스마트 기본값 계산 (데이터 기반)
    # ---------------------------------------------------------
    # 데이터가 로드되면 현재 데이터의 최대값을 계산해둡니다.
    def get_max_val(col):
        if col in df_main.columns and not df_main.empty:
            return float(df_main[col].max())
        return 0.0

    current_max_dep = get_max_val("보증금") if get_max_val("보증금") > 0 else 10000.0
    current_max_rent = get_max_val("월차임") if get_max_val("월차임") > 0 else 500.0
    current_max_kwon = get_max_val("권리금") if get_max_val("권리금") > 0 else 5000.0
    current_max_man = get_max_val("관리비") if get_max_val("관리비") > 0 else 50.0
    current_max_area = get_max_val("면적") if get_max_val("면적") > 0 else 100.0
    current_max_fl = get_max_val("층") if get_max_val("층") > 0 else 50.0

    # 입력 가능한 절대 한계치 (1조 원)
    LIMIT_HUGE = 100000000.0 
    LIMIT_RENT = 1000000.0

    # ---------------------------------------------------------
    # [핵심 로직 2] 초기화 함수 (Key 동기화 완벽 구현)
    # ---------------------------------------------------------
    def reset_filters_dynamic():
        # 1. 텍스트 및 셀렉트박스 리셋
        st.session_state['search_keyword'] = ""
        st.session_state['exact_bunji'] = ""
        st.session_state['selected_gu_box'] = "전체" # 실제 위젯 key와 일치
        st.session_state['selected_dong_box'] = "전체"
        
        # 2. 숫자값 리셋 (Min=0, Max=현재 데이터의 최대값)
        st.session_state['min_dep'] = 0.0
        st.session_state['max_dep'] = current_max_dep 
        st.session_state['min_rent'] = 0.0
        st.session_state['max_rent'] = current_max_rent
        st.session_state['min_kwon'] = 0.0
        st.session_state['max_kwon'] = current_max_kwon
        st.session_state['min_man'] = 0.0
        st.session_state['max_man'] = current_max_man
        st.session_state['min_area'] = 0.0
        st.session_state['max_area'] = current_max_area
        st.session_state['min_fl'] = -20.0  # 지하 20층까지 확장
        st.session_state['max_fl'] = current_max_fl if current_max_fl > 0 else 50.0
        
        st.session_state['is_no_kwon'] = False

    # 최초 실행 시 혹은 시트 변경 시 세션 상태 초기화가 필요하면 주석 해제하여 사용
    # (여기서는 값이 없을 때만 초기값을 넣도록 설정)
    if 'max_dep' not in st.session_state:
        reset_filters_dynamic()

    # ---------------------------------------------------------
    # [모듈 2: 최종 완성형 필터 엔진]
    # ---------------------------------------------------------
    with st.expander("🔍 정밀 검색 및 제어판 (열기/닫기)", expanded=True):
        # [A] 검색 및 지역
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
        with c1: st.text_input("통합 검색", key='search_keyword', placeholder="키워드 입력")
        with c2: st.text_input("번지 정밀검색", key='exact_bunji', placeholder="예: 50-1")
        
        unique_gu = ["전체"] + sorted(df_main['지역_구'].unique().tolist())
        with c3: selected_gu = st.selectbox("지역 (구)", unique_gu, key='selected_gu_box')
            
        if selected_gu == "전체":
            unique_dong = ["전체"] + sorted(df_main['지역_동'].unique().tolist())
        else:
            unique_dong = ["전체"] + sorted(df_main[df_main['지역_구'] == selected_gu]['지역_동'].unique().tolist())
        with c4: selected_dong = st.selectbox("지역 (동)", unique_dong, key='selected_dong_box')

        # [초기화 버튼]
        if st.button("🔄 검색 조건 초기화", use_container_width=True, type="primary"):
            reset_filters_dynamic()
            st.rerun()

        st.divider()

        # [B] 수치 정밀 입력 (스마트 기본값 + 1조 한계)
        r1_col1, r1_col2, r1_col3 = st.columns(3)

        with r1_col1:
            st.markdown("##### 💰 금액 조건 (단위: 만원)")
            c_d1, c_d2 = st.columns(2)
            st.number_input("보증금(최소)", step=1000.0, key='min_dep')
            # value는 session_state에서 가져오므로 생략, max_value는 1조 제한
            st.number_input("보증금(최대)", max_value=LIMIT_HUGE, step=1000.0, key='max_dep') 
            
            c_r1, c_r2 = st.columns(2)
            st.number_input("월세(최소)", step=100.0, key='min_rent')
            st.number_input("월세(최대)", max_value=LIMIT_RENT, step=100.0, key='max_rent')

        with r1_col2:
            st.markdown("##### 🔑 권리금/관리비")
            is_no_kwon = st.checkbox("무권리 매물만 보기", key='is_no_kwon')
            c_k1, c_k2 = st.columns(2)
            st.number_input("권리금(최소)", step=500.0, key='min_kwon', disabled=is_no_kwon)
            st.number_input("권리금(최대)", max_value=LIMIT_HUGE, step=500.0, key='max_kwon', disabled=is_no_kwon)

            c_m1, c_m2 = st.columns(2)
            st.number_input("관리비(최소)", step=5.0, key='min_man')
            st.number_input("관리비(최대)", max_value=LIMIT_RENT, step=5.0, key='max_man')

        with r1_col3:
            st.markdown("##### 📐 면적/층수")
            c_a1, c_a2 = st.columns(2)
            st.number_input("면적(최소)", step=10.0, key='min_area')
            st.number_input("면적(최대)", max_value=LIMIT_HUGE, step=10.0, key='max_area')
            
            c_f1, c_f2 = st.columns(2)
            # 층수 범위 확장 (-20 ~ 100)
            st.number_input("층(최저)", min_value=-20.0, step=1.0, key='min_fl')
            st.number_input("층(최고)", max_value=100.0, step=1.0, key='max_fl')

    # [C] 필터링 로직 (안전한 검색)
    df_filtered = df_main.copy()

    # 1. 지역 필터
    if selected_gu != "전체":
        df_filtered = df_filtered[df_filtered['지역_구'] == selected_gu]
    if selected_dong != "전체":
        df_filtered = df_filtered[df_filtered['지역_동'] == selected_dong]

    # 2. 번지수 정밀 타격
    if st.session_state.exact_bunji:
        df_filtered = df_filtered[df_filtered['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]

    # 3. 수치 범위 필터
    df_filtered = df_filtered[
        (df_filtered['보증금'] >= st.session_state['min_dep']) & (df_filtered['보증금'] <= st.session_state['max_dep']) &
        (df_filtered['월차임'] >= st.session_state['min_rent']) & (df_filtered['월차임'] <= st.session_state['max_rent']) &
        (df_filtered['면적'] >= st.session_state['min_area']) & (df_filtered['면적'] <= st.session_state['max_area']) &
        (df_filtered['관리비'] >= st.session_state['min_man']) & (df_filtered['관리비'] <= st.session_state['max_man'])
    ]
    
    if '층' in df_filtered.columns:
         df_filtered = df_filtered[
            (df_filtered['층'] >= st.session_state['min_fl']) & (df_filtered['층'] <= st.session_state['max_fl'])
         ]

    # 4. 권리금 로직
    if is_no_kwon:
        df_filtered = df_filtered[df_filtered['권리금'] == 0]
    else:
        df_filtered = df_filtered[
            (df_filtered['권리금'] >= st.session_state['min_kwon']) & (df_filtered['권리금'] <= st.session_state['max_kwon'])
        ]

    # ---------------------------------------------------------
    # [핵심 로직 3] 키워드 검색 로직 안전화 (논리 분리)
    # ---------------------------------------------------------
    search_val = st.session_state.search_keyword
    if search_val:
        # 1. 모든 행에 대해 False인 기본 마스크 생성
        keyword_mask = pd.Series([False] * len(df_filtered), index=df_filtered.index)
        
        # 2. 존재하는 컬럼만 확인하여 OR 연산 (Syntax Error 방지)
        # 내용(특징) 검색
        if '내용' in df_filtered.columns:
            keyword_mask |= df_filtered['내용'].astype(str).str.contains(search_val, case=False)
        
        # 건물명 검색
        if '건물명' in df_filtered.columns:
            keyword_mask |= df_filtered['건물명'].astype(str).str.contains(search_val, case=False)
            
        # 매물 구분 검색
        if '구분' in df_filtered.columns:
            keyword_mask |= df_filtered['구분'].astype(str).str.contains(search_val, case=False)
            
        # 3. 최종 필터링 적용
        df_filtered = df_filtered[keyword_mask]

    # 결과 출력
    st.info(f"📋 **{selected_sheet}** 탭 검색 결과: **{len(df_filtered)}**건 (전체 {len(df_main)}건)")
    
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
        column_order=["선택", "지역_동", "번지", "층", "보증금", "월차임", "권리금", "면적", "내용"],
        key="data_editor_key"
    )

except Exception as e:
    st.error(f"🚨 시스템 에러: {e}")
    st.write(e) # 개발 모드용 에러 상세 출력

st.divider()
st.caption("Developed by Gemini & Pro-Mode")
