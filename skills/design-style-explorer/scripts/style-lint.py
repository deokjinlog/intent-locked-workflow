#!/usr/bin/env python3
"""design-style-explorer 스타일 린터 — 크리틱 루프의 기계화.

생성된 style-NN-*.html 이 그 스타일의 '금지' 규칙을 위반하는지 결정론적으로 검사한다.
생성 → 린트 → 위반 수정 → 재린트 (Ralph 루프)의 자동 게이트. "느낌상 점검"이 아니라
검증된 출력을 만든다. 특히 병렬로 12개를 한 번에 뽑을 때 필수.

한계: 정규식 휴리스틱이라 구조적 위반(라운드/그림자/그라디언트/폰트 등)만 잡는다.
의미 규칙(주황 정확히 3곳 / 골드 면적 5% 등)은 [MANUAL] 로 안내만 한다.
FAIL 은 실제 위반인지 확인 후 수정한다 (드물게 오탐 가능).

사용법:
  python3 style-lint.py <html파일 또는 디렉토리>
  # 파일명이 style-{NN}-*.html 이어야 스타일을 인식. 아니면 --style NN 지정.
종료코드: FAIL 있으면 1, 없으면 0.
"""
import re, sys, os, glob

def rd(p):
    with open(p, encoding="utf-8", errors="ignore") as f:
        return f.read()

def has(s, pat):
    return re.search(pat, s, re.I | re.S) is not None

def radius_nonzero(s):
    for m in re.finditer(r"border-radius\s*:\s*([^;}\n]+)", s, re.I):
        if re.search(r"[1-9]\d*\s*(px|rem|em|%)", m.group(1)):
            return True
    return False

def soft_shadow(s):
    # box-shadow 의 blur(3번째 px 값) > 0 = 부드러운 그림자. inset/none 제외.
    for m in re.finditer(r"box-shadow\s*:\s*([^;}\n]+)", s, re.I):
        v = m.group(1).lower()
        if "inset" in v or "none" in v:
            continue
        nums = re.findall(r"-?\d*\.?\d+", v)
        if len(nums) >= 3 and float(nums[2]) > 0:
            return True
    return False

def has_shadow(s):
    return has(s, r"box-shadow\s*:\s*(?!none)[^;}\n]*\d")

def has_serif(s):
    return has(s, r"font-family\s*:[^;}]*\bserif\b")

def dark_bg(s):
    m = re.search(r"(?:body|html)\s*\{[^}]*?background[^;}]*?(#[0-9a-fA-F]{3,6})", s, re.I | re.S)
    if not m:
        return False
    h = m.group(1).lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (r + g + b) / 3 < 60
    except ValueError:
        return False

# (레벨, 설명, 위반이면 True 인 함수)
RULES = {
    "01": [("FAIL", "흰/밝은 배경 금지 (HUD는 어둠)", lambda s: not dark_bg(s))],
    "02": [("FAIL", "애니메이션 금지 (정적이 신뢰)", lambda s: has(s, r"@keyframes\b|animation\s*:\s*(?!none\b|unset\b|initial\b|inherit\b)")),
           ("FAIL", "그림자 금지", has_shadow),
           ("FAIL", "그라디언트 금지", lambda s: has(s, r"(?:linear|radial|conic)-gradient\s*\(")),
           ("FAIL", "라운드 금지 (radius 0)", radius_nonzero)],
    "03": [("FAIL", "모노스페이스 금지", lambda s: has(s, r"font-family[^;}]*(?:monospace|Plex Mono|Share Tech)")),
           ("FAIL", "다크 배경 금지", dark_bg)],
    "04": [("FAIL", "라운드 금지", radius_nonzero)],
    "05": [("FAIL", "라운드 금지", radius_nonzero),
           ("FAIL", "그라디언트 금지", lambda s: has(s, r"(?:linear|radial|conic)-gradient\s*\(")),
           ("FAIL", "블러 금지", lambda s: has(s, r"blur\s*\(")),
           ("FAIL", "부드러운 그림자 금지 (하드섀도만)", soft_shadow)],
    "06": [("FAIL", "backdrop-filter 필수 (유리)", lambda s: not has(s, r"backdrop-filter"))],
    "07": [("FAIL", "그림자 금지", has_shadow),
           ("FAIL", "라운드 금지 (radius 0)", radius_nonzero),
           ("FAIL", "그라디언트 금지", lambda s: has(s, r"(?:linear|radial|conic)-gradient\s*\("))],
    "08": [("FAIL", "그림자 금지 (조명으로 표현)", soft_shadow),
           ("FAIL", "카운트업 금지 (숫자가 뛰면 안 됨)", lambda s: has(s, r"countUp|count-up|카운트업")),
           ("FAIL", "글로우/네온 금지", lambda s: has(s, r"text-shadow\s*:\s*(?!none)[^;}]*[1-9]"))],
    "09": [("FAIL", "라운드 금지 (픽셀)", radius_nonzero),
           ("FAIL", "블러 금지", lambda s: has(s, r"blur\s*\(")),
           ("FAIL", "세리프 금지", has_serif)],
    "10": [("FAIL", "카드 그림자 금지", has_shadow),
           ("FAIL", "다크 배경 금지", dark_bg)],
    "11": [("FAIL", "순백/순흑 금지", lambda s: has(s, r"#fff(fff)?\b|#000(000)?\b|:\s*white\b|:\s*black\b")),
           ("FAIL", "모노스페이스 금지", lambda s: has(s, r"font-family[^;}]*monospace"))],
    "12": [("FAIL", "플랫 금지 (box-shadow 필수)", lambda s: not has_shadow(s)),
           ("FAIL", "다크 배경 금지", dark_bg)],
}

