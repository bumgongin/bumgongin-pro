# list_view.py
import streamlit as st
import pandas as pd
import time
import math
import re
import core_engine as engine
import map_service as map_api

def show_main_list():
    df = st.session_state.df_main
    is_sale = "매매" in st.session_state.current_sheet

    # [1] 상세 보기 모드 (4개 탭 구조 완벽 복구)
    if st.session_state.selected_item is not None:
        render_detail_view(st.session_state.selected_item, is_sale)
        return

    # [2] 강력한 필터링 로직 복구
    df_f = df.copy()
    
    # 구/동/항목 멀티셀렉트 필터
    if st.session_state.selected_cat: df_f = df_f[df_f['구분'].isin(st.session_state.selected_cat)]
    if st.session_state.selected_gu: df_f = df_f[df_f['지역_구'].isin(st.session_state.selected_gu)]
    
    # 번지 검색 (사장님 요청: 딱 일치하는 번지만 나오게)
    if st.session_state.exact_bunji:
        df_f = df_f[df_f['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]
    
    # 키워드 통합 검색
    if st.session_state.search_keyword:
        kw = st.session_state.search_keyword
        df_f = df_f[df_f.astype(str).apply(lambda x: x.str.contains(kw, case=False)).any(axis=1)]

    # 금액 및 무권리 로직
    if is_sale:
        df_f = df_f[(df_f['매매가'] >= st.session_state.min_price) & (df_f['매매가'] <= st.session_state.max_price)]
    else:
        df_f = df_f[(df_f['보증금'] >= st.session_state.min_dep) & (df_f['보증금'] <= st.session_state.max_dep)]
        df_f = df_f[(df_f['월차임'] >= st.session_state.min_rent) & (df_f['월차임'] <= st.session_state.max_rent)]
        # [복구] 무권리 필터 (권리금이 0인 것만 추출)
        if st.session_state.is_no_kwon:
            df_f = df_f[df_f['권리금'] == 0]

    # 면적 및 층수 필터 (정규식 정제 포함)
    df_f = df_f[(df_f['면적'] >= st.session_state.min_area) & (df_f['면적'] <= st.session_state.max_area)]
    
    def clean_floor(val):
        match = re.search(r'(-?\d+)', str(val))
        return float(match.group(1)) if match else 1.0

    df_f['floor_val'] = df_f['층'].apply(clean_floor)
    df_f = df_f[(df_f['floor_val'] >= st.session_state.min_fl) & (df_f['floor_val'] <= st.session_state.max_fl)]

    # [3] 출력
    st.info(f"📋 검색 결과: {len(df_f)}건")
    
    if st.session_state.view_mode == '🗂️ 카드 모드':
        for idx, row in df_f.head(30).iterrows():
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
        edited_df = st.data_editor(df_f.drop(columns=['floor_val']), use_container_width=True, hide_index=True, key="main_editor")
        if st.button("💾 변경사항 일괄 저장"):
            success, msg = engine.save_updates_to_sheet(edited_df, df, st.session_state.current_sheet)
            if success: st.success(msg); time.sleep(1); del st.session_state.df_main; st.rerun()

def render_detail_view(item, is_sale):
    if st.button("◀ 목록으로 돌아가기"):
        st.session_state.selected_item = None; st.rerun()
        
    st.subheader(f"🏠 {item.get('건물명')} 상세 정보")
    col1, col2 = st.columns([1.5, 1])
    addr = f"{item.get('지역_구', '')} {item.get('지역_동', '')} {item.get('번지', '')}".strip()
    
    with col1:
        lat, lng = map_api.get_naver_geocode(addr)
        if lat and lng:
            img = map_api.fetch_map_image(lat, lng, height=1024)
            if img: st.image(img, use_container_width=True)
        st.info(f"📍 주소: {addr}")

    with col2:
        # [복구] 사장님의 자부심! 완벽한 4개 탭 구조
        t1, t2, t3, t4 = st.tabs(["📝 기본/주소 수정", "📑 시설 상세", "📁 기타/광고 정보", "💬 브리핑"])
        
        with t1:
            with st.form("edit_basic"):
                c_name = st.text_input("건물명", value=item.get('건물명', ''))
                a1, a2, a3 = st.columns(3)
                n_gu = a1.text_input("지역(구)", value=item.get('지역_구'))
                n_dong = a2.text_input("지역(동)", value=item.get('지역_동'))
                n_bunji = a3.text_input("번지", value=item.get('번지'))
                
                c1, c2 = st.columns(2)
                n_dep = c1.text_input("보증금/매매가", value=str(item.get('보증금', item.get('매매가', 0))))
                n_rent = c2.text_input("월세/수익률", value=str(item.get('월차임', item.get('수익률', 0))))
                
                n_desc = st.text_area("특징", value=item.get('내용', ''), height=150)
                
                if st.form_submit_button("💾 정보 저장"):
                    item.update({'건물명': c_name, '지역_구': n_gu, '지역_동': n_dong, '번지': n_bunji, '내용': n_desc})
                    # 무권리 로직: 무권리 체크시 권리금 0 강제 업데이트 포함
                    if not is_sale and st.session_state.is_no_kwon: item['권리금'] = 0
                    
                    success, msg = engine.update_single_row(item, st.session_state.current_sheet)
                    if success: st.success(msg); time.sleep(1); del st.session_state.df_main; st.session_state.selected_item=None; st.rerun()

        with t2:
            st.caption("🏢 시설 세부 정보")
            with st.form("edit_facility"):
                cols = ['호실', '현업종', '층고', '주차', 'E/V', '화장실']
                f_data = {}
                for col in cols: f_data[col] = st.text_input(col, value=str(item.get(col, '')))
                if st.form_submit_button("💾 시설 정보 저장"):
                    item.update(f_data)
                    success, msg = engine.update_single_row(item, st.session_state.current_sheet)
                    if success: st.success(msg); time.sleep(1); del st.session_state.df_main; st.rerun()

        with t3:
            st.caption("📁 기타 및 광고 진행 상황")
            # 시트의 나머지 모든 컬럼을 자동으로 표시
            others = [c for c in item.index if c not in ['IronID', '선택', '건물명', '내용', '비고']]
            for col in others[:10]: st.write(f"**{col}**: {item[col]}")

        with t4:
            brief = f"[범공인 매물 브리핑]\n📍 위치: {addr}\n🏢 매물: {item.get('건물명')}\n📝 특징: {item.get('내용')}"
            st.code(brief, language=None)
