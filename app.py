# app.py
# 범공인 Pro v24 Enterprise - Main Control Tower (v24.99 Final Secure)
# Feature: Master Login, 3-Way Branching, Infinite Filter, Strong Sync

import streamlit as st
import pandas as pd
import core_engine as engine
import list_renderer     # 목록 렌더링 전담
import detail_renderer   # 상세 보기 전담
import new_item_renderer # 신규 등록 전담
import styles            # 스타일 모듈

# ==============================================================================
# [INIT] 시스템 초기화 및 보안 설정
# ==============================================================================
st.set_page_config(page_title="범공인 Pro (v24.99)", layout="wide", initial_sidebar_state="expanded")
styles.apply_custom_css()

# 1. 로그인 상태 관리 초기화
if 'auth_status' not in st.session_state: 
    st.session_state.auth_status = False

def check_password():
    """마스터 비밀번호 검증 함수"""
    if st.session_state.password_input == "bum24!":
        st.session_state.auth_status = True
    else:
        st.error("🔒 비밀번호가 올바르지 않습니다.")

# ==============================================================================
# [SECURITY GATE] 로그인 화면
# ==============================================================================
if not st.session_state.auth_status:
    # 로그인 전에는 사이드바와 메인 컨텐츠를 숨김
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center;'>🔐 범공인 Pro - 보안 접속</h2>", unsafe_allow_html=True)
            st.text_input("마스터 비밀번호를 입력하세요", type="password", key="password_input", on_change=check_password)
            
            if st.button("접속하기", use_container_width=True, type="primary"):
                check_password()
                if st.session_state.auth_status:
                    st.rerun()
    
    # 로그인 되지 않았으면 여기서 코드 중단
    st.stop()

# ==============================================================================
# [SYSTEM START] 로그인 성공 후 로직 진입
# ==============================================================================

# 1. 필수 상태 변수 초기화
if 'current_sheet' not in st.session_state: st.session_state.current_sheet = engine.SHEET_NAMES[0]
if 'selected_item' not in st.session_state: st.session_state.selected_item = None
if 'view_mode' not in st.session_state: st.session_state.view_mode = '🗂️ 카드 모드'
if 'page_num' not in st.session_state: st.session_state.page_num = 1
if 'editor_key_version' not in st.session_state: st.session_state.editor_key_version = 0

# 신규 등록 모드 상태 변수
if 'is_adding_new' not in st.session_state: st.session_state.is_adding_new = False

# 2. 스마트 필터 UI 토글 상태 초기화
if 'show_cat_search' not in st.session_state: st.session_state.show_cat_search = False
if 'show_gu_search' not in st.session_state: st.session_state.show_gu_search = False
if 'show_dong_search' not in st.session_state: st.session_state.show_dong_search = False

# 3. 수익률 필터 전용 키 초기화 (매매 모드용)
if 'min_yield' not in st.session_state: st.session_state.min_yield = 0.0
if 'max_yield' not in st.session_state: st.session_state.max_yield = 100.0

# 4. 검색 엔진 상태 초기화
engine.initialize_search_state()

# 세션 값 단축 접근 함수
def sess(key): return st.session_state.get(key)

# [Helper] 필터 변경 시 페이지 리셋 콜백
def reset_page():
    st.session_state.page_num = 1

