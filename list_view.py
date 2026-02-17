# list_view.py
import streamlit as st
import pandas as pd
import time
import math
import re
import core_engine as engine
import map_service as map_api

def show_main_list():
    if 'df_main' not in st.session_state or st.session_state.df_main is None:
        st.warning("데이터가 로드되지 않았습니다. 시트를 선택해 주세요.")
        return

    df_main = st.session_state.df_main
    is_sale_mode = "매매" in st.session_state.current_sheet

    # ==========================================
    # [A] 상세 보기 모드 (Detail View)
    # ==========================================
    if st.session_state.selected_item is not None:
        item = st.session_state.selected_item
        current_id = item.get('IronID')
        
        c_back, c_title = st.columns([1, 5])
        if c_back.button("◀ 목록으로"):
            st.session_state.selected_item = None
            st.rerun()
        
        c_title.markdown(f"### {item.get('건물명', '매물 상세')}")

        addr_full = f"{item.get('지역_구', '')} {item.get('지역_동', '')} {item.get('번지', '')}"
        col_left, col_right = st.columns([1.5, 1])

        with col_left:
            lat, lng = map_api.get_naver_geocode(addr_full)
            if lat and lng:
                is_pc = st.session_state.get('view_mode') == '🗂️ 카드 모드'
                map_img = map_api.fetch_map_image(lat, lng, height=1024 if is_pc else 700)
                if map_img: st.image(map_img, use_container_width=True)
            st.info(f"📍 주소: {addr_full}")

        with col_right:
            tab1, tab2 = st.tabs(["📝 정보 수정", "💬 브리핑 문구"])
            with tab1:
                with st.form("edit_form"):
                    new_name = st.text_input("건물명", value=item.get('건물명', ''))
                    a1, a2, a3 = st.columns(3)
                    new_gu = a1.text_input("지역(구)", value=item.get('지역_구', ''))
                    new_dong = a2.text_input("지역(동)", value=item.get('지역_동', ''))
                    new_bunji = a3.text_input("번지", value=item.get('번지', ''))
                    
                    new_desc = st.text_area("특징/내용", value=item.get('내용', ''), height=150)
                    
                    if st.form_submit_button("💾 시트에 즉시 저장", type="primary", use_container_width=True):
                        updated_data = item.copy()
                        updated_data.update({'건물명': new_name, '지역_구': new_gu, '지역_동': new_dong, '번지': new_bunji, '내용': new_desc})
                        success, msg = engine.update_single_row(updated_data, st.session_state.current_sheet)
                        if success:
                            st.success(msg); time.sleep(1); del st.session_state.df_main; st.session_state.selected_item = None; st.rerun()
        return

    # ==========================================
    # [B] 목록 보기 모드 (List View)
    # ==========================================
    # 검색 필터링 로직
    df_filtered = df_main.copy()
    if st.session_state.search_keyword:
        mask = df_filtered.astype(str).apply(lambda x: x.str.contains(st.session_state.search_keyword, case=False)).any(axis=1)
        df_filtered = df_filtered[mask]
    
    st.subheader(f"📋 매물 목록 ({len(df_filtered)}건)")
    
    # 카드 모드 출력
    for idx, row in df_filtered.head(20).iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**[{row.get('구분', '매물')}] {row.get('건물명', '이름없음')}**")
            c1.caption(f"📍 {row.get('지역_구', '')} {row.get('지역_동', '')} {row.get('번지', '')}")
            if c2.button("상세보기", key=f"btn_{row['IronID']}"):
                st.session_state.selected_item = row
                st.rerun()
