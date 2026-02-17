# app.py
import streamlit as st
import core_engine as engine
import list_view
import styles

# [INIT] 시스템 초기화
st.set_page_config(page_title="범공인 Pro (v24.90)", layout="wide", initial_sidebar_state="expanded")
styles.apply_custom_css()

# 모든 세션 상태 초기화 (이사 중 분실 방지)
if 'current_sheet' not in st.session_state: st.session_state.current_sheet = engine.SHEET_NAMES[0]
if 'selected_item' not in st.session_state: st.session_state.selected_item = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = '🗂️ 카드 모드'
if 'editor_key_version' not in st.session_state: st.session_state.editor_key_version = 0

engine.initialize_search_state()

with st.sidebar:
    st.header("📂 관리 도구")
    
    # [1] 시트 선택 로직
    curr_idx = engine.SHEET_NAMES.index(st.session_state.current_sheet)
    selected_sheet = st.selectbox("작업 시트 선택", engine.SHEET_NAMES, index=curr_idx)
    if selected_sheet != st.session_state.current_sheet:
        st.session_state.current_sheet = selected_sheet
        if 'df_main' in st.session_state: del st.session_state.df_main
        st.session_state.selected_item = None
        st.rerun()

    if 'df_main' not in st.session_state:
        st.session_state.df_main = engine.load_sheet_data(st.session_state.current_sheet)
    df = st.session_state.df_main

    # [2] 통합 검색 및 상세 필터
    st.divider()
    st.text_input("🔍 통합 키워드 검색", key='search_keyword')
    st.text_input("📍 번지 검색 (정확히)", key='exact_bunji')
    
    with st.expander("🏷️ 항목/지역 필터", expanded=True):
        st.multiselect("구분", sorted(df['구분'].unique()), key='selected_cat')
        st.multiselect("지역(구)", sorted(df['지역_구'].unique()), key='selected_gu')
        st.multiselect("지역(동)", sorted(df['지역_동'].unique()), key='selected_dong')

    with st.expander("💰 금액/면적/층 필터", expanded=False):
        is_sale = "매매" in st.session_state.current_sheet
        if is_sale:
            st.number_input("최소 매가", key='min_price')
            st.number_input("최대 매가", key='max_price', value=10000000.0)
        else:
            st.number_input("최소 보증", key='min_dep')
            st.number_input("최대 보증", key='max_dep', value=10000000.0)
            st.number_input("최소 월세", key='min_rent')
            st.number_input("최대 월세", key='max_rent', value=100000.0)
            # 권리금 최소/최대 필터 복구
            st.number_input("최소 권리", key='min_kwon')
            st.number_input("최대 권리", key='max_kwon', value=1000000.0)
            st.checkbox("🚫 무권리만 보기", key='is_no_kwon')
        
        st.divider()
        st.number_input("최소 면적", key='min_area')
        st.number_input("최대 면적", key='max_area', value=100000.0)
        st.number_input("최저 층", key='min_fl', value=-10.0)
        st.number_input("최고 층", key='max_fl', value=100.0)

    if st.button("🔄 필터 초기화", use_container_width=True): engine.safe_reset()
    st.divider()
    st.radio("보기 설정", ['🗂️ 카드 모드', '📋 리스트 모드'], key='view_mode_radio')
    if st.session_state.view_mode_radio != st.session_state.view_mode:
        st.session_state.view_mode = st.session_state.view_mode_radio
        st.rerun()

st.title("🏙️ 범공인 매물장 (Pro)")
list_view.show_main_list()
