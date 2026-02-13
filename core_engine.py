# core_engine.py
# 범공인 Pro v24 Enterprise - Core Data Engine Module (v24.23.2)
# Feature: Full Logic Restoration & No Pass

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
    df.columns = df.columns.str.replace(' ', '').str.strip()
    synonym_map = {
        "보증금": ["보증금(만원)", "기보증금", "보증금"],
        "월차임": ["월차임(만원)", "월세(만원)", "월세", "기월세"],
        "권리금": ["권리금(만원)", "권리금"],
        "관리비": ["관리비(만원)", "관리비"],
        "매매가": ["매매가(만원)", "매매금액", "매매가"],
        "면적": ["전용면적(평)", "실평수", "전용면적", "면적"],
        "대지면적": ["대지면적(평)", "대지", "대지면적"],
        "연면적": ["연면적(평)", "연면적"],
        "수익률": ["수익률(%)", "수익률"],
        "층": ["해당층", "층", "지상층"],
        "내용": ["매물특징", "특징", "비고", "내용"],
        "번지": ["지역_번지", "번지", "지번"],
        "구분": ["매물구분", "구분"],
        "건물명": ["건물명", "빌딩명"]
    }
    for standard, aliases in synonym_map.items():
        for alias in aliases:
            clean = alias.replace(' ', '')
            if clean in df.columns:
                df.rename(columns={clean: standard}, inplace=True)
                break 
    return df

def sanitize_dataframe(df):
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    for col in STRING_COLS:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
    return df.fillna("")

def validate_data_integrity(df):
    errors = []
    for col in REQUIRED_COLS:
        if col not in df.columns: errors.append(f"필수 컬럼 누락: {col}")
        elif df[col].astype(str).str.strip().eq("").any():
            errors.append(f"필수값 누락: {col} 컬럼에 빈 행이 있습니다.")
    if errors: return False, "\n".join(errors)
    return True, "Integrity Check Passed"

# ==============================================================================
# [SECTION 3: CORE LOAD ENGINE]
# ==============================================================================

def initialize_search_state():
    if 'editor_key_version' not in st.session_state: st.session_state.editor_key_version = 0
    defaults = {
        'search_keyword': "", 'exact_bunji': "", 'selected_cat': [], 'selected_gu': [], 'selected_dong': [],
        'min_price': 0.0, 'max_price': 10000000.0, 'min_dep': 0.0, 'max_dep': 1000000.0,
        'min_rent': 0.0, 'max_rent': 10000.0, 'min_kwon': 0.0, 'max_kwon': 100000.0,
        'min_area': 0.0, 'max_area': 10000.0, 'min_land': 0.0, 'max_land': 10000.0,
        'min_total': 0.0, 'max_total': 10000.0, 'min_fl': 0.0, 'max_fl': 100.0, 'is_no_kwon': False
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def safe_reset():
    for key in list(st.session_state.keys()):
        if key not in ['current_sheet', 'editor_key_version']: del st.session_state[key]
    st.session_state.editor_key_version += 1
    st.cache_data.clear(); st.rerun()

@st.cache_data(ttl=600)
def load_sheet_data(sheet_name):
    gid = SHEET_GIDS.get(sheet_name)
    if not gid: return None
    try:
        df = pd.read_csv(f"{SHEET_URL}/export?format=csv&gid={gid}")
        df = normalize_headers(df)
        df = sanitize_dataframe(df)
        df = df.drop(columns=[c for c in ['선택', 'IronID', 'Unnamed: 0'] if c in df.columns], errors='ignore')
        df['IronID'] = [str(uuid.uuid4()) for _ in range(len(df))]
        df.insert(0, '선택', False)
        return df
    except: return None

# ==============================================================================
# [SECTION 4: MATCHING & UPDATE ENGINE]
# ==============================================================================

def create_match_signature(df, keys):
    temp_df = df.copy()
    temp_df['_match_sig'] = ""
    for k in keys:
        try:
            if k in NUMERIC_COLS:
                val = pd.to_numeric(temp_df[k].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                temp_df['_match_sig'] += val.round(1).astype(str).str.replace(r'\.0$', '', regex=True) + "|"
            else:
                val = temp_df[k].astype(str).str[:20] if k == '내용' else temp_df[k].astype(str)
                temp_df['_match_sig'] += val.str.replace(r'[^가-힣a-zA-Z0-9]', '', regex=True) + "|"
        except: continue
    return temp_df

def update_single_row(updated_row, sheet_name):
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        sheet_data = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0))
        match_keys = ['번지', '층', '면적'] 
        valid_keys = [k for k in match_keys if k in sheet_data.columns and k in updated_row]
        
        if len(valid_keys) < 2: return False, "식별 키 부족 (번지/층/면적 필수)"
        
        local_sig = ""
        for k in valid_keys:
             val = str(updated_row.get(k, '')).replace(',', '').strip()
             if k in NUMERIC_COLS:
                 try: val = str(round(float(val), 1)).replace('.0', '')
                 except: val = "0"
             else:
                 val = re.sub(r'[^가-힣a-zA-Z0-9]', '', val)
             local_sig += val + "|"
             
        server_sigs = []
        for _, row in sheet_data.iterrows():
            sig = ""
            for k in valid_keys:
                val = str(row.get(k, '')).replace(',', '').strip()
                if k in NUMERIC_COLS:
                    try: val = str(round(float(val), 1)).replace('.0', '')
                    except: val = "0"
                else:
                    val = re.sub(r'[^가-힣a-zA-Z0-9]', '', val)
                sig += val + "|"
            server_sigs.append(sig)
            
        try:
            target_idx = server_sigs.index(local_sig)
            for k, v in updated_row.items():
                if k in sheet_data.columns and k not in ['선택', 'IronID']:
                    if k in NUMERIC_COLS:
                        try: v = float(str(v).replace(',', ''))
                        except: v = 0.0
                    sheet_data.at[target_idx, k] = v
            conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=sheet_data)
            return True, "✅ 수정 사항이 저장되었습니다."
        except ValueError: return False, "❌ 원본 데이터를 찾을 수 없습니다."
    except Exception as e: return False, f"업데이트 실패: {str(e)}"

