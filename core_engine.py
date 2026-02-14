# core_engine.py
# 범공인 Pro v24 Enterprise - Core Data Engine Module (v24.28.1)
# Feature: Negative Floor Support & Robust Regex Sanitization

import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import urllib.parse
import time
import uuid
import re
import traceback
import math
from datetime import datetime
import requests
import json

# ==============================================================================
# [SECTION 1: GLOBAL CONFIGURATION]
# ==============================================================================

SHEET_URL = "https://docs.google.com/spreadsheets/d/1bmTnLu-vMvlAGRSsCI4a8lk00U38covWl5Wfn9JZYVU"

SHEET_GIDS = {
    "임대": "2063575964", "임대(종료)": "791354475", 
    "매매": "1833762712", "매매(종료)": "1597438389",
    "임대브리핑": "982780192", "매매브리핑": "807085458"
}
SHEET_NAMES = list(SHEET_GIDS.keys())

NUMERIC_COLS = ["보증금", "월차임", "권리금", "관리비", "매매가", "수익률", "면적", "대지면적", "연면적", "층"]
STRING_COLS = ["구분", "지역_구", "지역_동", "번지", "건물명", "내용", "비고"]
REQUIRED_COLS = ["번지"]

# ==============================================================================
# [SECTION 2: DATA SANITIZATION ENGINE]
# ==============================================================================

def normalize_headers(df):
    """
    구글 시트 헤더를 표준화합니다.
    동의어 사전을 확장하여 실무 용어에 대응합니다.
    """
    df.columns = df.columns.str.replace(' ', '').str.strip()
    synonym_map = {
        "보증금": ["보증금(만원)", "기보증금(만원)", "기보증금", "보증금", "보증"],
        "월차임": ["월차임(만원)", "기월세(만원)", "월세(만원)", "월세", "기월세", "차임"],
        "권리금": ["권리금_입금가(만원)", "권리금(만원)", "권리금", "권리", "시설권리"],
        "관리비": ["관리비(만원)", "관리비"],
        "매매가": ["매매가(만원)", "매매금액(만원)", "매매금액", "매매가", "매가", "매매"],
        "면적": ["전용면적(평)", "실평수", "전용면적", "면적"],
        "대지면적": ["대지면적(평)", "대지", "대지면적"],
        "연면적": ["연면적(평)", "연면적"],
        "수익률": ["수익률(%)", "수익률"],
        "층": ["해당층", "층", "지상층", "층수"],
        "내용": ["매물특징", "특징", "비고", "내용"],
        "번지": ["지역_번지", "번지", "지번"],
        "구분": ["매물구분", "구분"],
        "건물명": ["건물명", "빌딩명"]
    }
    for standard, aliases in synonym_map.items():
        for alias in aliases:
            clean_alias = alias.replace(' ', '')
            if clean_alias in df.columns:
                df.rename(columns={clean_alias: standard}, inplace=True)
                break 
    return df

def sanitize_dataframe(df):
    """
    데이터프레임 값을 정제합니다.
    [v24.28.1] 층 컬럼은 마이너스(-) 기호를 보존하여 지하층을 올바르게 인식합니다.
    나머지 숫자 컬럼은 숫자와 소수점만 남깁니다.
    """
    for col in NUMERIC_COLS:
        if col in df.columns:
            try:
                val_str = df[col].astype(str)
                
                if col == '층':
                    # [지하층 복구 로직] 음수 기호(-)와 숫자, 소수점 추출
                    # extract를 사용하여 첫 번째로 발견된 숫자 패턴(음수 포함)을 가져옵니다.
                    cleaned_series = val_str.str.extract(r'(-?[\d.]+)')[0]
                else:
                    # [일반 숫자 로직] 숫자(0-9)와 소수점(.)을 제외한 모든 문자 제거
                    cleaned_series = val_str.str.replace(r'[^0-9.]', '', regex=True)
                
                # 빈 문자열 처리 및 숫자 변환
                df[col] = pd.to_numeric(cleaned_series, errors='coerce').fillna(0)
            except: 
                df[col] = 0.0
                
    for col in STRING_COLS:
        if col in df.columns:
            try:
                # 문자열 컬럼: 불필요한 연속 공백을 하나로 줄임
                df[col] = df[col].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
            except: 
                df[col] = ""
                
    return df.fillna("")

