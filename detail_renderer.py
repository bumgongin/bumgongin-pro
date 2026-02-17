# detail_renderer.py
# 범공인 Pro v24 Enterprise - Detail View Engine (v24.95 Final)
# Feature: 4-Tab Detail, Lease/Sale Mode, Contact Actions, Smart Action Bar

import streamlit as st
import pandas as pd
import time
import re
import core_engine as engine
import map_service as map_api
import infra_engine

def render_detail_view(item):
    """
    상세 보기 및 수정 페이지 렌더링 (Full Logic)
    """
    # [A] 상단 네비게이션 및 데이터 정제
    if st.button("◀ 목록으로 돌아가기"):
        st.session_state.selected_item = None
        st.rerun()

    # 데이터 정제 (NaN -> 공백)
    item = {k: (str(v).replace('nan', '') if pd.notna(v) else '') for k, v in item.items()}
    current_sheet = st.session_state.current_sheet
    is_sale_mode = "매매" in current_sheet

    # [B] 인프라 분석 (지하철 정보 호출)
    addr_full = f"{item.get('지역_구', '')} {item.get('지역_동', '')} {item.get('번지', '')}".strip()
    lat, lng = map_api.get_naver_geocode(addr_full)
    
    subway_info = "" # 브리핑용 지하철 정보
    if lat and lng:
        # 캐싱된 인프라 분석 호출 (속도 최적화)
        # 실제 앱에서는 @st.cache_data가 적용된 함수를 호출해야 함 (여기서는 직접 호출 가정)
        try:
            infra_data = infra_engine.get_commercial_analysis(lat, lng)
            sub = infra_data.get('subway', {})
            if sub.get('station') and sub['station'] != "정보 없음":
                 w_min = int(round(sub.get('walk', 0)))
                 if w_min == 0: w_min = 1
                 subway_info = f" ({sub['station']} 도보 {w_min}분)"
        except:
            pass

    st.subheader(f"🏠 {item.get('건물명', '매물 상세 정보')}")

    # [C] 2단 레이아웃 (지도 1.5 : 탭 1)
    col_left, col_right = st.columns([1.5, 1])

    # --- LEFT COLUMN: MAP & INFRA ---
    with col_left:
        st.info(f"📍 {addr_full}")
        if lat and lng:
            # PC 최적화 높이 (800px)
            map_img = map_api.fetch_map_image(lat, lng, height=800)
            if map_img:
                st.image(map_img, use_container_width=True)
            
            naver_url = f"https://map.naver.com/v5/search/{addr_full}?c={lng},{lat},17,0,0,0,dh"
            st.link_button("🗺️ 네이버 지도 앱에서 열기", naver_url, use_container_width=True)
        else:
            st.error("위치 정보를 찾을 수 없습니다.")

    # --- RIGHT COLUMN: 4-TAB DETAIL ---
    with col_right:
        t1, t2, t3, t4 = st.tabs(["📝 기본/주소", "📑 시설/내용", "📁 기타 정보", "💬 브리핑"])

        # [TAB 1] 기본 정보 (임대/매매 분기)
        with t1:
            with st.form("form_basic"):
                updates_basic = {}
                
                if is_sale_mode:
                    # 매매 필드 (13개)
                    fields_sale = ['구분', '지역_구', '지역_동', '번지', '해당층', '호실', 
                                   '매매가', '대지면적', '건축면적', '연면적', '전용면적', '수익률', '연락처']
                    c1, c2 = st.columns(2)
                    for i, col in enumerate(fields_sale):
                        target = c1 if i % 2 == 0 else c2
                        updates_basic[col] = target.text_input(col, value=item.get(col, ''))
                else:
                    # 임대 필드 (12개)
                    fields_rent = ['구분', '지역_구', '지역_동', '번지', '층', '호실', 
                                   '보증금', '월차임', '관리비', '권리금', '면적', '연락처']
                    c1, c2 = st.columns(2)
                    for i, col in enumerate(fields_rent):
                        target = c1 if i % 2 == 0 else c2
                        updates_basic[col] = target.text_input(col, value=item.get(col, ''))

                # 연락처 특수 기능 (전화/문자)
                contact_val = updates_basic.get('연락처', '')
                if contact_val:
                    # 숫자만 추출
                    clean_num = re.sub(r'[^0-9]', '', contact_val)
                    if len(clean_num) >= 9:
                        bc1, bc2 = st.columns(2)
                        bc1.markdown(f'''<a href="tel:{clean_num}" target="_self" style="text-decoration:none;">
                            <div style="text-align:center; background-color:#f0f2f6; padding:8px; border-radius:5px; border:1px solid #ccc;">📞 전화 걸기</div></a>''', unsafe_allow_html=True)
                        bc2.markdown(f'''<a href="sms:{clean_num}" target="_self" style="text-decoration:none;">
                            <div style="text-align:center; background-color:#f0f2f6; padding:8px; border-radius:5px; border:1px solid #ccc;">💬 문자 보내기</div></a>''', unsafe_allow_html=True)

                st.write("")
                if st.form_submit_button("💾 기본정보 저장", use_container_width=True):
                    item.update(updates_basic)
                    success, msg = engine.update_single_row(item, current_sheet)
                    handle_save_result(success, msg)

        # [TAB 2] 시설/내용 수정
        with t2:
            with st.form("form_facility"):
                updates_fac = {}
                
                if is_sale_mode:
                    # 매매 시설 필드
                    fields_fac_sale = ['주용도', '기보증금', '기월세', '관리비', '주차', 'EV', '현업종']
                    c1, c2 = st.columns(2)
                    for i, col in enumerate(fields_fac_sale):
                        target = c1 if i % 2 == 0 else c2
                        updates_fac[col] = target.text_input(col, value=item.get(col, ''))
                    
                    updates_fac['특이사항'] = st.text_area("특이사항", value=item.get('특이사항', ''), height=100)
                else:
                    # 임대 시설 필드
                    fields_fac_rent = ['현업종', '주차', '화장실', 'E/V', '층고']
                    c1, c2 = st.columns(2)
                    for i, col in enumerate(fields_fac_rent):
                        target = c1 if i % 2 == 0 else c2
                        updates_fac[col] = target.text_input(col, value=item.get(col, ''))
                    
                    updates_fac['특이사항'] = st.text_input("특이사항", value=item.get('특이사항', ''))
                    updates_fac['내용'] = st.text_area("내용(특징)", value=item.get('내용', ''), height=150)

                if st.form_submit_button("💾 시설정보 저장", use_container_width=True):
                    item.update(updates_fac)
                    success, msg = engine.update_single_row(item, current_sheet)
                    handle_save_result(success, msg)

        # [TAB 3] 기타 정보 (모두 수정 가능)
        with t3:
            with st.form("form_etc"):
                updates_etc = {}
                fields_etc = ['접수경로', '접수일', '사진', '광고_포스', '광고_모두', '광고_블로그', '사용승인일', '건축물용도', '매물특징']
                
                c1, c2 = st.columns(2)
                for i, col in enumerate(fields_etc):
                    val = item.get(col, '')
                    target = c1 if i % 2 == 0 else c2
                    updates_etc[col] = target.text_input(col, value=val)
                
                if st.form_submit_button("💾 기타정보 저장", use_container_width=True):
                    item.update(updates_etc)
                    success, msg = engine.update_single_row(item, current_sheet)
                    handle_save_result(success, msg)

        # [TAB 4] 카톡 브리핑 생성
        with t4:
            st.markdown("##### 💬 카톡 브리핑 생성기")
            
            # 브리핑 데이터 준비
            b_loc = f"{item.get('지역_구','')} {item.get('지역_동','')}{subway_info}"
            b_name = f"{item.get('건물명','')} ({item.get('층','')}층)"
            b_area = f"실 {item.get('면적','-')}평"
            
            if is_sale_mode:
                b_price = f"매매 {item.get('매매가','-')}만"
            else:
                b_price = f"보 {item.get('보증금','-')} / 월 {item.get('월차임','-')} / 관 {item.get('관리비','-')}"
            
            b_feat = item.get('내용', '') or item.get('특이사항', '문의 요망')
            
            briefing_text = f"""[매물 브리핑]
📍 위치: {b_loc}
🏢 건물: {b_name}
📐 면적: {b_area}
💰 금액: {b_price}
📝 특징: {b_feat}

📞 문의: 범공인중개사"""
            
            st.text_area("복사용 텍스트", value=briefing_text, height=250)
            st.caption("▲ 전체 선택 후 복사하여 사용하세요.")

    # [D] 하단 지능형 액션 바
    st.divider()
    render_smart_action_bar(item, current_sheet, is_sale_mode)

