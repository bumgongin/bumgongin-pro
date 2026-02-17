# list_view.py
import streamlit as st
import pandas as pd
import time
import math
import re
import core_engine as engine
import map_service as map_api

def show_main_list():
    if 'df_main' not in st.session_state: return
    df = st.session_state.df_main
    is_sale = "매매" in st.session_state.current_sheet

    # [1] 상세 보기 화면
    if st.session_state.selected_item is not None:
        render_detail_view(st.session_state.selected_item, is_sale)
        return

    # [2] 통합 필터링 로직 (누락 기능 복구)
    df_f = df.copy()
    
    # 지역/구분 필터
    if st.session_state.selected_cat: df_f = df_f[df_f['구분'].isin(st.session_state.selected_cat)]
    if st.session_state.selected_gu: df_f = df_f[df_f['지역_구'].isin(st.session_state.selected_gu)]
    if st.session_state.selected_dong: df_f = df_f[df_f['지역_동'].isin(st.session_state.selected_dong)]
    
    # 금액/면적 필터 (복구된 핵심 로직)
    try:
        if is_sale:
            df_f = df_f[(df_f['매매가'] >= st.session_state.min_price) & (df_f['매매가'] <= st.session_state.max_price)]
        else:
            df_f = df_f[(df_f['보증금'] >= st.session_state.min_dep) & (df_f['보증금'] <= st.session_state.max_dep)]
            df_f = df_f[(df_f['월차임'] >= st.session_state.min_rent) & (df_f['월차임'] <= st.session_state.max_rent)]
        df_f = df_f[(df_f['면적'] >= st.session_state.min_area) & (df_f['면적'] <= st.session_state.max_area)]
    except: pass # 컬럼이 없는 시트 대비

    # 검색어 필터
    if st.session_state.search_keyword:
        kw = st.session_state.search_keyword
        df_f = df_f[df_f.astype(str).apply(lambda x: x.str.contains(kw, case=False)).any(axis=1)]
    if st.session_state.exact_bunji:
        df_f = df_f[df_f['번지'].astype(str).str.contains(st.session_state.exact_bunji)]

    # [3] 출력 및 페이지네이션
    st.info(f"📋 검색 결과: {len(df_f)}건")
    
    if st.session_state.view_mode == '🗂️ 카드 모드':
        # 카드 출력 (상단 50건만)
        for idx, row in df_f.head(50).iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    price_txt = f"매 {row.get('매매가', 0):,}만" if is_sale else f"보 {row.get('보증금', 0):,} / 월 {row.get('월차임', 0):,}"
                    st.markdown(f"**{price_txt}** | {row.get('건물명')} ({row.get('구분')})")
                    st.caption(f"📍 {row.get('지역_구')} {row.get('지역_동')} {row.get('번지')} | {row.get('면적')}평")
                if c2.button("상세", key=f"btn_{row['IronID']}"):
                    st.session_state.selected_item = row
                    st.rerun()
    else:
        # 리스트 모드
        edited_df = st.data_editor(df_f, use_container_width=True, hide_index=True, key="main_editor_v2")
        if st.button("💾 리스트 수정사항 저장", type="primary"):
            success, msg = engine.save_updates_to_sheet(edited_df, df, st.session_state.current_sheet)
            if success: st.success(msg); time.sleep(1); del st.session_state.df_main; st.rerun()

def render_detail_view(item, is_sale):
    if st.button("◀ 목록으로"):
        st.session_state.selected_item = None
        st.rerun()
        
    st.subheader(f"🏠 {item.get('건물명', '매물 상세')} 정보")
    col1, col2 = st.columns([1.5, 1])
    addr = f"{item.get('지역_구', '')} {item.get('지역_동', '')} {item.get('번지', '')}".strip()
    
    with col1:
        lat, lng = map_api.get_naver_geocode(addr)
        if lat and lng:
            img = map_api.fetch_map_image(lat, lng, height=1024)
            if img: st.image(img, use_container_width=True)
        st.success(f"📍 주소: {addr}")

    with col2:
        t1, t2, t3, t4 = st.tabs(["📝 기본/주소", "📑 시설 상세", "📁 기타 정보", "💬 브리핑"])
        
        with t1:
            with st.form("edit_form_final"):
                new_name = st.text_input("건물명", value=item.get('건물명', ''))
                a1, a2, a3 = st.columns(3)
                new_gu = a1.text_input("지역(구)", value=item.get('지역_구', ''))
                new_dong = a2.text_input("지역(동)", value=item.get('지역_동', ''))
                new_bunji = a3.text_input("번지", value=item.get('번지', ''))
                
                c1, c2 = st.columns(2)
                new_area = c1.text_input("면적(평)", value=str(item.get('면적', 0)))
                new_floor = c2.text_input("층수", value=str(item.get('층', '')))
                
                new_desc = st.text_area("특징/내용", value=item.get('내용', ''), height=100)
                
                if st.form_submit_button("💾 정보 업데이트", type="primary", use_container_width=True):
                    updated_data = item.copy()
                    updated_data.update({
                        '건물명': new_name, '지역_구': new_gu, '지역_동': new_dong, 
                        '번지': new_bunji, '면적': new_area, '층': new_floor, '내용': new_desc
                    })
                    success, msg = engine.update_single_row(updated_data, st.session_state.current_sheet)
                    if success:
                        st.success(msg); time.sleep(1); del st.session_state.df_main
                        st.session_state.selected_item = None; st.rerun()
                    else: st.error(msg)
        
        with t2:
            st.info("시설 정보는 구글 시트에서 직접 관리하거나 향후 업데이트 예정입니다.")
        
        with t4:
            brief = f"[범공인 매물]\n📍 위치: {addr}\n🏢 매물명: {item.get('건물명')}\n📐 면적: {item.get('면적')}평\n📝 내용: {item.get('내용')}"
            st.code(brief, language=None)
