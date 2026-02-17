# app.py
import streamlit as st
import core_engine as engine
import list_view
import styles

# [1] 초기화
st.set_page_config(page_title="범공인 Pro (v24.60)", layout="wide", initial_sidebar_state="expanded")
styles.apply_custom_css()
engine.initialize_search_state()

# [2] 사이드바 설정
with st.sidebar:
    st.header("📂 관리 도구")
    
    if 'current_sheet' not in st.session_state: 
        st.session_state.current_sheet = engine.SHEET_NAMES[0]
    
    curr_idx = engine.SHEET_NAMES.index(st.session_state.current_sheet)
    selected_sheet = st.selectbox("시트 선택", engine.SHEET_NAMES, index=curr_idx)
    
    if selected_sheet != st.session_state.current_sheet:
        st.session_state.current_sheet = selected_sheet
        if 'df_main' in st.session_state: del st.session_state.df_main
        st.rerun()

    if 'df_main' not in st.session_state:
        st.session_state.df_main = engine.load_sheet_data(st.session_state.current_sheet)

    st.divider()
    # 전역 검색 변수 (list_view와 공유)
    st.text_input("🔍 검색어", key='search_keyword', placeholder="건물명, 특징 등")
    st.text_input("📍 번지", key='exact_bunji', placeholder="예: 123-1")
    
    if st.button("🔄 초기화"):
        engine.safe_reset()

# [3] 메인 화면 실행
st.title("🏙️ 범공인 매물장 (Pro)")
list_view.show_main_list()
