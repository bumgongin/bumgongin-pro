# list_renderer.py
# 범공인 Pro v24 Enterprise - List Renderer Module (v24.95 Final)
# Feature: Precision Pagination, Smart Editor, Batch Transactions, 4-Tab Detail

import streamlit as st
import pandas as pd
import math
import time
import re
import core_engine as engine
import map_service as map_api

# 한 페이지에 표시할 매물 수 (리스트 튀는 현상 방지)
ITEMS_PER_PAGE = 30

def show_main_list():
    """
    메인 리스트 및 상세 페이지 렌더링 컨트롤러 (Full Logic)
    """
    # [A] 상세 보기 모드 진입 확인 (최우선 처리)
    if st.session_state.selected_item is not None:
        render_detail_view(st.session_state.selected_item)
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

    # [C] 결과 집계 및 제어 UI
    total_count = len(df_f)
    if total_count == 0:
        st.warning("🔍 검색 결과가 없습니다.")
        return

    # 전체 선택/해제 버튼
    c_sel1, c_sel2, c_pg = st.columns([1, 1, 2])
    if c_sel1.button("✅ 전체 선택", use_container_width=True):
        target_ids = df_f['IronID'].tolist()
        st.session_state.df_main.loc[st.session_state.df_main['IronID'].isin(target_ids), '선택'] = True
        st.session_state.editor_key_version += 1 # 리스트 뷰 강제 갱신
        st.rerun()
        
    if c_sel2.button("⬜ 전체 해제", use_container_width=True):
        st.session_state.df_main['선택'] = False
        st.session_state.editor_key_version += 1
        st.rerun()

    # 페이지네이션 계산
    total_pages = math.ceil(total_count / ITEMS_PER_PAGE)
    if st.session_state.page_num > total_pages: st.session_state.page_num = 1
    
    start_idx = (st.session_state.page_num - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    df_page = df_f.iloc[start_idx:end_idx]

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

    # [D] 뷰 모드에 따른 렌더링 분기
    if st.session_state.view_mode == '🗂️ 카드 모드':
        render_card_view(df_page, is_sale)
    else:
        render_list_view_editor(df_page)

    # [E] 하단 페이지네이션 (사용성 강화)
    st.write("")
    c_b1, c_b2, c_b3 = st.columns([1, 2, 1])
    if c_b1.button("◀ 이전", key="prev_pg_btm") and st.session_state.page_num > 1:
        st.session_state.page_num -= 1
        st.rerun()
    if c_b3.button("다음 ▶", key="next_pg_btm") and st.session_state.page_num < total_pages:
        st.session_state.page_num += 1
        st.rerun()

    # [F] 하단 액션바 (선택된 항목 일괄 처리)
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
            
            # 2. 내용 출력 (매매/임대 구분)
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
    """리스트 모드 (st.data_editor 활용 - 무적 설정)"""
    # 돋보기 컬럼 추가 (맨 앞에 배치)
    df_editor = df_page.copy()
    df_editor.insert(0, "🔍", False)
    
    # 컬럼 설정 (체크박스, 돋보기 등)
    column_config = {
        "🔍": st.column_config.CheckboxColumn(width="small", label="이동"),
        "선택": st.column_config.CheckboxColumn(width="small"),
        "IronID": None # 숨김 (Key로 사용)
    }

    # 데이터 에디터 출력 (행 고정, 순서 유지)
    edited_df = st.data_editor(
        df_editor,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed", # 행 추가/삭제 방지
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
    if st.button("💾 리스트 선택 상태 동기화 (필수)", use_container_width=True):
        for index, row in edited_df.iterrows():
            st.session_state.df_main.loc[st.session_state.df_main['IronID'] == row['IronID'], '선택'] = row['선택']
        st.success("선택 상태가 저장되었습니다.")
        time.sleep(0.5)
        st.rerun()

def render_action_bar():
    """하단 일괄 작업 바 (트랜잭션 연결)"""
    selected_rows = st.session_state.df_main[st.session_state.df_main['선택'] == True]
    if selected_rows.empty: return

    st.divider()
    st.info(f"✅ {len(selected_rows)}개 매물 선택됨")
    
    c1, c2, c3 = st.columns(3)
    cur_sheet = st.session_state.current_sheet
    is_end_sheet = "(종료)" in cur_sheet
    base_name = cur_sheet.replace("(종료)", "").replace("브리핑", "").strip()
    base_label = "매매" if "매매" in cur_sheet else "임대"
    
    # 1. 이동/복구
    if is_end_sheet:
        if c1.button(f"♻️ {base_label} 목록으로 복구"):
            engine.execute_transaction("restore", selected_rows, cur_sheet, base_name)
            del st.session_state.df_main
            st.rerun()
    elif "브리핑" not in cur_sheet:
        if c1.button(f"🚩 {base_label} 종료 처리 (이동)"):
            engine.execute_transaction("move", selected_rows, cur_sheet, f"{base_name}(종료)")
            del st.session_state.df_main
            st.rerun()
            
    # 2. 브리핑 복사
    if "브리핑" not in cur_sheet:
        if c2.button(f"🚀 {base_label} 브리핑 복사"):
            engine.execute_transaction("copy", selected_rows, cur_sheet, f"{base_name}브리핑")
            st.success("복사 완료!")
            time.sleep(1)
            # 복사는 리스트 갱신 불필요 (선택 상태 유지)

    # 3. 영구 삭제
    if c3.button("🗑️ 영구 삭제", type="primary"):
        engine.execute_transaction("delete", selected_rows, cur_sheet)
        del st.session_state.df_main
        st.rerun()

def render_detail_view(item):
    """상세 페이지 (4단 탭 + 지도 + 모바일 연락처)"""
    st.button("◀ 목록으로 돌아가기", on_click=lambda: st.session_state.update(selected_item=None))
    
    # 헤더
    st.subheader(f"🏠 {item.get('건물명', '매물 상세')}")
    
    # 2단 레이아웃 (지도 / 탭)
    c_left, c_right = st.columns([1, 1.2])
    
    # [왼쪽] 지도 및 위치 정보
    with c_left:
        addr = f"{item.get('지역_구')} {item.get('지역_동')} {item.get('번지')}"
        st.info(f"📍 {addr}")
        
        # 지도 이미지 호출 (높이 조절)
        lat, lng = map_api.get_naver_geocode(addr)
        if lat and lng:
            # PC에서는 800, 모바일에서는 400 (고정값)
            img_data = map_api.fetch_map_image(lat, lng, height=600)
            if img_data: st.image(img_data, use_container_width=True)
            
            # 네이버 지도 바로가기 버튼
            naver_url = f"https://map.naver.com/v5/search/{addr}?c={lng},{lat},17,0,0,0,dh"
            st.link_button("🗺️ 네이버 지도 앱에서 열기", naver_url, use_container_width=True)
        else:
            st.error("위치 정보를 찾을 수 없습니다.")

    # [오른쪽] 4단 탭 상세 정보
    with c_right:
        t1, t2, t3, t4 = st.tabs(["📝 기본/주소", "📑 시설/내용", "📁 기타 정보", "💬 브리핑"])
        
        # 탭1: 기본 정보 (수정 가능)
        with t1:
            with st.form("form_basic"):
                cols_basic = ['구분', '지역_구', '지역_동', '번지', '층', '호실', '보증금', '월차임', '관리비', '권리금', '면적', '연락처']
                updates_basic = {}
                
                # 2열 배치
                c_f1, c_f2 = st.columns(2)
                for i, col in enumerate(cols_basic):
                    val = str(item.get(col, '')).replace('nan', '')
                    target_col = c_f1 if i % 2 == 0 else c_f2
                    updates_basic[col] = target_col.text_input(col, value=val)
                
                # [모바일 터치 기능] 연락처 버튼 생성
                contact_num = updates_basic.get('연락처')
                if contact_num:
                    c_call, c_sms = st.columns(2)
                    clean_num = re.sub(r'[^0-9]', '', contact_num)
                    if clean_num:
                        c_call.markdown(f'<a href="tel:{clean_num}" target="_self" style="text-decoration:none;"><button style="width:100%; border:1px solid #ddd; padding:5px; border-radius:5px;">📞 전화 걸기</button></a>', unsafe_allow_html=True)
                        c_sms.markdown(f'<a href="sms:{clean_num}" target="_self" style="text-decoration:none;"><button style="width:100%; border:1px solid #ddd; padding:5px; border-radius:5px;">💬 문자 보내기</button></a>', unsafe_allow_html=True)

                if st.form_submit_button("💾 기본정보 저장", use_container_width=True):
                    item.update(updates_basic)
                    success, msg = engine.update_single_row(item, st.session_state.current_sheet)
                    if success:
                        st.success(msg)
                        time.sleep(1)
                        if 'df_main' in st.session_state: del st.session_state.df_main
                        st.rerun()
                    else:
                        st.error(msg)
        
        # 탭2: 시설 상세 (수정 가능)
        with t2:
            with st.form("form_facility"):
                cols_fac = ['현업종', '주차', '화장실', 'E/V', '층고']
                cols_area = ['특이사항', '내용']
                
                updates_fac = {}
                c_fac1, c_fac2 = st.columns(2)
                
                for i, col in enumerate(cols_fac):
                    val = str(item.get(col, '')).replace('nan', '')
                    target_col = c_fac1 if i % 2 == 0 else c_fac2
                    updates_fac[col] = target_col.text_input(col, value=val)
                
                for col in cols_area:
                    val = str(item.get(col, '')).replace('nan', '')
                    updates_fac[col] = st.text_area(col, value=val, height=100)
                
                if st.form_submit_button("💾 시설정보 저장", use_container_width=True):
                    item.update(updates_fac)
                    success, msg = engine.update_single_row(item, st.session_state.current_sheet)
                    if success:
                        st.success(msg)
                        time.sleep(1)
                        if 'df_main' in st.session_state: del st.session_state.df_main
                        st.rerun()
                    else:
                        st.error(msg)

        # 탭3: 기타 정보
        with t3:
            cols_etc = ['접수경로', '접수일', '사진', '광고_포스', '광고_모두', '광고_블로그', '사용승인일', '건축물용도']
            with st.form("form_etc"):
                updates_etc = {}
                for col in cols_etc:
                     val = str(item.get(col, '')).replace('nan', '')
                     updates_etc[col] = st.text_input(col, value=val)
                
                if st.form_submit_button("💾 기타정보 저장", use_container_width=True):
                    item.update(updates_etc)
                    engine.update_single_row(item, st.session_state.current_sheet)
                    st.success("저장되었습니다.")
                    time.sleep(1)
                    del st.session_state.df_main
                    st.rerun()

        # 탭4: 브리핑 생성
        with t4:
            area_py = item.get('면적', '-')
            deposit = item.get('보증금', '-')
            rent = item.get('월차임', '-')
            man = item.get('관리비', '-')
            
            brief_txt = f"""[매물 브리핑]
📍 위치: {addr}
🏢 건물: {item.get('건물명', '-')} ({item.get('층', '-')}층)
📐 면적: {area_py}평
💰 금액: 보 {deposit} / 월 {rent} / 관 {man}
📝 특징: {item.get('내용', '-')}

📞 문의: 범공인중개사"""
            
            st.text_area("복사용 텍스트 (전체 선택 후 복사하세요)", value=brief_txt, height=250)
