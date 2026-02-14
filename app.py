# app.py
# 범공인 Pro v24 Enterprise - Main Application Entry (v24.27.3)
# Feature: Urgent Debugging, Force Visualization, Fragment Disabled

import streamlit as st
import pandas as pd
import time
import math
import core_engine as engine  # [Core Engine v24.24.3]
import map_service as map_api # [Map Service v24.23.7]
import styles                 # [Style Module v24.23.7]
import infra_engine           # [Infra Engine v24.27.2]

# ==============================================================================
# [INIT] 시스템 초기화
# ==============================================================================
st.set_page_config(page_title="범공인 Pro (v24.27.3)", layout="wide", initial_sidebar_state="expanded")
styles.apply_custom_css()

# 상태 변수 초기화
if 'current_sheet' not in st.session_state: st.session_state.current_sheet = engine.SHEET_NAMES[0]
if 'action_status' not in st.session_state: st.session_state.action_status = None 
if 'view_mode' not in st.session_state: st.session_state.view_mode = '🗂️ 카드 모드'
if 'page_num' not in st.session_state: st.session_state.page_num = 1
if 'selected_item' not in st.session_state: st.session_state.selected_item = None 
if 'zoom_level' not in st.session_state: st.session_state.zoom_level = 16 

# 인프라 분석 결과 보존을 위한 상태 변수 초기화 (2버튼 체제)
if 'infra_res_c' not in st.session_state: st.session_state.infra_res_c = None # 상권+역세권
if 'infra_res_d' not in st.session_state: st.session_state.infra_res_d = None # 배후수요
if 'last_analyzed_id' not in st.session_state: st.session_state.last_analyzed_id = None

# 스마트 필터 토글
if 'show_cat_search' not in st.session_state: st.session_state.show_cat_search = False
if 'show_gu_search' not in st.session_state: st.session_state.show_gu_search = False
if 'show_dong_search' not in st.session_state: st.session_state.show_dong_search = False

engine.initialize_search_state()
def sess(key): return st.session_state[key]

# ==============================================================================
# [HELPER] 인프라 분석 캐싱 래퍼 (성능 최적화)
# ==============================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def cached_commercial(lat, lng):
    # v24.27.2: 통합 상권 분석 (지하철 포함 + 하이브리드 검색)
    return infra_engine.get_commercial_analysis(lat, lng)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_demand(lat, lng):
    return infra_engine.get_demand_analysis(lat, lng)

