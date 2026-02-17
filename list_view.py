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

    # [1] 상세 보기 모드 (사장님 요청 4개 탭 정밀 구성)
    if st.session_state.selected_item is not None:
        render_detail_view(st.session_state.selected_item, is_sale)
        return

    # [2] 필터링 로직 (무권리 충돌 방지 포함)
    df_f = df.copy()
    if st.session_state.selected_cat: df_f = df_f[df_f['구분'].isin(st.session_state.selected_cat)]
    if st.session_state.selected_gu: df_f = df_f[df_f['지역_구'].isin(st.session_state.selected_gu)]
    if st.session_state.selected_dong: df_f = df_f[df_f['지역_동'].isin(st.session_state.selected_dong)]
    if st.session_state.exact_bunji: df_f = df_f[df_f['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]
    if st.session_state.search_keyword:
        kw = st.session_state.search_keyword
        df_f = df_f[df_f.astype(str).apply(lambda x: x.str.contains(kw, case=False)).any(axis=1)]

    # 금액 및 층수 필터
    if is_sale:
        df_f = df_f[(df_f['매매가'] >= st.session_state.min_price) & (df_f['매매가'] <= st.session_state.max_price)]
    else:
        df_f = df_f[(df_f['보증금'] >= st.session_state.min_dep) & (df_f['보증금'] <= st.session_state.max_dep)]
        df_f = df_f[(df_f['월차임'] >= st.session_state.min_rent) & (df_f['월차임'] <= st.session_state.max_rent)]
        if st.session_state.is_no_kwon: df_f = df_f[df_f['권리금'] == 0]
        else: df_f = df_f[(df_f['권리금'] >= st.session_state.min_kwon) & (df_f['권리금'] <= st.session_state.max_kwon)]
    
    df_f = df_f[(df_f['면적'] >= st.session_state.min_area) & (df_f['면적'] <= st.session_state.max_area)]
    # 층수 필터 (음수 보존)
    df_f['floor_val'] = df_f['층'].astype(str).str.extract(r'(-?\d+)')[0].fillna(1).astype(float)
    df_f = df_f[(df_f['floor_val'] >= st.session_state.min_fl) & (df_f['floor_val'] <= st.session_state.max_fl)]

    # [3] 버튼: 전체 선택/해제
    c_sel1, c_sel2 = st.columns(2)
    if c_sel1.button("✅ 목록 전체 선택"):
        st.session_state.df_main.loc[df_f.index, '선택'] = True
        st.rerun()
    if c_sel2.button("⬜ 목록 전체 해제"):
        st.session_state.df_main['선택'] = False
        st.rerun()

    # [4] 화면 출력
    if st.session_state.view_mode == '🗂️ 카드 모드':
        for idx, row in df_f.iterrows():
            with st.container(border=True):
                col_chk, col_txt, col_btn = st.columns([1, 10, 2])
                # 체크박스 상태 유지
                new_chk = col_chk.checkbox("", key=f"chk_{row['IronID']}", value=row['선택'])
                if new_chk != row['선택']:
                    st.session_state.df_main.loc[st.session_state.df_main['IronID'] == row['IronID'], '선택'] = new_chk
                    st.rerun()
                col_txt.markdown(f"**{row.get('건물명')}** ({row.get('구분')}) | {row.get('지역_구')} {row.get('지역_동')} {row.get('번지')}")
                if col_btn.button("상세보기", key=f"btn_{row['IronID']}"):
                    st.session_state.selected_item = row
                    st.rerun()
    else:
        # 리스트 모드 (데이터 순서 및 고정 복구)
        df_display = df_f.drop(columns=['floor_val'])
        edited_df = st.data_editor(df_display, use_container_width=True, hide_index=True, num_rows="fixed", key=f"editor_{st.session_state.editor_key_version}")
        
        # 리스트 모드 상세보기 버튼 (첫 번째 컬럼에 배치하거나 별도 버튼 활용)
        if st.button("💾 위 수정사항 시트에 저장"):
            success, msg = engine.save_updates_to_sheet(edited_df, df, st.session_state.current_sheet)
            if success: st.success(msg); time.sleep(1); del st.session_state.df_main; st.rerun()

    # [5] 하단 액션바 (이동/복사/삭제 완벽 복구)
    render_action_bar(st.session_state.df_main[st.session_state.df_main['선택']==True])

def render_detail_view(item, is_sale):
    if st.button("◀ 목록으로"): st.session_state.selected_item = None; st.rerun()
    st.subheader(f"🏠 {item.get('건물명')} 상세 정보")
    
    col1, col2 = st.columns([1.5, 1])
    with col1:
        addr = f"{item.get('지역_구')} {item.get('지역_동')} {item.get('번지')}"
        lat, lng = map_api.get_naver_geocode(addr)
        if lat and lng:
            img = map_api.fetch_map_image(lat, lng, height=1024)
            if img: st.image(img, use_container_width=True)
        st.info(f"📍 주소: {addr}")

    with col2:
        # [복구] 사장님이 요청하신 4개 탭 및 정밀 항목
        t1, t2, t3, t4 = st.tabs(["📝 기본/주소", "📑 시설 상세", "📁 접수/광고", "💬 브리핑"])
        
        with t1: # 탭1: 기본 정보 (요청 항목 12개)
            with st.form("f_basic"):
                f1_cols = ['구분', '지역_구', '지역_동', '번지', '층', '호실', '보증금', '월차임', '관리비', '권리금', '면적', '연락처']
                updates = {}
                for c in f1_cols: updates[c] = st.text_input(c, value=str(item.get(c, '')))
                if st.form_submit_button("💾 기본정보 저장"):
                    item.update(updates)
                    success, msg = engine.update_single_row(item, st.session_state.current_sheet)
                    if success: st.success(msg); time.sleep(1); del st.session_state.df_main; st.session_state.selected_item=None; st.rerun()

        with t2: # 탭2: 시설 상세 (요청 항목 7개)
            with st.form("f_facility"):
                f2_cols = ['현업종', '주차', '화장실', 'E/V', '층고', '특이사항', '내용']
                updates2 = {}
                for c in f2_cols: updates2[c] = st.text_area(c, value=str(item.get(c, ''))) if c in ['특이사항', '내용'] else st.text_input(c, value=str(item.get(c, '')))
                if st.form_submit_button("💾 시설정보 저장"):
                    item.update(updates2)
                    engine.update_single_row(item, st.session_state.current_sheet)
                    st.success("저장 완료"); time.sleep(1); del st.session_state.df_main; st.rerun()

        with t3: # 탭3: 접수/광고 (요청 항목 8개)
            f3_cols = ['접수경로', '접수일', '사진', '광고_포스', '광고_모두', '광고_블로그', '사용승인일', '건축물용도']
            for c in f3_cols: st.write(f"**{c}**: {item.get(c, '')}")

        with t4: # 탭4: 카톡 브리핑 (기존 유지)
            brief = f"[범공인 매물]\n📍 위치: {addr}\n🏢 건물: {item.get('건물명')}\n💰 조건: 보 {item.get('보증금')} / 월 {item.get('월차임')}\n📝 내용: {item.get('내용')}"
            st.code(brief, language=None)

def render_action_bar(selected_rows):
    if selected_rows.empty: return
    st.divider()
    st.success(f"✅ {len(selected_rows)}건 선택됨")
    cur = st.session_state.current_sheet
    c1, c2, c3 = st.columns(3)
    
    # 이동/복사/삭제 로직 (임대/매매 자동 대응)
    base = "임대" if "임대" in cur else "매매"
    target_end = f"{base}(종료)"
    target_brief = f"{base}브리핑"

    if "종료" not in cur and "브리핑" not in cur:
        if c1.button(f"🚩 {base} 종료 처리"):
            engine.execute_transaction("move", selected_rows, cur, target_end)
            st.rerun()
        if c2.button(f"🚀 {base} 브리핑 복사"):
            engine.execute_transaction("copy", selected_rows, cur, target_brief)
            st.rerun()
    elif "종료" in cur:
        if c1.button(f"♻️ {base} 목록 복구"):
            engine.execute_transaction("restore", selected_rows, cur, base)
            st.rerun()
    
    if c3.button("🗑️ 영구 삭제", type="primary"):
        engine.execute_transaction("delete", selected_rows, cur)
        st.rerun()
