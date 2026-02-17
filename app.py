# app.py
# 범공인 Pro v24 Enterprise - Main Control Tower (v24.96 Precision Refined)
# Feature: View Mode Protection, Yield Filter, Infinite Range, Strong Sync

import streamlit as st
import pandas as pd
import core_engine as engine
import list_renderer     # 목록 렌더링 전담
import detail_renderer   # 상세 보기 전담
import styles            # 스타일 모듈

# ==============================================================================
# [INIT] 시스템 초기화 및 상태 관리
# ==============================================================================
st.set_page_config(page_title="범공인 Pro (v24.96)", layout="wide", initial_sidebar_state="expanded")
styles.apply_custom_css()

# 1. 필수 상태 변수 초기화 (앱 구동 시 1회 실행)
if 'current_sheet' not in st.session_state: st.session_state.current_sheet = engine.SHEET_NAMES[0]
if 'selected_item' not in st.session_state: st.session_state.selected_item = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = '🗂️ 카드 모드'
if 'page_num' not in st.session_state: st.session_state.page_num = 1
if 'editor_key_version' not in st.session_state: st.session_state.editor_key_version = 0

# 2. 스마트 필터 UI 토글 상태 초기화
if 'show_cat_search' not in st.session_state: st.session_state.show_cat_search = False
if 'show_gu_search' not in st.session_state: st.session_state.show_gu_search = False
if 'show_dong_search' not in st.session_state: st.session_state.show_dong_search = False

# 3. 수익률 필터 전용 키 초기화 (매매 모드용)
if 'min_yield' not in st.session_state: st.session_state.min_yield = 0.0
if 'max_yield' not in st.session_state: st.session_state.max_yield = 100.0

# 4. 검색 엔진 상태 초기화 (나머지 필터 값 등)
engine.initialize_search_state()

# 세션 값 단축 접근 함수
def sess(key): return st.session_state.get(key)

