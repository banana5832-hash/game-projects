"""3D 프린팅용 파일(.stl / .3mf)로 내보낸다.

    blender --background --python to_print.py -- 캐릭터.glb -o 캐릭터.stl --height 120

옵션
    --height H   키를 H 밀리미터로 맞춘다(기본 120). 프린터 베드에 맞춰 골라라.
    --solid      떨어져 있는 덩어리들을 하나로 합치고 안쪽 면을 정리한다.
                 프린터 슬라이서가 모델을 뚫린 것으로 볼 때 켜라.

내보낸 뒤에는 슬라이서(Cura·PrusaSlicer 등)에서 한 번 확인해라.
변환 서비스로 만든 모델은 얇은 머리카락이나 손가락이 프린트 중에 부러지기 쉽다.
"""
import argparse, os, sys, math

import bpy
import mathutils


def argv_after_dashes():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def meshes():
    return [o for o in bpy.data.objects if o.type == "MESH"]


def world_bounds():
    """내보낸 파일에 실제로 들어가는 면의 꼭짓점만으로 크기를 잰다.

    폴리곤을 줄이면 어느 면에도 속하지 않는 꼭짓점이 남는데, 내보내기는 그것을
    버린다. 그 점까지 세면 크기가 어긋나므로 삼각형이 쓰는 점만 본다.
    """
    dg = bpy.context.evaluated_depsgraph_get()
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for o in meshes():
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        me.calc_loop_triangles()
        mw = oe.matrix_world
        used = set()
        for t in me.loop_triangles:
            used.update(t.vertices)
        for i in used:
            p = mw @ me.vertices[i].co
            for k in range(3):
                if p[k] < lo[k]:
                    lo[k] = p[k]
                if p[k] > hi[k]:
                    hi[k] = p[k]
        oe.to_mesh_clear()
    if lo[0] == float("inf"):
        raise SystemExit("메시가 하나도 없다")
    return lo, hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--height", type=float, default=120.0)
    ap.add_argument("--solid", action="store_true")
    a = ap.parse_args(argv_after_dashes())

    src = os.path.abspath(a.src)
    out = os.path.abspath(a.out or os.path.splitext(src)[0] + ".stl")
    if not os.path.exists(src):
        raise SystemExit(f"파일이 없다: {src}")
    ext = os.path.splitext(out)[1].lower()
    if ext not in (".stl", ".3mf"):
        raise SystemExit("출력은 .stl 이나 .3mf 여야 한다")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    si = os.path.splitext(src)[1].lower()
    if si in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=src)
    elif si == ".obj":
        bpy.ops.wm.obj_import(filepath=src)
    elif si == ".stl":
        bpy.ops.wm.stl_import(filepath=src)
    else:
        raise SystemExit(f"읽을 수 없는 형식이다: {si}")
    print(f"[1/4] 불러왔다: {os.path.basename(src)} · 메시 {len(meshes())}개")

    # 뼈대·빈 오브젝트는 프린트에 필요 없다
    for o in list(bpy.data.objects):
        if o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)

    lo, hi = world_bounds()
    h = hi[2] - lo[2]
    if h > 1e-9:
        s = a.height / h
        for o in bpy.data.objects:
            if o.parent is None:
                o.scale = [v * s for v in o.scale]
        bpy.context.view_layer.update()
        print(f"[2/4] 키를 {a.height}mm 로 맞췄다")

    lo, hi = world_bounds()
    for o in bpy.data.objects:
        if o.parent is None:
            o.location[0] -= (lo[0] + hi[0]) / 2.0
            o.location[1] -= (lo[1] + hi[1]) / 2.0
            o.location[2] -= lo[2]
    bpy.context.view_layer.update()
    print("[3/4] 바닥 가운데로 옮겼다")

    # 크기를 메시에 굳힌다. 이걸 해야 아래 덩어리 만들기가 제대로 된다.
    for o in meshes():
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    ms = meshes()
    if not ms:
        raise SystemExit("메시가 하나도 없다")
    bpy.context.view_layer.objects.active = ms[0]
    if len(ms) > 1:
        bpy.ops.object.join()
    for o in bpy.data.objects:
        o.select_set(False)

    obj = meshes()[0]
    bpy.context.view_layer.objects.active = obj
    if a.solid:
        lo, hi = world_bounds()
        size = max(hi[i] - lo[i] for i in range(3))
        mod = obj.modifiers.new("덩어리", "REMESH")
        mod.mode = "VOXEL"
        mod.voxel_size = max(size / 320.0, 0.05)   # 가장 긴 쪽을 약 320칸으로
        bpy.ops.object.modifier_apply(modifier=mod.name)
        obj.data.calc_loop_triangles()
        print(f"[4/4] 하나의 덩어리로 다시 만들었다 · 삼각형 {len(obj.data.loop_triangles)}")
    else:
        obj.data.calc_loop_triangles()
        print(f"[4/4] 메시를 하나로 합쳤다 · 삼각형 {len(obj.data.loop_triangles)}")

    # 덩어리로 다시 만들면 표면이 조금 둥글려져 키가 미세하게 달라진다. 다시 맞춘다.
    lo, hi = world_bounds()
    h = hi[2] - lo[2]
    if h > 1e-9 and abs(h - a.height) > 1e-6:
        obj.scale = [v * (a.height / h) for v in obj.scale]
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.select_set(False)
        lo, hi = world_bounds()
        for o in bpy.data.objects:
            if o.parent is None:
                o.location[2] -= lo[2]
        bpy.context.view_layer.update()

    lo, hi = world_bounds()
    print(f"내보내기 직전: 키 {hi[2]-lo[2]:.1f}mm · 가로 {hi[0]-lo[0]:.1f}mm · 세로 {hi[1]-lo[1]:.1f}mm")

    if ext == ".stl":
        try:
            bpy.ops.wm.stl_export(filepath=out)          # Blender 4.2 이상
        except (AttributeError, RuntimeError):
            bpy.ops.export_mesh.stl(filepath=out)        # 그 이전
    else:
        done = False
        for call in (lambda: bpy.ops.export_mesh.threemf(filepath=out),
                     lambda: bpy.ops.export_scene.threemf(filepath=out)):
            try:
                call()
                done = True
                break
            except (AttributeError, RuntimeError):
                continue
        if not done:
            raise SystemExit(
                "이 Blender에는 3MF 내보내기가 없다. 애드온을 따로 깔아야 한다.\n"
                "슬라이서는 .stl도 모두 읽으니, -o 를 .stl 로 바꿔 쓰는 쪽이 간단하다.")

    print(f"\n저장했다: {out}  ({os.path.getsize(out)/1048576:.2f} MB)")
    print(f"크기: 키 {a.height}mm · 슬라이서에서 벽 두께와 서포트를 확인해라")


if __name__ == "__main__":
    main()
