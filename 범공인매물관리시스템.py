import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import uuid
import time

# [1. 시스템 기본 설정]
st.set_page_config(page_title="범공인 Pro (v24.15)", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1bmTnLu-vMvlAGRSsCI4a8lk00U38covWl5Wfn9JZYVU/edit"

# [2. 스타일: 모바일 최적화]
st.markdown("""
    <style>
    .stButton button { min-height: 60px !important; font-size: 16px !important; font-weight: 700 !important; }
    @media (max-width: 768px) { .stDataEditor { font-size: 12px !important; } }
    </style>
""", unsafe_allow_html=True)

# [3. 데이터 엔진: 사장님 시트 맞춤형]
@st.cache_data(ttl=60)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # 한글 이름 대신 '첫 번째 시트'를 강제로 가져오도록 설정 (에러 방지)
    df = conn.read(spreadsheet=SHEET_URL, ttl=0)
    
    # [컬럼 매핑] 사장님 시트의 실제 이름 -> 시스템 내부 이름
    mapping = {
        "구분": "구분",
        "지역_구": "지역_구",
        "지역_동": "지역_동",
        "보증금(만원)": "보증금",
        "월차임(만원)": "월차임",
        "전용면적(평)": "면적",
        "매물 특징": "내용",
        "지역_번지": "번지"
    }
    
    # 시트 데이터 정제
    df = df.rename(columns=mapping)
    df = df.fillna("")
    
    # 필수 컬럼 보장
    for col in ["선택", "구분", "지역_구", "지역_동", "보증금", "월차임", "면적", "내용"]:
        if col not in df.columns: df[col] = ""
    
    df.insert(0, '선택', False)
    return df

# 데이터 로드 실행
try:
    df_main = load_data()
    st.session_state.data = df_main
    load_success = True
except Exception as e:
    st.error(f"데이터 로드 중 에러 발생: {e}")
    load_success = False

# [4. UI 구성]
with st.sidebar:
    st.header("🏗️ 범공인 Pro")
    if load_success:
        st.success(f"✅ 데이터 {len(st.session_state.data)}건 로드 성공!")
    
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

st.title("🏙️ 매물 관리 모드")

if load_success:
    # [MODULE: FILTER_SECTION] - 사장님 시트 맞춤형 필터
    with st.expander("🔍 정밀 필터 설정", expanded=True):
        f_col1, f_col2, f_col3 = st.columns(3)
        
        with f_col1:
            gu_list = ["전체"] + sorted(list(set(df_main["지역_구"].astype(str))))
            sel_gu = st.selectbox("📍 지역(구)", gu_list)
        
        with f_col2:
            df_filtered = df_main[df_main["지역_구"] == sel_gu] if sel_gu != "전체" else df_main
            dong_list = ["전체"] + sorted(list(set(df_filtered["지역_동"].astype(str))))
            sel_dong = st.selectbox("🏠 지역(동)", dong_list)
        
        with f_col3:
            search = st.text_input("📝 키워드 검색 (내용/번지)")

    # 필터 적용
    df_final = df_filtered.copy()
    if sel_dong != "전체": df_final = df_final[df_final["지역_동"] == sel_dong]
    if search: df_final = df_final[df_final["내용"].str.contains(search) | df_final["번지"].str.contains(search)]

    # [MODULE: LIST_SECTION]
    st.subheader(f"📋 검색 결과 ({len(df_final)}건)")
    st.data_editor(
        df_final,
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config={
            "선택": st.column_config.CheckboxColumn(width="small"),
            "보증금": st.column_config.NumberColumn("보증금(만)", format="%d"),
            "월차임": st.column_config.NumberColumn("월세(만)", format="%d"),
            "면적": st.column_config.NumberColumn("면적(평)", format="%.1f")
        }
    )

    # [MODULE: ACTION_PANEL]
    st.divider()
    st.subheader("🎮 액션 패널")
    st.info("🚧 다음 단계: 선택한 매물을 '임대(종료)' 시트로 이동시키는 트랜잭션 모듈 조립 예정")