def render_smart_action_bar(item, sheet_name, is_sale):
    """시트 상태별 맞춤형 액션 버튼"""
    target_df = pd.DataFrame([item])
    base_name = sheet_name.replace("(종료)", "").replace("브리핑", "").strip()
    
    c1, c2, c3 = st.columns(3)
    
    # CASE 1: 종료 시트 (복구/복사/삭제)
    if "(종료)" in sheet_name:
        if c1.button("♻️ 목록으로 복구", use_container_width=True):
            engine.execute_transaction("restore", target_df, sheet_name, base_name)
            reset_and_close()
        
        target_brief = f"{base_name}브리핑"
        if c2.button("🚀 브리핑 복사", use_container_width=True):
            engine.execute_transaction("copy", target_df, sheet_name, target_brief)
            st.success("브리핑 시트로 복사되었습니다.")
            
        if c3.button("🗑️ 영구 삭제", type="primary", use_container_width=True):
            engine.execute_transaction("delete", target_df, sheet_name)
            reset_and_close()
            
    # CASE 2: 브리핑 시트 (삭제만)
    elif "브리핑" in sheet_name:
        # 중앙 정렬을 위해 c2 사용
        if c2.button("🗑️ 브리핑 삭제", type="primary", use_container_width=True):
            engine.execute_transaction("delete", target_df, sheet_name)
            reset_and_close()
            
    # CASE 3: 일반 시트 (종료/복사/삭제)
    else:
        target_end = f"{base_name}(종료)"
        if c1.button("🚩 종료 처리 (이동)", use_container_width=True):
            engine.execute_transaction("move", target_df, sheet_name, target_end)
            reset_and_close()
            
        target_brief = f"{base_name}브리핑"
        if c2.button("🚀 브리핑 복사", use_container_width=True):
            engine.execute_transaction("copy", target_df, sheet_name, target_brief)
            st.success("브리핑 시트로 복사되었습니다.")
            
        if c3.button("🗑️ 영구 삭제", type="primary", use_container_width=True):
            engine.execute_transaction("delete", target_df, sheet_name)
            reset_and_close()

def handle_save_result(success, msg):
    """저장 결과 처리 헬퍼"""
    if success:
        st.success("✅ 저장되었습니다!")
        time.sleep(1.0)
        # 데이터 갱신을 위해 캐시 삭제
        if 'df_main' in st.session_state: 
            del st.session_state.df_main
        st.rerun()
    else:
        st.error(f"❌ 저장 실패: {msg}")

def reset_and_close():
    """작업 완료 후 목록으로 복귀"""
    st.success("처리 완료!")
    time.sleep(1.0)
    st.session_state.selected_item = None
    if 'df_main' in st.session_state: 
        del st.session_state.df_main
    st.rerun()
