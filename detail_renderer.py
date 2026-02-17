# detail_renderer.py
# 범공인 Pro v24 Enterprise - Detail View Engine (v24.96 Final Refined)
# Feature: Single Column Layout, Unified Terminology, Naver Map Base

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

    # [B] 인프라 분석 및 지도 준비
    addr_full = f"{item.get('지역_구', '')} {item.get('지역_동', '')} {item.get('번지', '')}".strip()
    lat, lng = map_api.get_naver_geocode(addr_full)
    
    # 줌 레벨 초기화 (네이버 지도 최적값 17)
    if 'map_zoom' not in st.session_state:
        st.session_state.map_zoom = 17

    st.subheader(f"🏠 {item.get('건물명', '매물 상세 정보')}")

    # [C] 2단 레이아웃 (지도 1.5 : 탭 1)
    col_left, col_right = st.columns([1.5, 1])

    # --- LEFT COLUMN: MAP & INFRA CONTROL ---
    with col_left:
        st.info(f"📍 {addr_full}")
        
        if lat and lng:
            # 줌 컨트롤러
            z1, z2, z_info = st.columns([1, 1, 4])
            if z1.button("➕ 확대"):
                st.session_state.map_zoom = min(st.session_state.map_zoom + 1, 20)
                st.rerun()
            if z2.button("➖ 축소"):
                st.session_state.map_zoom = max(st.session_state.map_zoom - 1, 10)
                st.rerun()
            z_info.caption(f"현재 줌 레벨: {st.session_state.map_zoom}")

            # 지도 이미지 출력 (높이 800px)
            map_img = map_api.fetch_map_image(lat, lng, height=800, zoom_level=st.session_state.map_zoom)
            if map_img:
                st.image(map_img, use_container_width=True)
            
            naver_url = f"https://map.naver.com/v5/search/{addr_full}?c={lng},{lat},17,0,0,0,dh"
            st.link_button("🗺️ 네이버 지도 앱에서 열기", naver_url, use_container_width=True)
            
            # [상권 분석 섹션]
            st.divider()
            if st.button("📊 상권 요약 분석 보기 (300m 반경)", use_container_width=True):
                with st.spinner("주변 시설 및 상권을 분석 중입니다..."):
                    # 인프라 엔진 호출
                    infra_data = infra_engine.get_commercial_analysis(lat, lng)
                    if infra_data:
                        # 1. 지하철 정보
                        sub = infra_data.get('subway', {})
                        if sub.get('station') and sub['station'] != "정보 없음":
                             # 도보 거리 산식 보수적 적용 (네이버 지도 기준)
                             w_min = int(round(sub.get('walk', 0)))
                             if w_min == 0: w_min = 1
                             st.success(f"🚇 **{sub['station']}** ({sub.get('line','')}) : 도보 약 {w_min}분 ({int(sub.get('dist', 0))}m)")
                             # 브리핑용 데이터 세션 저장
                             st.session_state.last_subway_info = f" ({sub['station']} 도보 {w_min}분)"
                        else:
                             st.session_state.last_subway_info = ""

                        # 2. 분석 테이블 출력 (2열 배치)
                        tab_fac, tab_anchor = st.tabs(["편의 시설", "앵커 브랜드"])
                        
                        with tab_fac:
                            fac_df = infra_data.get('facilities')
                            if fac_df is not None and not fac_df.empty:
                                st.dataframe(fac_df, use_container_width=True, hide_index=True)
                            else:
                                st.info("주변 300m 이내 주요 시설 데이터가 없습니다.")

                        with tab_anchor:
                            anchor_df = infra_data.get('anchors')
                            if anchor_df is not None and not anchor_df.empty:
                                st.dataframe(anchor_df, use_container_width=True, hide_index=True)
                            else:
                                st.info("주변 1km 이내 주요 브랜드가 없습니다.")
                    else:
                        st.error("분석 데이터를 가져오지 못했습니다.")
        else:
            st.error("위치 정보를 찾을 수 없습니다. (주소 확인 필요)")

    # --- RIGHT COLUMN: 4-TAB DETAIL FORM ---
    with col_right:
        t1, t2, t3, t4 = st.tabs(["📝 기본/주소", "📑 시설/내용", "📁 기타 정보", "💬 브리핑"])

        # [TAB 1] 기본 정보 (1열 배치 - 모바일 최적화)
        with t1:
            with st.form("form_basic"):
                updates_basic = {}
                
                if is_sale_mode:
                    # 매매 필드 (13개 - 1열 순차 배치)
                    fields_sale = ['구분', '지역_구', '지역_동', '번지', '해당층', '호실', 
                                   '매매가', '대지면적', '건축면적', '연면적', '전용면적', '수익률', '연락처']
                    for col in fields_sale:
                        updates_basic[col] = st.text_input(col, value=item.get(col, ''))
                else:
                    # 임대 필드 (12개 - 1열 순차 배치)
                    fields_rent = ['구분', '지역_구', '지역_동', '번지', '층', '호실', 
                                   '보증금', '월차임', '관리비', '권리금', '면적', '연락처']
                    for col in fields_rent:
                        updates_basic[col] = st.text_input(col, value=item.get(col, ''))

                # 연락처 특수 기능 (전화/문자)
                contact_val = updates_basic.get('연락처', '')
                if contact_val:
                    clean_num = re.sub(r'[^0-9]', '', contact_val)
                    if len(clean_num) >= 9:
                        bc1, bc2 = st.columns(2)
                        bc1.markdown(f'''<a href="tel:{clean_num}" target="_self" style="text-decoration:none;">
                            <div style="text-align:center; background-color:#e8f0fe; padding:10px; border-radius:8px; border:1px solid #ccc; font-weight:bold;">📞 전화 걸기</div></a>''', unsafe_allow_html=True)
                        bc2.markdown(f'''<a href="sms:{clean_num}" target="_self" style="text-decoration:none;">
                            <div style="text-align:center; background-color:#e8f0fe; padding:10px; border-radius:8px; border:1px solid #ccc; font-weight:bold;">💬 문자 보내기</div></a>''', unsafe_allow_html=True)

                st.write("")
                if st.form_submit_button("💾 기본정보 저장", use_container_width=True):
                    item.update(updates_basic)
                    success, msg = engine.update_single_row(item, current_sheet)
                    handle_save_result(success, msg)

        # [TAB 2] 시설/내용 수정 (1열 배치 - 모바일 최적화)
        with t2:
            with st.form("form_facility"):
                updates_fac = {}
                
                if is_sale_mode:
                    # 매매 시설 필드 (8개 - 1열 순차 배치)
                    fields_fac_sale = ['주용도', '기보증금', '기월세', '관리비', '주차', 'EV', '현업종']
                    for col in fields_fac_sale:
                        updates_fac[col] = st.text_input(col, value=item.get(col, ''))
                    
                    updates_fac['특이사항'] = st.text_area("특이사항 (내부용)", value=item.get('특이사항', ''), height=100)
                else:
                    # 임대 시설 필드 (7개 - 1열 순차 배치)
                    fields_fac_rent = ['현업종', '주차', '화장실', 'E/V', '층고']
                    for col in fields_fac_rent:
                        updates_fac[col] = st.text_input(col, value=item.get(col, ''))
                    
                    updates_fac['특이사항'] = st.text_area("특이사항 (내부용)", value=item.get('특이사항', ''), height=100)
                    # 용어 통일: '내용' -> '매물특징'
                    updates_fac['매물특징'] = st.text_area("매물특징 (브리핑용)", value=item.get('매물특징', ''), height=150)

                if st.form_submit_button("💾 시설정보 저장", use_container_width=True):
                    item.update(updates_fac)
                    success, msg = engine.update_single_row(item, current_sheet)
                    handle_save_result(success, msg)

        # [TAB 3] 기타 정보 (1열 배치 - 모바일 최적화)
        with t3:
            with st.form("form_etc"):
                updates_etc = {}
                fields_etc = ['접수경로', '접수일', '사진', '광고_포스', '광고_모두', '광고_블로그', '사용승인일', '건축물용도']
                
                for col in fields_etc:
                    val = item.get(col, '')
                    updates_etc[col] = st.text_input(col, value=val)
                
                if st.form_submit_button("💾 기타정보 저장", use_container_width=True):
                    item.update(updates_etc)
                    success, msg = engine.update_single_row(item, current_sheet)
                    handle_save_result(success, msg)

        # [TAB 4] 카톡 브리핑 생성 (자동 완성)
        with t4:
            st.markdown("##### 💬 카톡 브리핑 생성기")
            
            # 인프라 정보 가져오기 (세션에 저장된 값 활용)
            sub_txt = st.session_state.get('last_subway_info', '')
            
            # 브리핑 데이터 조립
            b_loc = f"{item.get('지역_구','')} {item.get('지역_동','')}{sub_txt}"
            b_name = f"{item.get('건물명','')} ({item.get('층','')}층)"
            
            if is_sale_mode:
                b_price = f"매매 {item.get('매매가','-')}만"
                if item.get('수익률'): b_price += f" (수익률 {item.get('수익률')}%)"
                b_spec = f"대지 {item.get('대지면적','-')}평 / 연면 {item.get('연면적','-')}평"
            else:
                b_price = f"보 {item.get('보증금','-')} / 월 {item.get('월차임','-')} / 관 {item.get('관리비','-')}"
                if item.get('권리금') and item.get('권리금') != '0': b_price += f" / 권 {item.get('권리금')}"
                b_spec = f"실 {item.get('면적','-')}평"
            
            # 특이사항(내부용) 제외하고 매물특징(브리핑용)만 사용
            b_feat = item.get('매물특징', '') or "문의 요망"
            
            briefing_text = f"""[매물 브리핑] (네이버 지도 도보 기준)
📍 위치: {b_loc}
🏢 건물: {b_name}
📐 스펙: {b_spec}
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