def validate_data_integrity(df):
    """
    필수 컬럼 및 데이터 무결성을 검증합니다.
    """
    errors = []
    for col in REQUIRED_COLS:
        if col not in df.columns: 
            errors.append(f"필수 컬럼 누락: {col}")
        elif df[col].astype(str).str.strip().eq("").any():
            errors.append(f"필수값 누락: {col} 컬럼에 빈 행이 있습니다.")
    
    if errors: 
        return False, "\n".join(errors)
    return True, "Integrity Check Passed"

# ==============================================================================
# [SECTION 3: CORE LOAD ENGINE]
# ==============================================================================

def initialize_search_state():
    """
    앱 실행 시 세션 상태(검색 필터 등)를 초기화합니다.
    """
    if 'editor_key_version' not in st.session_state:
        st.session_state.editor_key_version = 0
        
    defaults = {
        'search_keyword': "", 'exact_bunji': "", 'selected_cat': [], 
        'selected_gu': [], 'selected_dong': [], 'is_no_kwon': False,
        'min_price': 0.0, 'max_price': 10000000.0, 'min_dep': 0.0, 'max_dep': 1000000.0,
        'min_rent': 0.0, 'max_rent': 10000.0, 'min_kwon': 0.0, 'max_kwon': 100000.0,
        'min_area': 0.0, 'max_area': 10000.0, 'min_land': 0.0, 'max_land': 10000.0,
        'min_total': 0.0, 'max_total': 10000.0, 'min_fl': -5.0, 'max_fl': 100.0 # 층 범위 확장
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def safe_reset():
    """
    필터 관련 세션 상태를 초기화하고 리런합니다.
    """
    for key in list(st.session_state.keys()):
        # 핵심 시스템 변수는 유지
        if key not in ['current_sheet', 'editor_key_version']:
            del st.session_state[key]
    st.session_state.editor_key_version += 1
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=600)
def load_sheet_data(sheet_name):
    """
    구글 시트에서 데이터를 로드하고 전처리합니다.
    """
    gid = SHEET_GIDS.get(sheet_name)
    if not gid: return None
    
    csv_url = f"{SHEET_URL}/export?format=csv&gid={gid}"
    
    try:
        df = pd.read_csv(csv_url)
        df = normalize_headers(df)
        df = sanitize_dataframe(df)
        
        # 시스템 컬럼 제거
        drop_cols = [c for c in ['선택', 'IronID', 'Unnamed: 0'] if c in df.columns]
        df = df.drop(columns=drop_cols, errors='ignore')
        
        # 로컬 식별자(IronID) 및 선택 컬럼 추가
        df['IronID'] = [str(uuid.uuid4()) for _ in range(len(df))]
        df.insert(0, '선택', False)
        
        return df
    except Exception as e:
        print(f"[Load Error] {e}")
        return None

# ==============================================================================
# [SECTION 4: MATCHING ENGINE]
# ==============================================================================

def create_match_signature(df, keys):
    """
    데이터 매칭을 위한 고유 서명(Signature)을 생성합니다.
    [v24.28.1] 층수의 음수값을 보존하여 서명을 생성합니다.
    """
    temp_df = df.copy()
    temp_df['_match_sig'] = ""
    
    for k in keys:
        try:
            if k in NUMERIC_COLS:
                val_str = temp_df[k].astype(str)
                if k == '층':
                    # 층수는 음수 포함 추출
                    val_str = val_str.str.extract(r'(-?[\d.]+)')[0]
                else:
                    # 나머지는 숫자만
                    val_str = val_str.str.replace(r'[^0-9.]', '', regex=True)
                
                val = pd.to_numeric(val_str, errors='coerce').fillna(0)
                temp_df['_match_sig'] += val.round(1).astype(str).str.replace(r'\.0$', '', regex=True) + "|"
            else:
                # 문자형: 특수문자 제거, 앞 20글자만 사용
                val = temp_df[k].astype(str).str[:20] if k == '내용' else temp_df[k].astype(str)
                temp_df['_match_sig'] += val.str.replace(r'[^가-힣a-zA-Z0-9]', '', regex=True) + "|"
        except: continue
        
    return temp_df

# ==============================================================================
# [SECTION 5: UPDATE ENGINE (FULL LOGIC)]
# ==============================================================================

