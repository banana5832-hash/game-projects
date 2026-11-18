"""게임에 넣을 .glb를 손질한다.

Blender를 화면 없이 돌려서, 변환 서비스(Tripo·Meshy)나 VRoid에서 받은 모델을
three.js 게임에 바로 쓸 수 있는 크기로 줄이고 방향을 맞춘다.

    blender --background --python glb_fixup.py -- 입력.glb -o 출력.glb --faces 20000

주요 옵션
    --faces N     삼각형을 N개 아래로 줄인다(기본 20000). 0이면 줄이지 않는다.
    --height H    발끝부터 머리끝까지를 H로 맞춘다(기본 1.8, 단위는 미터).
    --face-front  캐릭터가 +Z(화면 앞쪽)를 보도록 돌린다. 게임 코드가 +Z 정면을 쓴다.
    --no-center   바닥 가운데로 옮기지 않는다.
"""
import argparse, os, sys, math

import bpy
import mathutils


def argv_after_dashes():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_any(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".obj":
        # Blender 4.x
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == ".vrm":
        # VRM 애드온이 설치돼 있어야 한다. vrm_to_glb.py 쪽 설명을 보라.
        bpy.ops.import_scene.vrm(filepath=path)
    else:
        raise SystemExit(f"읽을 수 없는 형식이다: {ext}")


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


def tri_count():
    total = 0
    for o in meshes():
        me = o.data
        me.calc_loop_triangles()
        total += len(me.loop_triangles)
    return total


def apply_transforms():
    for o in meshes():
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in bpy.data.objects:
        o.select_set(False)


def rotate_all(z_deg):
    import mathutils
    rot = mathutils.Matrix.Rotation(math.radians(z_deg), 4, "Z")
    for o in bpy.data.objects:
        if o.parent is None:
            o.matrix_world = rot @ o.matrix_world


def decimate(target):
    """삼각형 수가 target을 넘으면 비율을 계산해 한 번에 줄인다."""
    cur = tri_count()
    if target <= 0 or cur <= target:
        return cur, cur
    ratio = max(0.02, target / float(cur))
    for o in meshes():
        mod = o.modifiers.new("줄이기", "DECIMATE")
        mod.ratio = ratio
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return cur, tri_count()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--faces", type=int, default=20000)
    ap.add_argument("--height", type=float, default=1.8)
    ap.add_argument("--face-front", action="store_true")
    ap.add_argument("--no-center", action="store_true")
    a = ap.parse_args(argv_after_dashes())

    src = os.path.abspath(a.src)
    out = os.path.abspath(a.out or os.path.splitext(src)[0] + "_game.glb")
    if not os.path.exists(src):
        raise SystemExit(f"파일이 없다: {src}")

    clear_scene()
    import_any(src)
    if not meshes():
        raise SystemExit("불러온 파일에 메시가 없다")
    print(f"[1/5] 불러왔다: {os.path.basename(src)} · 삼각형 {tri_count()}")

    if a.face_front:
        rotate_all(180.0)
        print("[2/5] +Z를 보도록 180도 돌렸다")
    else:
        print("[2/5] 방향은 그대로 둔다")

    apply_transforms()
    before, after = decimate(a.faces)
    if before != after:
        print(f"[3/5] 삼각형 {before} → {after}")
    else:
        print(f"[3/5] 삼각형 {after} · 줄이지 않았다")

    lo, hi = world_bounds()
    h = hi[2] - lo[2]
    if a.height > 0 and h > 1e-6:
        s = a.height / h
        for o in bpy.data.objects:
            if o.parent is None:
                o.scale = [v * s for v in o.scale]
        bpy.context.view_layer.update()
        print(f"[4/5] 키를 {h:.3f} → {a.height} 로 맞췄다")
    else:
        print("[4/5] 크기는 그대로 둔다")

    if not a.no_center:
        lo, hi = world_bounds()
        cx = (lo[0] + hi[0]) / 2.0
        cy = (lo[1] + hi[1]) / 2.0
        for o in bpy.data.objects:
            if o.parent is None:
                o.location[0] -= cx
                o.location[1] -= cy
                o.location[2] -= lo[2]
        bpy.context.view_layer.update()
        print("[5/5] 발바닥이 바닥(0)에 오도록 옮겼다")
    else:
        print("[5/5] 위치는 그대로 둔다")

    lo, hi = world_bounds()
    print(f"내보내기 직전 크기: 키 {hi[2]-lo[2]:.3f} · 바닥 z={lo[2]:.4f}")

    bpy.ops.export_scene.gltf(
        filepath=out,
        export_format="GLB",
        export_apply=True,
        export_yup=True,
    )
    mb = os.path.getsize(out) / (1024 * 1024)
    print(f"\n저장했다: {out}  ({mb:.2f} MB)")
    if mb > 15:
        print("경고: 15MB가 넘는다. --faces 를 더 낮추거나 텍스처를 줄여라.")


if __name__ == "__main__":
    main()
