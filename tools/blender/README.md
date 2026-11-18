# Blender 스크립트 — 3D 캐릭터를 게임과 프린터에 맞추기

VRoid Studio나 Tripo·Meshy에서 만든 3D 모델을 **ASCENDANT Gatebreaker**에 넣을 수 있는
`.glb`로 다듬고, 3D 프린팅용 `.stl`로도 내보낸다.

Blender를 화면 없이 돌리므로 창은 뜨지 않는다. 명령 한 줄이면 끝난다.

## 준비

Blender 4.0 이상이면 된다. Windows라면 보통 이 위치에 있다.

```
C:\Program Files\Blender Foundation\Blender 4.5\blender.exe
```

매번 긴 경로를 치기 싫으면 PowerShell에서 한 번 이렇게 정해 두면 그 창에서는 `blender`로 쓸 수 있다.

```powershell
Set-Alias blender "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
```

## 1. 게임에 넣을 `.glb` 만들기 — `glb_fixup.py`

```powershell
blender --background --python glb_fixup.py -- 캐릭터.glb -o 캐릭터_game.glb --faces 20000 --height 1.8 --face-front
```

하는 일은 다섯 가지다.

1. `.glb` `.gltf` `.fbx` `.obj` `.vrm` 중 하나를 읽는다
2. `--face-front`를 주면 캐릭터가 +Z를 보도록 180도 돌린다 (게임 코드가 +Z 정면을 쓴다)
3. 삼각형을 `--faces` 아래로 줄인다
4. 키를 `--height`로 맞춘다
5. 발바닥을 바닥(z=0)에, 좌우 가운데를 0에 맞춘다

| 옵션 | 기본값 | 뜻 |
| --- | --- | --- |
| `--faces N` | 20000 | 삼각형을 N개 아래로. `0`이면 줄이지 않는다 |
| `--height H` | 1.8 | 키를 H로 (미터). `0`이면 크기를 건드리지 않는다 |
| `--face-front` | 꺼짐 | +Z를 보도록 돌린다 |
| `--no-center` | 꺼짐 | 바닥 가운데로 옮기지 않는다 |

얼굴이나 손이 뭉개지면 `--faces`를 올려라. 3만까지는 웹에서도 괜찮다.
파일이 15MB를 넘으면 경고가 뜬다. 그때는 텍스처 해상도를 줄이는 쪽이 효과가 크다.

## 2. VRoid 캐릭터 가져오기 — `vrm_to_glb.py`

VRoid Studio에서 캐릭터를 만들고 `.vrm`으로 내보낸 다음 쓴다.

먼저 Blender에 **VRM 애드온**을 깔아야 한다.
<https://github.com/saturday06/VRM-Addon-for-Blender> 에서 zip을 받아
Blender → 편집 → 환경 설정 → 애드온 → 디스크에서 설치.

```powershell
blender --background --python vrm_to_glb.py -- 캐릭터.vrm -o 캐릭터.glb
```

VRM은 이미 +Z 정면이고 사람 크기라 돌리거나 키를 바꾸지 않는다.
VRoid 모델은 보통 삼각형이 7만~15만이라 기본으로 2만까지 줄인다.

## 3. 3D 프린팅용 파일 — `to_print.py`

```powershell
blender --background --python to_print.py -- 캐릭터.glb -o 캐릭터.stl --height 120
```

| 옵션 | 기본값 | 뜻 |
| --- | --- | --- |
| `--height H` | 120 | 키를 H 밀리미터로. 프린터 베드에 맞춰 골라라 |
| `--solid` | 꺼짐 | 떨어진 덩어리를 하나로 합치고 속을 메운다 |

슬라이서가 "모델이 뚫려 있다"고 하면 `--solid`를 켜라. 대신 표면이 아주 조금 둥글어진다.

`.3mf`는 Blender 기본 설치에 없다. 애드온을 따로 깔거나, 그냥 `.stl`을 써라.
슬라이서(Cura, PrusaSlicer, Bambu Studio)는 모두 `.stl`을 읽는다.

프린트 전에 슬라이서에서 꼭 확인해라. 변환 서비스로 만든 모델은 머리카락과 손가락이
얇아서 출력 중에 부러지기 쉽다. 그런 부분은 Blender에서 조금 두껍게 만들거나
서포트를 넉넉히 넣어라.

## 추천하는 순서

예쁜 미소녀·미소년을 안정적으로 얻는 길이다.

1. **VRoid Studio**에서 캐릭터를 만든다 (무료, 애니풍 전용, 슬라이더로 조절)
2. `.vrm`으로 내보낸다
3. `vrm_to_glb.py`로 게임용 `.glb`를 만든다
4. 그 `.glb`를 게임에 넣는다
5. 프린트하고 싶으면 `to_print.py`로 `.stl`을 뽑는다

그림 한 장을 Tripo나 Meshy로 변환하는 길도 있지만, 머리카락과 손이 자주 뭉개진다.
그 결과물도 `glb_fixup.py`로 다듬으면 쓸 만해진다.

## 시험해 본 환경

Blender 5.0.1로 전 과정을 돌려 확인했다. 키 맞추기, 바닥 정렬, +Z 정면 돌리기,
폴리곤 줄이기, `.stl` 내보내기가 모두 의도대로 나왔다.
`.vrm` 읽기는 VRM 애드온이 있어야 해서 여기서는 확인하지 못했다.