# ==============================================================================
# [SIDEBAR] 필터링 컨트롤 타워
# ==============================================================================
with st.sidebar:
    st.header("📂 관리 도구")
    
    # [A] 시트 선택 및 데이터 로드
    with st.container(border=True):
        st.markdown("##### 📄 작업 시트")
        try: curr_idx = engine.SHEET_NAMES.index(st.session_state.current_sheet)
        except: curr_idx = 0
        
        selected_sheet = st.selectbox(
            "시트 선택", 
            engine.SHEET_NAMES, 
            index=curr_idx, 
            label_visibility="collapsed"
        )
        
        # 시트 변경 감지 및 강제 리셋
        if selected_sheet != st.session_state.current_sheet:
            st.session_state.current_sheet = selected_sheet
            st.session_state.page_num = 1
            st.session_state.selected_item = None
            
            # [중요] 데이터 강제 갱신을 위해 캐시 삭제
            if 'df_main' in st.session_state: del st.session_state.df_main
            
            # 필터 상태 리셋 (체크박스 등) - 보기 모드는 유지
            current_view = st.session_state.view_mode
            engine.safe_reset() 
            st.session_state.view_mode = current_view
            st.rerun()

    # 데이터 로드 (캐싱 활용)
    if 'df_main' not in st.session_state:
        with st.spinner("데이터 로드 중..."):
            st.session_state.df_main = engine.load_sheet_data(st.session_state.current_sheet)
    df_main = st.session_state.df_main

    # [B] 키워드 검색
    st.write("")
    st.text_input("통합 검색 (건물명, 특징 등)", key='search_keyword')
    st.text_input("번지 검색 (정확히 일치)", key='exact_bunji')
    st.write("")
    
    # [C] 스마트 항목 필터링 (검색 + 멀티셀렉트)
    with st.container(border=True):
        st.markdown("##### 🏷️ 항목 필터링")
        
        # 1. 구분 (Category)
        c1, c2 = st.columns([4, 1])
        c1.markdown("구분")
        if c2.button("🔍", key="btn_cat"): st.session_state.show_cat_search = not st.session_state.show_cat_search
        
        unique_cat = sorted(df_main['구분'].astype(str).unique().tolist()) if '구분' in df_main.columns else []
        if st.session_state.show_cat_search:
            term = st.text_input("구분 검색", key="cat_term")
            if term: unique_cat = [x for x in unique_cat if term in x]
        st.multiselect("구분 선택", unique_cat, key='selected_cat', placeholder="전체", label_visibility="collapsed")
        
        # 2. 지역 (구)
        c3, c4 = st.columns([4, 1])
        c3.markdown("지역 (구)")
        if c4.button("🔍", key="btn_gu"): st.session_state.show_gu_search = not st.session_state.show_gu_search
        
        unique_gu = sorted(df_main['지역_구'].astype(str).unique().tolist()) if '지역_구' in df_main.columns else []
        if st.session_state.show_gu_search:
            term = st.text_input("구 검색", key="gu_term")
            if term: unique_gu = [x for x in unique_gu if term in x]
        st.multiselect("구 선택", unique_gu, key='selected_gu', placeholder="전체", label_visibility="collapsed")
        
        # 3. 지역 (동) - 구 선택에 따른 종속 필터링
        c5, c6 = st.columns([4, 1])
        c5.markdown("지역 (동)")
        if c6.button("🔍", key="btn_dong"): st.session_state.show_dong_search = not st.session_state.show_dong_search
        
        unique_dong = []
        if '지역_동' in df_main.columns:
            if st.session_state.selected_gu:
                unique_dong = sorted(df_main[df_main['지역_구'].isin(st.session_state.selected_gu)]['지역_동'].astype(str).unique().tolist())
            else:
                unique_dong = sorted(df_main['지역_동'].astype(str).unique().tolist())
        
        if st.session_state.show_dong_search:
            term = st.text_input("동 검색", key="dong_term")
            if term: unique_dong = [x for x in unique_dong if term in x]
        st.multiselect("동 선택", unique_dong, key='selected_dong', placeholder="전체", label_visibility="collapsed")

    st.write("")
    
    # [D] 상세 금액/면적 필터 (임대/매매 분기)
    is_sale_mode = "매매" in st.session_state.current_sheet
    with st.expander("💰 상세 설정 (금액/면적)", expanded=False):
        # [문제 10번 해결] 필터 범위 무한 확장 (1000억 이상)
        MAX_VAL = 100000000.0 
        
        if is_sale_mode:
            # 매매 모드
            c1, c2 = st.columns(2)
            c1.number_input("최소 매가", key='min_price', value=sess('min_price'))
            c2.number_input("최대 매가", key='max_price', value=sess('max_price'), max_value=MAX_VAL)
            
            c3, c4 = st.columns(2)
            c3.number_input("최소 대지", key='min_land', value=sess('min_land'))
            c4.number_input("최대 대지", key='max_land', value=sess('max_land'), max_value=MAX_VAL)
            
            # [수익률 전용 필터]
            c5, c6 = st.columns(2)
            c5.number_input("최소 수익률", key='min_yield', value=0.0, step=0.1)
            c6.number_input("최대 수익률", key='max_yield', value=100.0, step=0.1)
            
        else:
            # 임대 모드
            c1, c2 = st.columns(2)
            c1.number_input("최소 보증", key='min_dep', value=sess('min_dep'))
            c2.number_input("최대 보증", key='max_dep', value=sess('max_dep'), max_value=MAX_VAL)
            
            c3, c4 = st.columns(2)
            c3.number_input("최소 월세", key='min_rent', value=sess('min_rent'))
            c4.number_input("최대 월세", key='max_rent', value=sess('max_rent'), max_value=MAX_VAL)
            
            c7, c8 = st.columns(2)
            c7.number_input("최소 권리", key='min_kwon', value=sess('min_kwon'))
            c8.number_input("최대 권리", key='max_kwon', value=sess('max_kwon'), max_value=MAX_VAL)
            
            st.checkbox("🚫 무권리만 보기", key='is_no_kwon')

        st.divider()
        # 공통 필터 (면적/층 - 정밀 소수점 허용)
        c1, c2 = st.columns(2)
        c1.number_input("최소 실면적", key='min_area', value=sess('min_area'), step=1.0)
        c2.number_input("최대 실면적", key='max_area', value=sess('max_area'), max_value=MAX_VAL, step=1.0)
        
        c3, c4 = st.columns(2)
        c3.number_input("최저 층", key='min_fl', value=-10.0, step=1.0)
        c4.number_input("최고 층", key='max_fl', value=100.0, step=1.0)
    
    st.divider()
    # [문제 9번 해결] 필터 초기화 시 보기 모드 유지
    if st.button("🔄 필터 초기화", use_container_width=True): 
        # 1. 보기 모드 백업
        backup_view = st.session_state.view_mode
        # 2. 엔진 리셋 (필터값 초기화)
        engine.safe_reset()
        # 3. 보기 모드 복원 및 페이지 초기화
        st.session_state.view_mode = backup_view
        st.session_state.page_num = 1
        st.rerun()
        
    st.markdown("---")
    view_option = st.radio("보기", ['🗂️ 카드 모드', '📋 리스트 모드'], 
                           index=0 if st.session_state.view_mode == '🗂️ 카드 모드' else 1)
    if view_option != st.session_state.view_mode:
        st.session_state.view_mode = view_option
        st.rerun()

# ==============================================================================
# [MAIN CONTENT] - 뇌 (Brain)
# ==============================================================================
st.title("🏙️ 범공인 매물장 (Pro)")

# [E] 화면 분기 로직 (이중 레이어)
if st.session_state.selected_item is not None:
    # 상세 보기 모드 (detail_renderer 호출)
    detail_renderer.render_detail_view(st.session_state.selected_item)
else:
    # 목록 보기 모드 (list_renderer 호출)
    # 필터링 상태는 session_state를 통해 공유됨
    list_renderer.show_main_list()
