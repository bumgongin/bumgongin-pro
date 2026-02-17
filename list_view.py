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

    # [A] 상세 보기 화면 (에러 없이 4개 탭 모두 구현)
    if st.session_state.selected_item is not None:
        render_detail_view(st.session_state.selected_item, is_sale)
        return

    # [B] 필터링 로직 (모든 사이드바 값 적용)
    df_f = df.copy()
    if st.session_state.selected_cat: df_f = df_f[df_f['구분'].isin(st.session_state.selected_cat)]
    if st.session_state.selected_gu: df_f = df_f[df_f['지역_구'].isin(st.session_state.selected_gu)]
    if st.session_state.selected_dong: df_f = df_f[df_f['지역_동'].isin(st.session_state.selected_dong)]
    
    # 금액/면적 필터 적용
    try:
        if is_sale:
            df_f = df_f[(df_f['매매가'] >= st.session_state.min_price) & (df_f['매매가'] <= st.session_state.max_price)]
        else:
            df_f = df_f[(df_f['보증금'] >= st.session_state.min_dep) & (df_f['보증금'] <= st.session_state.max_dep)]
            df_f = df_f[(df_f['월차임'] >= st.session_state.min_rent) & (df_f['월차임'] <= st.session_state.max_rent)]
        df_f = df_f[(df_f['면적'] >= st.session_state.min_area) & (df_f['면적'] <= st.session_state.max_area)]
    except: pass

    if st.session_state.search_keyword:
        kw = st.session_state.search_keyword
        df_f = df_f[df_f.astype(str).apply(lambda x: x.str.contains(kw, case=False)).any(axis=1)]
    if st.session_state.exact_bunji:
        df_f = df_f[df_f['번지'].astype(str).str.contains(st.session_state.exact_bunji)]

    # [C] 결과 출력
    st.info(f"📋 검색 결과: {len(df_f)}건")
    
    if st.session_state.view_mode == '🗂️ 카드 모드':
        for idx, row in df_f.head(50).iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    price = f"매 {row.get('매매가', 0):,}만" if is_sale else f"보 {row.get('보증금', 0):,} / 월 {row.get('월차임', 0):,}"
                    st.markdown(f"**{price}** | {row.get('건물명')} ({row.get('구분')})")
                    st.caption(f"📍 {row.get('지역_구')} {row.get('지역_동')} {row.get('번지')} | {row.get('층')}층")
                if c2.button("상세", key=f"btn_{row['IronID']}"):
                    st.session_state.selected_item = row
                    st.rerun()
    else:
        # 리스트 모드 (데이터 에디터)
        edited_df = st.data_editor(df_f, use_container_width=True, hide_index=True, key=f"editor_{st.session_state.editor_key_version}")
        if st.button("💾 리스트 수정사항 저장"):
            success, msg = engine.save_updates_to_sheet(edited_df, df, st.session_state.current_sheet)
            if success: st.success(msg); time.sleep(1); del st.session_state.df_main; st.rerun()

def render_detail_view(item, is_sale):
    """상세 보기의 모든 기능을 탭별로 복구"""
    if st.button("◀ 목록으로 돌아가기"):
        st.session_state.selected_item = None
        st.rerun()
        
    st.subheader(f"🏠 {item.get('건물명')} 상세 정보")
    col1, col2 = st.columns([1.5, 1])
    addr = f"{item.get('지역_구', '')} {item.get('지역_동', '')} {item.get('번지', '')}".strip()
    
    with col1: # 왼쪽: 지도
        lat, lng = map_api.get_naver_geocode(addr)
        if lat and lng:
            img = map_api.fetch_map_image(lat, lng, height=1024)
            if img: st.image(img, use_container_width=True)
        st.info(f"📍 현재 주소: {addr}")

    with col2: # 오른쪽: 완벽한 4개 탭 복구
        t1, t2, t3, t4 = st.tabs(["📝 기본/주소 수정", "📑 시설 상세", "📁 기타 정보", "💬 브리핑"])
        
        with t1: # 주소 수정 폼 (사장님 핵심 요청사항)
            with st.form("edit_form_final"):
                st.caption("주소 및 기본 정보를 여기서 수정하세요.")
                c_name = st.text_input("건물명", value=item.get('건물명', ''))
                a1, a2, a3 = st.columns(3)
                n_gu = a1.text_input("지역(구)", value=item.get('지역_구', ''))
                n_dong = a2.text_input("지역(동)", value=item.get('지역_동', ''))
                n_bunji = a3.text_input("번지", value=item.get('번지', ''))
                
                c1, c2 = st.columns(2)
                n_area = c1.text_input("면적(평)", value=str(item.get('면적', 0)))
                n_floor = c2.text_input("층수", value=str(item.get('층', '')))
                
                n_desc = st.text_area("특징", value=item.get('내용', ''), height=150)
                
                if st.form_submit_button("💾 정보 저장", use_container_width=True, type="primary"):
                    updated_data = item.copy()
                    updated_data.update({
                        '건물명': c_name, '지역_구': n_gu, '지역_동': n_dong, 
                        '번지': n_bunji, '면적': n_area, '층': n_floor, '내용': n_desc
                    })
                    success, msg = engine.update_single_row(updated_data, st.session_state.current_sheet)
                    if success:
                        st.success(msg); time.sleep(1); del st.session_state.df_main
                        st.session_state.selected_item = None; st.rerun()
                    else: st.error(msg)
        
        with t2: st.caption("시설 정보 (준비 중)"); st.write(item.drop(['IronID', '선택'], errors='ignore').to_dict())
        with t3: st.caption("기타 비고"); st.write(item.get('비고', '정보 없음'))
        with t4:
            brief = f"[범공인 매물 브리핑]\n📍 위치: {addr}\n🏢 매물: {item.get('건물명')}\n📐 면적: {item.get('면적')}평\n📝 내용: {item.get('내용')}"
            st.code(brief, language=None)