def update_single_row(updated_row, sheet_name):
    """
    [Phase 4] 상세 보기 화면에서 단일 행을 즉시 업데이트합니다.
    [v24.28.1] 층 수정 시 마이너스 기호 처리 로직 추가.
    """
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # 1. 서버 데이터 로드
        sheet_data = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0))
        
        # 2. 매칭 키 설정
        match_keys = ['번지', '층', '면적'] 
        valid_keys = [k for k in match_keys if k in sheet_data.columns and k in updated_row]
        
        if len(valid_keys) < 2: 
            return False, "식별 키 부족 (번지/층/면적 필수)"
        
        # 3. 로컬 데이터 서명 생성 (정규식 이원화)
        local_sig = ""
        for k in valid_keys:
             val_str = str(updated_row.get(k, ''))
             if k in NUMERIC_COLS:
                 if k == '층':
                     match = re.search(r'(-?[\d.]+)', val_str)
                     val_clean = match.group(1) if match else "0"
                 else:
                     val_clean = re.sub(r'[^0-9.]', '', val_str)
                 
                 try: val = str(round(float(val_clean), 1)).replace('.0', '')
                 except: val = "0"
             else:
                 val = re.sub(r'[^가-힣a-zA-Z0-9]', '', val_str)
             local_sig += val + "|"
             
        # 4. 서버 데이터 서명 생성 (정규식 이원화)
        server_sigs = []
        for _, row in sheet_data.iterrows():
            sig = ""
            for k in valid_keys:
                val_str = str(row.get(k, ''))
                if k in NUMERIC_COLS:
                    if k == '층':
                        match = re.search(r'(-?[\d.]+)', val_str)
                        val_clean = match.group(1) if match else "0"
                    else:
                        val_clean = re.sub(r'[^0-9.]', '', val_str)
                        
                    try: val = str(round(float(val_clean), 1)).replace('.0', '')
                    except: val = "0"
                else:
                    val = re.sub(r'[^가-힣a-zA-Z0-9]', '', val_str)
                sig += val + "|"
            server_sigs.append(sig)
            
        # 5. 매칭 및 업데이트
        try:
            target_idx = server_sigs.index(local_sig)
            
            # 값 덮어쓰기
            for k, v in updated_row.items():
                if k in sheet_data.columns and k not in ['선택', 'IronID']:
                    if k in NUMERIC_COLS:
                        try: 
                            raw_v = str(v)
                            if k == '층':
                                # 층수는 마이너스 허용
                                match = re.search(r'(-?[\d.]+)', raw_v)
                                v_str = match.group(1) if match else "0"
                            else:
                                # 일반 숫자는 마이너스 제거
                                v_str = re.sub(r'[^0-9.]', '', raw_v)
                            
                            v = float(v_str) if v_str else 0.0
                        except: v = 0.0
                    sheet_data.at[target_idx, k] = v
            
            # 6. 저장
            conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=sheet_data)
            return True, "✅ 수정 사항이 저장되었습니다."
            
        except ValueError:
            return False, "❌ 원본 데이터를 찾을 수 없습니다. (키 값이 변경되었을 수 있음)"
            
    except Exception as e:
        return False, f"업데이트 실패: {str(e)}"

