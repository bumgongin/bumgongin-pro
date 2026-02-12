import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# [1. 시스템 설정]
st.set_page_config(
    page_title="범공인 Pro (v24.15)",
    layout="wide",
    initial_sidebar_state="collapsed"
)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1bmTnLu-vMvlAGRSsCI4a8lk00U38covWl5Wfn9JZYVU/edit"

# [2. 스타일: 모바일 터치 최적화]
st.markdown("""
    <style>
    .stButton button { min-height: 50px !important; font-size: 16px !important; font-weight: bold !important; }
    @media (max-width: 768px) { 
        .stDataEditor { font-size: 13px !important; }
        h1 { font-size: 24px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# [3. 데이터 로드 엔진]
@st.cache_data(ttl=60)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=SHEET_URL, ttl=0)
    df.columns = df.columns.str.strip()
    mapping = {
        "보증금(만원)": "보증금",
        "월차임(만원)": "월차임",
        "권리금_입금가(만원)": "권리금",
        "전용면적(평)": "면적",
        "매물 특징": "내용",
        "지역_번지": "번지",
        "관리비(만원)": "관리비"
    }
    df = df.rename(columns=mapping)
    df = df.fillna("")
    
    # 숫자형 데이터 안전 변환 (필터링 및 슬라이더용)
    numeric_cols = ["보증금", "월차임", "면적", "권리금", "관리비"]
    for col in numeric_cols:
        if col in df.columns:
            # 문자를 숫자로 변환, 에러나 빈 값은 0으로 처리
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if '선택' in df.columns:
        df = df.drop(columns=['선택'])
    df.insert(0, '선택', False)
    return df

# [4. 메인 실행 로직]
st.title("🏙️ 범공인 매물장")

try:
    df_main = load_data()
    
    # ---------------------------------------------------------
    # [모듈 2: 지능형 필터 엔진 시작]
    # ---------------------------------------------------------
    
    with st.expander("🔍 상세 검색 및 필터 (클릭하여 열기/닫기)", expanded=True):
        # [A] 검색창 및 지역 필터 (반응형 레이아웃)
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_keyword = st.text_input("검색어 입력 (건물명, 특징, 번지 등)", placeholder="예: 대로변, 1층, 역세권")

        # 동적 지역 필터 로직
        unique_gu = ["전체"] + sorted(df_main['지역_구'].unique().tolist())
        with col2:
            selected_gu = st.selectbox("지역 (구)", unique_gu)
        
        # 구 선택에 따른 동 목록 동적 생성
        if selected_gu == "전체":
            unique_dong = ["전체"] + sorted(df_main['지역_동'].unique().tolist())
        else:
            unique_dong = ["전체"] + sorted(df_main[df_main['지역_구'] == selected_gu]['지역_동'].unique().tolist())
            
        with col3:
            selected_dong = st.selectbox("지역 (동)", unique_dong)

        st.divider()

        # [B] 범위 슬라이더 (자동 min/max 계산)
        # 데이터프레임에서 최대값 추출 (데이터가 없을 경우 기본값 100 설정)
        max_deposit = int(df_main['보증금'].max()) if not df_main.empty else 10000
        max_rent = int(df_main['월차임'].max()) if not df_main.empty else 1000
        max_area = int(df_main['면적'].max()) if not df_main.empty else 100

        s_col1, s_col2, s_col3 = st.columns(3)
        
        with s_col1:
            val_deposit = st.slider("보증금 (만원)", 0, max_deposit, (0, max_deposit))
        with s_col2:
            val_rent = st.slider("월세 (만원)", 0, max_rent, (0, max_rent))
        with s_col3:
            val_area = st.slider("면적 (평)", 0, max_area, (0, max_area))

    # [C] 필터링 적용 (df_main -> df_filtered)
    df_filtered = df_main.copy()

    # 1. 지역 필터
    if selected_gu != "전체":
        df_filtered = df_filtered[df_filtered['지역_구'] == selected_gu]
    if selected_dong != "전체":
        df_filtered = df_filtered[df_filtered['지역_동'] == selected_dong]

    # 2. 슬라이더 범위 필터
    df_filtered = df_filtered[
        (df_filtered['보증금'] >= val_deposit[0]) & (df_filtered['보증금'] <= val_deposit[1]) &
        (df_filtered['월차임'] >= val_rent[0]) & (df_filtered['월차임'] <= val_rent[1]) &
        (df_filtered['면적'] >= val_area[0]) & (df_filtered['면적'] <= val_area[1])
    ]

    # 3. 키워드 검색 (내용, 번지, 구분 등 통합 검색)
    if search_keyword:
        # 여러 컬럼을 하나의 문자열로 합쳐서 검색 (대소문자 무시)
        keyword_mask = (
            df_filtered['내용'].astype(str).str.contains(search_keyword, case=False) | 
            df_filtered['번지'].astype(str).str.contains(search_keyword, case=False) |
            df_filtered['구분'].astype(str).str.contains(search_keyword, case=False)
        )
        df_filtered = df_filtered[keyword_mask]

    # ---------------------------------------------------------
    # [모듈 2 종료]
    # ---------------------------------------------------------

    st.success(f"✅ 총 {len(df_filtered)}건 검색됨 (전체 {len(df_main)}건 중)")
    
    edited_df = st.data_editor(
        df_filtered,  # 필터링된 데이터프레임 연결
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "선택": st.column_config.CheckboxColumn(width="small"),
            "보증금": st.column_config.NumberColumn("보증금(만)", format="%d"),
            "월차임": st.column_config.NumberColumn("월세(만)", format="%d"),
            "면적": st.column_config.NumberColumn("면적(평)", format="%.1f"),
            "내용": st.column_config.TextColumn("특징", width="large"),
        },
        column_order=["선택", "구분", "지역_구", "지역_동", "보증금", "월차임", "면적", "번지", "내용"],
        key="data_editor_key" # 위젯 키 고정
    )

except Exception as e:
    st.error(f"🚨 에러 발생: {e}")
    # 디버깅을 위해 에러 상세 내용 표시 (개발 단계에서 유용)
    st.write(e)

st.divider()
st.caption("Developed by Gemini & Pro-Mode")