# ==============================================================================
# [SIDEBAR] 필터링 컨트롤 타워
# ==============================================================================
with st.sidebar:
    st.header("📂 관리 도구")
    
    with st.container(border=True):
        st.markdown("##### 📄 작업 시트")
        try: curr_idx = engine.SHEET_NAMES.index(st.session_state.current_sheet)
        except: curr_idx = 0
        selected_sheet = st.selectbox("시트 선택", engine.SHEET_NAMES, index=curr_idx, label_visibility="collapsed")
        
        if selected_sheet != st.session_state.current_sheet:
            st.session_state.current_sheet = selected_sheet
            st.session_state.action_status = None 
            st.session_state.editor_key_version += 1
            st.session_state.page_num = 1
            st.session_state.selected_item = None
            st.session_state.zoom_level = 16
            
            # 시트 변경 시 분석 결과 초기화
            st.session_state.infra_res_c = None
            st.session_state.infra_res_d = None
            st.session_state.last_analyzed_id = None

            if 'df_main' in st.session_state: del st.session_state.df_main
            
            keys_to_clear = [k for k in st.session_state.keys() if k.startswith("chk_")]
            for k in keys_to_clear: del st.session_state[k]
            
            st.cache_data.clear()
            st.rerun()

    if 'df_main' not in st.session_state:
        with st.spinner("데이터 로드 중..."):
            loaded_df = engine.load_sheet_data(st.session_state.current_sheet)
            if loaded_df is not None: st.session_state.df_main = loaded_df
            else: st.error("🚨 데이터 로드 실패."); st.stop()
    df_main = st.session_state.df_main

    st.write(""); st.text_input("통합 검색", key='search_keyword'); st.text_input("번지 검색", key='exact_bunji'); st.write("")
    
    with st.container(border=True):
        st.markdown("##### 🏷️ 항목 필터링")
        c1, c2 = st.columns([4, 1]); c1.markdown("구분"); 
        if c2.button("🔍", key="btn_cat"): st.session_state.show_cat_search = not st.session_state.show_cat_search
        unique_cat = sorted(df_main['구분'].astype(str).unique().tolist()) if '구분' in df_main.columns else []
        if st.session_state.show_cat_search: 
            term = st.text_input("구분 검색", key="cat_term")
            if term: unique_cat = [x for x in unique_cat if term in x]
        st.multiselect("구분", unique_cat, key='selected_cat', placeholder="전체", label_visibility="collapsed")
        
        c3, c4 = st.columns([4, 1]); c3.markdown("지역 (구)"); 
        if c4.button("🔍", key="btn_gu"): st.session_state.show_gu_search = not st.session_state.show_gu_search
        unique_gu = sorted(df_main['지역_구'].astype(str).unique().tolist()) if '지역_구' in df_main.columns else []
        if st.session_state.show_gu_search: 
            term = st.text_input("구 검색", key="gu_term")
            if term: unique_gu = [x for x in unique_gu if term in x]
        st.multiselect("지역 (구)", unique_gu, key='selected_gu', placeholder="전체", label_visibility="collapsed")
        
        c5, c6 = st.columns([4, 1]); c5.markdown("지역 (동)"); 
        if c6.button("🔍", key="btn_dong"): st.session_state.show_dong_search = not st.session_state.show_dong_search
        unique_dong = []
        if '지역_동' in df_main.columns:
            if st.session_state.selected_gu: unique_dong = sorted(df_main[df_main['지역_구'].isin(st.session_state.selected_gu)]['지역_동'].astype(str).unique().tolist())
            else: unique_dong = sorted(df_main['지역_동'].astype(str).unique().tolist())
        if st.session_state.show_dong_search:
            term = st.text_input("동 검색", key="dong_term")
            if term: unique_dong = [x for x in unique_dong if term in x]
        st.multiselect("지역 (동)", unique_dong, key='selected_dong', placeholder="전체", label_visibility="collapsed")

    st.write("")
    is_sale_mode = "매매" in st.session_state.current_sheet
    with st.expander("💰 상세 설정", expanded=False):
        MAX_P = 10000000.0; MAX_A = 1000000.0
        if is_sale_mode:
            c1, c2 = st.columns(2); c1.number_input("최소 매가", key='min_price', value=sess('min_price')); c2.number_input("최대 매가", key='max_price', value=sess('max_price'), max_value=MAX_P)
            c3, c4 = st.columns(2); c3.number_input("최소 대지", key='min_land', value=sess('min_land')); c4.number_input("최대 대지", key='max_land', value=sess('max_land'), max_value=MAX_A)
        else:
            c1, c2 = st.columns(2); c1.number_input("최소 보증", key='min_dep', value=sess('min_dep')); c2.number_input("최대 보증", key='max_dep', value=sess('max_dep'), max_value=MAX_P)
            c3, c4 = st.columns(2); c3.number_input("최소 월세", key='min_rent', value=sess('min_rent')); c4.number_input("최대 월세", key='max_rent', value=sess('max_rent'), max_value=MAX_P)
            c7, c8 = st.columns(2); c7.number_input("최소 권리", key='min_kwon', value=sess('min_kwon')); c8.number_input("최대 권리", key='max_kwon', value=sess('max_kwon'), max_value=MAX_P)
        st.divider()
        c1, c2 = st.columns(2); c1.number_input("최소 면적", key='min_area', value=sess('min_area')); c2.number_input("최대 면적", key='max_area', value=sess('max_area'), max_value=MAX_A)
        c1, c2 = st.columns(2); c1.number_input("최저 층", key='min_fl', value=0.0, min_value=-10.0); c2.number_input("최고 층", key='max_fl', value=100.0, max_value=200.0)
        st.checkbox("무권리만 보기", key='is_no_kwon')
    
    st.divider()
    if st.button("🔄 초기화"): engine.safe_reset()
    st.markdown("---")
    view_option = st.radio("보기", ['🗂️ 카드 모드', '📋 리스트 모드'], index=0 if st.session_state.view_mode == '🗂️ 카드 모드' else 1)
    if view_option != st.session_state.view_mode: st.session_state.view_mode = view_option; st.rerun()

