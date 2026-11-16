"""Tripo AI로 3D 모델(.glb) 만들기.

사용:
  python tools/tripo_gen.py image  그림.jpg  [출력폴더]
  python tools/tripo_gen.py text   "흰 머리 소녀 캐릭터" [출력폴더]
  python tools/tripo_gen.py balance

키는 환경에 저장돼 있다(코드나 파일에 적지 않는다).
"""
import asyncio, os, sys
from tripo3d import TripoClient, TaskStatus

async def main():
    if len(sys.argv) < 2:
        print(__doc__); return 1
    mode = sys.argv[1]
    # 키는 네트워크 프록시가 요청에 넣어 주므로 형식만 맞는 자리표시자를 쓴다.
    key = os.environ.get("TRIPO_API_KEY") or "tsk_proxy-injected"
    async with TripoClient(api_key=key) as c:
        if mode == "balance":
            print(await c.get_balance()); return 0
        src = sys.argv[2]; out = sys.argv[3] if len(sys.argv) > 3 else "output"
        os.makedirs(out, exist_ok=True)
        if mode == "image":
            tid = await c.image_to_model(image=src)
        elif mode == "text":
            tid = await c.text_to_model(prompt=src)
        else:
            print(__doc__); return 1
        task = await c.wait_for_task(tid, verbose=True)
        if task.status != TaskStatus.SUCCESS:
            print("실패:", task.status); return 2
        print(await c.download_task_models(task, out))
    return 0

sys.exit(asyncio.run(main()))
