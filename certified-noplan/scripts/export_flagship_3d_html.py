"""S11 Tâche 3 — export HTML 3D PARTAGEABLE du flagship (vrai iiwa7 + étagère + preuve).

Un fichier `.html` qu'un prospect ouvre dans son navigateur, **sans Python, sans serveur** :
le vrai KUKA iiwa7, l'étagère en surplomb, les poses start/goal, le balayage start→goal en
curseur, le **corps certifié surligné** et la légende [A40] qui dit exactement ce que la paire
certifiée couvre. Orbite à la souris.

CE QUI EST DESSINÉ, ET CE QUE ÇA VAUT (A40 — un artefact qui porte un argument ne doit pas
mentir) :
  * chaque lien est dessiné par la **coque convexe de son mesh de visu Drake**, décimée par
    support à ~``K_DIRS`` sommets — la MÊME doctrine « niveau 1 » que le corps certifié ;
  * le **corps certifié** (lien 3) est dessiné avec sa coque GELÉE À 40 SOMMETS, celle du
    certificat, **verbatim** (`scripts/iiwa7_body_link3.json`) — surligné ;
  * la **couleur de collision** de chaque pose vient de `scenes.convex_collision_oracle`
    (l'oracle CORPS-CONVEXE, A43), calculée en Python à l'export : le HTML ne recalcule
    aucune collision, il AFFICHE le verdict de l'oracle. Rien à mentir côté JS.
  * les poses sont posées par **Drake** (`EvalBodyPoseInWorld`) aux mêmes q que la scène ;
    un contrôle asserte que le corps certifié posé par Drake coïncide avec celui posé par la
    chaîne GELÉE du certificat (parité ~2e-6, A41) — sinon l'export échoue bruyamment.

Three.js est chargé depuis un CDN (cdnjs). L'embarquer ajouterait ~600 ko au fichier ; on le
DIT dans la page. Les contrôles d'orbite sont écrits à la main (aucune autre dépendance).

Run: python scripts/export_flagship_3d_html.py [scene.yaml] [-o OUT.html]
"""
from __future__ import annotations

import argparse
import json
import os
from fractions import Fraction as F

import numpy as np

from cnp import scenes as _scenes
from cnp import viz as _viz

HERE = os.path.dirname(os.path.abspath(__file__))
SDF = "package://drake_models/iiwa_description/sdf/iiwa7_no_collision.sdf"
LINKS = [f"iiwa_link_{i}" for i in range(8)]
CERTIFIED_LINK = "iiwa_link_3"
K_DIRS = 120                      # directions de support par lien (silhouette décimée)
N_POSES = 15                      # poses du balayage start→goal
THREE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"


def _plant():
    from pydrake.geometry import SceneGraph
    from pydrake.multibody.parsing import Parser
    from pydrake.multibody.plant import MultibodyPlant
    from pydrake.systems.framework import DiagramBuilder
    builder = DiagramBuilder()
    plant = MultibodyPlant(0.0)
    sg = builder.AddSystem(SceneGraph())
    plant.RegisterAsSourceForSceneGraph(sg)
    Parser(plant).AddModels(url=SDF)
    plant.WeldFrames(plant.world_frame(), plant.GetFrameByName("iiwa_link_0"))
    plant.Finalize()
    return plant, sg, plant.CreateDefaultContext()


def _support_decimate(verts: np.ndarray, n_dirs: int) -> np.ndarray:
    """Silhouette à ~n_dirs sommets : le point d'appui le long de n_dirs directions réparties
    (sphère de Fibonacci), dédupliqué — chaque point est un VRAI sommet de la coque."""
    i = np.arange(n_dirs) + 0.5
    phi = np.arccos(1 - 2 * i / n_dirs)
    theta = np.pi * (1 + 5 ** 0.5) * i
    dirs = np.c_[np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)]
    keep = sorted({int(np.argmax(verts @ d)) for d in dirs})
    return verts[keep]


def _link_hulls(plant, sg) -> dict:
    """{nom de lien: sommets de la coque du mesh de VISU, dans le repère du lien}."""
    insp = sg.model_inspector()
    out = {}
    for gid in insp.GetAllGeometryIds():
        name = insp.GetName(insp.GetFrameId(gid))
        short = next((L for L in LINKS if name.endswith(L)), None)
        if short is None:
            continue
        hull = insp.GetShape(gid).GetConvexHull()
        V = np.array([hull.vertex(i) for i in range(hull.num_vertices())])
        out[short] = _support_decimate(V, K_DIRS)
    return out


