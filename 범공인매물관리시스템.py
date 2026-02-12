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
    /* 숫자 입력창 화살표 버튼 크기 확보 (모바일) */
    input[type=number] { min-height: 40px; }
    @media (max-width: 768px) { 
        .stDataEditor { font-size: 13px !important; }
        h1 { font-size: 24px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# [3. 데이터 로드 엔진 (전처리 강화)]
@st.cache_data(ttl=60)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=SHEET_URL, ttl=0)
    df.columns = df.columns.str.strip()
    
    # 매핑 테이블 (필요시 시트 컬럼명에 맞춰 조정하세요)
    mapping = {
        "보증금(만원)": "보증금",
        "월차임(만원)": "월차임",
        "권리금_입금가(만원)": "권리금",
        "전용면적(평)": "면적",
        "매물 특징": "내용",
        "지역_번지": "번지",
        "관리비(만원)": "관리비",
        "해당층": "층" # 시트에 '해당층' 컬럼이 있다면 '층'으로 매핑
    }
    df = df.rename(columns=mapping)
    df = df.fillna("")
    
    # [핵심] 숫자형 데이터 안전 변환 (음수 층수, 무권리 등 처리)
    numeric_cols = ["보증금", "월차임", "면적", "권리금", "관리비", "층"]
    for col in numeric_cols:
        if col in df.columns:
            # errors='coerce': 숫자가 아닌 문자가 섞여 있으면 NaN(결측치)으로 변환 후 0으로 채움
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if '선택' in df.columns:
        df = df.drop(columns=['선택'])
    df.insert(0, '선택', False)
    return df

# [4. 메인 실행 로직]
st.title("🏙️ 범공인 매물장 (Pro)")

try:
    df_main = load_data()
    
    # ---------------------------------------------------------
    # [모듈 2: 실무형 정밀 필터 엔진 (UI 개편)]
    # ---------------------------------------------------------
    
    with st.expander("🔍 정밀 검색창 (클릭)", expanded=True):
        # [A] 검색 및 지역 설정
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
        
        with c1:
            search_keyword = st.text_input("통합 검색", placeholder="키워드 (건물명, 특징 등)")
        with c2:
            exact_bunji = st.text_input("번지 정밀검색", placeholder="예: 50-1 (정확히 일치)")
        
        # 동적 지역 필터
        unique_gu = ["전체"] + sorted(df_main['지역_구'].unique().tolist())
        with c3:
            selected_gu = st.selectbox("지역 (구)", unique_gu)
        
        if selected_gu == "전체":
            unique_dong = ["전체"] + sorted(df_main['지역_동'].unique().tolist())
        else:
            unique_dong = ["전체"] + sorted(df_main[df_main['지역_구'] == selected_gu]['지역_동'].unique().tolist())
        with c4:
            selected_dong = st.selectbox("지역 (동)", unique_dong)

        st.divider()

        # [B] 수치 정밀 입력 (Range Input)
        # 레이아웃: [보증금/월세] / [권리금/관리비] / [면적/층]
        r1_col1, r1_col2, r1_col3 = st.columns(3)

        # 1. 금액 (보증금, 월세)
        with r1_col1:
            st.markdown("##### 💰 금액 조건")
            min_dep, max_dep = st.columns(2)
            input_min_dep = min_dep.number_input("보증금(최소)", value=0, step=500)
            input_max_dep = max_dep.number_input("보증금(최대)", value=100000, step=500)
            
            min_rent, max_rent = st.columns(2)
            input_min_rent = min_rent.number_input("월세(최소)", value=0, step=10)
            input_max_rent = max_rent.number_input("월세(최대)", value=10000, step=50)

        # 2. 권리금 및 관리비
        with r1_col2:
            st.markdown("##### 🔑 권리금/관리비")
            is_no_kwon = st.checkbox("무권리 매물만 보기")
            
            min_kwon, max_kwon = st.columns(2)
            # 무권리 체크 시 입력창 비활성화(disabled) 느낌을 주거나 로직으로 처리
            input_min_kwon = min_kwon.number_input("권리금(최소)", value=0, step=100, disabled=is_no_kwon)
            input_max_kwon = max_kwon.number_input("권리금(최대)", value=50000, step=100, disabled=is_no_kwon)

            min_man, max_man = st.columns(2)
            input_min_man = min_man.number_input("관리비(최소)", value=0, step=5)
            input_max_man = max_man.number_input("관리비(최대)", value=500, step=5)

        # 3. 면적 및 층수
        with r1_col3:
            st.markdown("##### 📐 면적/층수")
            min_area, max_area = st.columns(2)
            input_min_area = min_area.number_input("면적(최소)", value=0, step=5)
            input_max_area = max_area.number_input("면적(최대)", value=500, step=5)
            
            min_fl, max_fl = st.columns(2)
            # 층수는 음수(지하) 가능
            input_min_fl = min_fl.number_input("층(최저)", value=-2, step=1)
            input_max_fl = max_fl.number_input("층(최고)", value=20, step=1)

    # [C] 필터링 로직 엔진 (Processing)
    df_filtered = df_main.copy()

    # 1. 지역 필터
    if selected_gu != "전체":
        df_filtered = df_filtered[df_filtered['지역_구'] == selected_gu]
    if selected_dong != "전체":
        df_filtered = df_filtered[df_filtered['지역_동'] == selected_dong]

    # 2. 번지수 정밀 타격 (완전 일치)
    if exact_bunji:
        # 공백 제거 후 문자열 비교
        df_filtered = df_filtered[df_filtered['번지'].astype(str).str.strip() == exact_bunji.strip()]

    # 3. 수치 범위 필터 (Range)
    df_filtered = df_filtered[
        (df_filtered['보증금'] >= input_min_dep) & (df_filtered['보증금'] <= input_max_dep) &
        (df_filtered['월차임'] >= input_min_rent) & (df_filtered['월차임'] <= input_max_rent) &
        (df_filtered['면적'] >= input_min_area) & (df_filtered['면적'] <= input_max_area) &
        (df_filtered['관리비'] >= input_min_man) & (df_filtered['관리비'] <= input_max_man)
    ]
    
    # 4. 층수 필터 (컬럼 존재 시)
    if '층' in df_filtered.columns:
         df_filtered = df_filtered[
            (df_filtered['층'] >= input_min_fl) & (df_filtered['층'] <= input_max_fl)
         ]

    # 5. 권리금 로직 (무권리 vs 범위)
    if is_no_kwon:
        df_filtered = df_filtered[df_filtered['권리금'] == 0]
    else:
        df_filtered = df_filtered[
            (df_filtered['권리금'] >= input_min_kwon) & (df_filtered['권리금'] <= input_max_kwon)
        ]

    # 6. 통합 키워드 검색
    if search_keyword:
        keyword_mask = (
            df_filtered['내용'].astype(str).str.contains(search_keyword, case=False) | 
            df_filtered['건물명'].astype(str).str.contains(search_keyword, case=False) if '건물명' in df_filtered.columns else False |
            df_filtered['구분'].astype(str).str.contains(search_keyword, case=False)
        )
        df_filtered = df_filtered[keyword_mask]

    # ---------------------------------------------------------
    # [모듈 2 종료]
    # ---------------------------------------------------------

    # 상단 정보 표시
    st.info(f"📋 검색 결과: **{len(df_filtered)}**건 (전체 {len(df_main)}건 중)")
    
    # 결과 테이블
    edited_df = st.data_editor(
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
            "번지": st.column_config.TextColumn("번지"),
            "내용": st.column_config.TextColumn("특징", width="large"),
        },
        # 컬럼 순서 재배치 (보기 편하게)
        column_order=["선택", "지역_동", "번지", "층", "보증금", "월차임", "권리금", "면적", "내용"],
        key="data_editor_key"
    )

except Exception as e:
    st.error(f"🚨 시스템 에러: {e}")
    st.caption("관리자에게 문의하세요.")

st.divider()
st.caption("Developed by Gemini & Pro-Mode")
