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
    # 'sans-serif' 의 serif 는 오탐 — 부정 lookbehind 로 제외
    return has(s, r"font-family\s*:[^;}]*(?<!sans-)\bserif\b")

def _hex_dark(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return False
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (r + g + b) / 3 < 60
    except ValueError:
        return False

def _resolve_vars(val, s):
    # var(--x) → :root 등에 정의된 --x 의 hex 값으로 치환
    def rep(m):
        vm = re.search(re.escape(m.group(1)) + r"\s*:\s*(#[0-9a-fA-F]{3,6})", s, re.I)
        return vm.group(1) if vm else m.group(0)
    return re.sub(r"var\((--[\w-]+)\)", rep, val)

def _block_bg_dark(block, s):
    # 규칙 블록의 background 값의 '첫 색'이 어두우면 다크로 본다 (그라디언트/변수 포함)
    bm = re.search(r"background(?:-color|-image)?\s*:\s*([^;}]+)", block, re.I)
    if not bm:
        return False
    hexes = re.findall(r"#[0-9a-fA-F]{3,6}", _resolve_vars(bm.group(1), s))
    return bool(hexes) and _hex_dark(hexes[0])

def dark_bg(s):
    # body/html/:root 직접 배경 (그라디언트·CSS 변수 포함)
    for sel in (r"body", r"html", r":root"):
        for m in re.finditer(sel + r"\s*\{([^}]*)\}", s, re.I | re.S):
            if _block_bg_dark(m.group(1), s):
                return True
    # 풀뷰포트(100vh) 래퍼에 다크 배경 → 시각적으로 다크
    for m in re.finditer(r"\{([^}]*(?:min-height|height)\s*:\s*100vh[^}]*)\}", s, re.I | re.S):
        if _block_bg_dark(m.group(1), s):
            return True
    return False

# (레벨, 설명, 위반이면 True 인 함수)
RULES = {
    "01": [("FAIL", "흰/밝은 배경 금지 (HUD는 어둠)", lambda s: not dark_bg(s))],
    "02": [("FAIL", "애니메이션 금지 (정적이 신뢰)", lambda s: has(s, r"@keyframes\b|animation\s*:\s*(?!none\b|unset\b|initial\b|inherit\b)")),
           ("FAIL", "그림자 금지 (부드러운 elevation)", soft_shadow),
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
    "07": [("FAIL", "그림자 금지 (부드러운 elevation)", soft_shadow),
           ("FAIL", "라운드 금지 (radius 0)", radius_nonzero),
           ("FAIL", "그라디언트 금지", lambda s: has(s, r"(?:linear|radial|conic)-gradient\s*\("))],
    "08": [("FAIL", "그림자 금지 (조명으로 표현)", soft_shadow),
           ("FAIL", "카운트업 금지 (숫자가 뛰면 안 됨)", lambda s: has(s, r"countUp|count-up|카운트업")),
           ("FAIL", "글로우/네온 금지", lambda s: has(s, r"text-shadow\s*:\s*(?!none)[^;}]*[1-9]"))],
    "09": [("FAIL", "라운드 금지 (픽셀)", radius_nonzero),
           ("FAIL", "블러 금지", lambda s: has(s, r"blur\s*\(")),
           ("FAIL", "세리프 금지", has_serif)],
    "10": [("FAIL", "카드 그림자 금지 (부드러운)", soft_shadow),
           ("FAIL", "다크 배경 금지", dark_bg)],
    "11": [("FAIL", "순백/순흑 금지", lambda s: has(s, r"#fff(fff)?\b|#000(000)?\b|:\s*white\b|:\s*black\b")),
           ("FAIL", "모노스페이스 금지", lambda s: has(s, r"font-family[^;}]*monospace"))],
    "12": [("FAIL", "플랫 금지 (box-shadow 필수)", lambda s: not has_shadow(s)),
           ("FAIL", "다크 배경 금지", dark_bg)],
    "13": [("FAIL", "다크 배경 필수 (오로라는 어둠 위 광채)", lambda s: not dark_bg(s)),
           ("FAIL", "오로라 그라디언트 필수", lambda s: not has(s, r"(?:linear|radial|conic)-gradient\s*\("))],
    "14": [("FAIL", "라운드 카드 필수 (벤토)", lambda s: not radius_nonzero(s)),
           ("FAIL", "그리드 레이아웃 필수 (벤토 조합)", lambda s: not has(s, r"display\s*:\s*grid|grid-template"))],
    "15": [("FAIL", "다크 배경 금지 (파스텔 밝게)", dark_bg),
           ("FAIL", "소프트 섀도 필수 (클레이 입체)", lambda s: not has_shadow(s)),
           ("FAIL", "라운드 필수 (말랑)", lambda s: not radius_nonzero(s)),
           ("FAIL", "세리프 금지", has_serif)],
    "16": [("FAIL", "elevation 그림자 필수 (머티리얼)", lambda s: not has_shadow(s)),
           ("FAIL", "글래스(backdrop-filter) 금지", lambda s: has(s, r"backdrop-filter")),
           ("FAIL", "세리프 금지", has_serif)],
    "17": [("FAIL", "그라디언트 필수 (크롬·홀로그램)", lambda s: not has(s, r"(?:linear|radial|conic)-gradient\s*\(")),
           ("FAIL", "세리프 금지", has_serif)],
    "18": [("FAIL", "그림자 금지 (격자·타이포가 위계)", has_shadow),
           ("FAIL", "라운드 금지 (radius 0)", radius_nonzero),
           ("FAIL", "그라디언트 금지", lambda s: has(s, r"(?:linear|radial|conic)-gradient\s*\(")),
           ("FAIL", "다크 배경 금지 (순백)", dark_bg)],
    "19": [],  # 맥시멀리즘 — 구조 규칙 없음(과잉이 정체성), MANUAL 로 판단
    "20": [("FAIL", "다크 배경 필수 (관제 대시보드)", lambda s: not dark_bg(s))],
    "21": [],  # AI 프로덕트 — 라이트/다크 유연, MANUAL
    "22": [("FAIL", "다크 배경 금지 (라이트 친근)", dark_bg)],
    "23": [],  # 엔터프라이즈 — MANUAL
    "24": [("FAIL", "다크 배경 금지 (calm 라이트)", dark_bg)],
    "25": [],  # 커머스 — MANUAL
    "26": [("FAIL", "다크 배경 필수 (절제된 다크)", lambda s: not dark_bg(s)),
           ("FAIL", "네온 글로우 금지", lambda s: has(s, r"text-shadow\s*:\s*(?!none)[^;}]*[1-9]"))],
    "27": [("FAIL", "다크 배경 금지 (웜 라이트)", dark_bg)],
    "28": [],  # 접근성 — 대비는 사람 확인(MANUAL)
    "29": [("FAIL", "다크 배경 금지 (밝은 활력)", dark_bg)],
    "30": [("FAIL", "다크 배경 금지 (라이트 밀도)", dark_bg)],
}

# 모든 스타일 공통 — 콘텐츠 견고성 (WARN, references/content-checklist.md 축)
# FAIL 아님(exit code 영향 X) — 최악 콘텐츠 견딤 자동 신호만.
UNIVERSAL = [
    ("WARN", "tabular-nums 없음 (큰 숫자 정렬)", lambda s: not has(s, r"tabular-nums|font-variant-numeric")),
    ("WARN", "반응형 @media 없음 (모바일 대응)", lambda s: not has(s, r"@media")),
    ("WARN", "prefers-reduced-motion 없음 (접근성)", lambda s: not has(s, r"prefers-reduced-motion")),
]

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
    "13": "오로라 3색은 배경/보더 글로우에만 / 텍스트 흰빛 / 대비 4.5:1",
    "14": "비대칭 벤토 배열(큰1+중2~3+소 여러) / 카드마다 독립 위젯 / 균일 카드 아님",
    "15": "이중 소프트 섀도(바깥 진하게+안쪽 밝게) / radius 28px+ / 파스텔 채도",
    "16": "elevation 단계(dp1·2·4·8) / FAB 우하단 / 큰 터치 타겟",
    "17": "크롬 텍스트 + 신스웨이브 그리드 지평선 / 네온 마젠타·시안 / 스캔라인",
    "18": "엄격한 모듈 그리드 / 빨강 딱 1곳 액센트 / 비대칭 대형 타이포",
    "19": "색·패턴·폰트 폭발 + 겹침 / 단 본문 가독 사수(색면 위 잉크블랙)",
    "20": "촘촘한 위젯 그리드 / 게이지·스파크라인 / 상태 임계 색+텍스트",
    "21": "보라·인디고 그라디언트 액센트 + AI 스파클 / 은은한 글로우 / 클린 라이트",
    "22": "큰 친근 숫자 + 둥근 카드(20px) / 브랜드 컬러 1 / 신뢰+친근 균형",
    "23": "정보 밀도 + 실용 네이비 / 명확한 구획선 / 사이드바 헤비 / 절제",
    "24": "calm 스카이블루·세이지 / 넉넉한 여백 / 부드러운 라운드 / 접근성",
    "25": "볼드 브랜드 + 상품 썸네일 + 프로모 배지 / 활기 / 구매욕",
    "26": "얇은 헤어라인 / 저채도 액센트 1 / 미니멀 여백 / 네온·골드 없음",
    "27": "크림·테라코타·올리브 웜톤 / 따뜻한 절제 / 차가운 파랑 없음",
    "28": "대비 7:1+ / 굵은 2px 보더 / 상태 색+텍스트+아이콘 / 큰 터치 타겟",
    "29": "비비드 컬러 섹션 블록 / 클린 대비 / 밝은 배경 / 무채색 주조 아님",
    "30": "촘촘한 라이트 테이블 + 필터 칩 / 뉴트럴 그리드라인 / 성긴 여백 아님",
}

STYLE_NAME = {
    "01": "SF HUD", "02": "공공포털", "03": "트렌디 SaaS", "04": "고밀도 터미널",
    "05": "브루탈리즘", "06": "글래스모피즘", "07": "미니멀 모노크롬", "08": "럭셔리 다크",
    "09": "레트로 픽셀", "10": "에디토리얼", "11": "네이처 오가닉", "12": "뉴모피즘",
    "13": "오로라 그라디언트", "14": "벤토 그리드", "15": "클레이모피즘", "16": "머티리얼",
    "17": "Y2K 베이퍼웨이브", "18": "스위스", "19": "맥시멀리즘", "20": "다크 대시보드",
    "21": "AI 프로덕트", "22": "핀테크 소프트", "23": "엔터프라이즈 B2B", "24": "헬스케어 웰니스",
    "25": "커머스 리테일", "26": "다크 프로 미니멀", "27": "웜 프로페셔널", "28": "하이컨트라스트 접근성",
    "29": "컬러풀 모던", "30": "데이터 리치 라이트",
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
    fails = [desc for lvl, desc, fn in RULES[nn] if fn(html)]
    warns = [desc for lvl, desc, fn in UNIVERSAL if fn(html)]
    tag = "FAIL" if fails else "PASS"
    print(f"[{tag}] {os.path.basename(path)}  (STYLE {nn} · {name})")
    for d in fails:
        print(f"    ✗ {d}")
    for d in warns:
        print(f"    ⚠ {d}  (콘텐츠 견고성)")
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
