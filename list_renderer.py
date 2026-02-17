# list_renderer.py
# 범공인 Pro v24 Enterprise - List Renderer Module (v24.96 Precision Fix)
# Feature: Page-only Selection, Smart Editor, Batch Actions, External Detail View

import streamlit as st
import pandas as pd
import math
import time
import core_engine as engine
import map_service as map_api
import detail_renderer # 상세 보기 전담 모듈 (분리 완료)

# 한 페이지에 표시할 매물 수
ITEMS_PER_PAGE = 30

def show_main_list():
    """
    메인 리스트 및 상세 페이지 렌더링 컨트롤러 (Full Logic)
    """
    # [A] 상세 보기 모드 진입 확인 (최우선 처리)
    if st.session_state.selected_item is not None:
        # 이 파일에는 렌더링 함수가 없으므로 외부 모듈 호출
        detail_renderer.render_detail_view(st.session_state.selected_item)
        return

    # [B] 데이터 필터링 로직 (app.py의 상태 변수 활용)
    df = st.session_state.df_main
    df_f = df.copy()

    # 1. 항목/지역 필터
    if st.session_state.selected_cat:
        df_f = df_f[df_f['구분'].isin(st.session_state.selected_cat)]
    if st.session_state.selected_gu:
        df_f = df_f[df_f['지역_구'].isin(st.session_state.selected_gu)]
    if st.session_state.selected_dong:
        df_f = df_f[df_f['지역_동'].isin(st.session_state.selected_dong)]
    
    # 2. 검색 필터 (번지 정확 일치 & 키워드 포함)
    if st.session_state.exact_bunji:
        df_f = df_f[df_f['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]
    if st.session_state.search_keyword:
        kw = st.session_state.search_keyword
        # 모든 컬럼을 문자열로 변환 후 대소문자 무시 검색
        mask = df_f.astype(str).apply(lambda x: x.str.contains(kw, case=False)).any(axis=1)
        df_f = df_f[mask]

    # 3. 금액/면적/층수 정밀 필터
    is_sale = "매매" in st.session_state.current_sheet
    if is_sale:
        if st.session_state.min_price: df_f = df_f[df_f['매매가'] >= st.session_state.min_price]
        if st.session_state.max_price < 10000000.0: df_f = df_f[df_f['매매가'] <= st.session_state.max_price]
    else:
        if st.session_state.min_dep: df_f = df_f[df_f['보증금'] >= st.session_state.min_dep]
        if st.session_state.max_dep < 10000000.0: df_f = df_f[df_f['보증금'] <= st.session_state.max_dep]
        
        if st.session_state.min_rent: df_f = df_f[df_f['월차임'] >= st.session_state.min_rent]
        if st.session_state.max_rent < 100000.0: df_f = df_f[df_f['월차임'] <= st.session_state.max_rent]
        
        # 권리금 필터 (무권리 옵션 포함)
        if st.session_state.is_no_kwon:
            df_f = df_f[df_f['권리금'] == 0]
        else:
            if st.session_state.min_kwon: df_f = df_f[df_f['권리금'] >= st.session_state.min_kwon]
            if st.session_state.max_kwon < 1000000.0: df_f = df_f[df_f['권리금'] <= st.session_state.max_kwon]

    # 공통 필터 (면적)
    if st.session_state.min_area: df_f = df_f[df_f['면적'] >= st.session_state.min_area]
    if st.session_state.max_area < 100000.0: df_f = df_f[df_f['면적'] <= st.session_state.max_area]
    
    # 층수 필터 (음수 보존 및 정규식 추출)
    if '층' in df_f.columns:
        # 숫자만 추출하되 음수(-) 부호는 살림
        df_f['floor_val'] = df_f['층'].astype(str).str.extract(r'(-?\d+)')[0].fillna(1).astype(float)
        if st.session_state.min_fl > -10.0: df_f = df_f[df_f['floor_val'] >= st.session_state.min_fl]
        if st.session_state.max_fl < 100.0: df_f = df_f[df_f['floor_val'] <= st.session_state.max_fl]
        df_f = df_f.drop(columns=['floor_val']) # 필터 후 임시 컬럼 제거

    # [C] 결과 집계 및 페이지 계산
    total_count = len(df_f)
    if total_count == 0:
        st.warning("🔍 검색 결과가 없습니다.")
        return

    total_pages = math.ceil(total_count / ITEMS_PER_PAGE)
    if st.session_state.page_num > total_pages: st.session_state.page_num = 1
    
    start_idx = (st.session_state.page_num - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    
    # 현재 페이지의 데이터만 슬라이싱
    df_page = df_f.iloc[start_idx:end_idx]

    # [D] 상단 컨트롤 바 (전체 선택 / 해제 / 신규 등록 / 페이지네이션)
    c_sel1, c_sel2, c_new, c_pg = st.columns([1, 1, 1.5, 2])
    
    # 전체 선택 로직 수정: 전체(df_f)가 아닌 현재 페이지(df_page)만 선택
    if c_sel1.button("✅ 전체 선택", use_container_width=True):
        target_ids = df_page['IronID'].tolist()
        st.session_state.df_main.loc[st.session_state.df_main['IronID'].isin(target_ids), '선택'] = True
        st.session_state.editor_key_version += 1 # 리스트 뷰 강제 갱신
        st.rerun()
        
    if c_sel2.button("⬜ 전체 해제", use_container_width=True):
        st.session_state.df_main['선택'] = False
        st.session_state.editor_key_version += 1
        st.rerun()

    # 신규 등록 버튼 (준비 중)
    if c_new.button("➕ 신규 매물 등록", use_container_width=True):
        st.warning("🚧 신규 등록 기능은 준비 중입니다. (구글 시트에서 직접 추가해주세요)")

    # 페이지네이션 UI (상단)
    with c_pg:
        c_p1, c_p2, c_p3 = st.columns([1, 2, 1])
        if c_p1.button("◀", key="prev_pg") and st.session_state.page_num > 1:
            st.session_state.page_num -= 1
            st.rerun()
        c_p2.markdown(f"<div style='text-align:center; padding-top:5px; font-weight:bold;'>PAGE {st.session_state.page_num} / {total_pages} ({total_count}건)</div>", unsafe_allow_html=True)
        if c_p3.button("▶", key="next_pg") and st.session_state.page_num < total_pages:
            st.session_state.page_num += 1
            st.rerun()

    # [E] 뷰 모드에 따른 렌더링 분기
    if st.session_state.view_mode == '🗂️ 카드 모드':
        render_card_view(df_page, is_sale)
    else:
        render_list_view_editor(df_page)

    # [F] 하단 페이지네이션 (사용성 강화)
    st.write("")
    c_b1, c_b2, c_b3 = st.columns([1, 2, 1])
    if c_b1.button("◀ 이전 페이지", key="prev_pg_btm", use_container_width=True) and st.session_state.page_num > 1:
        st.session_state.page_num -= 1
        st.rerun()
    if c_b3.button("다음 페이지 ▶", key="next_pg_btm", use_container_width=True) and st.session_state.page_num < total_pages:
        st.session_state.page_num += 1
        st.rerun()

    # [G] 하단 액션바 (선택된 항목 일괄 처리)
    render_action_bar()

def render_card_view(df_page, is_sale):
    """
    카드 형태의 리스트 출력 (이름없음 방지 및 체크박스 동기화)
    """
    version = st.session_state.editor_key_version
    
    for idx, row in df_page.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([0.5, 8, 1.5])
            
            # 1. 체크박스 (Key에 버전 포함하여 강제 갱신)
            iid = row['IronID']
            is_checked = st.session_state.df_main.loc[st.session_state.df_main['IronID'] == iid, '선택'].values[0]
            
            # Key를 매번 다르게 주어 리런 시 상태 반영 보장
            new_chk = c1.checkbox("", value=bool(is_checked), key=f"chk_card_{iid}_{version}")
            
            if new_chk != is_checked:
                st.session_state.df_main.loc[st.session_state.df_main['IronID'] == iid, '선택'] = new_chk
                st.rerun()
            
            # 2. 내용 출력 (건물명 미입력 처리)
            b_name = row.get('건물명')
            if pd.isna(b_name) or str(b_name).strip() == "" or str(b_name) == "nan":
                b_name = "건물명 미입력"
            
            info = f"**{b_name}** [{row.get('구분')}] | {row.get('지역_구')} {row.get('지역_동')} {row.get('번지')}\n"
            if is_sale:
                info += f"💰 매매 {int(row.get('매매가',0)):,} / 대지 {row.get('대지면적')}평"
            else:
                info += f"💰 보 {int(row.get('보증금',0)):,} / 월 {int(row.get('월차임',0)):,} / 권 {int(row.get('권리금',0)):,}"
            info += f"\n📐 {row.get('층')}층 / {row.get('면적')}평"
            c2.markdown(info)
            
            # 3. 상세 버튼
            if c3.button("상세보기", key=f"btn_detail_{iid}_{version}", use_container_width=True):
                st.session_state.selected_item = row
                st.rerun()

def render_list_view_editor(df_page):
    """
    리스트 모드 (st.data_editor 활용 - 무적 설정 및 상세 이동)
    """
    # 돋보기 컬럼 추가 (맨 앞에 배치)
    df_editor = df_page.copy()
    df_editor.insert(0, "🔍", False)
    
    # 컬럼 설정 (라벨 수정 및 고정)
    column_config = {
        "🔍": st.column_config.CheckboxColumn(width="small", label="상세보기"),
        "선택": st.column_config.CheckboxColumn(width="small"),
        "IronID": None # 숨김 (Key로 사용)
    }

    # 모든 데이터 컬럼 비활성화 (정렬/이동 차단)
    disabled_cols = [col for col in df_editor.columns if col not in ['선택', '🔍']]

    # 데이터 에디터 출력 (행 고정, 순서 유지)
    edited_df = st.data_editor(
        df_editor,
        column_config=column_config,
        disabled=disabled_cols,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed", # 행 추가/삭제 방지 (무적 설정)
        height=600,       # 충분한 높이 확보
        key=f"editor_main_{st.session_state.editor_key_version}"
    )

    # 이벤트 처리 1: 상세 페이지 이동 (돋보기 체크 감지)
    if edited_df['🔍'].any():
        target_row = edited_df[edited_df['🔍'] == True].iloc[0]
        # 원본 데이터에서 해당 행 찾기 (IronID 기준)
        original_row = st.session_state.df_main[st.session_state.df_main['IronID'] == target_row['IronID']].iloc[0]
        st.session_state.selected_item = original_row
        st.rerun()

    # 이벤트 처리 2: 선택 상태 동기화 (수동 저장 버튼)
    # data_editor는 자동 동기화가 까다로우므로 명시적 버튼 사용이 안정적임
    if st.button("💾 리스트 선택 상태 저장 (체크박스 반영)", use_container_width=True):
        for index, row in edited_df.iterrows():
            st.session_state.df_main.loc[st.session_state.df_main['IronID'] == row['IronID'], '선택'] = row['선택']
        st.success("선택 상태가 저장되었습니다.")
        time.sleep(0.5)
        st.rerun()

def render_action_bar():
    """
    하단 일괄 작업 바 (트랜잭션 연결)
    """
    selected_rows = st.session_state.df_main[st.session_state.df_main['선택'] == True]
    if selected_rows.empty: return

    st.divider()
    st.info(f"✅ {len(selected_rows)}개 매물 선택됨 (작업을 수행하려면 아래 버튼을 누르세요)")
    
    c1, c2, c3 = st.columns(3)
    cur_sheet = st.session_state.current_sheet
    is_end_sheet = "(종료)" in cur_sheet
    base_name = cur_sheet.replace("(종료)", "").replace("브리핑", "").strip()
    base_label = "매매" if "매매" in cur_sheet else "임대"
    
    # 1. 이동/복구
    if is_end_sheet:
        if c1.button(f"♻️ {base_label} 목록으로 복구", use_container_width=True):
            engine.execute_transaction("restore", selected_rows, cur_sheet, base_name)
            del st.session_state.df_main
            st.rerun()
    elif "브리핑" not in cur_sheet:
        if c1.button(f"🚩 {base_label} 종료 처리 (이동)", use_container_width=True):
            engine.execute_transaction("move", selected_rows, cur_sheet, f"{base_name}(종료)")
            del st.session_state.df_main
            st.rerun()
            
    # 2. 브리핑 복사
    if "브리핑" not in cur_sheet:
        if c2.button(f"🚀 {base_label} 브리핑 시트로 복사", use_container_width=True):
            engine.execute_transaction("copy", selected_rows, cur_sheet, f"{base_name}브리핑")
            st.success("브리핑 시트로 복사가 완료되었습니다!")
            time.sleep(1)
            # 복사는 리스트 갱신 불필요 (선택 상태 유지)

    # 3. 영구 삭제
    if c3.button("🗑️ 선택 항목 영구 삭제", type="primary", use_container_width=True):
        engine.execute_transaction("delete", selected_rows, cur_sheet)
        del st.session_state.df_main
        st.rerun()
