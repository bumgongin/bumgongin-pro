# app.py
# 범공인 Pro v24 Enterprise - Main Application Entry (v24.35.1 Layout Refine)
# Feature: 4-Tab Layout, Map Scaling, Error Shielding

import streamlit as st
import pandas as pd
import time
import math
import re
import core_engine as engine  # [Core Engine v24.29.2]
import map_service as map_api # [Map Service v24.23.7]
import styles                 # [Style Module v24.23.7]
import infra_engine           # [Infra Engine v24.30.1]

# ==============================================================================
# [INIT] 시스템 초기화
# ==============================================================================
st.set_page_config(page_title="범공인 Pro (v24.35.1)", layout="wide", initial_sidebar_state="expanded")
styles.apply_custom_css()

# 상태 변수 초기화
if 'current_sheet' not in st.session_state: st.session_state.current_sheet = engine.SHEET_NAMES[0]
if 'action_status' not in st.session_state: st.session_state.action_status = None 
if 'view_mode' not in st.session_state: st.session_state.view_mode = '🗂️ 카드 모드'
if 'page_num' not in st.session_state: st.session_state.page_num = 1
if 'selected_item' not in st.session_state: st.session_state.selected_item = None 
if 'zoom_level' not in st.session_state: st.session_state.zoom_level = 16 

# 인프라 분석 결과 보존을 위한 상태 변수 초기화
if 'infra_res_c' not in st.session_state: st.session_state.infra_res_c = None 
if 'last_analyzed_id' not in st.session_state: st.session_state.last_analyzed_id = None

# 스마트 필터 토글
if 'show_cat_search' not in st.session_state: st.session_state.show_cat_search = False
if 'show_gu_search' not in st.session_state: st.session_state.show_gu_search = False
if 'show_dong_search' not in st.session_state: st.session_state.show_dong_search = False

engine.initialize_search_state()
def sess(key): return st.session_state[key]

# ==============================================================================
# [HELPER] 인프라 분석 캐싱 래퍼
# ==============================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def cached_commercial(lat, lng):
    # v24.30.1: 통합 상권 분석 (필터 해제 + 보행자 경로)
    return infra_engine.get_commercial_analysis(lat, lng)

