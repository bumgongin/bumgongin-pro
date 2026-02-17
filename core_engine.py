# core_engine.py
# 범공인 Pro v24 Enterprise - Core Data Engine Module (v24.29.2)
# Feature: Negative Floor Regex Fix (Precision Surgery)

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
    [v24.29.2 수술 완료] '층' 컬럼은 마이너스(-) 기호를 보존하여 지하층을 올바르게 인식합니다.
    나머지 숫자 컬럼(금액, 면적 등)은 음수가 없으므로 기존대로 정제합니다.
    """
    for col in NUMERIC_COLS:
        if col in df.columns:
            try:
                val_str = df[col].astype(str)
                
                # [수정된 로직] 층수는 마이너스 허용, 그 외는 숫자만 남김
                if col == '층':
                    # 정규식: 음수 기호(-) 옵션 포함, 숫자 및 소수점 추출
                    cleaned_series = val_str.str.extract(r'(-?[\d.]+)')[0]
                    # 층수는 결측 시 1층으로 가정
                    df[col] = pd.to_numeric(cleaned_series, errors='coerce').fillna(1)
                else:
                    # 기존 로직: 숫자(0-9)와 소수점(.)을 제외한 모든 문자 제거 (음수 불가)
                    cleaned_series = val_str.str.replace(r'[^0-9.]', '', regex=True)
                    # 금액/면적은 결측 시 0으로 가정
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
        'min_total': 0.0, 'max_total': 10000.0, 'min_fl': -5.0, 'max_fl': 100.0
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
    구글 시트에서 데이터를 로드하고 전처리합니다. (IronID 보존 및 빈칸 채우기)
    """
    gid = SHEET_GIDS.get(sheet_name)
    if not gid: return None
    
    csv_url = f"{SHEET_URL}/export?format=csv&gid={gid}"
    
    try:
        df = pd.read_csv(csv_url)
        df = normalize_headers(df)
        df = sanitize_dataframe(df)
        
        # [수정 지점] IronID 열을 확인하고 비어있는 칸(NaN)에 고유 번호를 채웁니다.
        if 'IronID' not in df.columns:
            df['IronID'] = [str(uuid.uuid4()) for _ in range(len(df))]
        else:
            # 시트에 열은 있지만 칸이 비어있는 경우를 대비한 안전장치
            df['IronID'] = df['IronID'].apply(lambda x: str(uuid.uuid4()) if pd.isna(x) or str(x).strip() == "" else str(x))
        
        if '선택' in df.columns: df = df.drop(columns=['선택'])
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
    """
    temp_df = df.copy()
    temp_df['_match_sig'] = ""
    
    for k in keys:
        try:
            if k in NUMERIC_COLS:
                val_str = temp_df[k].astype(str)
                if k == '층':
                    val_str = val_str.str.extract(r'(-?[\d.]+)')[0]
                else:
                    val_str = val_str.str.replace(r'[^0-9.]', '', regex=True)
                
                val = pd.to_numeric(val_str, errors='coerce').fillna(0)
                temp_df['_match_sig'] += val.round(1).astype(str).str.replace(r'\.0$', '', regex=True) + "|"
            else:
                val = temp_df[k].astype(str).str[:20] if k == '내용' else temp_df[k].astype(str)
                temp_df['_match_sig'] += val.str.replace(r'[^가-힣a-zA-Z0-9]', '', regex=True) + "|"
        except: continue
        
    return temp_df

# ==============================================================================
# [SECTION 5: UPDATE ENGINE (FULL LOGIC)]
# ==============================================================================

def update_single_row(updated_row, sheet_name):
    """
    [Phase 4] IronID를 기준으로 단일 행을 즉시 업데이트합니다. (구/동/번지 수정 가능)
    """
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # 1. 서버 데이터 로드
        sheet_data = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0))
        
        # 2. 고유 식별자(IronID) 확인
        target_id = updated_row.get('IronID')
        if not target_id or 'IronID' not in sheet_data.columns:
            return False, "❌ 식별 불가 (먼저 상세페이지에서 저장을 수행하여 ID를 생성하세요)"
        
        # 3. 매칭 및 업데이트 (ID로 행 위치 찾기)
        try:
            # 문자열로 변환하여 정확히 비교
            match_list = sheet_data.index[sheet_data['IronID'].astype(str) == str(target_id)].tolist()
            
            if not match_list:
                return False, "❌ 원본 데이터를 찾을 수 없습니다. (ID 매칭 실패)"
            
            row_idx = match_list[0]
            
            # 4. 값 덮어쓰기 (선택/IronID 제외)
            for k, v in updated_row.items():
                if k in sheet_data.columns and k not in ['선택', 'IronID']:
                    # 숫자 컬럼인 경우 정제 후 소수점 처리
                    if k in NUMERIC_COLS:
                        try:
                            val_str = re.sub(r'[^0-9.-]', '', str(v)) if v else "0"
                            v = float(val_str) if val_str else 0.0
                        except: v = 0.0
                    sheet_data.at[row_idx, k] = v
            
            # 5. 저장
            conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=sheet_data)
            return True, "✅ 정보가 안전하게 저장되었습니다."
            
        except Exception as e:
            return False, f"매칭 오류: {str(e)}"
            
    except Exception as e:
        return False, f"저장 실패: {str(e)}"

def save_updates_to_sheet(edited_df, original_df, sheet_name):
    """
    [Phase 1] IronID를 기준으로 리스트 뷰의 대량 수정 사항을 안전하게 저장합니다.
    """
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # 1. 변경된 행만 추출 (IronID 기준 대조)
        df_org = original_df.set_index('IronID')
        df_new = edited_df.set_index('IronID')
        changed_ids = []
        for iid in df_org.index.intersection(df_new.index):
            # 선택 체크박스를 제외한 나머지 데이터가 변했는지 확인
            if not df_org.loc[iid].drop(['선택'], errors='ignore').astype(str).equals(
                   df_new.loc[iid].drop(['선택'], errors='ignore').astype(str)):
                changed_ids.append(iid)
        
        if not changed_ids: return True, "변경 사항 없음", None

        # 2. 서버 데이터 로드 (실시간 반영을 위해 ttl=0)
        sheet_data = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0))
        
        if 'IronID' not in sheet_data.columns:
            return False, "❌ 시트에 IronID 열이 없습니다. 먼저 상세페이지에서 저장을 한 번 수행하세요.", None

        # 3. ID 매칭 및 값 덮어쓰기
        for sig in changed_ids:
            # 서버 시트에서 해당 IronID가 몇 번째 줄인지 찾기
            match_list = sheet_data.index[sheet_data['IronID'].astype(str) == str(sig)].tolist()
            if match_list:
                target_idx = match_list[0]
                for col in sheet_data.columns:
                    # '선택'이나 'IronID'는 시트 값을 건드리지 않고 나머지 정보만 업데이트
                    if col in df_new.columns and col not in ['선택', 'IronID']:
                        sheet_data.at[target_idx, col] = df_new.loc[sig, col]

        # 4. 최종 저장
        conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=sheet_data)
        return True, f"✅ {len(changed_ids)}건 저장 완료", None
        
    except Exception as e: 
        return False, f"저장 실패: {str(e)}", None

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
