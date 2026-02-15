def fetch_map_image(lat, lng, zoom_level=16, height=300):
    """
    위도, 경도, 줌 레벨, 높이를 받아 정적 지도 이미지(Binary)를 반환합니다.
    """
    if not lat or not lng:
        return None
    
    url = "https://maps.apigw.ntruss.com/map-static/v2/raster"
    
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
    }
    
    # 네이버 API가 허용하는 최대 높이 1024 제한 (안전장치)
    safe_height = min(int(height), 1024)
    
    params = {
        "w": "1000",        # 가로 너비 확장
        "h": str(safe_height), 
        "center": f"{lng},{lat}",
        "level": str(zoom_level),
        "markers": f"type:t|size:mid|pos:{lng} {lat}|label:매물",
        "scale": "2" 
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        print(f"Map Fetch Internal Error: {e}")
        return None