# ==============================================================================
# [SIDEBAR] 필터링 컨트롤 타워
# ==============================================================================
with st.sidebar:
    st.header("📂 관리 도구")
    
    with st.container(border=True):
        st.markdown("##### 📄 작업 시트")
        try: curr_idx = engine.SHEET_NAMES.index(st.session_state.current_sheet)
        except: curr_idx = 0
        selected_sheet = st.selectbox("시트 선택", engine.SHEET_NAMES, index=curr_idx, label_visibility="collapsed")
        
        if selected_sheet != st.session_state.current_sheet:
            st.session_state.current_sheet = selected_sheet
            st.session_state.action_status = None 
            st.session_state.editor_key_version += 1
            st.session_state.page_num = 1
            st.session_state.selected_item = None
            st.session_state.zoom_level = 16
            
            # 시트 변경 시 분석 결과 초기화
            st.session_state.infra_res_c = None
            st.session_state.last_analyzed_id = None

            if 'df_main' in st.session_state: del st.session_state.df_main
            
            keys_to_clear = [k for k in st.session_state.keys() if k.startswith("chk_")]
            for k in keys_to_clear: del st.session_state[k]
            
            st.cache_data.clear()
            st.rerun()

    if 'df_main' not in st.session_state:
        with st.spinner("데이터 로드 중..."):
            loaded_df = engine.load_sheet_data(st.session_state.current_sheet)
            if loaded_df is not None: st.session_state.df_main = loaded_df
            else: st.error("🚨 데이터 로드 실패."); st.stop()
    df_main = st.session_state.df_main

    st.write(""); st.text_input("통합 검색", key='search_keyword'); st.text_input("번지 검색", key='exact_bunji'); st.write("")
    
    with st.container(border=True):
        st.markdown("##### 🏷️ 항목 필터링")
        c1, c2 = st.columns([4, 1]); c1.markdown("구분"); 
        if c2.button("🔍", key="btn_cat"): st.session_state.show_cat_search = not st.session_state.show_cat_search
        unique_cat = sorted(df_main['구분'].astype(str).unique().tolist()) if '구분' in df_main.columns else []
        if st.session_state.show_cat_search: 
            term = st.text_input("구분 검색", key="cat_term")
            if term: unique_cat = [x for x in unique_cat if term in x]
        st.multiselect("구분", unique_cat, key='selected_cat', placeholder="전체", label_visibility="collapsed")
        
        c3, c4 = st.columns([4, 1]); c3.markdown("지역 (구)"); 
        if c4.button("🔍", key="btn_gu"): st.session_state.show_gu_search = not st.session_state.show_gu_search
        unique_gu = sorted(df_main['지역_구'].astype(str).unique().tolist()) if '지역_구' in df_main.columns else []
        if st.session_state.show_gu_search: 
            term = st.text_input("구 검색", key="gu_term")
            if term: unique_gu = [x for x in unique_gu if term in x]
        st.multiselect("지역 (구)", unique_gu, key='selected_gu', placeholder="전체", label_visibility="collapsed")
        
        c5, c6 = st.columns([4, 1]); c5.markdown("지역 (동)"); 
        if c6.button("🔍", key="btn_dong"): st.session_state.show_dong_search = not st.session_state.show_dong_search
        unique_dong = []
        if '지역_동' in df_main.columns:
            if st.session_state.selected_gu: unique_dong = sorted(df_main[df_main['지역_구'].isin(st.session_state.selected_gu)]['지역_동'].astype(str).unique().tolist())
            else: unique_dong = sorted(df_main['지역_동'].astype(str).unique().tolist())
        if st.session_state.show_dong_search:
            term = st.text_input("동 검색", key="dong_term")
            if term: unique_dong = [x for x in unique_dong if term in x]
        st.multiselect("지역 (동)", unique_dong, key='selected_dong', placeholder="전체", label_visibility="collapsed")

    st.write("")
    is_sale_mode = "매매" in st.session_state.current_sheet
    with st.expander("💰 상세 설정", expanded=False):
        MAX_P = 10000000.0; MAX_A = 1000000.0
        if is_sale_mode:
            c1, c2 = st.columns(2); c1.number_input("최소 매가", key='min_price', value=sess('min_price')); c2.number_input("최대 매가", key='max_price', value=sess('max_price'), max_value=MAX_P)
            c3, c4 = st.columns(2); c3.number_input("최소 대지", key='min_land', value=sess('min_land')); c4.number_input("최대 대지", key='max_land', value=sess('max_land'), max_value=MAX_A)
        else:
            c1, c2 = st.columns(2); c1.number_input("최소 보증", key='min_dep', value=sess('min_dep')); c2.number_input("최대 보증", key='max_dep', value=sess('max_dep'), max_value=MAX_P)
            c3, c4 = st.columns(2); c3.number_input("최소 월세", key='min_rent', value=sess('min_rent')); c4.number_input("최대 월세", key='max_rent', value=sess('max_rent'), max_value=MAX_P)
            c7, c8 = st.columns(2); c7.number_input("최소 권리", key='min_kwon', value=sess('min_kwon')); c8.number_input("최대 권리", key='max_kwon', value=sess('max_kwon'), max_value=MAX_P)
        st.divider()
        c1, c2 = st.columns(2); c1.number_input("최소 면적", key='min_area', value=sess('min_area')); c2.number_input("최대 면적", key='max_area', value=sess('max_area'), max_value=MAX_A)
        c1, c2 = st.columns(2); c1.number_input("최저 층", key='min_fl', value=0.0, min_value=-10.0); c2.number_input("최고 층", key='max_fl', value=100.0, max_value=200.0)
        st.checkbox("무권리만 보기", key='is_no_kwon')
    
    st.divider()
    if st.button("🔄 초기화"): engine.safe_reset()
    st.markdown("---")
    view_option = st.radio("보기", ['🗂️ 카드 모드', '📋 리스트 모드'], index=0 if st.session_state.view_mode == '🗂️ 카드 모드' else 1)
    if view_option != st.session_state.view_mode: st.session_state.view_mode = view_option; st.rerun()

# ==============================================================================
# [MAIN CONTENT]
# ==============================================================================
st.title("🏙️ 범공인 매물장 (Pro)")

# [v24.36.0] Clean & Robust main_list_view
def main_list_view():
    # --------------------------------------------------------------------------
    # [DETAIL VIEW] 2-Column Layout (Map/Info)
    # --------------------------------------------------------------------------
    if st.session_state.selected_item is not None:
        item = st.session_state.selected_item
        
        # 매물이 바뀌면 분석 결과 초기화
        current_id = item.get('IronID')
        if st.session_state.last_analyzed_id != current_id:
            st.session_state.infra_res_c = None
            st.session_state.last_analyzed_id = current_id

        c_back, c_title = st.columns([1, 5])
        if c_back.button("◀ 목록"): st.session_state.selected_item = None; st.rerun()
        c_title.markdown(f"### {item.get('건물명', '매물 상세')}")

        addr_full = f"{item.get('지역_구', '')} {item.get('지역_동', '')} {item.get('번지', '')}"
        
        # [Layout Optimization] Ratio 1.5 : 1
