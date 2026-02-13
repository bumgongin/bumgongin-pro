import requests
import pandas as pd
import re
import math

# ==========================================
# 1. API 환경 설정 (보안 및 VPC 규격 준수)
# ==========================================

# [NAVER Enterprise VPC 설정]
NAVER_VPC_CLIENT_ID = "j6kk02fqy0"
NAVER_VPC_CLIENT_SECRET = "Lm0UTMBLuPWeDQJ4OZNn3ec82tvgAvllqJ46ceuU"
NAVER_VPC_ENDPOINT = "https://maps.apigw.ntruss.com/"

NAVER_VPC_HEADERS = {
    "x-ncp-apigw-api-key-id": NAVER_VPC_CLIENT_ID,
    "x-ncp-apigw-api-key": NAVER_VPC_CLIENT_SECRET,
    "Content-Type": "application/json"
}

# [KAKAO REST API 설정]
KAKAO_REST_KEY = "72e1d9f46c8c70448510d2f6215ad512"
KAKAO_HEADERS = {
    "Authorization": f"KakaoAK {KAKAO_REST_KEY}"
}

# 공통 설정
TIMEOUT_SEC = 2  # 모든 요청은 2초 내 응답 제한

# ==========================================
# 2. 유틸리티 함수 (내부 로직 - 방어적 코딩)
# ==========================================

def _call_kakao_local(endpoint, params):
    """카카오 로컬 API 호출 래퍼 (실패 시 빈 리스트 반환 보장)"""
    url = f"https://dapi.kakao.com/v2/local/search/{endpoint}.json"
    try:
        response = requests.get(url, headers=KAKAO_HEADERS, params=params, timeout=TIMEOUT_SEC)
        if response.status_code == 200:
            return response.json().get('documents', [])
        return []
    except Exception:
        return []

def _extract_exit_number(place_name):
    """정규표현식을 이용해 역 이름에서 출구 번호 추출"""
    if not place_name or not isinstance(place_name, str):
        return ""
    try:
        match = re.search(r'(\d+번\s?출구)', place_name)
        if match:
            return match.group(1)
    except Exception:
        pass
    return ""

def _calculate_walking_data(origin_x, origin_y, dest_x, dest_y):
    """도보 거리 및 시간 계산 (Zero-Failure)"""
    if not (origin_x and origin_y and dest_x and dest_y):
        return 0, 0

    url = "https://apis-navi.kakaomobility.com/v1/directions"
    params = {
        "origin": f"{origin_x},{origin_y}",
        "destination": f"{dest_x},{dest_y}",
        "priority": "RECOMMEND",
        "car_type": 1 
    }
    
    try:
        response = requests.get(url, headers=KAKAO_HEADERS, params=params, timeout=TIMEOUT_SEC)
        if response.status_code == 200:
            routes = response.json().get('routes', [])
            if routes:
                summary = routes[0].get('summary', {})
                dist_m = summary.get('distance', 0)
                return dist_m, round(dist_m / 67, 1)
    except Exception:
        pass 

    # Fallback: 직선 거리 1.25배 보정
    try:
        dx = (float(dest_x) - float(origin_x)) * 88000
        dy = (float(dest_y) - float(origin_y)) * 111000
        dist_m = int(math.sqrt(dx**2 + dy**2) * 1.25)
        return dist_m, round(dist_m / 67, 1)
    except Exception:
        return 0, 0

# ==========================================
# 3. 핵심 분석 함수 (Zero-Failure 구조)
# ==========================================

def get_transport_analysis(lat, lng):
    """
    [섹션 1] 교통망 분석 (v24.26.4 순도 100% 로직)
    - 지하철: '지하철,전철' 카테고리 필터링 및 이름 정제(괄호 제거)
    - 버스: size=45, 멀티 키워드, 카테고리 필터링으로 정밀 카운트
    """
    default_details = pd.DataFrame(columns=['place_name', 'distance', 'phone'])
    result = {
        "subway_station": "정보 없음",
        "exit_info": "",
        "subway_dist": 0,
        "walk_time": 0,
        "bus_stop_count": 0,
        "details": default_details
    }

    try:
        if not lat or not lng:
            return result

        # 1. 지하철역 검색
        sub_params = {"category_group_code": "SW8", "x": lng, "y": lat, "radius": 500, "sort": "distance"}
        subways_raw = _call_kakao_local("category", sub_params)
        
        # [Step 1-1] 지하철 순도 필터링: 카테고리에 '지하철,전철' 필수
        subways = [s for s in subways_raw if '지하철,전철' in s.get('category_name', '')]

        if subways:
            nearest = subways[0]
            raw_name = nearest.get('place_name', '')
            
            # [Step 1-2] 이름 정제: 괄호와 그 안의 내용(식당명 등) 완전 제거
            clean_name = re.sub(r'\(.*\)', '', raw_name).strip()
            station_base_name = clean_name.split()[0] 
            
            # 출구 정밀 검색
            exit_params = {"query": f"{station_base_name} 출구", "x": lng, "y": lat, "radius": 500, "sort": "distance"}
            exits = _call_kakao_local("keyword", exit_params)
            
            target_obj = nearest
            exit_name = ""
            if exits:
                target_obj = exits[0]
                exit_name = _extract_exit_number(target_obj.get('place_name', ''))
                if not exit_name: exit_name = target_obj.get('place_name', '')
            
            dist, time = _calculate_walking_data(lng, lat, target_obj.get('x'), target_obj.get('y'))
            
            result["subway_station"] = station_base_name
            result["exit_info"] = exit_name
            result["subway_dist"] = dist
            result["walk_time"] = time
            
            df = pd.DataFrame(subways)
            cols = [c for c in ['place_name', 'distance', 'phone'] if c in df.columns]
            result["details"] = df[cols].head(5)

        # 2. 버스 정류장 전수 조사 (멀티 키워드 & size=45 & 카테고리 필터)
        bus_keywords = ["정류장", "버스정류장", "정류소"]
        unique_bus_stops = {}

        for kw in bus_keywords:
            # size를 45로 늘려 누락 방지
            bus_params = {"query": kw, "x": lng, "y": lat, "radius": 500, "size": 45}
            found_buses = _call_kakao_local("keyword", bus_params)
            
            for b in found_buses:
                p_id = b.get('id')
                cat_name = b.get('category_name', '')
                # [Step 1-3] 버스 카테고리 정밀 필터 (교통,운송 > 버스)
                if p_id and ('교통,운송 > 버스' in cat_name or '정류장' in cat_name):
                    unique_bus_stops[p_id] = b
        
        result["bus_stop_count"] = len(unique_bus_stops)

    except Exception as e:
        print(f"[Transport Analysis Error] {e}")
        return result

    return result

