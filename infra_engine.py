import requests
import pandas as pd
import re
import math

# ==========================================
# 1. API 환경 설정
# ==========================================
NAVER_VPC_CLIENT_ID = "j6kk02fqy0"
NAVER_VPC_CLIENT_SECRET = "Lm0UTMBLuPWeDQJ4OZNn3ec82tvgAvllqJ46ceuU"
NAVER_VPC_ENDPOINT = "https://maps.apigw.ntruss.com/"

NAVER_VPC_HEADERS = {
    "x-ncp-apigw-api-key-id": NAVER_VPC_CLIENT_ID,
    "x-ncp-apigw-api-key": NAVER_VPC_CLIENT_SECRET,
    "Content-Type": "application/json"
}

KAKAO_REST_KEY = "72e1d9f46c8c70448510d2f6215ad512"
KAKAO_HEADERS = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
TIMEOUT_SEC = 2.0  # 경로 탐색을 위해 타임아웃 소폭 증가

# ==========================================
# 2. 유틸리티 함수
# ==========================================
def _call_kakao_local(endpoint, params):
    url = f"https://dapi.kakao.com/v2/local/search/{endpoint}.json"
    try:
        response = requests.get(url, headers=KAKAO_HEADERS, params=params, timeout=TIMEOUT_SEC)
        if response.status_code == 200:
            return response.json().get('documents', [])
        return []
    except Exception:
        return []

def _extract_exit_number(place_name):
    if not place_name or not isinstance(place_name, str): return ""
    try:
        match = re.search(r'(\d+번\s?출구)', place_name)
        if match: return match.group(1)
    except Exception: pass
    return ""

def calculate_haversine(lat1, lon1, lat2, lon2):
    """[Backup] 직선 거리 계산 (API 실패 시 Fallback용)"""
    try:
        R = 6371000 
        phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
        dphi = math.radians(float(lat2) - float(lat1))
        dlambda = math.radians(float(lon2) - float(lon1))
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return int(R * c)
    except Exception: return 0

def _get_pedestrian_route(origin_lng, origin_lat, dest_lng, dest_lat):
    """
    실제 보행자 경로(도보) 분석 함수
    Returns: (distance_meter, duration_minute)
    """
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    params = {
        "origin": f"{origin_lng},{origin_lat}",
        "destination": f"{dest_lng},{dest_lat}",
        "priority": "RECOMMEND",
        "car_type": 1 
    }
    
    try:
        response = requests.get(url, headers=KAKAO_HEADERS, params=params, timeout=TIMEOUT_SEC)
        if response.status_code == 200:
            routes = response.json().get('routes', [])
            if routes:
                summary = routes[0].get('summary', {})
                dist = summary.get('distance', 0)
                # 도보 시간 보정 (분속 67m 기준 + 10% 지연 가중치)
                walk_time = round((dist / 67) * 1.1, 1) 
                return dist, walk_time
    except Exception: pass
    
    line_dist = calculate_haversine(origin_lat, origin_lng, dest_lat, dest_lng)
    return int(line_dist * 1.3), round((line_dist * 1.3) / 67, 1)

# ==========================================
# 3. 핵심 분석 함수 (v24.30.1 수술 적용)
# ==========================================

def get_commercial_analysis(lat, lng):
    """
    [통합 상권 분석]
    1. 지하철역 분석 (필터 해제 + 실제 경로 기반)
    2. 주변 10대 필수 시설 리스트
    3. Top 10 앵커 브랜드 스캔
    """
    result = {
        "subway": {
            "station": "정보 없음", "exit": "", "dist": 0, "walk": 0,
            "coords": {"origin": (0, 0), "target": (0, 0)}
        },
        "facilities": pd.DataFrame(columns=['장소명', '업종', '거리(m)', '도보(분)']),
        "anchors": pd.DataFrame(columns=["브랜드", "지점명", "거리(m)", "도보(분)"])
    }

    try:
        if not lat or not lng: return result

        # [수술] 지하철 필터 해제: SW8 그룹의 모든 결과를 수용함
        subways_params = {"category_group_code": "SW8", "x": lng, "y": lat, "radius": 700, "sort": "distance"}
        subways = _call_kakao_local("category", subways_params) 

        if subways:
            target_node = subways[0]
            name = target_node.get('place_name', '').split()[0]
            
            # 출구 정밀 검색 (반경 800m 확장)
            exit_params = {"query": f"{name} 출구", "x": lng, "y": lat, "radius": 800, "sort": "distance", "size": 1}
            exits = _call_kakao_local("keyword", exit_params)
            
            final_node = exits[0] if exits else target_node
            exit_info = _extract_exit_number(final_node.get('place_name', ''))
            
            # 실제 보행자 경로 엔진 가동 (직선거리 로직 calculate_haversine 폐기)
            # [v24.30.5] 카카오가 이미 계산한 거리를 최우선으로 사용