def _triangles(V: np.ndarray) -> list:
    from scipy.spatial import ConvexHull
    return [[int(x) for x in tri] for tri in ConvexHull(V).simplices]


def build(scene_path: str, out_path: str) -> str:
    sc, _ = _scenes.load(scene_path)
    plant, sg, ctx = _plant()
    hulls = _link_hulls(plant, sg)
    missing = [L for L in LINKS if L not in hulls]
    if missing:
        raise RuntimeError(f"géométrie de visu absente pour {missing}")

    # le corps CERTIFIÉ est celui du certificat, verbatim (40 sommets gelés), pas une re-dérivation
    cert_hull_body = np.array([[float(F(str(c))) for c in v] for v in sc.hull_vertices])
    body_fk = _scenes._body_fk(sc)
    oracle = _scenes.convex_collision_oracle(sc)

    st = np.array([float(v) for v in sc.start_s])
    go = np.array([float(v) for v in sc.goal_s])
    s_list = [st + (go - st) * (k / (N_POSES - 1)) for k in range(N_POSES)]

    def q_of(s):                       # q = 2·arctan(s) sur les 7 joints débloqués
        return 2.0 * np.arctan(np.asarray(s, float))

    poses, parity = [], 0.0
    for s in s_list:
        plant.SetPositions(ctx, q_of(s))
        Ts = []
        for L in LINKS:
            X = plant.EvalBodyPoseInWorld(ctx, plant.GetBodyByName(L)).GetAsMatrix4()
            Ts.append([float(x) for x in X.T.reshape(-1)])       # column-major (Three.js)
        # contrôle A40/A41 : le corps certifié posé par la CHAÎNE GELÉE coïncide avec Drake
        Xd = plant.EvalBodyPoseInWorld(ctx, plant.GetBodyByName(CERTIFIED_LINK)).GetAsMatrix4()
        W_chain = np.array([body_fk.eval_world_point(v, s) for v in cert_hull_body])
        Wcert = [[float(c) for c in p] for p in W_chain]
        poses.append({"s": [float(x) for x in s], "q_deg": [float(x) for x in
                                                            np.degrees(q_of(s))],
                      "T": Ts, "body_world": Wcert, "colliding": bool(oracle(s)),
                      "phi": float(_viz.phi_eval(sc, s))})
        del Xd
    # parité chaîne↔Drake sur le corps certifié (via la coque link-frame reconstruite)
    parity = _body_parity(plant, ctx, hulls, sc, body_fk, cert_hull_body, s_list, q_of)
    if parity > 5e-6:
        raise RuntimeError(f"parité corps chaîne↔Drake {parity:.2e} > 5e-6 — export refusé "
                           "(un artefact d'argument ne doit pas mentir, A40)")

    obs = {}
    for nm, (A, b) in sc.obstacles.items():
        bnds = _viz._box_bounds(A, b)
        if bnds is not None:
            obs[nm] = {"min": [bnds[k][0] for k in range(3)],
                       "max": [bnds[k][1] for k in range(3)]}

    data = {
        "links": [{"name": L, "V": hulls[L].round(5).tolist(), "F": _triangles(hulls[L]),
                   "certified": L == CERTIFIED_LINK} for L in LINKS],
        "body_hull_faces": _triangles(cert_hull_body),
        "poses": poses, "obstacles": obs,
        "scene": os.path.basename(scene_path),
        "delta": str(sc.delta),
        "limits": _viz.limits_caption(sc),
        "joint_names": [n for n, _, _ in _viz.joint_limits_deg(sc)],
        "body_parity": f"{parity:.2e}",
        "start_idx": 0, "goal_idx": N_POSES - 1,
    }
    html = _TEMPLATE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    html = html.replace("__THREE__", THREE_CDN)
    with open(out_path, "w") as f:
        f.write(html)
    kb = os.path.getsize(out_path) / 1024
    n_coll = sum(p["colliding"] for p in poses)
    print(f"parité corps chaîne↔Drake : {parity:.2e} (<= 5e-6 exigé)")
    print(f"poses : {N_POSES}, dont {n_coll} en collision (oracle corps-convexe)")
    print(f"écrit {out_path}  ({kb:.0f} ko ; Three.js chargé depuis {THREE_CDN})")
    return out_path