# 정규식으로 못 잡는 의미 규칙 — 사람이 확인
MANUAL = {
    "01": "동시 발광 3곳 이하 / 어둠 비율 60%+ / 부팅 시퀀스 구현",
    "02": "단위·출처·기준일 명기 / 흑백 인쇄 가능(@media print)",
    "03": "개별 트랜지션 0.3s 이하 / 카운트업 실패해도 최종숫자 HTML 존재",
    "04": "유채색 5색 이하 / 흐르는 이벤트 로그 / 넓은 여백 없음",
    "05": "원색 3색 이내 / KPI 대표수치 72px+ / 찍히는 hover",
    "06": "흰 텍스트 대비 4.5:1 / 유리 2겹 이하 / 배경 이동 인지 직전 속도",
    "07": "주황 정확히 3곳 / 폰트 크기 5단계(11·16·24·36·54)만 / 여백 4단계만",
    "08": "모든 모션 500ms+ / 골드 면적 5% 이하 / 세리프 대형수치가 주인공",
    "09": "READY? 오프닝 / 블록 단위 차트 / Press Start 2P 로 한글 금지",
    "10": "KPI마다 헤드라인 해설(데이터와 일치) / 수직 괘선 남발 금지",
    "11": "모든 색 따뜻한 톤 / 유기 radius 일관 규칙 / 성장 은유 과하지 않게",
    "12": "광원 좌상단 일관 / 볼록·오목이 위계와 일치 / 눌림 반응 전 요소",
}

STYLE_NAME = {
    "01": "SF HUD", "02": "공공포털", "03": "트렌디 SaaS", "04": "고밀도 터미널",
    "05": "브루탈리즘", "06": "글래스모피즘", "07": "미니멀 모노크롬", "08": "럭셔리 다크",
    "09": "레트로 픽셀", "10": "에디토리얼", "11": "네이처 오가닉", "12": "뉴모피즘",
}


def style_of(path, override):
    if override:
        return override.zfill(2)
    m = re.search(r"(?:style-)?(\d{2})", os.path.basename(path))
    return m.group(1) if m else None


def lint(path, override=None):
    nn = style_of(path, override)
    name = STYLE_NAME.get(nn, "?")
    if nn not in RULES:
        print(f"[SKIP] {os.path.basename(path)} — 스타일 번호 인식 실패 (--style NN 지정)")
        return 0
    html = rd(path)
    fails = [(desc) for lvl, desc, fn in RULES[nn] if fn(html)]
    tag = "FAIL" if fails else "PASS"
    print(f"[{tag}] {os.path.basename(path)}  (STYLE {nn} · {name})")
    for d in fails:
        print(f"    ✗ {d}")
    print(f"    [MANUAL] {MANUAL.get(nn,'')}")
    return len(fails)


def main(argv):
    override = None
    args = []
    it = iter(argv)
    for a in it:
        if a == "--style":
            override = next(it, None)
        else:
            args.append(a)
    if not args:
        print(__doc__)
        return 0
    targets = []
    for a in args:
        if os.path.isdir(a):
            files = sorted(glob.glob(os.path.join(a, "*.html")))
            targets += [f for f in files if os.path.basename(f) not in ("index.html", "gallery.html")]
        else:
            targets.append(a)
    if not targets:
        print("검사할 style-*.html 없음")
        return 0
    total = sum(lint(t, override) for t in targets)
    print(f"\n총 위반: {total}건 " + ("→ 수정 후 재린트" if total else "→ 통과 ✅"))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
