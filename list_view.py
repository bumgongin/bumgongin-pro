# list_view.py - 매물 목록 및 상세 수정 로직
import streamlit as st
import pandas as pd
import time
import math
import core_engine as engine
import map_service as map_api

def show_main_list():
    if 'df_main' not in st.session_state: return
    df = st.session_state.df_main
    is_sale = "매매" in st.session_state.current_sheet

    # [1] 상세 보기 화면 (Detail View)
    if st.session_state.selected_item is not None:
        render_detail_view(st.session_state.selected_item, is_sale)
        return

    # [2] 데이터 필터링 로직
    df_f = df.copy()
    if st.session_state.selected_cat: df_f = df_f[df_f['구분'].isin(st.session_state.selected_cat)]
    if st.session_state.selected_gu: df_f = df_f[df_f['지역_구'].isin(st.session_state.selected_gu)]
    if st.session_state.selected_dong: df_f = df_f[df_f['지역_동'].isin(st.session_state.selected_dong)]
    if st.session_state.search_keyword:
        kw = st.session_state.search_keyword
        df_f = df_f[df_f.astype(str).apply(lambda x: x.str.contains(kw, case=False)).any(axis=1)]
    if st.session_state.exact_bunji:
        df_f = df_f[df_f['번지'].astype(str).str.contains(st.session_state.exact_bunji)]

    # [3] 페이지네이션
    ITEMS_PER_PAGE = 30
    total_count = len(df_f)
    total_pages = math.ceil(total_count / ITEMS_PER_PAGE)
    
    st.info(f"📋 총 {total_count}건 검색됨 (페이지: {total_pages})")
    page = st.number_input("페이지 선택", min_value=1, max_value=max(1, total_pages), value=1)
    df_page = df_f.iloc[(page-1)*ITEMS_PER_PAGE : page*ITEMS_PER_PAGE]

    # [4] 보기 모드 분기
    if st.session_state.view_mode == '🗂️ 카드 모드':
        for idx, row in df_page.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**[{row.get('구분')}] {row.get('건물명', '이름없음')}**")
                    st.caption(f"📍 {row.get('지역_구')} {row.get('지역_동')} {row.get('번지')} | {row.get('층')}층")
                if c2.button("상세", key=f"btn_{row['IronID']}"):
                    st.session_state.selected_item = row
                    st.rerun()
    else:
        # 리스트 모드 (데이터 에디터)
        edited_df = st.data_editor(df_page, use_container_width=True, hide_index=True, key="main_editor")
        if st.button("💾 리스트 수정사항 저장", type="primary"):
            success, msg = engine.save_updates_to_sheet(edited_df, df, st.session_state.current_sheet)
            if success:
                st.success(msg); time.sleep(1); del st.session_state.df_main; st.rerun()

def render_detail_view(item, is_sale):
    if st.button("◀ 목록으로"):
        st.session_state.selected_item = None
        st.rerun()
        
    st.subheader(f"🏠 {item.get('건물명', '매물 상세')} 정보")
    col1, col2 = st.columns([1.5, 1])
    addr = f"{item.get('지역_구', '')} {item.get('지역_동', '')} {item.get('번지', '')}".strip()
    
    with col1: # 지도 영역
        lat, lng = map_api.get_naver_geocode(addr)
        if lat and lng:
            img = map_api.fetch_map_image(lat, lng, height=1024)
            if img: st.image(img, use_container_width=True)
        st.success(f"📍 주소: {addr}")

    with col2: # 수정 탭 영역
        t1, t2, t3, t4 = st.tabs(["📝 기본/주소", "📑 시설 상세", "📁 기타 정보", "💬 브리핑"])
        
        with t1: # 사장님이 요청하신 주소 수정 폼
            with st.form("edit_form_final"):
                new_name = st.text_input("건물명", value=item.get('건물명', ''))
                a1, a2, a3 = st.columns(3)
                new_gu = a1.text_input("지역(구)", value=item.get('지역_구', ''))
                new_dong = a2.text_input("지역(동)", value=item.get('지역_동', ''))
                new_bunji = a3.text_input("번지", value=item.get('번지', ''))
                new_desc = st.text_area("특징", value=item.get('내용', ''), height=150)
                
                if st.form_submit_button("💾 정보 업데이트", use_container_width=True, type="primary"):
                    updated_data = item.copy()
                    updated_data.update({
                        '건물명': new_name, '지역_구': new_gu, '지역_동': new_dong, 
                        '번지': new_bunji, '내용': new_desc
                    })
                    success, msg = engine.update_single_row(updated_data, st.session_state.current_sheet)
                    if success:
                        st.success(msg); time.sleep(1); del st.session_state.df_main
                        st.session_state.selected_item = None; st.rerun()
                    else: st.error(msg)
        
        with t4:
            brief = f"[매물 브리핑]\n📍 위치: {addr}\n🏢 매물명: {item.get('건물명')}\n📝 내용: {item.get('내용')}"
            st.code(brief, language=None)
