# app.py
# 범공인 Pro v24 Enterprise - Main Application Entry (v24.22.4)
# Feature: Responsive Cards, Text Sanitizer, Checkbox Integration

import streamlit as st
import pandas as pd
import time
import math
import core_engine as engine  # [Core Engine v24.21.2]
import styles                 # [Style Module v24.22.4]

# ==============================================================================
# [INIT] 시스템 초기화
# ==============================================================================
st.set_page_config(
    page_title="범공인 Pro (v24.22.4)",
    layout="wide",
    initial_sidebar_state="expanded"
)

styles.apply_custom_css()

# 상태 초기화
if 'current_sheet' not in st.session_state: st.session_state.current_sheet = engine.SHEET_NAMES[0]
if 'action_status' not in st.session_state: st.session_state.action_status = None 
if 'view_mode' not in st.session_state: st.session_state.view_mode = '🗂️ 카드 모드'
if 'page_num' not in st.session_state: st.session_state.page_num = 1
    
# 스마트 필터
if 'show_cat_search' not in st.session_state: st.session_state.show_cat_search = False
if 'show_gu_search' not in st.session_state: st.session_state.show_gu_search = False
if 'show_dong_search' not in st.session_state: st.session_state.show_dong_search = False
    
engine.initialize_search_state()
def sess(key): return st.session_state[key]

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
            if 'df_main' in st.session_state: del st.session_state.df_main
            st.cache_data.clear()
            st.rerun()

    if 'df_main' not in st.session_state:
        with st.spinner("데이터 로드 중..."):
            loaded_df = engine.load_sheet_data(st.session_state.current_sheet)
            if loaded_df is not None: st.session_state.df_main = loaded_df
            else: st.error("🚨 데이터 로드 실패."); st.stop()
    df_main = st.session_state.df_main

    st.write("") 

    with st.container(border=True):
        st.markdown("##### 🔍 키워드 검색")
        st.text_input("통합 검색", key='search_keyword', placeholder="내용, 건물명 등")
        st.text_input("번지 검색", key='exact_bunji', placeholder="예: 50-1")

    st.write("") 

    with st.container(border=True):
        st.markdown("##### 🏷️ 항목 필터링")
        
        c1, c2 = st.columns([4, 1])
        c1.markdown("구분")
        if c2.button("🔍", key="btn_cat"): st.session_state.show_cat_search = not st.session_state.show_cat_search
        unique_cat = sorted(df_main['구분'].astype(str).unique().tolist()) if '구분' in df_main.columns else []
        if st.session_state.show_cat_search:
            term = st.text_input("구분 검색", key="cat_term")
            if term: unique_cat = [x for x in unique_cat if term in x]
        st.multiselect("구분 선택", unique_cat, key='selected_cat', placeholder="전체 선택", label_visibility="collapsed")

        c3, c4 = st.columns([4, 1])
        c3.markdown("지역 (구)")
        if c4.button("🔍", key="btn_gu"): st.session_state.show_gu_search = not st.session_state.show_gu_search
        unique_gu = sorted(df_main['지역_구'].astype(str).unique().tolist()) if '지역_구' in df_main.columns else []
        if st.session_state.show_gu_search:
            term = st.text_input("구 검색", key="gu_term")
            if term: unique_gu = [x for x in unique_gu if term in x]
        st.multiselect("지역 (구) 선택", unique_gu, key='selected_gu', placeholder="전체 선택", label_visibility="collapsed")
        
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
        st.multiselect("지역 (동) 선택", unique_dong, key='selected_dong', placeholder="전체 선택", label_visibility="collapsed")

    st.write("")

    is_sale_mode = "매매" in st.session_state.current_sheet
    with st.expander("💰 상세 금액/면적 설정", expanded=False):
        MAX_PRICE = 10000000.0 
        MAX_AREA = 1000000.0
        if is_sale_mode:
            c1, c2 = st.columns(2); c1.number_input("최소 매가", key='min_price', value=sess('min_price')); c2.number_input("최대 매가", key='max_price', value=sess('max_price'), max_value=MAX_PRICE)
            c3, c4 = st.columns(2); c3.number_input("최소 대지", key='min_land', value=sess('min_land')); c4.number_input("최대 대지", key='max_land', value=sess('max_land'), max_value=MAX_AREA)
        else:
            c1, c2 = st.columns(2); c1.number_input("최소 보증", key='min_dep', value=sess('min_dep')); c2.number_input("최대 보증", key='max_dep', value=sess('max_dep'), max_value=MAX_PRICE)
            c3, c4 = st.columns(2); c3.number_input("최소 월세", key='min_rent', value=sess('min_rent')); c4.number_input("최대 월세", key='max_rent', value=sess('max_rent'), max_value=MAX_PRICE)
            c7, c8 = st.columns(2); c7.number_input("최소 권리", key='min_kwon', value=sess('min_kwon')); c8.number_input("최대 권리", key='max_kwon', value=sess('max_kwon'), max_value=MAX_PRICE)

        st.divider()
        c1, c2 = st.columns(2); c1.number_input("최소 면적", key='min_area', value=sess('min_area')); c2.number_input("최대 면적", key='max_area', value=sess('max_area'), max_value=MAX_AREA)
        c1, c2 = st.columns(2); c1.number_input("최저 층", key='min_fl', value=0.0, min_value=-10.0); c2.number_input("최고 층", key='max_fl', value=100.0, max_value=200.0)
        st.checkbox("무권리만 보기", key='is_no_kwon')
    
    st.divider()
    if st.button("🔄 조건 초기화"): engine.safe_reset()
    
    st.markdown("---")
    view_option = st.radio("보기 모드", ['🗂️ 카드 모드', '📋 리스트 모드'], index=0 if st.session_state.view_mode == '🗂️ 카드 모드' else 1)
    if view_option != st.session_state.view_mode:
        st.session_state.view_mode = view_option
        st.rerun()

