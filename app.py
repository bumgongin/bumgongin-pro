# app.py
import streamlit as st
import core_engine as engine
import list_view
import styles

# [1] 초기화 및 스타일 적용
st.set_page_config(page_title="범공인 Pro (v24.60)", layout="wide", initial_sidebar_state="expanded")
styles.apply_custom_css()
engine.initialize_search_state()

# [2] 사이드바: 필터 및 제어 센터
with st.sidebar:
    st.header("📂 관리 도구")
    
    # 시트 선택 로직
    if 'current_sheet' not in st.session_state: st.session_state.current_sheet = engine.SHEET_NAMES[0]
    curr_idx = engine.SHEET_NAMES.index(st.session_state.current_sheet) if st.session_state.current_sheet in engine.SHEET_NAMES else 0
    selected_sheet = st.selectbox("작업 시트 선택", engine.SHEET_NAMES, index=curr_idx)
    
    if selected_sheet != st.session_state.current_sheet:
        st.session_state.current_sheet = selected_sheet
        if 'df_main' in st.session_state: del st.session_state.df_main
        st.rerun()

    # 데이터 로드
    if 'df_main' not in st.session_state:
        with st.spinner("데이터 로드 중..."):
            st.session_state.df_main = engine.load_sheet_data(st.session_state.current_sheet)

    # 통합 검색 필터
    st.divider()
    st.text_input("🔍 통합 키워드 검색", key='search_keyword')
    st.text_input("📍 번지 검색", key='exact_bunji')
    
    if st.button("🔄 검색 초기화", use_container_width=True):
        engine.safe_reset()

# [3] 메인 화면 실행
st.title("🏙️ 범공인 매물장 (Pro)")
list_view.show_main_list()
