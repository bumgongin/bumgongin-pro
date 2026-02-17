# app.py
import streamlit as st
import core_engine as engine
import list_view
import styles

# [1] 시스템 초기화 및 모든 상태 변수 준비 (에러 방지)
st.set_page_config(page_title="범공인 Pro (v24.75)", layout="wide", initial_sidebar_state="expanded")
styles.apply_custom_css()

# 중요: 사라졌던 상태 변수들을 여기서 모두 초기화합니다.
if 'current_sheet' not in st.session_state: st.session_state.current_sheet = engine.SHEET_NAMES[0]
if 'selected_item' not in st.session_state: st.session_state.selected_item = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = '🗂️ 카드 모드'
if 'page_num' not in st.session_state: st.session_state.page_num = 1
if 'editor_key_version' not in st.session_state: st.session_state.editor_key_version = 0
if 'action_status' not in st.session_state: st.session_state.action_status = None
if 'zoom_level' not in st.session_state: st.session_state.zoom_level = 16
if 'infra_res_c' not in st.session_state: st.session_state.infra_res_c = None
if 'last_analyzed_id' not in st.session_state: st.session_state.last_analyzed_id = None

# 필터용 초기값 설정
engine.initialize_search_state()

# [2] 사이드바: 강력한 필터 컨트롤 타워 복구
with st.sidebar:
    st.header("📂 관리 도구")
    
    # 시트 선택
    curr_idx = engine.SHEET_NAMES.index(st.session_state.current_sheet)
    selected_sheet = st.selectbox("작업 시트 선택", engine.SHEET_NAMES, index=curr_idx)
    if selected_sheet != st.session_state.current_sheet:
        st.session_state.current_sheet = selected_sheet
        if 'df_main' in st.session_state: del st.session_state.df_main
        st.session_state.selected_item = None
        st.rerun()

    # 데이터 로드
    if 'df_main' not in st.session_state:
        st.session_state.df_main = engine.load_sheet_data(st.session_state.current_sheet)
    
    df = st.session_state.df_main

    # 통합 및 번지 검색
    st.divider()
    st.text_input("🔍 통합 키워드 검색", key='search_keyword')
    st.text_input("📍 번지 검색", key='exact_bunji')
    
    # 사라졌던 상세 필터들 100% 복구
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
    st.radio("보기 모드", ['🗂️ 카드 모드', '📋 리스트 모드'], key='view_mode_radio')
    # 라디오 버튼 값을 세션 상태와 동기화
    if st.session_state.view_mode_radio != st.session_state.view_mode:
        st.session_state.view_mode = st.session_state.view_mode_radio
        st.rerun()

# [3] 메인 본체 실행
st.title("🏙️ 범공인 매물장 (Pro)")
list_view.show_main_list()