def get_commercial_analysis(lat, lng):
    """
    [섹션 2] 상권 인프라 분석 (v24.26.4 앵커 확장)
    - 7대 핵심 앵커(스타벅스, 맥도날드, 올리브영, 다이소, 버거킹, 써브웨이, 메가커피)
    """
    default_counts = {k: 0 for k in ["음식점", "카페", "편의점", "은행", "병원"]}
    default_anchors = pd.DataFrame(columns=["브랜드", "지점명", "거리(m)", "도보(분)"])
    result = {"counts": default_counts, "anchors": default_anchors}

    try:
        if not lat or not lng: return result
        categories = {"음식점": "FD6", "카페": "CE7", "편의점": "CS2", "은행": "BK9", "병원": "HP8"}
        
        current_counts = {}
        for name, code in categories.items():
            params = {"category_group_code": code, "x": lng, "y": lat, "radius": 300}
            data = _call_kakao_local("category", params)
            current_counts[name] = len(data)
        result["counts"] = current_counts

        # [Step 2] 앵커 시설 7종으로 대폭 확장
        anchors_list = []
        target_anchors = ["스타벅스", "맥도날드", "올리브영", "다이소", "버거킹", "써브웨이", "메가커피"]
        
        for anchor in target_anchors:
            params = {"query": anchor, "x": lng, "y": lat, "radius": 1000, "sort": "distance"}
            data = _call_kakao_local("keyword", params)
            if data:
                nearest = data[0]
                dist = int(nearest.get('distance', 0))
                anchors_list.append({
                    "브랜드": anchor, "지점명": nearest.get('place_name', '정보없음'),
                    "거리(m)": dist, "도보(분)": round(dist / 67, 1)
                })
            else:
                anchors_list.append({"브랜드": anchor, "지점명": "없음", "거리(m)": "-", "도보(분)": "-"})
        result["anchors"] = pd.DataFrame(anchors_list)
    except Exception as e:
        print(f"[Commercial Analysis Error] {e}")
    return result

def get_demand_analysis(lat, lng):
    """
    [섹션 3] 업무/생활 수요 분석
    """
    columns = ["구분", "시설명", "거리(m)"]
    default_df = pd.DataFrame(columns=columns)

    try:
        if not lat or not lng: return default_df
        demand_list = []
        seen_places = set()

        office_kws = ["지식산업센터", "오피스", "빌딩"]
        for kw in office_kws:
            params = {"query": kw, "x": lng, "y": lat, "radius": 500}
            places = _call_kakao_local("keyword", params)
            for p in places:
                p_id = p.get('id')
                if p_id and p_id not in seen_places:
                    demand_list.append({"구분": "업무시설", "시설명": p.get('place_name', ''), "거리(m)": int(p.get('distance', 0))})
                    seen_places.add(p_id)

        edu_codes = {"학교": "SC4", "학원": "AC5"}
        for name, code in edu_codes.items():
            params = {"category_group_code": code, "x": lng, "y": lat, "radius": 500}
            places = _call_kakao_local("category", params)
            for p in places:
                p_id = p.get('id')
                if p_id and p_id not in seen_places:
                    demand_list.append({"구분": f"교육({name})", "시설명": p.get('place_name', ''), "거리(m)": int(p.get('distance', 0))})
                    seen_places.add(p_id)

        admin_kws = ["주민센터", "우체국", "구청", "경찰서"]
        for kw in admin_kws:
            params = {"query": kw, "x": lng, "y": lat, "radius": 800}
            places = _call_kakao_local("keyword", params)
            for p in places:
                p_id = p.get('id')
                if p_id and p_id not in seen_places:
                    demand_list.append({"구분": "행정/공공", "시설명": p.get('place_name', ''), "거리(m)": int(p.get('distance', 0))})
                    seen_places.add(p_id)

        if demand_list:
            df = pd.DataFrame(demand_list)
            df = df.sort_values(by="거리(m)").head(15).reset_index(drop=True)
            return df
        return default_df
    except Exception as e:
        print(f"[Demand Analysis Error] {e}")
        return default_df
