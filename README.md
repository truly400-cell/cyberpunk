# Expanded Dual Wielding 3.7 — 양손 위치·회전 맞춤 패치 v4 TEST

[v4 설치 ZIP 다운로드](https://github.com/truly400-cell/cyberpunk/raw/refs/heads/main/downloads/EDW_3.7_MatchedPose_v4_TEST.zip)

긴 총기에서 오른손 회전만 바꾸던 v3를 교체했습니다. v4는 **왼쪽 어깨·팔·손·무기의 위치와 회전을 기준으로 오른쪽을 대칭 배치**하도록 상위 그래프를 수정합니다. 왼쪽과 오른손 권총·리볼버 원본 포즈는 보존합니다. 무기의 모델 크기가 다르면 외곽선까지 같아지는 것은 아닙니다.

**게임 완전 종료 → 이전 v1/v2/v3 패치 OFF → v4만 ON. 원본 EDW3.7은 켜둡니다.** 수동 설치는 ZIP의 archive/bin/r6를 게임 폴더의 같은 경로에 덮어씁니다. 내부 archive 이름은 이전과 같아 중복 설치를 막습니다. Reload all mods만으로는 교체되지 않습니다.

CET의 **EDW Matched Dual-Gun Pose** 창에서 Match 체크, **Extra roll trim=0**을 사용하고 닫은 뒤 양손 SMG·AR·산탄총 등으로 LT 조준합니다. 이전 45도 설정은 추가 보정 0도로 이전합니다. 왼손의 기울기를 함께 반영하므로 0도에서도 맞춤 포즈는 켜집니다. `GetMod("EDWRightCant").status()`에서 `[EDWRightCant v4]`, 활성 요청 `weight=1`을 확인할 수 있습니다. 3초 테스트 버튼도 유지했습니다.

종료 크래시 로그는 CET 종료 중 무기·아이템·스탯 파괴 경로의 널 접근을 보여주지만 EDW를 단일 원인으로 지목하지는 않습니다. 이전 패치의 **플레이어 객체 보관과 onShutdown 네이티브 호출을 제거**했습니다. 이제 종료 시 Lua 상태만 정리하고, 플레이어 분리 전에 업데이트를 차단하며, 상태 표시는 숫자·문자열 스냅샷만 읽습니다. 크래시 보고 기능을 끄는 변경은 없습니다.

WolvenKit8.18.0 변환·패킹·재추출 일치, 새 노드51개의 초기화/소유자 등록, 원본 필드·연결 보존, 7개 생명주기 테스트와 5개 참조 뼈대 수학 테스트(무작위128포즈 포함)를 통과했습니다. **실제 플레이어 뼈대·게임 자세·redscript 컴파일·종료 크래시 해결은 이 환경에서 검증하지 못했습니다.** 원본3.7 전용이며 다른 player_base 변경 모드와 충돌할 수 있습니다. 상세 설치·진단·검증 결과는 ZIP에 있습니다.

---

# VHaptics Trigger Recoil — 듀얼센스 USB 테스트 빌드 v1

[설치 ZIP 다운로드](https://github.com/truly400-cell/cyberpunk/raw/refs/heads/main/downloads/VHaptics_TriggerRecoil_USB_TEST_v1.zip) · [추가 프로그램 소스 및 테스트](https://github.com/truly400-cell/cyberpunk/raw/refs/heads/main/downloads/VHaptics_TriggerRecoil_USB_TEST_v1_SOURCE.zip)

사용자가 제공한 VHaptics v1.0에 **발사 이벤트 기반 적응형 트리거 진동**을 추가했습니다. SMG·돌격소총·기관총은 연사 간격에 따라 트리거를 떨고, 발사가 끝나면 효과를 해제합니다. 기존 몸체 오디오 진동 실행 파일과 CSV·redscript는 유지합니다.

**듀얼센스/엣지 USB 전용이며 실제 Windows·게임·패드 실행은 미검증입니다.** Lua 연결 검증, Go 테스트 12개, Windows x64 빌드 및 정적 검사를 통과한 테스트 빌드입니다. 블루투스는 지원하지 않습니다.

게임 종료 후 기존 모드를 백업하고 ZIP의 `bin`·`r6` 폴더를 게임 설치 폴더에 덮어쓰세요. 모드 폴더의 `start_triggers.bat`를 별도로 실행해야 합니다. **게임의 바닐라 적응형 트리거 및 DSX 등 다른 트리거 출력을 꺼야 합니다. 바닐라 압력과 진동을 합성하는 기능은 없습니다.** 원본 `VHaptics.exe`의 몸체 진동은 기존 사용법대로 실행합니다.

강도는 모드 폴더의 `triggers.ini`에서 `strength=5`를 1~8로 조절한 뒤 보조 프로그램을 재시작합니다. `test_triggers.bat`로 게임 밖에서 R2 2초 테스트를 할 수 있으며, 중단은 `stop_triggers.bat`입니다. 설치·진단·원복 안내와 검증 보고서는 ZIP에 있습니다.

참고 요청된 Nexus Mods 4156 페이지는 네트워크 정책 때문에 확인하지 못했습니다. 첨부 모드와 공개 DualSense USB 프로토콜을 바탕으로 추가 기능을 구현했습니다.

---

# Alex Complete 1.0 — Bob Pack Vol.2 #006 / 빨간색 v1

[설치용 PATCH ZIP 다운로드](https://github.com/truly400-cell/cyberpunk/raw/refs/heads/main/downloads/Alex_Bob006_Red_v1_PATCH.zip) · [.archive 파일만 다운로드](https://github.com/truly400-cell/cyberpunk/raw/refs/heads/main/downloads/%21%21%21%21%21_Alex_Bob006_Red_PATCH_v1.archive)

사용자가 제공한 Alex Complete 1.0에 **Bob #006 단발과 빨간색(red_apple)**을 적용하는 추가 패치입니다. 게임을 종료하고 **원본 Alex Complete 1.0의 파일을 모두 유지한 채**, ZIP의 `archive` 폴더를 게임 설치 폴더에 풀어 넣으세요. **ArchiveXL·RED4ext와 원본 모드의 기존 의존 모드가 필요합니다.** 필요한 Bob 헤어 리소스는 포함되어 있습니다.

알렉스 외형 38개를 변경하며 얼굴·의상·표정·스크립트를 유지합니다. **변장·변신 중간 연출용 외형 8개는 기존 헤어를 보존합니다.** WolvenKit 8.18.0 수정·패킹·재추출, 비헤어 데이터 보존, 107개 세그먼트 압축 해제 및 인덱스 CRC64 검사를 통과했습니다. **실제 게임 실행은 미검증입니다.** 설치·복구 안내와 검증 보고서는 ZIP에 있습니다.

PATCH .archive SHA-256: `03b966c1a89bdae56576f7db915959066146d725a11984f6672a8e0c38736bc8`

---

# Songbird Rework 2.1 DS — Vikki 앞머리 포니테일 / 금발 v1

[설치용 PATCH ZIP 다운로드](https://github.com/truly400-cell/cyberpunk/raw/refs/heads/main/downloads/Songbird_Vikki_Bangs_Blonde_v1_PATCH.zip) · [.archive 파일만 다운로드](https://github.com/truly400-cell/cyberpunk/raw/refs/heads/main/downloads/%21%21%21%21%21_Songbird_Vikki_Bangs_Blonde_PATCH_v1.archive)

사용자가 제공한 Songbird Rework 2.1 DS에 Vikki High Ponytail의 **앞머리 포함 버전**과 **금발(blonde_golden)**을 적용하는 추가 패치입니다. 게임을 종료하고 **원본 `ARK_PACK_SongBird_Rework_2.1_DS.archive`는 유지한 채**, ZIP의 `archive` 폴더를 게임 설치 폴더에 풀어 넣으세요. **ArchiveXL과 호환되는 RED4ext가 필요합니다.** Vikki 헤어 리소스는 포함되어 있습니다.

WolvenKit 8.18.0 수정·패킹·재추출, 외형별 금발/리그 연결, 비헤어 컴포넌트 보존, 150개 세그먼트 압축 해제 및 인덱스 CRC64 검사를 통과했습니다. 얼굴·의상은 원본 설정을 유지합니다. **실제 게임 실행은 미검증입니다.** 설치·복구 안내와 검증 보고서는 ZIP에 있습니다.

PATCH .archive SHA-256: `50103239fbc82d3a4a6f8f03ea74125d7157f1b3c78b67793cdb890791d11c85`

---

# Maiko New Look — Atomiic Short Shag Hair v1

[설치용 ZIP 다운로드](https://github.com/truly400-cell/cyberpunk/raw/refs/heads/main/downloads/Maiko_NewLook_Atomiic_ShortShag_v1.zip) · [.archive 파일만 다운로드](https://github.com/truly400-cell/cyberpunk/raw/refs/heads/main/downloads/%21_Maiko_NewLook_Atomiic_ShortShag_v1.archive)

사용자가 제공한 Maiko New Look Alt 버전의 머리를 Atomiic Short Shag Hair로 교체했습니다. WolvenKit 8.18.0으로 제작했으며, 얼굴·의상과 기존 머리색(일반: 갈색, 캐주얼: 분홍색)을 유지합니다. 일반·캐주얼 및 포토모드용 마에코 외형에 적용됩니다.

게임을 완전히 종료하고 기존 `!_Tyger_Claws_gang_NewLook_Maiko_Alt_V1.archive`를 게임 폴더 밖으로 옮겨 백업한 뒤, ZIP의 `archive` 폴더를 Cyberpunk 2077 설치 폴더에 풀어 넣으세요. **ArchiveXL과 호환되는 RED4ext가 필요합니다.** 필요한 아토믹 헤어 리소스는 포함되어 있습니다. 다른 마에코 외형 변경 모드와 함께 설치하지 마세요.

리소스 38개 재추출, 압축 세그먼트 247개 해제, 인덱스 CRC64 및 ZIP 무결성 검사를 통과했습니다. 마에코 외형 4개의 헤어 변경과 나머지 외형 84개의 보존을 확인했으며, 수정하지 않은 압축 버퍼 168개는 원본 바이트 그대로 유지합니다. **실제 게임 실행은 미검증입니다.** 자세한 설치·복구 안내와 검증 보고서는 ZIP에 있습니다.

ZIP SHA-256: `fffeb0bc49847265243af1b51d1756fee2868357d7a2e445247b111e7965100d`

.archive SHA-256: `a9b12aef482f69700cab5fca0d2079d37117eedc1dd588d4bd5f4fa8401c0f9e`

---

# ELIZABETH Bob003 Black — 바닐라 헤어 중첩 수정 v6

[새 v6 ZIP 다운로드](https://github.com/truly400-cell/cyberpunk/raw/refs/heads/main/downloads/ELIZABETH_Bob003_Black_HOLOCALL_v6_ArchiveXL.zip)

게임을 완전히 종료하고 기존 Elizabeth 모드 v3·v4·v5를 게임 폴더 밖으로 옮긴 뒤, ZIP의 `archive` 폴더를 Cyberpunk 2077 설치 폴더에 풀어 넣으세요. **v6의 `.archive`와 `.archive.xl` 두 파일을 함께 설치해야 합니다.** v5에서 사용한 ArchiveXL과 호환되는 RED4ext를 유지하세요.

사용자는 v5에서 홀로콜 입 움직임이 정상이라고 확인했지만, 일반 외형에 원래 헤어가 함께 보인다고 보고했습니다. 사용자가 올린 게임 원본을 대조한 결과 일반 외형의 기본 헤어는 `hh_034`, 잠복 외형은 `hh_083`이었습니다. v6는 외형별 실제 헤어 이름·ID로 교체 대상을 바로잡았습니다.

v5의 얼굴 보존 방식을 유지하고, 일반 외형의 원본 헤어·리그·그림자 3개를 정확히 교체합니다. 헤어 캡만 추가하며 잠복 외형의 기존 교체는 유지합니다. 원본 얼굴·의상 컴포넌트는 패치하지 않고, 나머지 38개 모드 리소스는 동일합니다.

WolvenKit 재추출, 69개 세그먼트 압축 해제, 인덱스 CRC64 및 ZIP 무결성 검사를 통과했습니다. 업로드된 원본에 ArchiveXL의 실제 병합 규칙을 적용해, 원래 헤어 메시가 남지 않고 비헤어 컴포넌트가 유지됨을 확인했습니다. **v6의 실제 게임 실행은 아직 미검증입니다.** 자세한 설치·복구 안내는 ZIP의 `README_KO.txt`에 있습니다.

v6 ZIP SHA-256: `fd56f5b7f6bec03152b0087ec56349ce6d50ff23313c3f4ae41192755df38317`
