# new_item_renderer.py
# 범공인 Pro v24 Enterprise - New Item Entry Module (v24.97)
# Feature: Single Column Layout, Smart Form, Validation, Auto-Save

import streamlit as st
import pandas as pd
import time
import core_engine as engine

def render_new_item_form():
    """
    신규 매물 등록 인터페이스 (1열 배치 & 모바일 최적화)
    """
    # [A] 상단 네비게이션
    st.subheader("📝 신규 매물 등록")
    
    # 등록 취소 버튼 (목록으로 복귀)
    if st.button("◀ 등록 취소 (목록으로)", use_container_width=True):
        st.session_state.is_adding_new = False
        st.rerun()

    # [B] 모드 판별 (임대 vs 매매)
    current_sheet = st.session_state.current_sheet
    is_sale_mode = "매매" in current_sheet
    
    mode_label = "매매" if is_sale_mode else "임대"
    st.info(f"현재 **[{current_sheet}]** 시트에 신규 매물을 등록합니다.")

    # [C] 입력 폼 시작
    with st.form("new_entry_form"):
        st.markdown("#### 1. 기본 정보")
        
        # 데이터 수집용 딕셔너리
        input_data = {}

        # 1. 구분/지역 (공통)
        input_data['구분'] = st.text_input("구분 (예: 상가, 사무실)")
        input_data['지역_구'] = st.text_input("지역_구 (예: 강남구)")
        input_data['지역_동'] = st.text_input("지역_동 (예: 역삼동)")
        
        # 2. 번지 (필수)
        input_data['번지'] = st.text_input("📍 번지 (필수 입력)")

        if is_sale_mode:
            # [매매 전용 필드]
            input_data['해당층'] = st.text_input("해당층")
            input_data['호실'] = st.text_input("호실")
            
            # 숫자형 데이터 (공란 허용)
            MAX_VAL = 999999999999.0
            input_data['매매가'] = st.number_input("매매가 (만원)", value=None, step=1000.0, max_value=MAX_VAL)
            input_data['대지면적'] = st.number_input("대지면적 (평)", value=None, step=1.0, max_value=MAX_VAL)
            input_data['건축면적'] = st.number_input("건축면적 (평)", value=None, step=1.0, max_value=MAX_VAL)
            input_data['연면적'] = st.number_input("연면적 (평)", value=None, step=1.0, max_value=MAX_VAL)
            input_data['전용면적'] = st.number_input("전용면적 (평)", value=None, step=1.0, max_value=MAX_VAL)
            input_data['수익률'] = st.number_input("수익률 (%)", value=None, step=0.1)
            
        else:
            # [임대 전용 필드]
            input_data['층'] = st.text_input("층 (예: 1, -1)")
            input_data['호실'] = st.text_input("호실")
            
            # 숫자형 데이터 (공란 허용)
            MAX_VAL = 999999999999.0
            input_data['보증금'] = st.number_input("보증금 (만원)", value=None, step=100.0, max_value=MAX_VAL)
            input_data['월차임'] = st.number_input("월차임 (만원)", value=None, step=10.0, max_value=MAX_VAL)
            input_data['관리비'] = st.number_input("관리비 (만원)", value=None, step=5.0, max_value=MAX_VAL)
            input_data['권리금'] = st.number_input("권리금 (만원)", value=None, step=100.0, max_value=MAX_VAL)
            input_data['면적'] = st.number_input("면적 (평)", value=None, step=1.0, max_value=MAX_VAL)

        input_data['연락처'] = st.text_input("연락처 (010-0000-0000)")

        st.divider()
        st.markdown("#### 2. 시설 및 내용")
        
        # [공통 시설/내용]
        input_data['주용도'] = st.text_input("주용도")
        input_data['주차'] = st.text_input("주차")
        input_data['EV'] = st.text_input("EV (승강기)")
        input_data['화장실'] = st.text_input("화장실")
        input_data['층고'] = st.text_input("층고 (m)")
        input_data['현업종'] = st.text_input("현업종")
        
        # 텍스트 영역 (넓게)
        input_data['매물특징'] = st.text_area("매물특징 (브리핑용)", height=150, placeholder="손님에게 보여질 매물의 특징을 입력하세요.")
        input_data['특이사항'] = st.text_area("특이사항 (내부용)", height=100, placeholder="비밀번호, 임대인 성향 등 내부 정보를 입력하세요.")

        st.divider()
        st.markdown("#### 3. 행정 및 광고")
        
        # [공통 행정/광고]
        input_data['접수경로'] = st.text_input("접수경로")
        input_data['접수일'] = st.text_input("접수일 (YYYY-MM-DD)")
        input_data['사진'] = st.text_input("사진 링크 (URL)")
        
        input_data['광고_포스'] = st.text_input("광고_포스 (O/X)")
        input_data['광고_모두'] = st.text_input("광고_모두 (O/X)")
        input_data['광고_블로그'] = st.text_input("광고_블로그 (O/X)")
        
        input_data['사용승인일'] = st.text_input("사용승인일")
        input_data['건축물용도'] = st.text_input("건축물용도")

        st.divider()
        
        # [D] 제출 버튼 및 로직
        submit_btn = st.form_submit_button("🚀 신규 매물 등록 완료", use_container_width=True)
        
        if submit_btn:
            # 1. 필수값 체크
            if not input_data.get('번지') or str(input_data['번지']).strip() == "":
                st.error("⚠️ 번지(주소)는 필수 입력 항목입니다.")
                st.stop()
            
            # 2. 데이터 저장 (Core Engine 호출)
            success, msg = engine.add_new_row(input_data, current_sheet)
            
            # 3. 결과 처리
            if success:
                st.success(f"✅ {msg}")
                time.sleep(1.5)
                # 상태 초기화 및 목록 복귀
                st.session_state.is_adding_new = False
                st.session_state.selected_item = None
                st.rerun()
            else:
                st.error(f"❌ 등록 실패: {msg}")