def main_list_view():
    # --------------------------------------------------------------------------
    # [DETAIL VIEW] 2-Column Layout (Map/Info)
    # --------------------------------------------------------------------------
    if st.session_state.selected_item is not None:
        item = st.session_state.selected_item
        
        # 매물이 바뀌면 분석 결과 초기화
        current_id = item.get('IronID')
        if st.session_state.last_analyzed_id != current_id:
            st.session_state.infra_res_c = None
            st.session_state.last_analyzed_id = current_id

        c_back, c_title = st.columns([1, 5])
        if c_back.button("◀ 목록"): st.session_state.selected_item = None; st.rerun()
        c_title.markdown(f"### {item.get('건물명', '매물 상세')}")

        addr_full = f"{item.get('지역_구', '')} {item.get('지역_동', '')} {item.get('번지', '')}"
        
        # 좌측 지도 1.5 : 우측 상세 1 비율
        col_left, col_right = st.columns([1.5, 1])
        
        # --- LEFT COLUMN: MAP ---
        with col_left:
            c_info, c_zoom = st.columns([3, 1])
            c_info.caption(f"📍 {addr_full}")
            z_minus, z_plus = c_zoom.columns(2)
            if z_minus.button("－", key="zoom_out_v2", use_container_width=True):
                if st.session_state.zoom_level > 10: st.session_state.zoom_level -= 1; st.rerun()
            if z_plus.button("＋", key="zoom_in_v2", use_container_width=True):
                if st.session_state.zoom_level < 19: st.session_state.zoom_level += 1; st.rerun()
            
            lat, lng = map_api.get_naver_geocode(addr_full)
            if lat and lng:
                # 기기별 높이: PC(800), 모바일(520) - 뷰 모드 기준으로 유추
                map_h = 1000 if st.session_state.view_mode == '🗂️ 카드 모드' else 520
                try:
                    map_img = map_api.fetch_map_image(lat, lng, zoom_level=st.session_state.zoom_level, height=map_h)
                except:
                    map_img = map_api.fetch_map_image(lat, lng, zoom_level=st.session_state.zoom_level)
                
                if map_img:
                    st.image(map_img, use_container_width=True)

                st.link_button("📍 네이버 지도에서 위치 확인 (공식)", f"https://map.naver.com/v5/search/{addr_full}", use_container_width=True, type="primary")
            else:
                st.warning("위치 확인 불가")

        # --- RIGHT COLUMN: ACTIONS & TABS ---
        with col_right:
            cur_tab = st.session_state.current_sheet
            base_label = "매매" if "매매" in cur_tab else "임대"
            
            # 1. 퀵 액션
            q1, q2 = st.columns(2)
            if "브리핑" in cur_tab:
                if q1.button("🗑️ 삭제", use_container_width=True, type="primary"):
                    engine.execute_transaction("delete", pd.DataFrame([item]), cur_tab)
                    st.session_state.selected_item = None; del st.session_state.df_main; st.rerun()
            elif "(종료)" in cur_tab:
                base_tab = cur_tab.replace("(종료)", "").strip()
                if q1.button(f"♻️ 복구", use_container_width=True):
                    engine.execute_transaction("restore", pd.DataFrame([item]), cur_tab, base_tab)
                    st.session_state.selected_item = None; del st.session_state.df_main; st.rerun()
            else:
                if q1.button(f"🚩 종료", use_container_width=True):
                    engine.execute_transaction("move", pd.DataFrame([item]), cur_tab, f"{base_label}(종료)")
                    st.session_state.selected_item = None; del st.session_state.df_main; st.rerun()
            
            if q2.button(f"🚀 브리핑 복사", use_container_width=True):
                engine.execute_transaction("copy", pd.DataFrame([item]), cur_tab, f"{base_label}브리핑")
                st.success("복사 완료"); time.sleep(0.5)

            # 2. 보안 정보
            st.divider()
            with st.expander("🔒 보안 정보 (임대인/연락처)", expanded=False):
                owner = item.get('임대인', '미확확인')
                st.write(f"👤 **임대인**: {owner}")
                raw_c = f"{str(item.get('연락처', ''))} {str(item.get('연락처2', ''))}".replace('nan', '')
                numbers = re.findall(r'\d{2,3}-\d{3,4}-\d{4}', raw_c)
                if numbers:
                    for num in sorted(set(numbers)):
                        c1, c2 = st.columns(2)
                        c1.link_button(f"📞 통화 ({num})", f"tel:{num}", use_container_width=True)
                        c2.link_button(f"💬 문자 ({num})", f"sms:{num}", use_container_width=True)
                else: st.caption("등록된 연락처 없음")

            # 3. 4단 탭 (사장님 맞춤 구성)
            t1, t2, t3, t4 = st.tabs(["📝 기본", "📑 상세(1)", "📁 상세(2)", "💬 카톡"])
            
            with t1:
                with st.form("f_core"):
                    c1, c2 = st.columns(2)
                    n_cat = c1.text_input("구분", item.get('구분', ''))
                    n_name = c2.text_input("건물명", item.get('건물명', ''))
                    c3, c4 = st.columns(2)
                    if "매매" in cur_tab:
                        n_p = c3.text_input("매매가", str(item.get('매매가', 0)))
                        n_y = c4.text_input("수익률", str(item.get('수익률', 0)))
                    else:
                        n_p = c3.text_input("보증금", str(item.get('보증금', 0)))
                        n_y = c4.text_input("월세", str(item.get('월차임', 0)))
                    n_desc = st.text_area("특징", item.get('내용', ''), height=100)
                    if st.form_submit_button("저장", use_container_width=True, type="primary"):
                        updated = item.copy()
                        updated.update({'구분':n_cat, '건물명':n_name, '내용':n_desc})
                        if "매매" in cur_tab: updated.update({'매매가':n_p, '수익률':n_y})
                        else: updated.update({'보증금':n_p, '월차임':n_y})
                        engine.update_single_row(updated, cur_tab)
                        del st.session_state.df_main; st.rerun()

            with t2: # 상세(1): 실무 필수 데이터
                with st.form("f_d1"):
                    d1_cols = ['호실', '현업종', '층고', '주차', 'E/V', '화장실', '특이사항', '사진']
                    d1_data = {}
                    for col in d1_cols: d1_data[col] = st.text_input(col, str(item.get(col, '')).replace('nan',''))
                    if st.form_submit_button("상세(1) 저장", use_container_width=True):
                        updated = item.copy(); updated.update(d1_data)
                        engine.update_single_row(updated, cur_tab)
                        del st.session_state.df_main; st.rerun()

            with t3: # 상세(2): 관리용 데이터
                with st.form("f_d2"):
                    exc = ['구분','건물명','매매가','수익률','보증금','월차임','권리금','관리비','면적','층','내용','비고','선택','IronID','임대인','연락처','연락처2','지역_구','지역_동','번지', '층_clean', 'Unnamed: 0', '_match_sig']
                    exc += ['호실', '현업종', '층고', '주차', 'E/V', '화장실', '특이사항', '사진']
                    d2_cols = [c for c in item.index if c not in exc]
                    d2_data = {}
                    for col in d2_cols: d2_data[col] = st.text_input(col, str(item.get(col, '')).replace('nan',''))
                    if st.form_submit_button("상세(2) 저장", use_container_width=True):
                        updated = item.copy(); updated.update(d2_data)
                        engine.update_single_row(updated, cur_tab)
                        del st.session_state.df_main; st.rerun()

            with t4: # 카톡 브리핑
                sub = st.session_state.infra_res_c.get('subway', {}) if st.session_state.infra_res_c else {}
                w_txt = f" ({sub['station']} 도보 {int(round(sub['walk']))}분)" if sub.get('station') and sub['station'] != "정보 없음" else ""
                p_txt = f"매매 {int(item.get('매매가', 0)):,}만" if "매매" in cur_tab else f"보 {int(item.get('보증금', 0)):,} / 월 {int(item.get('월차임', 0)):,}"
                msg = f"[범공인 매물 브리핑]\n📍 위치: {addr_full}{w_txt}\n🏢 구분: {item.get('구분','')} ({item.get('층','')}층/{item.get('면적',0)}평)\n💰 조건: {p_txt}\n📝 특징: {item.get('내용','').strip()}"
                st.code(msg, language=None)
                st.caption("▲ Copy 버튼으로 복사")

        # --- BOTTOM SECTION: INFRA ANALYSIS (Wide View) ---
        st.divider()
        if lat and lng:
            if st.button("📊 입지요약 분석 실행", use_container_width=True):
                with st.spinner("분석 중..."):
                    st.session_state.infra_res_c = cached_commercial(lat, lng); st.rerun()
            
            if st.session_state.infra_res_c:
                res = st.session_state.infra_res_c
                sub = res.get('subway', {})
                if sub.get('station') and sub['station'] != "정보 없음":
                    st.success(f"**🚆 {sub['station']}** | 도보 약 {int(round(sub['walk']))}분 ({sub['dist']}m)")
                
                c_a, c_b = st.columns(2)
                with c_a:
                    st.markdown("##### 📍 주변 시설 (300m)")
                    df_f = res.get('facilities')
                    if df_f is not None and not df_f.empty:
                        try: st.dataframe(df_f.astype(str), hide_index=True, use_container_width=True)
                        except: st.dataframe(df_f)
                    else: st.caption("정보 없음")
                with c_b:
                    st.markdown("##### 🏆 주요 브랜드")
                    df_h = res.get('anchors')
                    if df_h is not None and not df_h.empty:
                        try: st.dataframe(df_h.astype(str), hide_index=True, use_container_width=True)
                        except: st.dataframe(df_h)
                    else: st.caption("정보 없음")
        return

    # --- LIST VIEW LOGIC ---
    df_filtered = df_main.copy()
    # (기존 필터 및 페이징 로직 유지)
    if st.session_state.selected_cat: df_filtered = df_filtered[df_filtered['구분'].isin(st.session_state.selected_cat)]
    if st.session_state.selected_gu: df_filtered = df_filtered[df_filtered['지역_구'].isin(st.session_state.selected_gu)]
    if st.session_state.selected_dong: df_filtered = df_filtered[df_filtered['지역_동'].isin(st.session_state.selected_dong)]
    
    search_val = st.session_state.search_keyword.strip()
    if search_val:
        mask = df_filtered.fillna("").astype(str).apply(lambda x: ' '.join(x), axis=1).str.contains(search_val, case=False)
        df_filtered = df_filtered[mask]

    # 층수 정제 필터 (유령 공백 제거 버전)
    if '층' in df_filtered.columns and not df_filtered.empty:
        df_filtered['층_clean'] = pd.to_numeric(df_filtered['층'].astype(str).str.extract(r'(-?\d+)')[0], errors='coerce').fillna(1)
        df_filtered = df_filtered[(df_filtered['층_clean'] >= st.session_state.min_fl) & (df_filtered['층_clean'] <= st.session_state.max_fl)]

    total_count = len(df_filtered)
    if total_count == 0: st.warning("🔍 검색 결과가 없습니다."); return

    ITEMS_PER_PAGE = 50
    total_pages = math.ceil(total_count / ITEMS_PER_PAGE)
    start_idx = (st.session_state.page_num - 1) * ITEMS_PER_PAGE
    df_page = df_filtered.iloc[start_idx : start_idx + ITEMS_PER_PAGE]
    
    st.info(f"📋 검색 결과: **{total_count}**건 (페이지: {st.session_state.page_num}/{total_pages})")

    # 카드 모드 / 리스트 모드 출력부 (기존 유지하되 간결화)
    if st.session_state.view_mode == '🗂️ 카드 모드':
        with st.container(height=500):
            for idx, row in df_page.iterrows():
                c_chk, c_card, c_btn = st.columns([1, 10, 3])
                c_card.markdown(f"""<div class="listing-card"><b>{row.get('구분')}</b> | {row.get('지역_동')} {row.get('번지')}<br>📐 {row.get('면적')}평 / {row.get('층')}층</div>""", unsafe_allow_html=True)
                if c_btn.button("상세", key=f"dtl_{row['IronID']}", use_container_width=True):
                    st.session_state.selected_item = row; st.rerun()
    else:
        st.data_editor(df_page, use_container_width=True, hide_index=True)

    # 페이징 컨트롤
    cp1, cp2, cp3 = st.columns([1, 1, 1])
    if cp1.button("◀", key="p_prev") and st.session_state.page_num > 1: st.session_state.page_num -= 1; st.rerun()
    cp2.markdown(f"<div style='text-align:center'>{st.session_state.page_num} / {total_pages}</div>", unsafe_allow_html=True)
    if cp3.button("▶", key="p_next") and st.session_state.page_num < total_pages: st.session_state.page_num += 1; st.rerun()

main_list_view()
