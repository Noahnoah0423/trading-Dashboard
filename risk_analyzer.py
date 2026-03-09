"""
=============================================================================
 시장 위기 경보 분석 모듈 (Risk Analyzer)
 - VIX 지수 기반 3단계 시장 위험도 판별
 - 퀀트 트레이딩에서 널리 쓰이는 임계치 기반
=============================================================================
"""

from typing import Dict, Any


def calculate_market_risk(vix_value: float) -> Dict[str, Any]:
    """
    VIX 지수를 입력받아 3단계 시장 위기 상태를 반환합니다.

    퀀트 트레이딩 표준 임계치:
        - VIX < 20    → 안전 (Safe)
        - 20 ≤ VIX < 30 → 주의 (Warning)
        - VIX ≥ 30    → 위험 (Danger)

    Args:
        vix_value: 현재 VIX 지수 (숫자)

    Returns:
        {
            "level": "safe" | "warning" | "danger",
            "label_ko": "안전" | "주의" | "위험",
            "label_en": "Safe" | "Warning" | "Danger",
            "color": "#00d4aa" | "#ffaa00" | "#ff4444",
            "icon": "✅" | "⚠️" | "🚨",
            "message": 상세 설명 메시지,
            "vix": VIX 값
        }
    """
    # -----------------------------------------------------------------------
    # VIX 값 유효성 검사
    # -----------------------------------------------------------------------
    if vix_value is None or not isinstance(vix_value, (int, float)):
        return {
            "level": "unknown",
            "label_ko": "데이터 없음",
            "label_en": "No Data",
            "color": "#888888",
            "icon": "❓",
            "message": "VIX 데이터를 불러올 수 없습니다.",
            "vix": None,
        }

    # -----------------------------------------------------------------------
    # 3단계 위기 경보 판별 (if-elif 조건문)
    # -----------------------------------------------------------------------
    if vix_value < 20:
        # ✅ 안전 구간: VIX < 20
        return {
            "level": "safe",
            "label_ko": "안전",
            "label_en": "Safe",
            "color": "#00d4aa",
            "icon": "✅",
            "message": (
                f"🟢 DEFCON 5 — Soft Landing & 안정적\n\n"
                f"현재 VIX: **{vix_value:.2f}** | 시장 변동성이 정상 범위 내에 있습니다.\n"
                f"리스크 온(Risk-On) 전략이 유효한 구간입니다."
            ),
            "vix": vix_value,
        }

    elif vix_value < 30:
        # ⚠️ 주의 구간: 20 ≤ VIX < 30
        return {
            "level": "warning",
            "label_ko": "주의",
            "label_en": "Warning",
            "color": "#ffaa00",
            "icon": "⚠️",
            "message": (
                f"🟡 DEFCON 3 — 변동성 확대 주의\n\n"
                f"현재 VIX: **{vix_value:.2f}** | 시장 변동성이 상승하고 있습니다.\n"
                f"포지션 축소 및 헤지 비율 점검을 권고합니다."
            ),
            "vix": vix_value,
        }

    else:
        # 🚨 위험 구간: VIX ≥ 30
        return {
            "level": "danger",
            "label_ko": "위험",
            "label_en": "Danger",
            "color": "#ff4444",
            "icon": "🚨",
            "message": (
                f"🔴 DEFCON 1 — 시스템 리스크 경보 발령\n\n"
                f"현재 VIX: **{vix_value:.2f}** | 극심한 시장 변동성이 감지되었습니다.\n"
                f"즉각적인 리스크 관리 조치가 필요합니다. 방어적 포지션 전환을 권고합니다."
            ),
            "vix": vix_value,
        }


# ---------------------------------------------------------------------------
# 테스트용 메인 실행
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_values = [12.5, 15.0, 20.0, 25.3, 30.0, 42.8, None]

    print("=" * 60)
    print(" VIX 기반 시장 위기 경보 테스트")
    print("=" * 60)

    for vix in test_values:
        result = calculate_market_risk(vix)
        print(f"  VIX={str(vix):>6s} → {result['icon']} {result['label_ko']} ({result['label_en']})")
