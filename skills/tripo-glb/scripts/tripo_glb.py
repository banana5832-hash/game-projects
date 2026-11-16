#!/usr/bin/env python3
"""그림 한 장 -> Tripo 3D 모델(.glb) 내려받기.

  python tripo_glb.py 그림.png --out output [--face-limit 20000] [--lowpoly] [--no-texture] [--max-mb 15]
  python tripo_glb.py --balance

키는 환경 변수 TRIPO_API_KEY에서 읽는다(코드나 파일에 적지 않는다).
"""
import argparse, asyncio, os, sys
from tripo3d import TripoClient, TaskStatus


def size_mb(path):
    return os.path.getsize(path) / 1024 / 1024


async def run(a):
    key = os.environ.get("TRIPO_API_KEY")
    if not key:
        print("TRIPO_API_KEY가 없다. tripo3d.ai에서 키를 발급해 환경 변수로 설정해 달라.")
        return 2
    async with TripoClient(api_key=key) as c:
        if a.balance:
            print(await c.get_balance())
            return 0
        if not a.image or not os.path.isfile(a.image):
            print("그림 파일을 찾을 수 없다:", a.image)
            return 2
        os.makedirs(a.out, exist_ok=True)

        tid = await c.image_to_model(
            image=a.image,
            face_limit=a.face_limit,
            texture=not a.no_texture,
            pbr=not a.no_texture,
        )
        task = await c.wait_for_task(tid, verbose=True)
        if task.status != TaskStatus.SUCCESS:
            print("생성 실패:", task.status, getattr(task, "error_msg", ""))
            return 3

        if a.lowpoly:
            tid2 = await c.smart_lowpoly(original_model_task_id=tid, face_limit=a.face_limit)
            task = await c.wait_for_task(tid2, verbose=True)
            if task.status != TaskStatus.SUCCESS:
                print("저폴리 변환 실패:", task.status, getattr(task, "error_msg", ""))
                return 3

        files = await c.download_task_models(task, a.out)
        paths = [p for p in files.values() if p]
        if not paths:
            print("내려받은 파일이 없다:", files)
            return 3
        for p in dict.fromkeys(paths):
            mb = size_mb(p)
            print(f"{p}  {mb:.1f}MB")
            if mb > a.max_mb:
                print(f"경고: {a.max_mb}MB를 넘는다. --lowpoly 나 더 작은 --face-limit 로 다시 만들어 보자.")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("image", nargs="?")
    p.add_argument("--out", default="output")
    p.add_argument("--face-limit", type=int, default=20000)
    p.add_argument("--lowpoly", action="store_true")
    p.add_argument("--no-texture", action="store_true")
    p.add_argument("--max-mb", type=float, default=15)
    p.add_argument("--balance", action="store_true")
    sys.exit(asyncio.run(run(p.parse_args())))


if __name__ == "__main__":
    main()