def _body_parity(plant, ctx, hulls, sc, body_fk, cert_hull_body, s_list, q_of) -> float:
    """max ‖ corps posé par la CHAÎNE GELÉE − corps posé par Drake ‖ sur les poses affichées."""
    import numpy.linalg as la
    Lk = CERTIFIED_LINK
    plant.SetPositions(ctx, np.zeros(7))
    Xd0 = plant.EvalBodyPoseInWorld(ctx, plant.GetBodyByName(Lk)).GetAsMatrix4()
    # coque certifiée ramenée dans le repère du lien Drake, via la pose à q=0
    W0 = np.array([body_fk.eval_world_point(v, np.zeros(len(sc.box)))
                   for v in cert_hull_body])
    link_pts = (la.inv(Xd0[:3, :3]) @ (W0 - Xd0[:3, 3]).T).T
    err = 0.0
    for s in s_list:
        plant.SetPositions(ctx, q_of(s))
        Xd = plant.EvalBodyPoseInWorld(ctx, plant.GetBodyByName(Lk)).GetAsMatrix4()
        Wd = (Xd[:3, :3] @ link_pts.T).T + Xd[:3, 3]
        Wc = np.array([body_fk.eval_world_point(v, s) for v in cert_hull_body])
        err = max(err, float(np.abs(Wc - Wd).max()))
    return err


