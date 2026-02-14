# app.py
# 범공인 Pro v24 Enterprise - Main Application Entry (v24.32.2 Layout Refactor)
# Feature: 2-Column Detail Layout, Clean UI, Stable Logic

import streamlit as st
import pandas as pd
import time
import math
import core_engine as engine  # [Core Engine v24.29.2]
import map_service as map_api # [Map Service v24.23.7]
import styles                 # [Style Module v24.23.7]
import infra_engine           # [Infra Engine v24.30.1]

# ==============================================================================
# [INIT] 시스템 초기화
# ==============================================================================
st.set_page_config(page_title="범공인 Pro (v24.32.2)", layout="wide", initial_sidebar_state="expanded")
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

def main_list_view():
    # --------------------------------------------------------------------------
    # [DETAIL VIEW] 2-Column Layout
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
        
        # [2-Column Layout Start]
        col_left, col_right = st.columns([1.2, 1])
        
        # --- LEFT COLUMN: MAP & ANALYSIS ---
        with col_left:
            # Zoom Buttons
            c_info, c_zoom = st.columns([3, 1])
            c_info.caption(f"📍 {addr_full}")
            z_minus, z_plus = c_zoom.columns(2)
            if z_minus.button("－", key="zoom_out", use_container_width=True, type="secondary"):
                if st.session_state.zoom_level > 10: st.session_state.zoom_level -= 1
                st.rerun()
            if z_plus.button("＋", key="zoom_in", use_container_width=True, type="secondary"):
                if st.session_state.zoom_level < 19: st.session_state.zoom_level += 1
                st.rerun()
            
            lat, lng = map_api.get_naver_geocode(addr_full)
            if lat and lng:
                map_img = map_api.fetch_map_image(lat, lng, zoom_level=st.session_state.zoom_level)
                if map_img: 
                    st.image(map_img, use_column_width=True)
                
                naver_url = f"https://map.naver.com/v5/search/{addr_full}?c={lng},{lat},17,0,0,0,dh"
                st.link_button("📍 네이버 지도에서 위치 확인 (공식)", naver_url, use_container_width=True, type="primary")
                
                # 분석 버튼 및 결과
                st.markdown("---")
                if st.button("📊 입지요약", use_container_width=True):
                    try:
                        with st.spinner("지하철 및 주요 시설 스캔 중..."):
                            st.session_state.infra_res_c = cached_commercial(lat, lng)
                            st.rerun()
                    except Exception as e: st.error(f"오류: {e}")
                
                st.write("")
                if st.session_state.infra_res_c:
                    c_data = st.session_state.infra_res_c
                    sub = c_data.get('subway', {})
                    if sub.get('station') and sub['station'] != "정보 없음":
                        w_min = int(round(sub['walk']))
                        if w_min == 0: w_min = 1
                        st.success(f"**🚆 {sub['station']} {sub.get('exit', '')}** | 도보 약 {w_min}분 ({sub['dist']}m)")
                    
                    st.markdown("##### 📍 인근 주변 시설 (300m 이내)")
                    fac_df = c_data.get('facilities')
                    if fac_df is not None and not fac_df.empty:
                        st.dataframe(fac_df, hide_index=True, use_container_width=True)
                    else: st.caption("데이터 없음")
                    
                    st.markdown("##### 🏆 상권 Top 10 브랜드 (1km)")
                    anchor_df = c_data.get('anchors')
                    if anchor_df is not None and not anchor_df.empty:
                        st.dataframe(anchor_df, hide_index=True, use_container_width=True)
            else:
                st.warning("위치 확인 불가")

        # --- RIGHT COLUMN: EDIT FORM & BRIEFING ---
        with col_right:
            st.button("🎊 계약 완료", disabled=True, use_container_width=True)
            st.write("") # 간격
            
            with st.form("edit_form"):
                st.markdown("#### 📝 매물 정보 수정")
                c1, c2 = st.columns(2)
                new_cat = c1.text_input("**구분**", value=item.get('구분', ''))
                new_name = c2.text_input("**건물명**", value=item.get('건물명', ''))
                
                c3, c4 = st.columns(2)
                if is_sale_mode:
                    new_price = c3.text_input("**매매가**", value=str(item.get('매매가', 0)).replace(',',''))
                    new_yield = c4.text_input("**수익률**", value=str(item.get('수익률', 0)).replace(',',''))
                else:
                    new_dep = c3.text_input("**보증금**", value=str(item.get('보증금', 0)).replace(',',''))
                    new_rent = c4.text_input("**월세**", value=str(item.get('월차임', 0)).replace(',',''))
                
                c5, c6 = st.columns(2)
                if is_sale_mode:
                     new_land = c5.text_input("**대지면적**", value=str(item.get('대지면적', 0)).replace(',',''))
                     new_total = c6.text_input("**연면적**", value=str(item.get('연면적', 0)).replace(',',''))
                else:
                     new_kwon = c5.text_input("**권리금**", value=str(item.get('권리금', 0)).replace(',',''))
                     new_man = c6.text_input("**관리비**", value=str(item.get('관리비', 0)).replace(',',''))

                c7, c8 = st.columns(2)
                new_area = c7.text_input("**전용면적**", value=str(item.get('면적', 0)).replace(',',''))
                new_floor = c8.text_input("**층수**", value=str(item.get('층', '')))
                
                new_desc = st.text_area("**특징**", value=item.get('내용', ''), height=150)
                new_memo = st.text_area("**비고**", value=item.get('비고', ''), height=80)

                if st.form_submit_button("💾 수정 완료", type="primary", use_container_width=True):
                    updated_data = item.copy()
                    updated_data.update({'구분': new_cat, '건물명': new_name, '면적': new_area, '층': new_floor, '내용': new_desc, '비고': new_memo})
                    if is_sale_mode: updated_data.update({'매매가': new_price, '수익률': new_yield, '대지면적': new_land, '연면적': new_total})
                    else: updated_data.update({'보증금': new_dep, '월차임': new_rent, '권리금': new_kwon, '관리비': new_man})
                    
                    success, msg = engine.update_single_row(updated_data, st.session_state.current_sheet)
                    if success:
                        st.success(msg); time.sleep(1.5); del st.session_state.df_main
                        st.session_state.selected_item = None; st.cache_data.clear(); st.rerun()
                    else: st.error(msg)
            
            # 카톡 브리핑 생성기
            st.write("")
            with st.expander("💬 카톡 브리핑 문구 생성 (복사용)", expanded=True):
                sub = st.session_state.infra_res_c.get('subway', {}) if st.session_state.infra_res_c else {}
                walk_txt = ""
                if sub.get('station') and sub['station'] != "정보 없음":
                    w_min = int(round(sub['walk']))
                    if w_min == 0: w_min = 1
                    walk_txt = f" ({sub['station']} 도보 {w_min}분)"

                is_sale = "매매" in st.session_state.current_sheet
                addr_disp = f"{item.get('지역_구', '')} {item.get('지역_동', '')} {item.get('번지', '')}".strip()
                
                if is_sale:
                    price_txt = f"매매 {int(item.get('매매가', 0)):,}만"
                    if item.get('수익률', 0) > 0: price_txt += f" (수익률 {item['수익률']}%)"
                else:
                    kwon = int(item.get('권리금', 0))
                    kwon_txt = f" / 권 {kwon:,}" if kwon > 0 else " / 권 무"
                    price_txt = f"보 {int(item.get('보증금', 0)):,} / 월 {int(item.get('월차임', 0)):,}{kwon_txt}"
                    if item.get('관리비', 0) > 0: price_txt += f" (관 {int(item['관리비']):,})"

                spec_txt = f"{item.get('층', '')}층 / 실 {item.get('면적', 0)}평"
                desc_txt = item.get('내용', '상세내용 문의').strip()

                briefing_msg = f"""[범공인 매물 브리핑]
📍 위치: {addr_disp}{walk_txt}
🏢 구분: {item.get('구분', '')} ({spec_txt})
💰 조건: {price_txt}
📝 특징: {desc_txt}"""

                st.code(briefing_msg, language=None)
                st.caption("▲ Copy 버튼으로 복사")

        return

    # --------------------------------------------------------------------------
    # [LIST VIEW] Filter & Pagination
    # --------------------------------------------------------------------------
    df_filtered = df_main.copy()
    if '구분' in df_filtered.columns and st.session_state.selected_cat: df_filtered = df_filtered[df_filtered['구분'].isin(st.session_state.selected_cat)]
    if '지역_구' in df_filtered.columns and st.session_state.selected_gu: df_filtered = df_filtered[df_filtered['지역_구'].isin(st.session_state.selected_gu)]
    if '지역_동' in df_filtered.columns and st.session_state.selected_dong: df_filtered = df_filtered[df_filtered['지역_동'].isin(st.session_state.selected_dong)]
    if '번지' in df_filtered.columns and st.session_state.exact_bunji: df_filtered = df_filtered[df_filtered['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]
    search_val = st.session_state.search_keyword.strip()
    if search_val:
        search_scope = df_filtered.drop(columns=['선택', 'IronID'], errors='ignore')
        mask = search_scope.fillna("").astype(str).apply(lambda x: ' '.join(x), axis=1).str.contains(search_val, case=False)
        df_filtered = df_filtered[mask]
    
    if is_sale_mode:
        if '매매가' in df_filtered.columns and not df_filtered.empty: df_filtered = df_filtered[(df_filtered['매매가'] >= st.session_state.min_price) & (df_filtered['매매가'] <= st.session_state.max_price)]
        if '대지면적' in df_filtered.columns and not df_filtered.empty: df_filtered = df_filtered[(df_filtered['대지면적'] >= st.session_state.min_land) & (df_filtered['대지면적'] <= st.session_state.max_land)]
    else:
        if '보증금' in df_filtered.columns and not df_filtered.empty: df_filtered = df_filtered[(df_filtered['보증금'] >= st.session_state.min_dep) & (df_filtered['보증금'] <= st.session_state.max_dep)]
        if '월차임' in df_filtered.columns and not df_filtered.empty: df_filtered = df_filtered[(df_filtered['월차임'] >= st.session_state.min_rent) & (df_filtered['월차임'] <= st.session_state.max_rent)]
        
        # [권리금 필터 로직 교정]
        if '권리금' in df_filtered.columns and not df_filtered.empty:
            if st.session_state.is_no_kwon:
                df_filtered = df_filtered[df_filtered['권리금'] == 0]
            else:
                df_filtered = df_filtered[(df_filtered['권리금'] >= st.session_state.min_kwon) & (df_filtered['권리금'] <= st.session_state.max_kwon)]
    
    if '면적' in df_filtered.columns and not df_filtered.empty: df_filtered = df_filtered[(df_filtered['면적'] >= st.session_state.min_area) & (df_filtered['면적'] <= st.session_state.max_area)]
    
    # [v24.32.2] 유령 공백 소탕 및 필터 로직 정밀 수리 (Clean Version)
    if '층' in df_filtered.columns and not df_filtered.empty:
        # 1. 층 데이터 정제 (마이너스 기호 포함 추출)
        df_filtered['층_clean'] = df_filtered['층'].astype(str).str.extract(r'(-?\d+)')[0]
        # 2. 숫자로 변환 (결측치는 1층으로 가정)
        df_filtered['층_clean'] = pd.to_numeric(df_filtered['층_clean'], errors='coerce').fillna(1)
        # 3. 필터 적용 (불필요한 공백 및 유령 문자 제거 완료)
        df_filtered = df_filtered[
            (df_filtered['층_clean'] >= st.session_state.min_fl) & 
            (df_filtered['층_clean'] <= st.session_state.max_fl)
        ]

    total_count = len(df_filtered)
    if total_count == 0: st.warning("🔍 검색 결과가 없습니다."); return

    ITEMS_PER_PAGE = 50
    total_pages = math.ceil(total_count / ITEMS_PER_PAGE)
    if st.session_state.page_num > total_pages: st.session_state.page_num = 1
    
    start_idx = (st.session_state.page_num - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    df_page = df_filtered.iloc[start_idx:end_idx]
    
    st.info(f"📋 검색 결과: **{total_count}**건 (페이지: {st.session_state.page_num}/{total_pages})")

    # ==========================================================================
    # [VIEW MODE A] CARD VIEW
    # ==========================================================================
    if st.session_state.view_mode == '🗂️ 카드 모드':
        c_act1, c_act2 = st.columns(2)
        if c_act1.button("✅ 전체 선택", key="sel_all_card"):
            target_ids = df_page['IronID'].tolist()
            st.session_state.df_main.loc[st.session_state.df_main['IronID'].isin(target_ids), '선택'] = True
            for iid in target_ids: st.session_state[f"chk_{iid}"] = True
            st.rerun()
        if c_act2.button("⬜ 전체 해제", key="desel_all_card"):
            st.session_state.df_main['선택'] = False
            for iid in st.session_state.df_main['IronID']:
                if f"chk_{iid}" in st.session_state: st.session_state[f"chk_{iid}"] = False
            st.rerun()

        with st.container(height=500):
            for idx, row in df_page.iterrows():
                raw_ho = str(row.get('호실', '')).replace('호', '').strip()
                ho_str = f"{raw_ho}호" if raw_ho else ""
                gubun = row.get('구분', '매물')
                
                if is_sale_mode:
                    price = f"매매 {int(row.get('매매가', 0)):,}만"
                    if row.get('수익률', 0) > 0: price += f" ({row['수익률']}%)"
                else:
                    price = f"보 {int(row.get('보증금', 0)):,} / 월 {int(row.get('월차임', 0)):,}"
                    if row.get('관리비', 0) > 0: price += f" (관 {int(row['관리비']):,})"
                addr = f"{row.get('지역_구', '')} {row.get('지역_동', '')} {row.get('번지', '')}"
                floor = f"{row.get('층', '')}층"
                
                if is_sale_mode: spec = f"대지:{row.get('대지면적', 0)}평 / 연면:{row.get('연면적', 0)}평"
                else:
                    spec = f"{ho_str} / 실:{row.get('면적', 0)}평"
                    if row.get('권리금', 0) > 0: spec += f" / 권:{int(row['권리금']):,}"
                    if row.get('현업종', ''): spec += f" / {row['현업종']}"
                
                c_chk, c_card, c_btn = st.columns([1, 10, 3]) 
                is_checked = st.session_state.df_main.loc[st.session_state.df_main['IronID'] == row['IronID'], '선택'].values[0]
                chk_key = f"chk_{row['IronID']}"
                if chk_key not in st.session_state: st.session_state[chk_key] = bool(is_checked)
                
                if c_chk.checkbox("", key=chk_key):
                    if not is_checked:
                        st.session_state.df_main.loc[st.session_state.df_main['IronID'] == row['IronID'], '선택'] = True
                        st.rerun()
                else:
                    if is_checked:
                        st.session_state.df_main.loc[st.session_state.df_main['IronID'] == row['IronID'], '선택'] = False
                        st.rerun()

                c_card.markdown(f"""
                <div class="listing-card">
                    <div class="card-row-1"><span class="card-tag">{gubun}</span><span class="card-price">{price}</span></div>
                    <div class="card-row-2">📍 {addr} <span style="color:#ddd">|</span> {floor}</div>
                    <div class="card-row-3">📐 {spec}</div>
                </div>""", unsafe_allow_html=True)
                
                with c_btn.container():
                    if st.button("상세", key=f"btn_detail_{row['IronID']}", use_container_width=True):
                        st.session_state.selected_item = row; st.rerun()
        
        c_prev, c_page, c_next = st.columns([1, 1, 1])
        if c_prev.button("◀", key="prev_list"):
            if st.session_state.page_num > 1: st.session_state.page_num -= 1; st.rerun()
        c_page.markdown(f"<div class='pagination-text'>{st.session_state.page_num} / {total_pages}</div>", unsafe_allow_html=True)
        if c_next.button("▶", key="next_list"):
            if st.session_state.page_num < total_pages: st.session_state.page_num += 1; st.rerun()

    # ==========================================================================
    # [VIEW MODE B] LIST VIEW
    # ==========================================================================
    else:
        c_act1, c_act2 = st.columns(2)
        if c_act1.button("✅ 전체 선택", key="sel_all_list"):
            target_ids = df_page['IronID'].tolist()
            st.session_state.df_main.loc[st.session_state.df_main['IronID'].isin(target_ids), '선택'] = True
            st.session_state.editor_key_version += 1; st.rerun()
        if c_act2.button("⬜ 전체 해제", key="desel_all_list"):
            st.session_state.df_main['선택'] = False
            st.session_state.editor_key_version += 1; st.rerun()

        df_list_view = df_page.copy()
        df_list_view.insert(0, '🔍', False)

        col_cfg = {
            "🔍": st.column_config.CheckboxColumn(width="small", label="상세"),
            "선택": st.column_config.CheckboxColumn(width="small"), 
            "IronID": None
        }
        format_map = {"매매가": "%d", "보증금": "%d", "월차임": "%d", "권리금": "%d", "면적": "%.1f", "대지면적": "%.1f", "연면적": "%.1f"}
        for col, fmt in format_map.items():
            if col in df_filtered.columns: col_cfg[col] = st.column_config.NumberColumn(col, format=fmt)
        if "내용" in df_filtered.columns: col_cfg["내용"] = st.column_config.TextColumn("특징", width="large")
        
        cols = ["내용", "보증금", "월차임", "매매가", "권리금", "관리비"]
        dis_cols = [c for c in df_filtered.columns if c not in ['선택', '🔍'] + cols]
        
        edited_df = st.data_editor(
            df_list_view,
            disabled=dis_cols,
            use_container_width=True,
            hide_index=True,
            column_config=col_cfg,
            key=f"editor_{st.session_state.editor_key_version}",
            height=400, 
            num_rows="fixed"
        )
        
        trigger_rows = edited_df[edited_df['🔍'] == True]
        if not trigger_rows.empty:
            target_row = df_main[df_main['IronID'] == trigger_rows.iloc[0]['IronID']].iloc[0]
            st.session_state.selected_item = target_row
            st.rerun()
        
        c_prev, c_page, c_next = st.columns([1, 1, 1])
        if c_prev.button("◀", key="prev_list"):
            if st.session_state.page_num > 1: st.session_state.page_num -= 1; st.rerun()
        c_page.markdown(f"<div class='pagination-text'>{st.session_state.page_num} / {total_pages}</div>", unsafe_allow_html=True)
        if c_next.button("▶", key="next_list"):
            if st.session_state.page_num < total_pages: st.session_state.page_num += 1; st.rerun()

        st.divider()
        if st.button("💾 변경사항 저장 (서버 반영)", type="primary", use_container_width=True, key="btn_save"):
            with st.status("💾 저장 중...", expanded=True) as status:
                save_df = edited_df.drop(columns=['🔍'], errors='ignore')
                success, msg, debug = engine.save_updates_to_sheet(save_df, st.session_state.df_main, st.session_state.current_sheet)
                if success:
                    status.update(label="완료!", state="complete"); st.success(msg); time.sleep(1.0)
                    if 'df_main' in st.session_state: del st.session_state.df_main
                    st.cache_data.clear(); st.rerun()
                else: st.error(msg)
    
    # [v24.32.1] selected_rows 안전 정의 (NameError 방지)
    selected_rows = pd.DataFrame() 
    if st.session_state.view_mode == '📋 리스트 모드':
        try:
            # 에디터에서 선택된 행 추출
            selected_rows = edited_df[edited_df['선택'] == True].drop(columns=['🔍'], errors='ignore')
        except:
            pass
    else:
        # 카드 모드에서 선택된 행 추출
        if 'df_main' in st.session_state:
            selected_rows = st.session_state.df_main[st.session_state.df_main['선택'] == True]

    # --- UNIVERSAL ACTION BAR ---
    st.divider()
    if len(selected_rows) > 0:
        st.success(f"✅ {len(selected_rows)}건 선택됨")
        cur_tab = st.session_state.current_sheet
        is_end = "(종료)" in cur_tab
        base_tab = cur_tab.replace("(종료)", "").replace("브리핑", "").strip()
        base_label = "매매" if "매매" in cur_tab else "임대"
        
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            if "브리핑" in cur_tab: st.button("🚫", disabled=True, use_container_width=True, key="btn_move_disabled")
            elif is_end:
                if st.button(f"♻️ 복구({base_label})", use_container_width=True, key="btn_restore"): st.session_state.action_status = 'restore_confirm'
            else:
                if st.button(f"🚀 {base_label}(종료)", use_container_width=True, key="btn_move"): st.session_state.action_status = 'move_confirm'
        with ac2:
            if "브리핑" not in cur_tab:
                if st.button(f"📋 {base_label}브리핑", use_container_width=True, key="btn_copy"): st.session_state.action_status = 'copy_confirm'
            else: st.button("🚫", disabled=True, use_container_width=True, key="btn_copy_disabled")
        with ac3:
            if st.button("🗑️ 삭제", type="primary", use_container_width=True, key="btn_del"): st.session_state.action_status = 'delete_confirm'

        if st.session_state.action_status == 'move_confirm':
            target = f"{base_tab}(종료)"
            with st.status(f"🚀 '{target}' 시트로 이동 중...", expanded=True):
                if st.button("이동 확정", key="conf_move", type="primary"):
                    _, msg, _ = engine.execute_transaction("move", selected_rows, cur_tab, target)
                    st.success(msg); time.sleep(1); del st.session_state.df_main; engine.safe_reset()

        elif st.session_state.action_status == 'restore_confirm':
            with st.status(f"♻️ '{base_tab}' 시트로 복구 중...", expanded=True):
                if st.button("복구 확정", key="conf_restore", type="primary"):
                    _, msg, _ = engine.execute_transaction("restore", selected_rows, cur_tab, base_tab)
                    st.success(msg); time.sleep(1); del st.session_state.df_main; engine.safe_reset()

        elif st.session_state.action_status == 'copy_confirm':
             target = f"{base_tab}브리핑"
             with st.status(f"📋 '{target}' 시트로 복사 중...", expanded=True):
                if st.button("복사 확정", key="conf_copy", type="primary"):
                    _, msg, _ = engine.execute_transaction("copy", selected_rows, cur_tab, target)
                    st.success(msg); time.sleep(1); st.session_state.action_status = None

        elif st.session_state.action_status == 'delete_confirm':
            with st.status("🗑️ 데이터 영구 삭제 경고", expanded=True):
                st.error("⚠️ 주의: 삭제된 데이터는 복구할 수 없습니다.")
                if st.button("영구 삭제 확정", key="conf_del", type="primary"):
                    _, msg, _ = engine.execute_transaction("delete", selected_rows, cur_tab)
                    st.success(msg); time.sleep(1); del st.session_state.df_main; engine.safe_reset()

    with st.container(): st.write(""); st.write("")

main_list_view()