api_dist = int(final_node.get('distance', 0))
if api_dist > 0:
    dist = api_dist
    # 분속 67m 기준 (30m면 약 0.5분 -> 1분으로 표시)
    walk = round(max(0.5, dist / 67), 1) 
else:
    # 거리가 없을 때만 보조 로직 작동
    dist, walk = _get_pedestrian_route(lng, lat, final_node['x'], final_node['y'])
            
            result["subway"] = {
                "station": name, "exit": exit_info, "dist": dist, "walk": walk,
                "coords": {"origin": (lat, lng), "target": (final_node['y'], final_node['x'])}
            }

        # [Step 2] 주변 10대 필수 시설 리스트
        target_cats = {"편의점": "CS2", "은행": "BK9", "카페": "CE7", "병원": "HP8", "약국": "PM9", "음식점": "FD6"}
        all_places = []
        for cat_name, code in target_cats.items():
            p = {"category_group_code": code, "x": lng, "y": lat, "radius": 300, "sort": "distance", "size": 5}
            items = _call_kakao_local("category", p)
            for item in items:
                d = int(item.get('distance', 0))
                all_places.append({
                    "장소명": item.get('place_name'),
                    "업종": cat_name,
                    "거리(m)": d,
                    "도보(분)": round(d / 67, 1)
                })
        
        if all_places:
            df_fac = pd.DataFrame(all_places)
            df_fac = df_fac.sort_values(by="거리(m)").head(10).reset_index(drop=True)
            result["facilities"] = df_fac

        # [Step 3] Top 10 앵커 브랜드 스캔
        target_anchors = ["스타벅스", "맥도날드", "올리브영", "다이소", "버거킹", "써브웨이", "메가커피", "파리바게뜨", "컴포즈커피", "배스킨라빈스"]
        anchors_list = []
        for anchor in target_anchors:
            p = {"query": anchor, "x": lng, "y": lat, "radius": 1000, "sort": "distance"}
            data = _call_kakao_local("keyword", p)
            if data:
                n = data[0]
                d = int(n.get('distance', 0))
                anchors_list.append({"브랜드": anchor, "지점명": n.get('place_name'), "거리(m)": d, "도보(분)": round(d/67, 1)})
            else:
                anchors_list.append({"브랜드": anchor, "지점명": "없음", "거리(m)": "-", "도보(분)": "-"})
        result["anchors"] = pd.DataFrame(anchors_list)

    except Exception as e:
        print(f"[Commercial Analysis Error] {e}")
        return result

    return result

def get_demand_analysis(lat, lng):
    """[함수 2] 수요 분석 (기존 유지)"""
    cols = ["구분", "시설명", "거리(m)"]
    default_df = pd.DataFrame(columns=cols)
    try:
        if not lat or not lng: return default_df
        demand = []
        seen = set()
        targets = [
            (["지식산업센터", "오피스", "빌딩"], "업무시설", 500, "keyword"),
            ({"학교": "SC4", "학원": "AC5"}, "교육", 500, "category"),
            (["주민센터", "우체국", "구청", "경찰서"], "행정/공공", 800, "keyword")
        ]
        for keys, label_type, rad, method in targets:
            if method == "keyword":
                for k in keys:
                    p = {"query": k, "x": lng, "y": lat, "radius": rad}
                    items = _call_kakao_local("keyword", p)
                    for i in items:
                        if i['id'] not in seen:
                            demand.append({"구분": label_type, "시설명": i['place_name'], "거리(m)": int(i['distance'])})
                            seen.add(i['id'])
            else: # category
                for name, code in keys.items():
                    p = {"category_group_code": code, "x": lng, "y": lat, "radius": rad}
                    items = _call_kakao_local("category", p)
                    for i in items:
                        if i['id'] not in seen:
                            demand.append({"구분": f"{label_type}({name})", "시설명": i['place_name'], "거리(m)": int(i['distance'])})
                            seen.add(i['id'])
        if demand:
            return pd.DataFrame(demand).sort_values(by="거리(m)").head(15).reset_index(drop=True)
        return default_df
    except Exception: return default_df