# ==============================================================================
# [MAIN CONTENT]
# ==============================================================================
st.title("🏙️ 범공인 매물장 (Pro)")

# [v24.27.3 Debugging] Fragment 해제 (주석 처리)
# @st.fragment
def main_list_view():
    # --------------------------------------------------------------------------
    # [DETAIL VIEW] Edit Mode with Map & Infra
    # --------------------------------------------------------------------------
    if st.session_state.selected_item is not None:
        item = st.session_state.selected_item
        
        # 매물이 바뀌면 분석 결과 초기화
        current_id = item.get('IronID')
        if st.session_state.last_analyzed_id != current_id:
            st.session_state.infra_res_c = None
            st.session_state.infra_res_d = None
            st.session_state.last_analyzed_id = current_id

        c_back, c_title = st.columns([1, 5])
        if c_back.button("◀ 목록"): st.session_state.selected_item = None; st.rerun()
        c_title.markdown(f"### {item.get('건물명', '매물 상세')}")

        addr_full = f"{item.get('지역_구', '')} {item.get('지역_동', '')} {item.get('번지', '')}"
        
        # [MAP & ZOOM CONTROLLER]
        with st.container():
            c_info, c_zoom = st.columns([3, 1])
            c_info.caption(f"📍 {addr_full}")
            
            # Zoom Buttons
            z_minus, z_plus = c_zoom.columns(2)
            if z_minus.button("－", key="zoom_out", use_container_width=True, type="secondary"):
                if st.session_state.zoom_level > 10: st.session_state.zoom_level -= 1
                st.rerun()
            if z_plus.button("＋", key="zoom_in", use_container_width=True, type="secondary"):
                if st.session_state.zoom_level < 19: st.session_state.zoom_level += 1
                st.rerun()
            
            lat, lng = map_api.get_naver_geocode(addr_full)
            if lat and lng:
                map_img = map_api.fetch_map_image(lat, lng, zoom_level=st.session_state.zoom_level)
                if map_img: st.image(map_img, use_column_width=True)
                else: st.warning("지도 로드 실패")
                
                # [카카오맵 연동]
                st.link_button("📍 카카오맵에서 실시간 로드뷰 확인", f"https://map.kakao.com/link/map/{item.get('건물명', '매물')},{lat},{lng}", use_container_width=True, type="primary")
            else: st.warning("위치 확인 불가")

        st.divider()
        with st.form("edit_form"):
            st.markdown("#### 📝 매물 정보 수정")
            c1, c2 = st.columns(2)
            new_cat = c1.text_input("구분", value=item.get('구분', ''))
            new_name = c2.text_input("건물명", value=item.get('건물명', ''))
            
            c3, c4 = st.columns(2)
            if is_sale_mode:
                new_price = c3.text_input("매매가", value=str(item.get('매매가', 0)).replace(',',''))
                new_yield = c4.text_input("수익률", value=str(item.get('수익률', 0)).replace(',',''))
            else:
                new_dep = c3.text_input("보증금", value=str(item.get('보증금', 0)).replace(',',''))
                new_rent = c4.text_input("월세", value=str(item.get('월차임', 0)).replace(',',''))
            
            c5, c6 = st.columns(2)
            if is_sale_mode:
                 new_land = c5.text_input("대지면적", value=str(item.get('대지면적', 0)).replace(',',''))
                 new_total = c6.text_input("연면적", value=str(item.get('연면적', 0)).replace(',',''))
            else:
                 new_kwon = c5.text_input("권리금", value=str(item.get('권리금', 0)).replace(',',''))
                 new_man = c6.text_input("관리비", value=str(item.get('관리비', 0)).replace(',',''))

            c7, c8 = st.columns(2)
            new_area = c7.text_input("전용면적", value=str(item.get('면적', 0)).replace(',',''))
            new_floor = c8.text_input("층수", value=str(item.get('층', '')))
            
            new_desc = st.text_area("특징", value=item.get('내용', ''), height=100)
            new_memo = st.text_area("비고", value=item.get('비고', ''), height=60)

            if st.form_submit_button("💾 수정 완료", type="primary", use_container_width=True):
                updated_data = item.copy()
                updated_data.update({'구분': new_cat, '건물명': new_name, '면적': new_area, '층': new_floor, '내용': new_desc, '비고': new_memo})
                if is_sale_mode: updated_data.update({'매매가': new_price, '수익률': new_yield, '대지면적': new_land, '연면적': new_total})
                else: updated_data.update({'보증금': new_dep, '월차임': new_rent, '권리금': new_kwon, '관리비': new_man})
                
                success, msg = engine.update_single_row(updated_data, st.session_state.current_sheet)
                if success:
                    st.success(msg); time.sleep(1.5); del st.session_state.df_main
                    st.session_state.selected_item = None; st.cache_data.clear(); st.rerun()
                else: st.error(msg)
        
        # [INFRA ANALYSIS - V24.27.3 DEBUGGING MODE]
        st.markdown("---")
        st.subheader("🏗️ 주변 인프라 분석 (반경 500~700m)")
        
        if not (lat and lng):
            st.error("⚠️ 좌표 정보가 없어 분석할 수 없습니다.")
        else:
            col_left, col_right = st.columns([1, 1])
            
            # [Left] 상권 & 역세권 분석
            with col_left:
                if st.button("📊 상권 & 역세권 분석", use_container_width=True):
                    try:
                        with st.spinner("지하철 및 상권 스캔 중..."):
                            res = cached_commercial(lat, lng)
                            st.session_state.infra_res_c = res
                            # [v24.27.3 디버깅: 엔진 응답 강제 출력]
                            st.write("DEBUG: 엔진 응답 확인", res.get('counts'))
                    except Exception as e: st.error(f"오류: {e}")

            # [Right] 배후 수요 분석
            with col_right:
                if st.button("🏢 배후 수요 분석", use_container_width=True):
                    try:
                        with st.spinner("배후 수요 탐색 중..."):
                            st.session_state.infra_res_d = cached_demand(lat, lng)
                    except Exception as e: st.error(f"오류: {e}")

            st.write("") # 간격

            # 2. 결과 출력 (Session State 기반)
            
            # [A. 상권 & 역세권 결과 출력부]
            if st.session_state.infra_res_c:
                c_data = st.session_state.infra_res_c
                
                # 1. 지하철 역세권 뱃지
                sub = c_data.get('subway', {})
                if sub.get('station') and sub['station'] != "정보 없음":
                    st.success(f"**🚆 {sub['station']} {sub.get('exit','')}** | 도보 약 {sub['walk']}분 ({sub['dist']}m)")
                else:
                    st.warning("🚆 반경 700m 내 지하철역 없음")
                
                # 2. 10대 업종 수치 뱃지 (차트 위 강제 출력)
                st.markdown("##### 📊 주변 업종 상세 수치")
                counts = c_data.get('counts', {})
                
                # [v24.27.3 최후의 보루: 데이터 없으면 더미 데이터라도 표시]
                if not counts:
                    counts = {"데이터 대기 중": 0}

                # 5개씩 2줄로 숫자 먼저 보여주기
                m_cols = st.columns(5)
                # counts가 비어있지 않으므로 루프 가능
                items = list(counts.items())
                for i, (name, val) in enumerate(items):
                    m_cols[i % 5].metric(name, f"{val}개")
                
                st.write("") # 간격
                
                # 3. 차트와 앵커시설 2열 배치
                chart_col, anchor_col = st.columns([1.2, 1])
                with chart_col:
                    st.markdown("##### 📈 밀집도 그래프")
                    # DataFrame으로 형식을 완전히 굳혀서 전달 (수치 실종 방지)
                    df_chart = pd.DataFrame.from_dict(counts, orient='index', columns=['개수'])
                    st.bar_chart(df_chart, height=400, color="#FF8C00") # 오렌지색
                
                with anchor_col:
                    st.markdown("##### 🏆 브랜드 Top 10")
                    st.dataframe(c_data['anchors'], hide_index=True, use_container_width=True)

            # [B. 배후 수요 결과]
            if st.session_state.infra_res_d is not None:
                d_df = st.session_state.infra_res_d
                
                st.divider()
                # [배후수요 요약 뱃지]
                office_cnt = len(d_df[d_df['구분'] == '업무시설']) if not d_df.empty and '구분' in d_df.columns else 0
                school_cnt = len(d_df[d_df['구분'].str.contains('교육')]) if not d_df.empty and '구분' in d_df.columns else 0
                
                if office_cnt > 0 or school_cnt > 0:
                    st.info(f"🏠 **배후수요**: 업무({office_cnt}) / 교육({school_cnt})")
                else:
                    st.info("🏠 **인근 배후수요**: 주요 집객 시설 없음")

                st.markdown("##### 🏢 주요 수요 시설 리스트 (거리순)")
                if not d_df.empty:
                    st.dataframe(d_df[['구분', '시설명', '거리(m)']], hide_index=True, use_container_width=True)
                else:
                    st.caption("데이터 없음")

        return

    # --------------------------------------------------------------------------
    # [LIST VIEW] Filter & Pagination
    # --------------------------------------------------------------------------
    df_filtered = df_main.copy()
    if '구분' in df_filtered.columns and st.session_state.selected_cat: df_filtered = df_filtered[df_filtered['구분'].isin(st.session_state.selected_cat)]
    if '지역_구' in df_filtered.columns and st.session_state.selected_gu: df_filtered = df_filtered[df_filtered['지역_구'].isin(st.session_state.selected_gu)]
    if '지역_동' in df_filtered.columns and st.session_state.selected_dong: df_filtered = df_filtered[df_filtered['지역_동'].isin(st.session_state.selected_dong)]
    if '번지' in df_filtered.columns and st.session_state.exact_bunji: df_filtered = df_filtered[df_filtered['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]
    search_val = st.session_state.search_keyword.strip()
    if search_val:
        search_scope = df_filtered.drop(columns=['선택', 'IronID'], errors='ignore')
        mask = search_scope.fillna("").astype(str).apply(lambda x: ' '.join(x), axis=1).str.contains(search_val, case=False)
        df_filtered = df_filtered[mask]
    
    if is_sale_mode:
        if '매매가' in df_filtered.columns and not df_filtered.empty: df_filtered = df_filtered[(df_filtered['매매가'] >= st.session_state.min_price) & (df_filtered['매매가'] <= st.session_state.max_price)]
        if '대지면적' in df_filtered.columns and not df_filtered.empty: df_filtered = df_filtered[(df_filtered['대지면적'] >= st.session_state.min_land) & (df_filtered['대지면적'] <= st.session_state.max_land)]
    else:
        if '보증금' in df_filtered.columns and not df_filtered.empty: df_filtered = df_filtered[(df_filtered['보증금'] >= st.session_state.min_dep) & (df_filtered['보증금'] <= st.session_state.max_dep)]
        if '월차임' in df_filtered.columns and not df_filtered.empty: df_filtered = df_filtered[(df_filtered['월차임'] >= st.session_state.min_rent) & (df_filtered['월차임'] <= st.session_state.max_rent)]
        
        # [권리금 필터 로직 교정]
        if '권리금' in df_filtered.columns and not df_filtered.empty:
            if st.session_state.is_no_kwon:
                df_filtered = df_filtered[df_filtered['권리금'] == 0]
            else:
                df_filtered = df_filtered[(df_filtered['권리금'] >= st.session_state.min_kwon) & (df_filtered['권리금'] <= st.session_state.max_kwon)]
    
    if '면적' in df_filtered.columns and not df_filtered.empty: df_filtered = df_filtered[(df_filtered['면적'] >= st.session_state.min_area) & (df_filtered['면적'] <= st.session_state.max_area)]
    if '층' in df_filtered.columns and not df_filtered.empty: df_filtered = df_filtered[(df_filtered['층'] >= st.session_state.min_fl) & (df_filtered['층'] <= st.session_state.max_fl)]

    total_count = len(df_filtered)
    if total_count == 0: st.warning("🔍 검색 결과가 없습니다."); return

    ITEMS_PER_PAGE = 50
    total_pages = math.ceil(total_count / ITEMS_PER_PAGE)
    if st.session_state.page_num > total_pages: st.session_state.page_num = 1
    
    start_idx = (st.session_state.page_num - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    df_page = df_filtered.iloc[start_idx:end_idx]
    
    st.info(f"📋 검색 결과: **{total_count}**건 (페이지: {st.session_state.page_num}/{total_pages})")

    # ==========================================================================
    # [VIEW MODE A] CARD VIEW
    # ==========================================================================
    if st.session_state.view_mode == '🗂️ 카드 모드':
        c_act1, c_act2 = st.columns(2)
        if c_act1.button("✅ 전체 선택", key="sel_all_card"):
            target_ids = df_page['IronID'].tolist()
            st.session_state.df_main.loc[st.session_state.df_main['IronID'].isin(target_ids), '선택'] = True
            for iid in target_ids: st.session_state[f"chk_{iid}"] = True
            st.rerun()
        if c_act2.button("⬜ 전체 해제", key="desel_all_card"):
            st.session_state.df_main['선택'] = False
            for iid in st.session_state.df_main['IronID']:
                if f"chk_{iid}" in st.session_state: st.session_state[f"chk_{iid}"] = False
            st.rerun()

        with st.container(height=500):
            for idx, row in df_page.iterrows():
                raw_ho = str(row.get('호실', '')).replace('호', '').strip()
                ho_str = f"{raw_ho}호" if raw_ho else ""
                gubun = row.get('구분', '매물')
                
                if is_sale_mode:
                    price = f"매매 {int(row.get('매매가', 0)):,}만"
                    if row.get('수익률', 0) > 0: price += f" ({row['수익률']}%)"
                else:
                    price = f"보 {int(row.get('보증금', 0)):,} / 월 {int(row.get('월차임', 0)):,}"
                    if row.get('관리비', 0) > 0: price += f" (관 {int(row['관리비']):,})"
                addr = f"{row.get('지역_구', '')} {row.get('지역_동', '')} {row.get('번지', '')}"
                floor = f"{row.get('층', '')}층"
                
                if is_sale_mode: spec = f"대지:{row.get('대지면적', 0)}평 / 연면:{row.get('연면적', 0)}평"
                else:
                    spec = f"{ho_str} / 실:{row.get('면적', 0)}평"
                    if row.get('권리금', 0) > 0: spec += f" / 권:{int(row['권리금']):,}"
                    if row.get('현업종', ''): spec += f" / {row['현업종']}"
                
                c_chk, c_card, c_btn = st.columns([1, 10, 3]) 
                is_checked = st.session_state.df_main.loc[st.session_state.df_main['IronID'] == row['IronID'], '선택'].values[0]
                chk_key = f"chk_{row['IronID']}"
                if chk_key not in st.session_state: st.session_state[chk_key] = bool(is_checked)
                
                if c_chk.checkbox("", key=chk_key):
                    if not is_checked:
                        st.session_state.df_main.loc[st.session_state.df_main['IronID'] == row['IronID'], '선택'] = True
                        st.rerun()
                else:
                    if is_checked:
                        st.session_state.df_main.loc[st.session_state.df_main['IronID'] == row['IronID'], '선택'] = False
                        st.rerun()

                c_card.markdown(f"""
                <div class="listing-card">
                    <div class="card-row-1"><span class="card-tag">{gubun}</span><span class="card-price">{price}</span></div>
                    <div class="card-row-2">📍 {addr} <span style="color:#ddd">|</span> {floor}</div>
                    <div class="card-row-3">📐 {spec}</div>
                </div>""", unsafe_allow_html=True)
                
                with c_btn.container():
                    if st.button("상세", key=f"btn_detail_{row['IronID']}", use_container_width=True):
                        st.session_state.selected_item = row; st.rerun()
        
        c_prev, c_page, c_next = st.columns([1, 1, 1])
        if c_prev.button("◀", key="prev_card"):
            if st.session_state.page_num > 1: st.session_state.page_num -= 1; st.rerun()
        c_page.markdown(f"<div class='pagination-text'>{st.session_state.page_num} / {total_pages}</div>", unsafe_allow_html=True)
        if c_next.button("▶", key="next_card"):
            if st.session_state.page_num < total_pages: st.session_state.page_num += 1; st.rerun()

    # ==========================================================================
    # [VIEW MODE B] LIST VIEW
    # ==========================================================================
    else:
        c_act1, c_act2 = st.columns(2)
        if c_act1.button("✅ 전체 선택", key="sel_all_list"):
            target_ids = df_page['IronID'].tolist()
            st.session_state.df_main.loc[st.session_state.df_main['IronID'].isin(target_ids), '선택'] = True
            st.session_state.editor_key_version += 1; st.rerun()
        if c_act2.button("⬜ 전체 해제", key="desel_all_list"):
            st.session_state.df_main['선택'] = False
            st.session_state.editor_key_version += 1; st.rerun()

        df_list_view = df_page.copy()
        df_list_view.insert(0, '🔍', False)

        col_cfg = {
            "🔍": st.column_config.CheckboxColumn(width="small", label="상세"),
            "선택": st.column_config.CheckboxColumn(width="small"), 
            "IronID": None
        }
        format_map = {"매매가": "%d", "보증금": "%d", "월차임": "%d", "권리금": "%d", "면적": "%.1f", "대지면적": "%.1f", "연면적": "%.1f"}
        for col, fmt in format_map.items():
            if col in df_filtered.columns: col_cfg[col] = st.column_config.NumberColumn(col, format=fmt)
        if "내용" in df_filtered.columns: col_cfg["내용"] = st.column_config.TextColumn("특징", width="large")
        
        cols = ["내용", "보증금", "월차임", "매매가", "권리금", "관리비"]
        dis_cols = [c for c in df_filtered.columns if c not in ['선택', '🔍'] + cols]
        
        edited_df = st.data_editor(
            df_list_view,
            disabled=dis_cols,
            use_container_width=True,
            hide_index=True,
            column_config=col_cfg,
            key=f"editor_{st.session_state.editor_key_version}",
            height=400, 
            num_rows="fixed"
        )
        
        trigger_rows = edited_df[edited_df['🔍'] == True]
        if not trigger_rows.empty:
            target_row = df_main[df_main['IronID'] == trigger_rows.iloc[0]['IronID']].iloc[0]
            st.session_state.selected_item = target_row
            st.rerun()
        
        c_prev, c_page, c_next = st.columns([1, 1, 1])
        if c_prev.button("◀", key="prev_list"):
            if st.session_state.page_num > 1: st.session_state.page_num -= 1; st.rerun()
        c_page.markdown(f"<div class='pagination-text'>{st.session_state.page_num} / {total_pages}</div>", unsafe_allow_html=True)
        if c_next.button("▶", key="next_list"):
            if st.session_state.page_num < total_pages: st.session_state.page_num += 1; st.rerun()

        st.divider()
        if st.button("💾 변경사항 저장 (서버 반영)", type="primary", use_container_width=True, key="btn_save"):
            with st.status("💾 저장 중...", expanded=True) as status:
                save_df = edited_df.drop(columns=['🔍'], errors='ignore')
                success, msg, debug = engine.save_updates_to_sheet(save_df, st.session_state.df_main, st.session_state.current_sheet)
                if success:
                    status.update(label="완료!", state="complete"); st.success(msg); time.sleep(1.0)
                    if 'df_main' in st.session_state: del st.session_state.df_main
                    st.cache_data.clear(); st.rerun()
                else: st.error(msg)
    
    # --- UNIVERSAL ACTION BAR ---
    st.divider()
    if st.session_state.view_mode == '📋 리스트 모드':
        try: selected_rows = edited_df[edited_df['선택'] == True].drop(columns=['🔍'], errors='ignore')
        except: selected_rows = pd.DataFrame()
    else:
        selected_rows = st.session_state.df_main[st.session_state.df_main['선택'] == True]
        
    if len(selected_rows) > 0:
        st.success(f"✅ {len(selected_rows)}건 선택됨")
        cur_tab = st.session_state.current_sheet
        is_end = "(종료)" in cur_tab
        base_tab = cur_tab.replace("(종료)", "").replace("브리핑", "").strip()
        base_label = "매매" if "매매" in cur_tab else "임대"
        
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            if "브리핑" in cur_tab: st.button("🚫", disabled=True, use_container_width=True, key="btn_move_disabled")
            elif is_end:
                if st.button(f"♻️ 복구({base_label})", use_container_width=True, key="btn_restore"): st.session_state.action_status = 'restore_confirm'
            else:
                if st.button(f"🚀 {base_label}(종료)", use_container_width=True, key="btn_move"): st.session_state.action_status = 'move_confirm'
        with ac2:
            if "브리핑" not in cur_tab:
                if st.button(f"📋 {base_label}브리핑", use_container_width=True, key="btn_copy"): st.session_state.action_status = 'copy_confirm'
            else: st.button("🚫", disabled=True, use_container_width=True, key="btn_copy_disabled")
        with ac3:
            if st.button("🗑️ 삭제", type="primary", use_container_width=True, key="btn_del"): st.session_state.action_status = 'delete_confirm'

        if st.session_state.action_status == 'move_confirm':
            target = f"{base_tab}(종료)"
            with st.status(f"🚀 이동 중...", expanded=True):
                if st.button("확인", key="conf_move", type="primary"):
                    _, msg, _ = engine.execute_transaction("move", selected_rows, cur_tab, target)
                    st.success(msg); time.sleep(1); del st.session_state.df_main; engine.safe_reset()

        elif st.session_state.action_status == 'restore_confirm':
            with st.status(f"♻️ 복구 중...", expanded=True):
                if st.button("확인", key="conf_restore", type="primary"):
                    _, msg, _ = engine.execute_transaction("restore", selected_rows, cur_tab, base_tab)
                    st.success(msg); time.sleep(1); del st.session_state.df_main; engine.safe_reset()

        elif st.session_state.action_status == 'copy_confirm':
            target = f"{base_tab}브리핑"
            with st.status(f"📋 복사 중...", expanded=True):
                if st.button("확인", key="conf_copy", type="primary"):
                    _, msg, _ = engine.execute_transaction("copy", selected_rows, cur_tab, target)
                    st.success(msg); time.sleep(1); st.session_state.action_status = None

        elif st.session_state.action_status == 'delete_confirm':
            with st.status(f"🗑️ 삭제 중...", expanded=True):
                st.error("복구 불가"); 
                if st.button("확인", key="conf_del", type="primary"):
                    _, msg, _ = engine.execute_transaction("delete", selected_rows, cur_tab)
                    st.success(msg); time.sleep(1); del st.session_state.df_main; engine.safe_reset()

    with st.container(): st.write(""); st.write("")

main_list_view()