def save_updates_to_sheet(edited_df, original_df, sheet_name):
    """
    [Phase 1] 리스트/카드 뷰에서의 대량 수정 사항을 배치 저장합니다.
    [v24.28.1] 지하층수 데이터 보존 로직 적용.
    """
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # 1. 변경된 행 감지
        df_org = original_df.set_index('IronID')
        df_new = edited_df.set_index('IronID')
        
        changed_ids = []
        for iid in df_org.index.intersection(df_new.index):
            row_org = df_org.loc[iid].drop(['선택'], errors='ignore').astype(str)
            row_new = df_new.loc[iid].drop(['선택'], errors='ignore').astype(str)
            if not row_org.equals(row_new):
                changed_ids.append(iid)
        
        if not changed_ids: return True, "변경 사항이 없습니다.", None

        # 2. 재시도 로직
        for attempt in range(3):
            try:
                sheet_data = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0))
                valid_keys = [k for k in ['번지', '층', '면적', '매매가', '보증금'] if k in sheet_data.columns and k in df_org.columns]
                if len(valid_keys) < 2: return False, "식별 키 부족", None

                # 매칭 서명 생성 시에도 층수는 음수 허용 로직이 create_match_signature에 반영됨
                target_sigs = create_match_signature(df_org.loc[changed_ids].reset_index(), valid_keys)['_match_sig'].tolist()
                server_sigs = create_match_signature(sheet_data, valid_keys)
                
                update_count = 0
                for idx, sig in zip(target_sigs, changed_ids):
                    match_indices = server_sigs.index[server_sigs['_match_sig'] == idx].tolist()
                    if match_indices:
                        match_idx = match_indices[0]
                        for col in sheet_data.columns:
                            if col in df_new.columns: 
                                val = df_new.loc[sig, col]
                                if col in NUMERIC_COLS:
                                    try: 
                                        val_str = str(val)
                                        if col == '층':
                                            # 층일 경우 음수 패턴 추출
                                            match = re.search(r'(-?[\d.]+)', val_str)
                                            val_clean = match.group(1) if match else "0"
                                        else:
                                            # 나머지는 숫자만
                                            val_clean = re.sub(r'[^0-9.]', '', val_str)
                                            
                                        val = float(val_clean) if val_clean else 0.0
                                    except: val = 0.0
                                sheet_data.at[match_idx, col] = val
                        update_count += 1
                
                if update_count == 0: return False, "원본 데이터 매칭 실패", None
                
                is_valid, msg = validate_data_integrity(sheet_data)
                if not is_valid: return False, f"무결성 오류: {msg}", None
                
                conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=sheet_data)
                return True, f"✅ {update_count}건 저장 완료!", None
                
            except Exception as e:
                time.sleep(attempt + 1)
                last_err = e
                continue
                
        return False, f"🚨 재시도 실패: {last_err}", None
        
    except Exception as e: 
        return False, f"🚨 치명적 오류: {e}", traceback.format_exc()

def execute_transaction(action_type, target_rows, source_sheet, target_sheet=None):
    """
    [Phase 2] 삭제, 이동, 복구, 복사 트랜잭션을 처리합니다.
    """
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        if target_rows.empty: return False, "대상 없음", None
        
        # 1. 소스 데이터 로드
        src_df = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=source_sheet, ttl=0))
        target_clean = target_rows.drop(columns=['선택', 'IronID'], errors='ignore')
        
        # 2. 매칭 키 설정
        v_keys = [k for k in ['번지', '층', '면적', '보증금', '매매가', '월차임', '내용'] if k in src_df.columns and k in target_clean.columns]
        
        # 3. 서명 생성
        src_sig = create_match_signature(src_df, v_keys)
        tgt_sig = create_match_signature(target_clean, v_keys)
        sigs = tgt_sig['_match_sig'].tolist()

        # 4. 액션 분기
        if action_type in ["delete", "move", "restore"]:
            # 소스에서 제거
            new_src = src_df[~src_sig['_match_sig'].isin(sigs)]
            
            if len(src_df) == len(new_src): 
                return False, "매칭 실패 (이미 삭제되었거나 변경됨)", pd.DataFrame({"Target": sigs[:1], "Server": src_sig['_match_sig'].iloc[:1]})
            
            # 이동/복구: 타겟 시트에 추가
            if action_type in ["move", "restore"] and target_sheet:
                tgt_df = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=target_sheet, ttl=0))
                common_cols = [c for c in src_df.columns if c in tgt_df.columns]
                new_tgt = pd.concat([tgt_df, target_clean[common_cols]], ignore_index=True)
                
                is_valid, msg = validate_data_integrity(new_tgt)
                if not is_valid: return False, msg, None
                
                conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet, data=new_tgt)
            
            # 소스 시트 업데이트
            conn.update(spreadsheet=SHEET_URL, worksheet=source_sheet, data=new_src)
            return True, f"✅ {action_type} 처리 완료", None
        
        elif action_type == "copy":
            tgt_df = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=target_sheet, ttl=0))
            common_cols = [c for c in src_df.columns if c in tgt_df.columns]
            new_tgt = pd.concat([tgt_df, target_clean[common_cols]], ignore_index=True)
            
            conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet, data=new_tgt)
            return True, "✅ 복사 완료", None
            
    except Exception as e: 
        return False, str(e), traceback.format_exc()