def save_updates_to_sheet(edited_df, original_df, sheet_name):
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df_org = original_df.set_index('IronID')
        df_new = edited_df.set_index('IronID')
        changed_ids = [iid for iid in df_org.index.intersection(df_new.index) 
                       if not df_org.loc[iid].drop(['선택'], errors='ignore').astype(str).equals(df_new.loc[iid].drop(['선택'], errors='ignore').astype(str))]
        
        if not changed_ids: return True, "변경 사항이 없습니다.", None

        for attempt in range(3):
            try:
                sheet_data = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0))
                valid_keys = [k for k in ['번지', '층', '면적', '매매가', '보증금'] if k in sheet_data.columns and k in df_org.columns]
                if len(valid_keys) < 2: return False, "식별 키 부족", None

                target_sigs = create_match_signature(df_org.loc[changed_ids].reset_index(), valid_keys)['_match_sig'].tolist()
                server_sigs = create_match_signature(sheet_data, valid_keys)
                
                update_count = 0
                for idx, sig in zip(target_sigs, changed_ids):
                    match_idx = server_sigs.index[server_sigs['_match_sig'] == idx].tolist()
                    if match_idx:
                        for col in sheet_data.columns:
                            if col in df_new.columns: sheet_data.at[match_idx[0], col] = df_new.loc[sig, col]
                        update_count += 1
                
                if update_count == 0: return False, "원본 데이터 매칭 실패", None
                is_v, msg = validate_data_integrity(sheet_data)
                if not is_v: return False, f"무결성 오류: {msg}", None
                
                conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=sheet_data)
                return True, f"✅ {update_count}건 저장 완료!", None
            except Exception as e:
                time.sleep(attempt + 1); last_err = e; continue
        return False, f"🚨 재시도 실패: {last_err}", None
    except Exception as e: return False, f"🚨 치명적 오류: {e}", traceback.format_exc()

def execute_transaction(action_type, target_rows, source_sheet, target_sheet=None):
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        if target_rows.empty: return False, "대상 없음", None
        src_df = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=source_sheet, ttl=0))
        target_clean = target_rows.drop(columns=['선택', 'IronID'], errors='ignore')
        v_keys = [k for k in ['번지', '층', '면적', '보증금', '매매가', '월차임', '내용'] if k in src_df.columns and k in target_clean.columns]
        
        src_sig = create_match_signature(src_df, v_keys)
        tgt_sig = create_match_signature(target_clean, v_keys)
        sigs = tgt_sig['_match_sig'].tolist()

        if action_type in ["delete", "move", "restore"]:
            new_src = src_df[~src_sig['_match_sig'].isin(sigs)]
            if len(src_df) == len(new_src): return False, "매칭 실패", None
            
            if action_type in ["move", "restore"] and target_sheet:
                tgt_df = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=target_sheet, ttl=0))
                new_tgt = pd.concat([tgt_df, target_clean], ignore_index=True)
                is_v, msg = validate_data_integrity(new_tgt)
                if not is_v: return False, msg, None
                conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet, data=new_tgt)
            
            conn.update(spreadsheet=SHEET_URL, worksheet=source_sheet, data=new_src)
            return True, f"✅ 처리 완료", None
        
        elif action_type == "copy":
            tgt_df = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=target_sheet, ttl=0))
            conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet, data=pd.concat([tgt_df, target_clean], ignore_index=True))
            return True, "✅ 복사 완료", None
            
    except Exception as e: return False, str(e), traceback.format_exc()