# ==============================================================================
# [SIDEBAR] 필터링 컨트롤 타워
# ==============================================================================
with st.sidebar:
    st.header("📂 관리 도구")
    
    # [A] 작업 시트 및 등록 버튼
    with st.container(border=True):
        # [신규 등록 버튼]
        if st.button("➕ 신규 매물 등록", use_container_width=True, type="primary"):
            st.session_state.selected_item = None
            st.session_state.is_adding_new = True
            st.rerun()
            
        st.divider()
        
        st.markdown("##### 📄 작업 시트")
        try: curr_idx = engine.SHEET_NAMES.index(st.session_state.current_sheet)
        except: curr_idx = 0
        
        selected_sheet = st.selectbox(
            "시트 선택", 
            engine.SHEET_NAMES, 
            index=curr_idx, 
            label_visibility="collapsed"
        )
        
        # 시트 변경 감지 및 강제 리셋 (데이터 강제 동기화)
        if selected_sheet != st.session_state.current_sheet:
            st.session_state.current_sheet = selected_sheet
            st.session_state.page_num = 1
            st.session_state.selected_item = None
            
            # [중요] 시트 변경 시 등록 모드 해제
            st.session_state.is_adding_new = False
            
            # 데이터 강제 갱신을 위해 세션 삭제 및 캐시 클리어
            if 'df_main' in st.session_state: del st.session_state.df_main
            st.cache_data.clear()
            
            # 필터 상태 리셋 (보기 모드는 유지)
            current_view = st.session_state.view_mode
            engine.safe_reset() 
            st.session_state.view_mode = current_view
            st.rerun()

    # 데이터 로드 (캐싱 활용)
    if 'df_main' not in st.session_state:
        with st.spinner("데이터 로드 중..."):
            st.session_state.df_main = engine.load_sheet_data(st.session_state.current_sheet)
    df_main = st.session_state.df_main

    # [B] 키워드 검색 (페이지 리셋 적용)
    st.write("")
    st.text_input("통합 검색 (건물명, 특징 등)", key='search_keyword', on_change=reset_page)
    st.text_input("번지 검색 (정확히 일치)", key='exact_bunji', on_change=reset_page)
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
        st.multiselect("구분 선택", unique_cat, key='selected_cat', placeholder="전체", label_visibility="collapsed", on_change=reset_page)
        
        # 2. 지역 (구)
        c3, c4 = st.columns([4, 1])
        c3.markdown("지역 (구)")
        if c4.button("🔍", key="btn_gu"): st.session_state.show_gu_search = not st.session_state.show_gu_search
        
        unique_gu = sorted(df_main['지역_구'].astype(str).unique().tolist()) if '지역_구' in df_main.columns else []
        if st.session_state.show_gu_search:
            term = st.text_input("구 검색", key="gu_term")
            if term: unique_gu = [x for x in unique_gu if term in x]
        st.multiselect("구 선택", unique_gu, key='selected_gu', placeholder="전체", label_visibility="collapsed", on_change=reset_page)
        
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
        st.multiselect("동 선택", unique_dong, key='selected_dong', placeholder="전체", label_visibility="collapsed", on_change=reset_page)

    st.write("")
    
    # [D] 상세 금액/면적 필터 (임대/매매 분기)
    # value=None으로 설정하여 공란(Clean UI) 구현, max_value는 조 단위 설정
    MAX_VAL = 999999999999.0 
    
    is_sale_mode = "매매" in st.session_state.current_sheet
    with st.expander("💰 상세 설정 (금액/면적)", expanded=False):
        
        if is_sale_mode:
            # 매매 모드
            c1, c2 = st.columns(2)
            c1.number_input("최소 매가", key='min_price', value=None, step=1000.0, max_value=MAX_VAL, on_change=reset_page)
            c2.number_input("최대 매가", key='max_price', value=None, step=1000.0, max_value=MAX_VAL, on_change=reset_page)
            
            c3, c4 = st.columns(2)
            c3.number_input("최소 대지", key='min_land', value=None, step=1.0, max_value=MAX_VAL, on_change=reset_page)
            c4.number_input("최대 대지", key='max_land', value=None, step=1.0, max_value=MAX_VAL, on_change=reset_page)
            
            # [수익률 전용 필터]
            c5, c6 = st.columns(2)
            c5.number_input("최소 수익률(%)", key='min_yield', value=None, step=0.1, on_change=reset_page)
            c6.number_input("최대 수익률(%)", key='max_yield', value=None, step=0.1, on_change=reset_page)
            
        else:
            # 임대 모드
            c1, c2 = st.columns(2)
            c1.number_input("최소 보증", key='min_dep', value=None, step=100.0, max_value=MAX_VAL, on_change=reset_page)
            c2.number_input("최대 보증", key='max_dep', value=None, step=100.0, max_value=MAX_VAL, on_change=reset_page)
            
            c3, c4 = st.columns(2)
            c3.number_input("최소 월세", key='min_rent', value=None, step=10.0, max_value=MAX_VAL, on_change=reset_page)
            c4.number_input("최대 월세", key='max_rent', value=None, step=10.0, max_value=MAX_VAL, on_change=reset_page)
            
            c7, c8 = st.columns(2)
            c7.number_input("최소 권리", key='min_kwon', value=None, step=100.0, max_value=MAX_VAL, on_change=reset_page)
            c8.number_input("최대 권리", key='max_kwon', value=None, step=100.0, max_value=MAX_VAL, on_change=reset_page)
            
            st.checkbox("🚫 무권리만 보기", key='is_no_kwon', on_change=reset_page)

        st.divider()
        # 공통 필터 (면적/층 - 정밀 소수점 허용)
        c1, c2 = st.columns(2)
        c1.number_input("최소 실면적", key='min_area', value=None, step=1.0, max_value=MAX_VAL, on_change=reset_page)
        c2.number_input("최대 실면적", key='max_area', value=None, step=1.0, max_value=MAX_VAL, on_change=reset_page)
        
        c3, c4 = st.columns(2)
        c3.number_input("최저 층", key='min_fl', value=None, step=1.0, min_value=-50.0, max_value=200.0, on_change=reset_page)
        c4.number_input("최고 층", key='max_fl', value=None, step=1.0, min_value=-50.0, max_value=200.0, on_change=reset_page)
    
    st.divider()
    # [보기 모드 보존 로직]
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
# [MAIN CONTENT] - 뇌 (Brain / 3-Way Branching)
# ==============================================================================
st.title("🏙️ 범공인 매물장 (Pro)")

if st.session_state.selected_item is not None:
    # 1. 상세 보기 모드 (Detail Renderer에 위임)
    detail_renderer.render_detail_view(st.session_state.selected_item)
elif st.session_state.is_adding_new:
    # 2. 신규 등록 모드 (New Item Renderer에 위임)
    new_item_renderer.render_new_item_form()
else:
    # 3. 목록 보기 모드 (List Renderer에 위임)
    # 필터링 상태는 session_state를 통해 공유됨
    list_renderer.show_main_list()
