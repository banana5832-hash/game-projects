"""VRoid Studio에서 내보낸 .vrm을 게임용 .glb로 바꾼다.

먼저 Blender에 VRM 애드온이 깔려 있어야 한다.
    https://github.com/saturday06/VRM-Addon-for-Blender  에서 zip을 받아
    Blender → 편집 → 환경 설정 → 애드온 → 디스크에서 설치.

    blender --background --python vrm_to_glb.py -- 캐릭터.vrm -o 캐릭터.glb

옵션은 glb_fixup.py와 같다. VRM은 이미 +Z 정면이고 키도 사람 크기라
기본값은 돌리지도 키를 바꾸지도 않는다.

VRoid 모델은 보통 삼각형이 7만~15만이라 그대로는 웹 게임에 무겁다.
기본으로 2만 아래까지 줄인다. 얼굴이 뭉개지면 --faces 를 올려라.
"""
import os, sys, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))


def has_vrm_addon():
    try:
        import addon_utils
        for m in addon_utils.modules():
            name = getattr(m, "__name__", "")
            if "vrm" in name.lower():
                return True
    except Exception:
        pass
    return False


def main():
    import bpy  # noqa: F401  (Blender 안에서만 돈다)
    if not has_vrm_addon():
        print("VRM 애드온이 보이지 않는다. 위 설명의 주소에서 받아 설치한 뒤 다시 실행해라.")
        print("설치했는데도 이 말이 나오면 환경 설정의 애드온 목록에서 체크가 켜져 있는지 봐라.")
        raise SystemExit(2)

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        raise SystemExit("쓸 .vrm 파일을 적어라")
    if "--faces" not in argv:
        argv += ["--faces", "20000"]
    if "--height" not in argv:
        argv += ["--height", "0"]        # VRM은 이미 사람 크기다

    sys.argv = [sys.argv[0], "--"] + argv
    exec(open(os.path.join(HERE, "glb_fixup.py"), encoding="utf8").read(),
         {"__name__": "__main__", "__file__": os.path.join(HERE, "glb_fixup.py")})


if __name__ == "__main__":
    main()
