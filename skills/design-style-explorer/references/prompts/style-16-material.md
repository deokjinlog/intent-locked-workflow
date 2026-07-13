# STYLE 16 — 머티리얼 (매력 축: 익숙함/체계)

매력 가설: 처음 봐도 어디를 눌러야 할지 안다. 매력은 새로움이 아니라 학습된 관성 — 온 세상이 쓰는 문법을 그대로 써서 인지 비용 0.
고도화 = elevation 그림자 레이어의 위계와 FAB의 존재감. 마스터 프롬프트 뒤에 붙여 사용한다.

```
[스타일 지시 — 머티리얼 v2]

■ 무드
Google Material Design 3. 종이(surface)가 여러 층으로 떠 있는 세계.
높이(elevation)가 곧 위계 — 더 높이 뜬 것이 더 중요하고 더 앞에 있다.
차분하고 체계적이며, 모든 요소가 규칙을 따른다. 발명이 아니라 준수.

■ 팔레트 — 톤 팔레트 (보라 primary + surface 톤)
Primary #6750A4 / on-primary #FFFFFF / primary-container #EADDFF / on-primary-container #21005D
Surface #FEF7FF / surface-container-low #F7F2FA / surface-container #F3EDF7 / surface-container-high #ECE6F0
on-surface #1D1B20 / on-surface-variant #49454F / outline #79747E
Secondary #625B71 / 문제(error) #B3261E / on-error-container #410E0B / 성공 #386A20
배경은 surface, 카드는 surface-container 계열 — 톤 차이가 층을 만든다.

■ 타이포 — Material type scale
본문 한글은 Pretendard 가정. 영문·숫자·라벨은 Roboto (구글폰트) 명시 로드.
Display-small 36/44 · Headline-medium 28/36 · Title-large 22/28 700 ·
Title-medium 16/24 500 · Body-large 16/24 400 · Body-medium 14/20 ·
Label-large 14/20 500 (버튼·탭·칩). letter-spacing은 라벨 0.1px, 본문 0.15~0.25px.

■ 형태
radius 중간 — 카드·시트 12px, 버튼·칩 8px(fully-rounded 칩은 pill), FAB 16px, 다이얼로그 28px.
elevation 5단계 그림자(dp): 
  dp1  0 1px 2px rgba(0,0,0,.30), 0 1px 3px 1px rgba(0,0,0,.15)  — 카드 기본
  dp2  0 1px 2px rgba(0,0,0,.30), 0 2px 6px 2px rgba(0,0,0,.15)  — 버튼 hover
  dp4  0 2px 3px rgba(0,0,0,.30), 0 6px 10px 4px rgba(0,0,0,.15) — 메뉴·FAB
  dp8  0 4px 4px rgba(0,0,0,.30), 0 8px 12px 6px rgba(0,0,0,.15) — 다이얼로그·드래그
큰 터치 타겟: 인터랙티브 요소 최소 48×48px 히트영역 확보.

■ 히어로 연출 — 층이 얹히는 순서 (로드 시퀀스)
0.0s 앱바(top app bar)가 위에서 elevation과 함께 내려앉음 (240ms, standard easing)
0.15s surface 위로 KPI 카드 4장이 왼→오 40ms씩 stagger, y+8px→0 + 페이드 (각 220ms)
0.45s 차트 카드가 dp1로 올라오며 막대가 baseline에서 500ms ease-out으로 차오름
0.6s 테이블 행이 상단부터 30ms 간격으로 페이드인
0.9s FAB가 우하단에서 scale 0.6→1 + dp4 그림자 등장 (250ms, emphasized easing) — 마지막에 톡

■ 마이크로 인터랙션 (이 스타일의 실체)
1) 리플: 모든 버튼·칩·행·FAB 클릭 시 클릭 지점에서 원형 리플이 400ms 퍼짐
   (primary 12% 투명 오버레이). state-layer 규칙 — hover 8% / focus 12% / pressed 12%.
2) elevation 상승: 버튼·카드 hover 시 dp1→dp2로 그림자 부드럽게 확장 (150ms)
3) FAB hover: dp4→dp8 상승 + 미세 scale 1.03. press 시 리플 + scale 0.97
4) 스위치·체크: track/thumb가 primary로 채워지며 thumb가 굴러가는 200ms 트랜지션
5) 탭 인디케이터: 하단 밑줄이 선택 탭으로 슬라이드 (250ms emphasized)

■ 시그니처
elevation 단계 그림자로 표현된 층위 + 우하단에 늘 떠 있는 원형 FAB(56px, primary 배경,
on-primary 아이콘, dp4). 이 둘이 화면을 즉시 "머티리얼"로 읽히게 하는 각인.

■ 접근성·안전장치
- prefers-reduced-motion: stagger·차오름·리플 확산 제거 (state-layer 색 변화만 즉시 적용)
- JS 실패 폴백: 리플 없이도 :hover/:active state-layer가 CSS만으로 동작, FAB는 정적 표시
- focus-visible: primary 3px 아웃라인 + offset 2px (그림자만으로 포커스 식별 금지)
- 대비: on-surface-variant는 본문 최소 크기에서 4.5:1 확보, error 텍스트는 아이콘 병행
- 큰 터치 타겟: 밀집 테이블에서도 행 높이 48px 이상, 아이콘 버튼 48×48 히트영역

■ 금지 (정체성의 절반)
글래스모피즘·backdrop-filter, 브루탈리즘식 하드엣지·1px 순검정 보더, 과한 그라디언트,
네온 글로우·발광 효과, 세리프 서체, 다크 배경 강제(밝은 surface 기본), radius 0 또는 24px 초과,
그림자 없는 완전 플랫(elevation 무시), FAB 생략, 광원 불일치(그림자 방향 제각각),
채도 높은 원색 남발(톤 팔레트 이탈).

■ 자체 크리틱 루프
1) elevation이 정보 위계와 일치하는가? — 더 중요한 것이 더 높이 떠 있는지 dp값 전수 검사
2) FAB가 우하단에 존재하며 주요 액션(예: 새 리포트/추가)을 담고 있는가?
3) 클릭 가능한 모든 요소에 리플 + state-layer가 빠짐없이 붙었는가?
4) 톤 팔레트를 벗어난 임의 색이나 세리프·글래스 잔재가 섞이지 않았는가? — 이탈 색 색출
```
