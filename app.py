# app.py
import streamlit as st
import core_engine as engine
import list_view
import styles

# [1] 시스템 초기화 및 상태 변수 100% 준비
st.set_page_config(page_title="범공인 Pro (v24.80)", layout="wide", initial_sidebar_state="expanded")
styles.apply_custom_css()

# 에러 방지를 위한 모든 세션 상태 초기화
if 'current_sheet' not in st.session_state: st.session_state.current_sheet = engine.SHEET_NAMES[0]
if 'selected_item' not in st.session_state: st.session_state.selected_item = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = '🗂️ 카드 모드'
if 'page_num' not in st.session_state: st.session_state.page_num = 1
if 'editor_key_version' not in st.session_state: st.session_state.editor_key_version = 0
if 'infra_res_c' not in st.session_state: st.session_state.infra_res_c = None
if 'last_analyzed_id' not in st.session_state: st.session_state.last_analyzed_id = None
if 'zoom_level' not in st.session_state: st.session_state.zoom_level = 16

# 스마트 필터 검색어 상태
for key in ['cat_term', 'gu_term', 'dong_term']:
    if key not in st.session_state: st.session_state[key] = ""

engine.initialize_search_state()

# [2] 사이드바: 강력한 필터 컨트롤 타워
with st.sidebar:
    st.header("📂 관리 도구")
    
    # 시트 선택
    curr_idx = engine.SHEET_NAMES.index(st.session_state.current_sheet)
    selected_sheet = st.selectbox("작업 시트", engine.SHEET_NAMES, index=curr_idx)
    if selected_sheet != st.session_state.current_sheet:
        st.session_state.current_sheet = selected_sheet
        if 'df_main' in st.session_state: del st.session_state.df_main
        st.session_state.selected_item = None
        st.rerun()

    if 'df_main' not in st.session_state:
        st.session_state.df_main = engine.load_sheet_data(st.session_state.current_sheet)
    
    df = st.session_state.df_main

    # 통합 키워드 및 번지 검색
    st.divider()
    st.text_input("🔍 통합 키워드 검색", key='search_keyword')
    st.text_input("📍 번지 딱 일치 검색", key='exact_bunji', placeholder="예: 50-1")
    
    # [복구] 항목/지역 필터 (검색칸 포함)
    with st.expander("🏷️ 항목/지역 상세 필터", expanded=True):
        # 구분 필터
        st.caption("구분")
        term_cat = st.text_input("구분 검색창", key="cat_term", label_visibility="collapsed")
        cats = sorted(df['구분'].unique())
        if term_cat: cats = [c for c in cats if term_cat in str(c)]
        st.multiselect("구분 선택", cats, key='selected_cat', label_visibility="collapsed")
        
        # 지역(구) 필터
        st.caption("지역(구)")
        term_gu = st.text_input("구 검색창", key="gu_term", label_visibility="collapsed")
        gus = sorted(df['지역_구'].unique())
        if term_gu: gus = [g for g in gus if term_gu in str(g)]
        st.multiselect("구 선택", gus, key='selected_gu', label_visibility="collapsed")

    # [복구] 금액/면적/층 필터
    with st.expander("💰 금액/면적/층 필터"):
        is_sale = "매매" in st.session_state.current_sheet
        if is_sale:
            st.number_input("최소 매가", key='min_price')
            st.number_input("최대 매가", key='max_price', value=1000000.0)
        else:
            st.number_input("최소 보증", key='min_dep')
            st.number_input("최대 보증", key='max_dep', value=1000000.0)
            st.number_input("최소 월세", key='min_rent')
            st.number_input("최대 월세", key='max_rent', value=10000.0)
            st.checkbox("🚫 무권리만 보기", key='is_no_kwon')
        
        st.divider()
        st.number_input("최소 면적", key='min_area')
        st.number_input("최대 면적", key='max_area', value=10000.0)
        st.number_input("최저 층", key='min_fl', value=-5.0)
        st.number_input("최고 층", key='max_fl', value=100.0)

    if st.button("🔄 필터 전체 초기화", use_container_width=True): engine.safe_reset()
    st.divider()
    st.radio("보기 모드", ['🗂️ 카드 모드', '📋 리스트 모드'], key='view_mode_radio')
    if st.session_state.view_mode_radio != st.session_state.view_mode:
        st.session_state.view_mode = st.session_state.view_mode_radio
        st.rerun()

# [3] 메인 화면 본체 실행
st.title("🏙️ 범공인 매물장 (Pro)")
list_view.show_main_list()
