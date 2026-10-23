# Daytona Arcade Recomp iOS·Windows 옵션 점검

대상 원본: alphanu1/daytona-arcade-recomp `32967f60c01c1753b329dc4a3e943c4e1275006b`.
수정 빌드: `082d635b6bef8fc5d6b59e10f3089f0fb2e7f124`.

## 변경 사항

| 항목 | iOS | Windows |
|---|---|---|
| Sync to display | 경과 시간 기준으로 게임을 60fps 진행. 원래 약 57.52fps보다 약 4.3% 빠릅니다. CADisplayLink에는 최대 지원 주사율을 요청합니다. | 기존 디스플레이 주기 기반 동작 유지. 다른 페이싱 모드와 상호 배타 선택. |
| VRR pacing | 실험적 Core Animation 주기 요청과 Metal 최소 표시 시간 적용. 실제 Metal 표시 타임스탬프를 기록하고, 표시가 목표보다 지속적으로 느리면 최소 표시 시간 제한을 해제해 원래 게임 시계로 복귀합니다. | 기존 약 57.52fps 프레임 타이머 유지. 드라이버 VRR을 켜 주는 기능으로 오인하지 않도록 설명 수정. |
| 두 모드 모두 끔 | 약 57.52fps 원래 게임 시계 사용. | 동일. |
| 57.52Hz 디스플레이용 Smooth pacing | 사용자 지정 주사율을 강제할 수 없어 숨김. | 해당 주사율 또는 배수의 디스플레이용 기존 기능 유지. |
| 그래픽 API | Metal 고정. 지원하지 않는 선택지는 숨기고 오래된 설정도 정리. | 자동·Vulkan·Direct3D 12 유지, Metal 선택지 제거. |
| 렌더러·렌더링 해상도 | 소프트웨어·실험적 하드웨어 유지. 하드웨어의 네이티브 drawable 해상도·고정 4K·정수 배율 유지. | 동일. 창 크기 프리셋도 유지. |
| 전체 화면·디스플레이 모드·창 크기·커서 | iOS가 관리하므로 데스크톱 전용 선택지는 숨김. | 유지. SDL이 요청을 거절하면 오류 표시. |
| 색상 | 채도·감마·대비와 GPU 3D 색상 보정 유지. 이미 보정된 CPU 타일/HUD를 GPU에서 다시 보정하던 중복 적용 수정. | 동일. SPIR-V·DXIL·MSL 셰이더 재생성. |
| 화면비·HUD·배경·시야 거리·프레임 스킵 등 | 기존 런타임 경로 유지. | 동일. |
| 오디오 | 볼륨·음소거·음악·효과음 유지. 네이티브 오디오의 실험적 제한 설명 유지. | 동일. 네이티브 오디오는 display sync의 피치 변화와 동일하게 동작하지 않음. |
| 입력 | SDL이 보고하는 키보드·컨트롤러·아날로그 설정 유지. 기존 터치/메뉴 변경 보존. | 키보드·게임패드·조이스틱·휠 축 설정 유지. |
| 포스 피드백 | SDL에서 럼블 지원을 보고하는 컨트롤러의 럼블 경로 유지. 휠 모터 반전·데스크톱 드라이버 토글은 숨김. 아이폰 본체 진동을 보장하지 않음. | 휠 모터·게임패드 럼블 유지. 반전은 휠에만 영향을 준다는 설명 추가. |
| 네트워크 링크 | 기존 TCP 링크 유지, 로컬 네트워크 권한 설명 추가. | 기존 Winsock 경로 유지. |

## 검증 범위

- iOS 타이밍 테스트: 30/60/80/120Hz 루프에서 게임 진행률, 모드 충돌 정리, 일시 정지 처리를 검증했습니다.
- iOS arm64 앱 소스 컴파일: 새 Objective-C++ 페이싱 코드와 수정된 SDL Metal 백엔드 컴파일을 통과했습니다.
- Windows: ClangCL 앱 컴파일과 app_pacing·app_config·app_controls 테스트 3개를 통과했습니다.
- Windows 최종 게임 실행 파일 빌드 성공. PE32+ x86-64 구조와 옵션 문자열을 확인했습니다. SDL은 정적으로 연결되며 MSVC 런타임 DLL 의존성이 있습니다.
- iOS 최종 게임 빌드 및 IPA 검사 성공. 번들 ID com.boucydesigns.daytona, 버전 0.5(빌드 5), arm64, ProMotion 허용 플래그, 아이콘·로컬 네트워크 설명, 페이싱 진단과 iOS 옵션 포함 여부를 확인했습니다. 데스크톱 전용 옵션 문자열이 없으며 서명·프로비저닝이 포함되지 않은 IPA입니다. 압축 파일 무결성 및 Mach-O 구조도 확인했습니다.

## 의도적으로 보장하지 않는 동작

iOS의 주사율 범위 설정은 운영체제에 대한 요청입니다. 정확한 57.52Hz 패널 구동, 물리적 VRR, 120Hz 고정 출력은 검증되지 않았습니다. Metal 표시 타임스탬프와 CADisplayLink 콜백 속도를 별도로 기록하며, 둘을 물리적 패널 스캔아웃 검증으로 표시하지 않습니다. 배터리·발열·운영체제 정책에 따라 실제 주기가 달라질 수 있습니다.

Sync to display는 게임을 60fps로 진행시키므로 120개의 서로 다른 게임 프레임을 만드는 기능이 아닙니다. 프레임 보간 방식의 Smooth Motion 추가는 사용자의 지시에 따라 보류했습니다.

Windows에서도 G-Sync/FreeSync를 앱이 활성화하거나 모니터의 실제 VRR 동작을 확인했다는 주장을 하지 않습니다. 실물 모니터·아이폰·컨트롤러·휠·복수 기기 링크·실제 오디오 출력 검증은 수행하지 않았습니다.

iOS 진단 파일은 앱의 Documents/daytona-pacing.csv에 기록됩니다. requested rate, CADisplayLink 시간, Metal 실제 표시 간격, 폴백 상태를 확인할 수 있으며 hardware_vrr_verified는 0입니다.

빌드 실행: https://github.com/ajellia81-cmd/daytona-arcade-recomp/actions/runs/39900985954

## 파일 SHA-256

- Daytona-Windows-pacing-audit.zip: `e417c82e023d39ca434011d92f20cf73c397f17bd6609ec8709006c126c8ace8`
- Daytona-iOS-pacing-audit-unsigned.ipa: `a97e052e7a4ff0920a2ddb795336a4b0b67b6ae896b562344b6be3808ee7eca6`
