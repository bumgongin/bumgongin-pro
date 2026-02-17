# list_view.py
# 범공인 Pro v24 Enterprise - List View Module (v24.90 Restored)
# Feature: Pagination, Smart Editor, Batch Actions, 4-Tab Detail

import streamlit as st
import pandas as pd
import math
import time
import core_engine as engine
import map_service as map_api

ITEMS_PER_PAGE = 30

def show_main_list():
    """메인 리스트 및 상세 페이지 렌더링 컨트롤러"""
    
    # [A] 상세 보기 모드 진입 확인
    if st.session_state.selected_item is not None:
        render_detail_view(st.session_state.selected_item)
        return

    # [B] 필터링 로직 (app.py의 상태 변수 활용)
    df = st.session_state.df_main
    df_f = df.copy()

    # 1. 항목/지역 필터
    if st.session_state.selected_cat:
        df_f = df_f[df_f['구분'].isin(st.session_state.selected_cat)]
    if st.session_state.selected_gu:
        df_f = df_f[df_f['지역_구'].isin(st.session_state.selected_gu)]
    if st.session_state.selected_dong:
        df_f = df_f[df_f['지역_동'].isin(st.session_state.selected_dong)]
    
    # 2. 검색 필터
    if st.session_state.exact_bunji:
        df_f = df_f[df_f['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]
    if st.session_state.search_keyword:
        kw = st.session_state.search_keyword
        # 모든 컬럼을 문자열로 변환 후 검색
        mask = df_f.astype(str).apply(lambda x: x.str.contains(kw, case=False)).any(axis=1)
        df_f = df_f[mask]

    # 3. 금액/면적 필터 (매매/임대 분기)
    is_sale = "매매" in st.session_state.current_sheet
    if is_sale:
        # 값이 비어있지 않은 경우에만 필터 적용 (0은 제외)
        if st.session_state.min_price: df_f = df_f[df_f['매매가'] >= st.session_state.min_price]
        if st.session_state.max_price < 10000000.0: df_f = df_f[df_f['매매가'] <= st.session_state.max_price]
    else:
        if st.session_state.min_dep: df_f = df_f[df_f['보증금'] >= st.session_state.min_dep]
        if st.session_state.max_dep < 10000000.0: df_f = df_f[df_f['보증금'] <= st.session_state.max_dep]
        
        if st.session_state.min_rent: df_f = df_f[df_f['월차임'] >= st.session_state.min_rent]
        if st.session_state.max_rent < 100000.0: df_f = df_f[df_f['월차임'] <= st.session_state.max_rent]
        
        # 권리금 필터
        if st.session_state.is_no_kwon:
            df_f = df_f[df_f['권리금'] == 0]
        else:
            if st.session_state.min_kwon: df_f = df_f[df_f['권리금'] >= st.session_state.min_kwon]
            if st.session_state.max_kwon < 1000000.0: df_f = df_f[df_f['권리금'] <= st.session_state.max_kwon]

    # 4. 공통 필터 (면적/층)
    if st.session_state.min_area: df_f = df_f[df_f['면적'] >= st.session_state.min_area]
    if st.session_state.max_area < 100000.0: df_f = df_f[df_f['면적'] <= st.session_state.max_area]
    
    # 층수 정제 및 필터
    if '층' in df_f.columns:
        df_f['floor_val'] = df_f['층'].astype(str).str.extract(r'(-?\d+)')[0].fillna(1).astype(float)
        if st.session_state.min_fl > -10.0: df_f = df_f[df_f['floor_val'] >= st.session_state.min_fl]
        if st.session_state.max_fl < 100.0: df_f = df_f[df_f['floor_val'] <= st.session_state.max_fl]
        df_f = df_f.drop(columns=['floor_val']) # 필터 후 임시 컬럼 제거

    # [C] 전체 선택/해제 및 페이지네이션
    total_count = len(df_f)
    if total_count == 0:
        st.warning("🔍 검색 결과가 없습니다.")
        return

    c_sel1, c_sel2, c_pg = st.columns([1, 1, 2])
    if c_sel1.button("✅ 전체 선택"):
        target_ids = df_f['IronID'].tolist()
        st.session_state.df_main.loc[st.session_state.df_main['IronID'].isin(target_ids), '선택'] = True
        st.session_state.editor_key_version += 1 # 리스트 뷰 갱신 트리거
        st.rerun()
        
    if c_sel2.button("⬜ 전체 해제"):
        st.session_state.df_main['선택'] = False
        st.session_state.editor_key_version += 1
        st.rerun()

    # 페이지 계산
    total_pages = math.ceil(total_count / ITEMS_PER_PAGE)
    if st.session_state.page_num > total_pages: st.session_state.page_num = 1
    
    start_idx = (st.session_state.page_num - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    df_page = df_f.iloc[start_idx:end_idx]

    # 페이지네이션 UI
    with c_pg:
        c_p1, c_p2, c_p3 = st.columns([1, 2, 1])
        if c_p1.button("◀", key="prev_pg") and st.session_state.page_num > 1:
            st.session_state.page_num -= 1
            st.rerun()
        c_p2.markdown(f"<div style='text-align:center; padding-top:5px;'><b>{st.session_state.page_num} / {total_pages}</b> ({total_count}건)</div>", unsafe_allow_html=True)
        if c_p3.button("▶", key="next_pg") and st.session_state.page_num < total_pages:
            st.session_state.page_num += 1
            st.rerun()

    # [D] 뷰 모드에 따른 렌더링
    if st.session_state.view_mode == '🗂️ 카드 모드':
        render_card_view(df_page, is_sale)
    else:
        render_list_view_editor(df_page)

    # [E] 하단 액션바 (선택된 항목 처리)
    render_action_bar()

def render_card_view(df_page, is_sale):
    """카드 형태의 리스트 출력"""
    for idx, row in df_page.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([0.5, 8, 1.5])
            
            # 1. 체크박스 (상태 동기화)
            is_checked = st.session_state.df_main.loc[st.session_state.df_main['IronID'] == row['IronID'], '선택'].values[0]
            new_chk = c1.checkbox("", value=bool(is_checked), key=f"chk_card_{row['IronID']}")
            if new_chk != is_checked:
                st.session_state.df_main.loc[st.session_state.df_main['IronID'] == row['IronID'], '선택'] = new_chk
                st.rerun()
            
            # 2. 내용 출력
            info = f"**{row.get('건물명','이름없음')}** [{row.get('구분')}] | {row.get('지역_구')} {row.get('지역_동')} {row.get('번지')}\n"
            if is_sale:
                info += f"💰 매매 {int(row.get('매매가',0)):,} / 대지 {row.get('대지면적')}평"
            else:
                info += f"💰 보 {int(row.get('보증금',0)):,} / 월 {int(row.get('월차임',0)):,} / 권 {int(row.get('권리금',0)):,}"
            info += f"\n📐 {row.get('층')}층 / {row.get('면적')}평"
            c2.markdown(info)
            
            # 3. 상세 버튼
            if c3.button("상세", key=f"btn_detail_{row['IronID']}", use_container_width=True):
                st.session_state.selected_item = row
                st.rerun()

def render_list_view_editor(df_page):
    """리스트 모드 (st.data_editor 활용)"""
    # 돋보기 컬럼 추가 (임시)
    df_editor = df_page.copy()
    df_editor.insert(0, "🔍", False)
    
    # 컬럼 설정 (체크박스, 돋보기 등)
    column_config = {
        "🔍": st.column_config.CheckboxColumn(width="small", label="이동"),
        "선택": st.column_config.CheckboxColumn(width="small"),
        "IronID": None # 숨김
    }

    # 데이터 에디터 출력
    edited_df = st.data_editor(
        df_editor,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed", # 행 추가/삭제 방지
        height=500,
        key=f"editor_main_{st.session_state.editor_key_version}"
    )

    # 이벤트 처리 1: 상세 페이지 이동 (돋보기 체크)
    if edited_df['🔍'].any():
        target_row = edited_df[edited_df['🔍'] == True].iloc[0]
        # 원본 데이터에서 해당 행 찾기
        original_row = st.session_state.df_main[st.session_state.df_main['IronID'] == target_row['IronID']].iloc[0]
        st.session_state.selected_item = original_row
        st.rerun()

    # 이벤트 처리 2: 선택 상태 동기화 (수동 저장 버튼 필요 없음, 즉시 반영 위해)
    # 에디터에서 변경된 '선택' 값을 원본 df_main에 반영
    # 주의: data_editor는 리런 시 초기화되므로, 변경 감지 로직이 필요하지만
    # 여기서는 "저장" 버튼을 통해 일괄 반영하는 것이 안정적임
    if st.button("💾 리스트 선택 상태 동기화 (필수)", use_container_width=True):
        for index, row in edited_df.iterrows():
            st.session_state.df_main.loc[st.session_state.df_main['IronID'] == row['IronID'], '선택'] = row['선택']
        st.success("선택 상태가 저장되었습니다.")
        st.rerun()

def render_action_bar():
    """하단 일괄 작업 바"""
    selected_rows = st.session_state.df_main[st.session_state.df_main['선택'] == True]
    if selected_rows.empty: return

    st.divider()
    st.info(f"✅ {len(selected_rows)}개 매물 선택됨")
    
    c1, c2, c3 = st.columns(3)
    cur_sheet = st.session_state.current_sheet
    is_end_sheet = "(종료)" in cur_sheet
    base_name = cur_sheet.replace("(종료)", "").replace("브리핑", "").strip()
    
    # 1. 이동/복구
    if is_end_sheet:
        if c1.button("♻️ 목록으로 복구"):
            engine.execute_transaction("restore", selected_rows, cur_sheet, base_name)
            st.rerun()
    elif "브리핑" not in cur_sheet:
        if c1.button("🚩 종료 처리 (이동)"):
            engine.execute_transaction("move", selected_rows, cur_sheet, f"{base_name}(종료)")
            st.rerun()
            
    # 2. 브리핑 복사
    if "브리핑" not in cur_sheet:
        if c2.button("🚀 브리핑 시트 복사"):
            engine.execute_transaction("copy", selected_rows, cur_sheet, f"{base_name}브리핑")
            st.success("복사 완료!")
            time.sleep(1)
            st.rerun()

    # 3. 영구 삭제
    if c3.button("🗑️ 영구 삭제", type="primary"):
        engine.execute_transaction("delete", selected_rows, cur_sheet)
        st.rerun()

def render_detail_view(item):
    """상세 페이지 (4단 탭 + 지도)"""
    st.button("◀ 목록으로 돌아가기", on_click=lambda: st.session_state.update(selected_item=None))
    
    st.subheader(f"🏠 {item.get('건물명', '매물 상세')}")
    
    c_left, c_right = st.columns([1, 1.2])
    
    with c_left:
        # 지도 영역
        addr = f"{item.get('지역_구')} {item.get('지역_동')} {item.get('번지')}"
        st.info(f"📍 {addr}")
        lat, lng = map_api.get_naver_geocode(addr)
        if lat and lng:
            img_data = map_api.fetch_map_image(lat, lng, height=400) # 상세페이지 지도 높이
            if img_data: st.image(img_data, use_container_width=True)
        else:
            st.error("위치 정보를 찾을 수 없습니다.")

    with c_right:
        # 4단 탭 구성
        t1, t2, t3, t4 = st.tabs(["📝 기본", "📑 시설", "📁 관리", "💬 브리핑"])
        
        # 탭1: 기본 정보
        with t1:
            with st.form("f1"):
                cols = ['구분', '매매가' if '매매가' in item else '보증금', '월차임', '권리금', '면적', '층']
                new_vals = {}
                for c in cols:
                    if c in item: new_vals[c] = st.text_input(c, value=str(item[c]))
                if st.form_submit_button("저장"):
                    item.update(new_vals)
                    engine.update_single_row(item, st.session_state.current_sheet)
                    st.rerun()
        
        # 탭2: 시설 상세
        with t2:
            with st.form("f2"):
                cols = ['호실', '현업종', '주차', 'E/V', '화장실', '특이사항']
                new_vals2 = {}
                for c in cols:
                    if c in item: new_vals2[c] = st.text_input(c, value=str(item.get(c,'')))
                if st.form_submit_button("시설 저장"):
                    item.update(new_vals2)
                    engine.update_single_row(item, st.session_state.current_sheet)
                    st.rerun()

        # 탭3: 접수/광고
        with t3:
             st.text_input("접수경로", value=str(item.get('접수경로','')), disabled=True)
             st.text_input("연락처", value=str(item.get('연락처','')), disabled=True)
             # 여기에 광고 체크박스 등 추가 가능

        # 탭4: 브리핑 생성
        with t4:
            txt = f"""[매물 브리핑]
위치: {addr}
금액: {item.get('보증금','-')}/{item.get('월차임','-')}
특징: {item.get('특이사항','-')}"""
            st.text_area("복사용 텍스트", value=txt, height=200)
