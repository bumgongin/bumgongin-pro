# app.py
# 범공인 Pro v24 Enterprise - Main Application Entry (v24.21.9)
# Final Fix: Container Removal & Direct Height Control

import streamlit as st
import pandas as pd
import time
import core_engine as engine  # [Core Engine v24.21.2]
import styles                 # [Style Module v24.21.9]

# ==============================================================================
# [INIT] 시스템 초기화
# ==============================================================================
st.set_page_config(
    page_title="범공인 Pro (v24.21.9)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일 적용
styles.apply_custom_css()

# 엔진 상태 초기화
if 'current_sheet' not in st.session_state: 
    st.session_state.current_sheet = engine.SHEET_NAMES[0]
if 'action_status' not in st.session_state: 
    st.session_state.action_status = None 

# 스마트 필터 토글 상태 초기화
if 'show_cat_search' not in st.session_state: st.session_state.show_cat_search = False
if 'show_gu_search' not in st.session_state: st.session_state.show_gu_search = False
if 'show_dong_search' not in st.session_state: st.session_state.show_dong_search = False
    
engine.initialize_search_state() # 필터 변수 초기화

def sess(key): return st.session_state[key]

# ==============================================================================
# [SIDEBAR] 필터링 컨트롤 타워
# ==============================================================================
with st.sidebar:
    st.header("📂 관리 도구")
    
    # 1. 시트 선택
    with st.container(border=True):
        st.markdown("##### 📄 작업 시트")
        try: curr_idx = engine.SHEET_NAMES.index(st.session_state.current_sheet)
        except: curr_idx = 0
        selected_sheet = st.selectbox("시트 선택", engine.SHEET_NAMES, index=curr_idx, label_visibility="collapsed")
        
        if selected_sheet != st.session_state.current_sheet:
            st.session_state.current_sheet = selected_sheet
            st.session_state.action_status = None 
            st.session_state.editor_key_version += 1
            if 'df_main' in st.session_state: del st.session_state.df_main
            st.cache_data.clear()
            st.rerun()

    # [데이터 로드 & 세션 고정]
    if 'df_main' not in st.session_state:
        with st.spinner("데이터를 불러오는 중..."):
            loaded_df = engine.load_sheet_data(st.session_state.current_sheet)
            if loaded_df is not None:
                st.session_state.df_main = loaded_df
            else:
                st.error("🚨 데이터 로드 실패. GID 설정을 확인하세요.")
                st.stop()
    
    df_main = st.session_state.df_main

    st.write("") # 간격

    # 2. 텍스트 검색
    with st.container(border=True):
        st.markdown("##### 🔍 키워드 검색")
        st.text_input("통합 검색 (내용, 건물명)", key='search_keyword', placeholder="검색어 입력")
        st.text_input("번지 정밀검색 (예: 50-1)", key='exact_bunji', placeholder="번지 입력")

    st.write("") 

    # 3. 항목 필터 (스마트 토글)
    with st.container(border=True):
        st.markdown("##### 🏷️ 항목 필터링")
        
        # [구분]
        c_cat_L, c_cat_B = st.columns([4, 1])
        c_cat_L.markdown("구분")
        if c_cat_B.button("🔍", key="btn_cat_search"):
            st.session_state.show_cat_search = not st.session_state.show_cat_search
            
        unique_cat = sorted(df_main['구분'].astype(str).unique().tolist()) if '구분' in df_main.columns else []
        
        if st.session_state.show_cat_search:
            cat_term = st.text_input("구분 검색", key="cat_search_term", placeholder="예: 상가")
            if cat_term:
                unique_cat = [c for c in unique_cat if cat_term in c]

        st.multiselect("구분 선택", unique_cat, key='selected_cat', placeholder="전체 선택", label_visibility="collapsed")

        # [지역 (구)]
        c_gu_L, c_gu_B = st.columns([4, 1])
        c_gu_L.markdown("지역 (구)")
        if c_gu_B.button("🔍", key="btn_gu_search"):
            st.session_state.show_gu_search = not st.session_state.show_gu_search
            
        unique_gu = sorted(df_main['지역_구'].astype(str).unique().tolist()) if '지역_구' in df_main.columns else []
        
        if st.session_state.show_gu_search:
            gu_term = st.text_input("구 검색", key="gu_search_term", placeholder="예: 강남구")
            if gu_term:
                unique_gu = [g for g in unique_gu if gu_term in g]
        
        st.multiselect("지역 (구) 선택", unique_gu, key='selected_gu', placeholder="전체 선택", label_visibility="collapsed")
        
        # [지역 (동)]
        c_dong_L, c_dong_B = st.columns([4, 1])
        c_dong_L.markdown("지역 (동)")
        if c_dong_B.button("🔍", key="btn_dong_search"):
            st.session_state.show_dong_search = not st.session_state.show_dong_search
            
        unique_dong = []
        if '지역_동' in df_main.columns:
            if st.session_state.selected_gu:
                unique_dong = sorted(df_main[df_main['지역_구'].isin(st.session_state.selected_gu)]['지역_동'].astype(str).unique().tolist())
            else:
                unique_dong = sorted(df_main['지역_동'].astype(str).unique().tolist())
        
        if st.session_state.show_dong_search:
            dong_term = st.text_input("동 검색", key="dong_search_term", placeholder="예: 역삼동")
            if dong_term:
                unique_dong = [d for d in unique_dong if dong_term in d]

        st.multiselect("지역 (동) 선택", unique_dong, key='selected_dong', placeholder="전체 선택", label_visibility="collapsed")

    st.write("")

    # 4. 수치 필터
    is_sale_mode = "매매" in st.session_state.current_sheet
    with st.expander("💰 상세 금액/면적 설정", expanded=False):
        if is_sale_mode:
            st.caption("🅰️ 매매가 (만원)")
            c1, c2 = st.columns(2)
            c1.number_input("최소", step=1000.0, key='min_price', value=sess('min_price'))
            c2.number_input("최대", step=1000.0, key='max_price', value=sess('max_price'))
            
            st.caption("🅱️ 대지면적 (평)")
            c3, c4 = st.columns(2)
            c3.number_input("최소", step=1.0, key='min_land', value=sess('min_land'))
            c4.number_input("최대", step=1.0, key='max_land', value=sess('max_land'))
        else:
            st.caption("🅰️ 보증금 (만원)")
            c1, c2 = st.columns(2)
            c1.number_input("최소", step=500.0, key='min_dep', value=sess('min_dep'))
            c2.number_input("최대", step=500.0, key='max_dep', value=sess('max_dep'))
            
            st.caption("🅱️ 월세 (만원)")
            c3, c4 = st.columns(2)
            c3.number_input("최소", step=10.0, key='min_rent', value=sess('min_rent'))
            c4.number_input("최대", step=10.0, key='max_rent', value=sess('max_rent'))
            
            st.caption("©️ 권리금 (만원)")
            c7, c8 = st.columns(2)
            c7.number_input("최소", step=100.0, key='min_kwon', value=sess('min_kwon'))
            c8.number_input("최대", step=100.0, key='max_kwon', value=sess('max_kwon'))

        st.divider()
        st.caption("📐 면적 (평)")
        cm1, cm2 = st.columns(2)
        cm1.number_input("최소", step=5.0, key='min_area', value=sess('min_area'))
        cm2.number_input("최대", step=5.0, key='max_area', value=sess('max_area'))

        st.caption("🏢 층수")
        cf1, cf2 = st.columns(2)
        cf1.number_input("최저", step=1.0, key='min_fl', value=sess('min_fl'))
        cf2.number_input("최고", step=1.0, key='max_fl', value=sess('max_fl'))

        st.caption("☑️ 기타")
        st.checkbox("무권리만 보기", key='is_no_kwon')
    
    st.divider()
    if st.button("🔄 조건 초기화"):
        engine.safe_reset()

# ==============================================================================
# [MAIN CONTENT] 리스트 및 액션 (Fragment Isolation)
# ==============================================================================
st.title("🏙️ 범공인 매물장 (Pro)")

@st.fragment
def main_list_view():
    # 1. 필터링 로직
    df_filtered = df_main.copy()

    # Multi-select
    if '구분' in df_filtered.columns and st.session_state.selected_cat:
        df_filtered = df_filtered[df_filtered['구분'].isin(st.session_state.selected_cat)]
    if '지역_구' in df_filtered.columns and st.session_state.selected_gu:
        df_filtered = df_filtered[df_filtered['지역_구'].isin(st.session_state.selected_gu)]
    if '지역_동' in df_filtered.columns and st.session_state.selected_dong:
        df_filtered = df_filtered[df_filtered['지역_동'].isin(st.session_state.selected_dong)]

    # Text
    if '번지' in df_filtered.columns and st.session_state.exact_bunji:
        df_filtered = df_filtered[df_filtered['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]
    
    search_val = st.session_state.search_keyword.strip()
    if search_val:
        search_scope = df_filtered.drop(columns=['선택', 'IronID'], errors='ignore')
        mask = search_scope.fillna("").astype(str).apply(lambda x: ' '.join(x), axis=1).str.contains(search_val, case=False)
        df_filtered = df_filtered[mask]

    # Numeric
    if is_sale_mode:
        if '매매가' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['매매가'] >= st.session_state.min_price) & (df_filtered['매매가'] <= st.session_state.max_price)]
        if '대지면적' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['대지면적'] >= st.session_state.min_land) & (df_filtered['대지면적'] <= st.session_state.max_land)]
    else:
        if '보증금' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['보증금'] >= st.session_state.min_dep) & (df_filtered['보증금'] <= st.session_state.max_dep)]
        if '월차임' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['월차임'] >= st.session_state.min_rent) & (df_filtered['월차임'] <= st.session_state.max_rent)]
        if '권리금' in df_filtered.columns and st.session_state.is_no_kwon:
            df_filtered = df_filtered[df_filtered['권리금'] == 0]
    
    if '면적' in df_filtered.columns:
        df_filtered = df_filtered[(df_filtered['면적'] >= st.session_state.min_area) & (df_filtered['면적'] <= st.session_state.max_area)]
    if '층' in df_filtered.columns:
        df_filtered = df_filtered[(df_filtered['층'] >= st.session_state.min_fl) & (df_filtered['층'] <= st.session_state.max_fl)]

    # --- MASS ACTION ---
    c_sel, c_desel, c_save = st.columns([1, 1, 2])
    
    if c_sel.button("✅ 전체 선택"):
        target_ids = df_filtered['IronID'].tolist()
        st.session_state.df_main.loc[st.session_state.df_main['IronID'].isin(target_ids), '선택'] = True
        st.session_state.editor_key_version += 1
        st.rerun()

    if c_desel.button("⬜ 전체 해제"):
        st.session_state.df_main['선택'] = False
        st.session_state.editor_key_version += 1
        st.rerun()

    if c_save.button("💾 변경사항 저장 (Beta)", type="primary"):
        with st.status("💾 서버에 저장 중...", expanded=True) as status:
            st.warning("⚠️ 리스트 하단의 저장 버튼을 이용해주세요.")

    # --- DATA EDITOR ---
    if len(df_filtered) == 0:
        st.warning("🔍 검색 결과가 없습니다.")
        return

    st.info(f"📋 검색 결과: **{len(df_filtered)}**건")
    
    col_cfg = {
        "선택": st.column_config.CheckboxColumn(width="small"),
        "IronID": None
    }
    format_map = {
        "매매가": "%d", "보증금": "%d", "월차임": "%d", "권리금": "%d",
        "면적": "%.1f", "대지면적": "%.1f", "연면적": "%.1f", "수익률": "%.2f%%"
    }
    for col, fmt in format_map.items():
        if col in df_filtered.columns:
            col_cfg[col] = st.column_config.NumberColumn(col, format=fmt)
    if "내용" in df_filtered.columns: 
        col_cfg["내용"] = st.column_config.TextColumn("특징", width="large")

    editable_cols = ["내용", "보증금", "월차임", "매매가", "권리금", "관리비"]
    disabled_cols = [c for c in df_filtered.columns if c not in ['선택'] + editable_cols]

    editor_key = f"editor_{st.session_state.current_sheet}_{st.session_state.editor_key_version}"
    
    # [DIRECT HEIGHT CONTROL] 컨테이너 없이 에디터 자체 높이 지정 (500px)
    # num_rows="fixed"로 행 추가/삭제 방지 (모바일 오터치 방지)
    edited_df = st.data_editor(
        df_filtered,
        disabled=disabled_cols,
        use_container_width=True,
        hide_index=True,
        column_config=col_cfg,
        key=editor_key,
        height=500, 
        num_rows="fixed"
    )

    # --- ACTION BAR (BOTTOM) ---
    st.divider()
    
    if st.button("💾 수정한 내용 서버에 저장하기", type="primary", use_container_width=True):
        with st.status("💾 저장 중...", expanded=True) as status:
            success, msg, debug_data = engine.save_updates_to_sheet(edited_df, st.session_state.df_main, st.session_state.current_sheet)
            if success:
                status.update(label="저장 완료!", state="complete")
                st.success(msg)
                time.sleep(1.5)
                if 'df_main' in st.session_state: del st.session_state.df_main
                st.cache_data.clear()
                st.rerun()
            else:
                status.update(label="저장 실패", state="error")
                st.error(msg)
                if debug_data: st.write(debug_data)

    st.write("")
    
    selected_rows = edited_df[edited_df['선택'] == True]
    selected_count = len(selected_rows)

    if selected_count > 0:
        st.success(f"✅ {selected_count}건 선택됨")
        
        current_tab = st.session_state.current_sheet
        is_ended = "(종료)" in current_tab
        is_briefing = "브리핑" in current_tab
        base_tab_name = current_tab.replace("(종료)", "").replace("브리핑", "").strip()
        
        ac1, ac2, ac3 = st.columns(3)
        
        # 1. 종료/복구
        with ac1:
            if is_briefing: 
                st.button("🚫", disabled=True, use_container_width=True)
            elif is_ended:
                target_restore = base_tab_name
                if st.button(f"♻️ 복구 ({target_restore})", use_container_width=True):
                    st.session_state.action_status = 'restore_confirm'
            else:
                target_end = f"{base_tab_name}(종료)"
                if st.button(f"🚀 종료 ({target_end})", use_container_width=True):
                    st.session_state.action_status = 'move_confirm'

        # 2. 복사
        with ac2:
            if not is_briefing:
                target_brief = f"{base_tab_name}브리핑"
                if st.button(f"📋 복사 ({target_brief})", use_container_width=True):
                    st.session_state.action_status = 'copy_confirm'
            else:
                st.button("🚫", disabled=True, use_container_width=True)

        # 3. 삭제
        with ac3:
            if st.button("🗑️ 삭제", type="primary", use_container_width=True):
                st.session_state.action_status = 'delete_confirm'

        # --- CONFIRMATION DIALOGUES ---
        if st.session_state.action_status == 'move_confirm':
            target_end = f"{base_tab_name}(종료)"
            with st.status(f"🚀 [종료] {selected_count}건을 이동합니다.", expanded=True) as status:
                if st.button("확인 (이동)"):
                    success, msg, debug = engine.execute_transaction("move", selected_rows, current_tab, target_end)
                    if success:
                        status.update(label="완료", state="complete")
                        st.success(msg)
                        time.sleep(1.0)
                        if 'df_main' in st.session_state: del st.session_state.df_main
                        engine.safe_reset()
                    else: st.error(msg)
        
        elif st.session_state.action_status == 'restore_confirm':
            target_restore = base_tab_name
            with st.status(f"♻️ [복구] {selected_count}건을 되돌립니다.", expanded=True) as status:
                if st.button("확인 (복구)"):
                    success, msg, debug = engine.execute_transaction("restore", selected_rows, current_tab, target_restore)
                    if success:
                        status.update(label="완료", state="complete")
                        st.success(msg)
                        time.sleep(1.0)
                        if 'df_main' in st.session_state: del st.session_state.df_main
                        engine.safe_reset()
                    else: st.error(msg)

        elif st.session_state.action_status == 'copy_confirm':
            target_brief = f"{base_tab_name}브리핑"
            with st.status(f"📋 [복사] {selected_count}건을 추가합니다.", expanded=True) as status:
                if st.button("확인 (복사)"):
                    success, msg, debug = engine.execute_transaction("copy", selected_rows, current_tab, target_brief)
                    if success:
                        status.update(label="완료", state="complete")
                        st.success(msg)
                        time.sleep(1.0)
                        st.session_state.action_status = None
                    else: st.error(msg)

        elif st.session_state.action_status == 'delete_confirm':
            with st.status(f"🗑️ [삭제] {selected_count}건을 영구 삭제합니다.", expanded=True) as status:
                st.error("⚠️ 복구할 수 없습니다.")
                if st.button("확인 (삭제)"):
                    success, msg, debug = engine.execute_transaction("delete", selected_rows, current_tab)
                    if success:
                        status.update(label="완료", state="complete")
                        st.success(msg)
                        time.sleep(1.0)
                        if 'df_main' in st.session_state: del st.session_state.df_main
                        engine.safe_reset()
                    else: st.error(msg)
    else:
        st.caption("👈 목록에서 '선택' 체크박스를 클릭하면 작업 버튼이 나타납니다.")
        st.session_state.action_status = None

# 프래그먼트 실행 (격리)
main_list_view()
