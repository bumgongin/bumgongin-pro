# list_view.py
import streamlit as st
import pandas as pd
import time
import math
import re
import core_engine as engine
import map_service as map_api

def show_main_list():
    df_main = st.session_state.df_main
    is_sale_mode = "매매" in st.session_state.current_sheet

    # [1] 상세 보기 화면 (Detail View)
    if st.session_state.selected_item is not None:
        item = st.session_state.selected_item
        current_id = item.get('IronID')
        
        if st.session_state.last_analyzed_id != current_id:
            st.session_state.infra_res_c = None
            st.session_state.last_analyzed_id = current_id

        c_back, c_title = st.columns([1, 5])
        if c_back.button("◀ 목록으로"): st.session_state.selected_item = None; st.rerun()
        c_title.markdown(f"### {item.get('건물명', '매물 상세')}")

        addr_full = f"{item.get('지역_구', '')} {item.get('지역_동', '')} {item.get('번지', '')}"
        col_left, col_right = st.columns([1.5, 1])

        with col_left:
            st.caption(f"📍 {addr_full}")
            lat, lng = map_api.get_naver_geocode(addr_full)
            if lat and lng:
                is_pc = st.session_state.get('view_mode') == '🗂️ 카드 모드'
                map_h = 1024 if is_pc else 700 
                map_img = map_api.fetch_map_image(lat, lng, zoom_level=st.session_state.zoom_level, height=map_h)
                if map_img: st.image(map_img, use_container_width=True)
                st.link_button("📍 네이버 지도에서 확인", f"https://map.naver.com/v5/search/{addr_full}", use_container_width=True)

        with col_right:
            tab1, tab2, tab3, tab4 = st.tabs(["📝 기본 수정", "📑 상세(1)", "📁 상세(2)", "💬 카톡 문구"])
            
            with tab1: # 구/동/번지 통합 수정 폼
                with st.form("edit_form_basic"):
                    c1, c2 = st.columns(2)
                    new_cat = c1.text_input("**구분**", value=item.get('구분', ''))
                    new_name = c2.text_input("**건물명**", value=item.get('건물명', ''))
                    
                    st.divider()
                    st.caption("📍 위치 정보 수정")
                    a1, a2, a3 = st.columns(3)
                    new_gu = a1.text_input("**지역(구)**", value=item.get('지역_구', ''))
                    new_dong = a2.text_input("**지역(동)**", value=item.get('지역_동', ''))
                    new_bunji = a3.text_input("**번지**", value=item.get('번지', ''))
                    st.divider()
                    
                    # 금액/면적 로직
                    c3, c4 = st.columns(2)
                    if is_sale_mode:
                        new_val1 = c3.text_input("**매매가**", value=str(item.get('매매가', 0)))
                        new_val2 = c4.text_input("**수익률**", value=str(item.get('수익률', 0)))
                    else:
                        new_val1 = c3.text_input("**보증금**", value=str(item.get('보증금', 0)))
                        new_val2 = c4.text_input("**월세**", value=str(item.get('월차임', 0)))

                    new_area = st.text_input("**전용면적**", value=str(item.get('면적', 0)))
                    new_floor = st.text_input("**층수**", value=str(item.get('층', '')))
                    new_desc = st.text_area("**특징**", value=item.get('내용', ''), height=100)
                    
                    if st.form_submit_button("💾 정보 업데이트", type="primary", use_container_width=True):
                        updated_data = item.copy()
                        updated_data.update({
                            '구분': new_cat, '건물명': new_name, '지역_구': new_gu, 
                            '지역_동': new_dong, '번지': new_bunji, '면적': new_area, '층': new_floor, '내용': new_desc
                        })
                        if is_sale_mode: updated_data.update({'매매가': new_val1, '수익률': new_val2})
                        else: updated_data.update({'보증금': new_val1, '월차임': new_val2})
                        
                        success, msg = engine.update_single_row(updated_data, st.session_state.current_sheet)
                        if success:
                            st.success(msg); time.sleep(1); del st.session_state.df_main; st.session_state.selected_item = None; st.rerun()
        return

    # [2] 목록 보기 화면 (기존 로직 이관)
    st.info(f"📋 총 {len(df_main)}건의 매물이 로드되었습니다.")
    # (여기에 카드 모드/리스트 모드 로직이 들어갑니다)