# ==============================================================================
# [MAIN CONTENT] 하이브리드 리스트 뷰
# ==============================================================================
st.title("🏙️ 범공인 매물장 (Pro)")

@st.fragment
def main_list_view():
    df_filtered = df_main.copy()

    # Filter Logic
    if '구분' in df_filtered.columns and st.session_state.selected_cat:
        df_filtered = df_filtered[df_filtered['구분'].isin(st.session_state.selected_cat)]
    if '지역_구' in df_filtered.columns and st.session_state.selected_gu:
        df_filtered = df_filtered[df_filtered['지역_구'].isin(st.session_state.selected_gu)]
    if '지역_동' in df_filtered.columns and st.session_state.selected_dong:
        df_filtered = df_filtered[df_filtered['지역_동'].isin(st.session_state.selected_dong)]
    if '번지' in df_filtered.columns and st.session_state.exact_bunji:
        df_filtered = df_filtered[df_filtered['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]
    
    search_val = st.session_state.search_keyword.strip()
    if search_val:
        search_scope = df_filtered.drop(columns=['선택', 'IronID'], errors='ignore')
        mask = search_scope.fillna("").astype(str).apply(lambda x: ' '.join(x), axis=1).str.contains(search_val, case=False)
        df_filtered = df_filtered[mask]

    # Numeric Filters (Condensed)
    if is_sale_mode:
        if '매매가' in df_filtered.columns: df_filtered = df_filtered[(df_filtered['매매가'] >= st.session_state.min_price) & (df_filtered['매매가'] <= st.session_state.max_price)]
        if '대지면적' in df_filtered.columns: df_filtered = df_filtered[(df_filtered['대지면적'] >= st.session_state.min_land) & (df_filtered['대지면적'] <= st.session_state.max_land)]
    else:
        if '보증금' in df_filtered.columns: df_filtered = df_filtered[(df_filtered['보증금'] >= st.session_state.min_dep) & (df_filtered['보증금'] <= st.session_state.max_dep)]
        if '월차임' in df_filtered.columns: df_filtered = df_filtered[(df_filtered['월차임'] >= st.session_state.min_rent) & (df_filtered['월차임'] <= st.session_state.max_rent)]
        if '권리금' in df_filtered.columns and st.session_state.is_no_kwon: df_filtered = df_filtered[df_filtered['권리금'] == 0]
    
    if '면적' in df_filtered.columns: df_filtered = df_filtered[(df_filtered['면적'] >= st.session_state.min_area) & (df_filtered['면적'] <= st.session_state.max_area)]
    if '층' in df_filtered.columns: df_filtered = df_filtered[(df_filtered['층'] >= st.session_state.min_fl) & (df_filtered['층'] <= st.session_state.max_fl)]

    # Info & Pagination Setup
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
        # Mass Action (Condensed)
        c_act1, c_act2 = st.columns(2)
        if c_act1.button("✅ 전체 선택", key="sel_all_card"):
            st.session_state.df_main.loc[st.session_state.df_main['IronID'].isin(df_page['IronID']), '선택'] = True
            st.rerun()
        if c_act2.button("⬜ 전체 해제", key="desel_all_card"):
            st.session_state.df_main['선택'] = False
            st.rerun()

        with st.container(height=500):
            for idx, row in df_page.iterrows():
                # [Data Processing]
                # 호실에서 '호' 제거 후 포맷팅
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
                
                if is_sale_mode:
                    spec = f"대지:{row.get('대지면적', 0)}평 / 연면:{row.get('연면적', 0)}평"
                else:
                    spec = f"{ho_str} / 실:{row.get('면적', 0)}평"
                    if row.get('권리금', 0) > 0: spec += f" / 권:{int(row['권리금']):,}"
                    if row.get('현업종', ''): spec += f" / {row['현업종']}"
                
                # [Card + Checkbox Layout]
                c_chk, c_card = st.columns([1, 15]) # 1:15 비율
                
                # Checkbox Logic
                is_checked = st.session_state.df_main.loc[st.session_state.df_main['IronID'] == row['IronID'], '선택'].values[0]
                if c_chk.checkbox("", value=bool(is_checked), key=f"chk_{row['IronID']}") != is_checked:
                    st.session_state.df_main.loc[st.session_state.df_main['IronID'] == row['IronID'], '선택'] = not is_checked
                    st.rerun()

                # Card Logic
                card_html = f"""
                <div class="listing-card">
                    <div class="card-row-1">
                        <span class="card-tag">{gubun}</span>
                        <span class="card-price">{price}</span>
                    </div>
                    <div class="card-row-2">
                        📍 {addr} <span style="color:#ddd">|</span> {floor}
                    </div>
                    <div class="card-row-3">
                        📐 {spec}
                    </div>
                </div>
                """
                c_card.markdown(card_html, unsafe_allow_html=True)
        
        # Pagination
        c_prev, c_page, c_next = st.columns([1, 1, 1])
        if c_prev.button("◀", key="prev_card"):
            if st.session_state.page_num > 1: st.session_state.page_num -= 1; st.rerun()
        c_page.markdown(f"<div class='pagination-text'>{st.session_state.page_num} / {total_pages}</div>", unsafe_allow_html=True)
        if c_next.button("▶", key="next_card"):
            if st.session_state.page_num < total_pages: st.session_state.page_num += 1; st.rerun()

    # ==========================================================================
    # [VIEW MODE B] LIST VIEW
    # ==========================================================================
    else:
        c_act1, c_act2 = st.columns(2)
        if c_act1.button("✅ 전체 선택", key="sel_all_list"):
            st.session_state.df_main.loc[st.session_state.df_main['IronID'].isin(df_page['IronID']), '선택'] = True
            st.session_state.editor_key_version += 1
            st.rerun()
        if c_act2.button("⬜ 전체 해제", key="desel_all_list"):
            st.session_state.df_main['선택'] = False
            st.session_state.editor_key_version += 1
            st.rerun()

        col_cfg = {"선택": st.column_config.CheckboxColumn(width="small"), "IronID": None}
        format_map = {"매매가": "%d", "보증금": "%d", "월차임": "%d", "권리금": "%d", "면적": "%.1f"}
        for col, fmt in format_map.items():
            if col in df_filtered.columns: col_cfg[col] = st.column_config.NumberColumn(col, format=fmt)
        if "내용" in df_filtered.columns: col_cfg["내용"] = st.column_config.TextColumn("특징", width="large")
        
        cols = ["내용", "보증금", "월차임", "매매가", "권리금", "관리비"]
        dis_cols = [c for c in df_filtered.columns if c not in ['선택'] + cols]
        
        edited_df = st.data_editor(
            df_page,
            disabled=dis_cols,
            use_container_width=True,
            hide_index=True,
            column_config=col_cfg,
            key=f"editor_{st.session_state.editor_key_version}",
            height=400, 
            num_rows="fixed"
        )
        
        c_prev, c_page, c_next = st.columns([1, 1, 1])
        if c_prev.button("◀", key="prev_list"):
            if st.session_state.page_num > 1: st.session_state.page_num -= 1; st.rerun()
        c_page.markdown(f"<div class='pagination-text'>{st.session_state.page_num} / {total_pages}</div>", unsafe_allow_html=True)
        if c_next.button("▶", key="next_list"):
            if st.session_state.page_num < total_pages: st.session_state.page_num += 1; st.rerun()

        st.divider()
        if st.button("💾 변경사항 저장 (서버 반영)", type="primary", use_container_width=True):
            with st.status("💾 저장 중...", expanded=True) as status:
                success, msg, debug = engine.save_updates_to_sheet(edited_df, st.session_state.df_main, st.session_state.current_sheet)
                if success:
                    status.update(label="완료!", state="complete"); st.success(msg); time.sleep(1.0)
                    if 'df_main' in st.session_state: del st.session_state.df_main
                    st.cache_data.clear(); st.rerun()
                else: st.error(msg)
    
    # --- UNIVERSAL ACTION BAR ---
    st.divider()
    selected_rows = st.session_state.df_main[st.session_state.df_main['선택'] == True]
    if len(selected_rows) > 0:
        st.success(f"✅ {len(selected_rows)}건 선택됨")
        cur_tab = st.session_state.current_sheet
        is_end = "(종료)" in cur_tab
        base_tab = cur_tab.replace("(종료)", "").replace("브리핑", "").strip()
        
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            if "브리핑" in cur_tab: st.button("🚫", disabled=True, use_container_width=True)
            elif is_end:
                if st.button(f"♻️ 복구", use_container_width=True): st.session_state.action_status = 'restore_confirm'
            else:
                if st.button(f"🚀 종료", use_container_width=True): st.session_state.action_status = 'move_confirm'
        with ac2:
            if "브리핑" not in cur_tab:
                if st.button(f"📋 복사", use_container_width=True): st.session_state.action_status = 'copy_confirm'
            else: st.button("🚫", disabled=True, use_container_width=True)
        with ac3:
            if st.button("🗑️ 삭제", type="primary", use_container_width=True): st.session_state.action_status = 'delete_confirm'

        if st.session_state.action_status == 'move_confirm':
            target = f"{base_tab}(종료)"
            with st.status(f"🚀 이동 중...", expanded=True):
                if st.button("확인"):
                    _, msg, _ = engine.execute_transaction("move", selected_rows, cur_tab, target)
                    st.success(msg); time.sleep(1); del st.session_state.df_main; engine.safe_reset()

        elif st.session_state.action_status == 'restore_confirm':
            with st.status(f"♻️ 복구 중...", expanded=True):
                if st.button("확인"):
                    _, msg, _ = engine.execute_transaction("restore", selected_rows, cur_tab, base_tab)
                    st.success(msg); time.sleep(1); del st.session_state.df_main; engine.safe_reset()

        elif st.session_state.action_status == 'copy_confirm':
            target = f"{base_tab}브리핑"
            with st.status(f"📋 복사 중...", expanded=True):
                if st.button("확인"):
                    _, msg, _ = engine.execute_transaction("copy", selected_rows, cur_tab, target)
                    st.success(msg); time.sleep(1); st.session_state.action_status = None

        elif st.session_state.action_status == 'delete_confirm':
            with st.status(f"🗑️ 삭제 중...", expanded=True):
                st.error("복구 불가"); 
                if st.button("확인"):
                    _, msg, _ = engine.execute_transaction("delete", selected_rows, cur_tab)
                    st.success(msg); time.sleep(1); del st.session_state.df_main; engine.safe_reset()

    with st.container(): st.write(""); st.write("")

main_list_view()