_TEMPLATE = r"""<meta charset="utf-8"><title>certified-noplan — flagship iiwa7 3D</title>
<style>
 :root{--bg:#0f1115;--fg:#e8e8ea;--mut:#9aa0aa;--gold:#d9a520;--red:#e05252;--grn:#4caf7d}
 html,body{margin:0;height:100%;background:var(--bg);color:var(--fg);
   font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
 #cv{position:fixed;inset:0}
 .panel{position:fixed;background:rgba(20,23,30,.92);border:1px solid #2a2f3a;
   border-radius:10px;padding:12px 14px;backdrop-filter:blur(6px);max-width:340px}
 #hud{top:14px;left:14px}
 #leg{bottom:14px;left:14px;font-size:12px}
 #ctl{bottom:14px;right:14px;width:320px}
 h1{font-size:15px;margin:0 0 6px}
 .k{color:var(--mut)}
 .chip{display:inline-block;padding:1px 7px;border-radius:20px;font-size:11px;font-weight:600}
 .ok{background:#12351f;color:var(--grn);border:1px solid #1d5232}
 .bad{background:#3a1717;color:var(--red);border:1px solid #5a2222}
 .sw{display:inline-block;width:11px;height:11px;border-radius:3px;vertical-align:-1px;
   margin-right:6px}
 input[type=range]{width:100%}
 button{background:#20242e;color:var(--fg);border:1px solid #333a47;border-radius:7px;
   padding:5px 10px;cursor:pointer;font-size:12px}
 button:hover{background:#2a2f3a}
 .small{font-size:11px;color:var(--mut)}
</style>
<canvas id="cv"></canvas>
<div class="panel" id="hud">
  <h1>certified-noplan — flagship <span class="k">KUKA iiwa7</span></h1>
  <div id="verdict"></div>
  <div class="small" id="meta"></div>
</div>
<div class="panel" id="leg">
  <div><span class="sw" style="background:#e0a93b"></span><b>corps certifié</b> (lien 3,
    coque 40 sommets du certificat)</div>
  <div><span class="sw" style="background:#6b7280"></span>autres liens — silhouettes convexes
    des meshes de visu Drake</div>
  <div><span class="sw" style="background:#8a8f98"></span>obstacle (H-rep exacte)</div>
  <div class="small" style="margin-top:7px;max-width:320px">
    <b>[A40] Ce que le certificat couvre :</b> la paire certifiée est
    <i>(corps surligné, obstacle)</i> — et rien d'autre. La preuve porte sur le corps
    surligné dans les limites articulaires affichées ; les autres liens sont là pour le
    contexte visuel, pas dans la preuve. Les couleurs de collision viennent de l'oracle
    corps-convexe, calculé côté Python à l'export.
  </div>
</div>
<div class="panel" id="ctl">
  <div><b>Balayage start → goal</b> <span class="small">(le chemin direct)</span></div>
  <input type="range" id="sl" min="0" max="0" step="1" value="0">
  <div id="pose" class="small"></div>
  <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">
    <button id="bs">start</button><button id="bg">goal</button>
    <button id="bm">transit (q2≈0)</button><button id="bp">▶ animer</button>
    <button id="bghost">fantômes</button>
  </div>
  <div class="small" id="limits" style="margin-top:8px"></div>
</div>
<script src="__THREE__"></script>
<script>
const D = __DATA__;
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x0f1115);
const cam = new THREE.PerspectiveCamera(42, innerWidth/innerHeight, .05, 100);
const rnd = new THREE.WebGLRenderer({canvas:document.getElementById('cv'),antialias:true});
rnd.setPixelRatio(devicePixelRatio); rnd.setSize(innerWidth, innerHeight);
scene.add(new THREE.HemisphereLight(0xdfe7ff, 0x20242c, 1.05));
const dl = new THREE.DirectionalLight(0xffffff, .75); dl.position.set(2,-2.5,3); scene.add(dl);
const grid = new THREE.GridHelper(3, 24, 0x2c3240, 0x1c2029);
grid.rotation.x = Math.PI/2; scene.add(grid);                     // Z-up (repère robot)

function meshFrom(V, F, mat){
  const g = new THREE.BufferGeometry();
  const pos = new Float32Array(F.length*9);
  for(let i=0;i<F.length;i++){ for(let k=0;k<3;k++){ const v=V[F[i][k]];
    pos[i*9+k*3]=v[0]; pos[i*9+k*3+1]=v[1]; pos[i*9+k*3+2]=v[2]; } }
  g.setAttribute('position', new THREE.BufferAttribute(pos,3)); g.computeVertexNormals();
  return new THREE.Mesh(g, mat);
}
const matLink = new THREE.MeshStandardMaterial({color:0x6b7280,roughness:.65,metalness:.15});
const matBodyOK = new THREE.MeshStandardMaterial({color:0xe0a93b,roughness:.4,
  metalness:.25,emissive:0x3a2a06});
const matBodyHit = new THREE.MeshStandardMaterial({color:0xe05252,roughness:.4,
  metalness:.25,emissive:0x3a0d0d});
const linkMeshes = D.links.map(L => {
  const m = meshFrom(L.V, L.F, L.certified ? matBodyOK.clone() : matLink.clone());
  m.visible = !L.certified;                      // le corps certifié est dessiné à part
  scene.add(m); return m;
});
// corps certifié : coque du CERTIFICAT (40 sommets), re-posée par sommets monde
const bodyMesh = meshFrom(D.poses[0].body_world, D.body_hull_faces, matBodyOK);
scene.add(bodyMesh);
function setBody(P){
  const F = D.body_hull_faces, V = P.body_world;
  const pos = bodyMesh.geometry.attributes.position.array;
  for(let i=0;i<F.length;i++) for(let k=0;k<3;k++){ const v=V[F[i][k]];
    pos[i*9+k*3]=v[0]; pos[i*9+k*3+1]=v[1]; pos[i*9+k*3+2]=v[2]; }
  bodyMesh.geometry.attributes.position.needsUpdate = true;
  bodyMesh.geometry.computeVertexNormals();
  bodyMesh.material = P.colliding ? matBodyHit : matBodyOK;
}
for(const [nm,o] of Object.entries(D.obstacles)){
  const s=[o.max[0]-o.min[0],o.max[1]-o.min[1],o.max[2]-o.min[2]];
  const b=new THREE.Mesh(new THREE.BoxGeometry(s[0],s[1],s[2]),
    new THREE.MeshStandardMaterial({color:0x8a8f98,roughness:.9,transparent:true,opacity:.55}));
  b.position.set(o.min[0]+s[0]/2,o.min[1]+s[1]/2,o.min[2]+s[2]/2); scene.add(b);
  const e=new THREE.LineSegments(new THREE.EdgesGeometry(b.geometry),
    new THREE.LineBasicMaterial({color:0xb9c0cc})); e.position.copy(b.position); scene.add(e);
}
// fantômes start / goal (A24-a) : toujours disponibles, masquables
const ghosts = [D.start_idx, D.goal_idx].map((idx,k)=>{
  const m = meshFrom(D.poses[idx].body_world, D.body_hull_faces,
    new THREE.MeshStandardMaterial({color:k?0x4caf7d:0x4a90d9,transparent:true,opacity:.35}));
  scene.add(m); return m;
});
// --- orbite maison (aucune dépendance en plus) ---
let th=-1.05, ph=1.15, rad=2.3, tgt=new THREE.Vector3(0,0,.45), drag=null;
function place(){ cam.position.set(tgt.x+rad*Math.sin(ph)*Math.cos(th),
  tgt.y+rad*Math.sin(ph)*Math.sin(th), tgt.z+rad*Math.cos(ph));
  cam.up.set(0,0,1); cam.lookAt(tgt); }
addEventListener('mousedown',e=>drag=[e.clientX,e.clientY]);
addEventListener('mouseup',()=>drag=null);
addEventListener('mousemove',e=>{ if(!drag)return;
  th -= (e.clientX-drag[0])*.008; ph = Math.min(3.0,Math.max(.15, ph-(e.clientY-drag[1])*.008));
  drag=[e.clientX,e.clientY]; place(); });
addEventListener('wheel',e=>{ rad=Math.min(8,Math.max(.7,rad*(1+Math.sign(e.deltaY)*.09)));
  place(); },{passive:true});
addEventListener('resize',()=>{ cam.aspect=innerWidth/innerHeight; cam.updateProjectionMatrix();
  rnd.setSize(innerWidth,innerHeight); });
// --- poses ---
const sl=document.getElementById('sl'); sl.max=D.poses.length-1;
function show(i){
  const P=D.poses[i];
  D.links.forEach((L,k)=>{ if(L.certified) return;
    linkMeshes[k].matrix.fromArray(P.T[k]); linkMeshes[k].matrixAutoUpdate=false;
    linkMeshes[k].matrixWorldNeedsUpdate=true; });
  setBody(P);
  document.getElementById('verdict').innerHTML =
    '<span class="chip '+(P.colliding?'bad':'ok')+'">'
    + (P.colliding?'corps certifié EN COLLISION':'corps certifié libre') + '</span>';
  document.getElementById('pose').textContent =
    'pose ' + (i+1) + '/' + D.poses.length + '   φ = s1 = ' + P.s[1].toFixed(3)
    + '   (|φ| ≤ ' + D.delta + ' = la dalle)   q2 = ' + P.q_deg[1].toFixed(1) + '°';
  sl.value=i;
}
sl.oninput=e=>show(+e.target.value);
document.getElementById('bs').onclick=()=>show(D.start_idx);
document.getElementById('bg').onclick=()=>show(D.goal_idx);
document.getElementById('bm').onclick=()=>show(Math.floor(D.poses.length/2));
let anim=null;
document.getElementById('bp').onclick=e=>{ if(anim){clearInterval(anim);anim=null;
  e.target.textContent='▶ animer';return;} e.target.textContent='⏸ pause';
  let i=+sl.value; anim=setInterval(()=>{ i=(i+1)%D.poses.length; show(i); },220); };
document.getElementById('bghost').onclick=()=>ghosts.forEach(g=>g.visible=!g.visible);
document.getElementById('meta').innerHTML =
  D.scene + ' &middot; corps certifié = lien 3 (40 sommets, coque du certificat)<br>'
  + 'parité corps chaîne↔Drake ' + D.body_parity
  + ' &middot; <span class="k">Three.js chargé depuis un CDN</span>';
document.getElementById('limits').textContent = D.limits;
place(); show(0);
(function loop(){ requestAnimationFrame(loop); rnd.render(scene,cam); })();
</script>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scene", nargs="?", default="scenes/S6_iiwa_real_shelf.yaml")
    ap.add_argument("-o", "--out", default=None)
    a = ap.parse_args()
    out = a.out or os.path.join("benchmarks", "figures", "share",
                                os.path.splitext(os.path.basename(a.scene))[0] + "_3d.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    build(a.scene, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
