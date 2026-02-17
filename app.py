# app.py - 범공인 Pro 메인 관리 타워
import streamlit as st
import core_engine as engine
import list_view
import styles

# [1] 시스템 초기화
st.set_page_config(page_title="범공인 Pro (v24.70)", layout="wide", initial_sidebar_state="expanded")
styles.apply_custom_css()
engine.initialize_search_state()

# [2] 사이드바: 필터 컨트롤 타워
with st.sidebar:
    st.header("📂 관리 도구")
    
    # 시트 선택 로직
    if 'current_sheet' not in st.session_state: st.session_state.current_sheet = engine.SHEET_NAMES[0]
    curr_idx = engine.SHEET_NAMES.index(st.session_state.current_sheet)
    selected_sheet = st.selectbox("작업 시트 선택", engine.SHEET_NAMES, index=curr_idx)
    
    if selected_sheet != st.session_state.current_sheet:
        st.session_state.current_sheet = selected_sheet
        if 'df_main' in st.session_state: del st.session_state.df_main
        st.rerun()

    # 데이터 로드
    if 'df_main' not in st.session_state:
        with st.spinner("데이터 로딩 중..."):
            st.session_state.df_main = engine.load_sheet_data(st.session_state.current_sheet)
    
    df = st.session_state.df_main

    # 상세 검색 필터
    st.divider()
    st.text_input("🔍 통합 검색", key='search_keyword', placeholder="건물명, 특징 등")
    st.text_input("📍 번지 검색", key='exact_bunji', placeholder="예: 123-1")
    
    with st.expander("🏷️ 항목/지역 필터", expanded=True):
        st.multiselect("구분", sorted(df['구분'].unique()), key='selected_cat')
        st.multiselect("지역 (구)", sorted(df['지역_구'].unique()), key='selected_gu')
        st.multiselect("지역 (동)", sorted(df['지역_동'].unique()), key='selected_dong')

    with st.expander("💰 금액/면적 필터"):
        is_sale = "매매" in st.session_state.current_sheet
        if is_sale:
            st.number_input("최소 매가", key='min_price')
            st.number_input("최대 매가", key='max_price', value=1000000.0)
        else:
            st.number_input("최소 보증", key='min_dep')
            st.number_input("최대 보증", key='max_dep', value=1000000.0)
            st.number_input("최소 월세", key='min_rent')
            st.number_input("최대 월세", key='max_rent', value=10000.0)
        st.number_input("최소 면적", key='min_area')
        st.number_input("최대 면적", key='max_area', value=10000.0)

    if st.button("🔄 필터 초기화", use_container_width=True): engine.safe_reset()
    st.divider()
    st.radio("보기 모드", ['🗂️ 카드 모드', '📋 리스트 모드'], key='view_mode')

# [3] 메인 화면 실행 (list_view 모듈에 위임)
st.title("🏙️ 범공인 매물장 (Pro)")
list_view.show_main_list()
