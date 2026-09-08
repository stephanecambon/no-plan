"""S11 Tâche 3 — export HTML 3D PARTAGEABLE et INTERACTIF (vrai iiwa7 + obstacle + preuve).

Un fichier `.html` qu'un prospect ouvre dans son navigateur, **sans Python, sans serveur** : le
vrai KUKA iiwa7, l'obstacle, **7 curseurs articulaires** qui bougent le robot en direct, la
**collision recalculée à chaque image**, les poses start/goal en **fantômes de bras ENTIER**, le
**corps certifié surligné** avec la légende [A40], des **tentatives d'évasion** rejouées, et une
orbite à la souris.

CE QUI FAIT QUE LA PAGE NE PEUT PAS MENTIR (A40) :
  * la cinématique et la collision viennent du **noyau JS PARTAGÉ** ``viz.JS_KINEMATICS_KERNEL`` —
    le code que l'invariant A40 teste sous node contre ``scenes.convex_collision_oracle``
    (0 écart / 694 configurations, `tests/test_flagship_real_interactive.py`). La page 3-D et le
    widget 2-D exécutent **le même code** ; on n'en écrit pas une seconde version non testée ;
  * le **corps certifié** est la coque GELÉE À 40 SOMMETS du certificat, **verbatim**
    (`scripts/iiwa7_body_link3.json`), posée par la chaîne du certificat ;
  * les autres liens sont dessinés par la **coque convexe de leur mesh de visu Drake**, décimée
    par support à ~``K_DIRS`` sommets — la même doctrine « niveau 1 » que le corps certifié —, et
    posés par la **même chaîne gelée**, via un offset constant par lien vérifié à l'export :
    au-delà de ``POSE_TOL`` sur 200 configurations ALÉATOIRES, l'export **échoue** au lieu de
    livrer un robot qui bouge faux ;
  * la géométrie de l'obstacle est celle de la scène (H-rep exacte, boîte alignée).

Three.js est chargé depuis un CDN (cdnjs). L'embarquer ajouterait ~600 ko au fichier ; on le
**dit** dans la page. Les contrôles d'orbite sont écrits à la main (aucune autre dépendance).

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
CHAIN = os.path.join(HERE, "iiwa7_chain.json")
SDF = "package://drake_models/iiwa_description/sdf/iiwa7_no_collision.sdf"
LINKS = [f"iiwa_link_{i}" for i in range(8)]
CERTIFIED_LINK = "iiwa_link_3"
K_DIRS = 120                      # directions de support par lien (silhouette décimée)
POSE_TOL = 5e-6                   # tolérance chaîne gelée ↔ Drake (plancher URDF ~2e-6, A41)
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
    """Triangles de la coque, ORIENTÉS VERS L'EXTÉRIEUR. ``ConvexHull.simplices`` ne garantit
    pas l'orientation ; des normales incohérentes donnent un rendu creux (faces manquantes)."""
    from scipy.spatial import ConvexHull
    V = np.asarray(V, float)
    c = V.mean(axis=0)
    out = []
    for tri in ConvexHull(V).simplices:
        a, b, d = V[tri[0]], V[tri[1]], V[tri[2]]
        if np.dot(np.cross(b - a, d - a), (a + b + d) / 3.0 - c) < 0:
            tri = [tri[0], tri[2], tri[1]]
        out.append([int(x) for x in tri])
    return out


# --------------------------------------------------------------------------- #
# Ancrage des liens Drake sur la chaîne GELÉE (c'est elle qui pose le robot dans la page)
# --------------------------------------------------------------------------- #

def _chain_fk(sc):
    """FK flottante de la chaîne du certificat + accès à un repère de chaîne quelconque."""
    from cnp import certificate as _cert
    from cnp.ratfk import SympyRatFK
    fk = SympyRatFK(_cert._spatial_joints(sc.robot), locked=sc.robot.locked_angles,
                    q_star=[float(v) for v in sc.robot.q_star])
    chain = json.load(open(CHAIN))

    def X(joint_idx: int, s) -> np.ndarray:
        """Le 4x4 monde du repère de chaîne APRÈS le joint ``joint_idx``, à la config ``s``."""
        body = fk.body(joint_idx)          # `_spatial_joints` nomme les corps par INDICE (j{i})
        s = np.asarray(s, float)
        o = body.eval_world_point([0, 0, 0], s)
        M = np.eye(4)
        for k, e in enumerate(([1, 0, 0], [0, 1, 0], [0, 0, 1])):
            M[:3, k] = body.eval_world_point(e, s) - o
        M[:3, 3] = o
        return M

    return fk, chain, X


def _link_anchors(plant, ctx, sc, n_cfg=200):
    """Pour chaque lien Drake : (index de repère de chaîne, offset CONSTANT 4x4), plus l'erreur
    maximale mesurée sur ``n_cfg`` configurations ALÉATOIRES.

    La page 3-D pose le robot avec la chaîne du CERTIFICAT (le noyau JS partagé), pas avec Drake :
    il faut donc, par lien, l'offset rigide qui envoie le repère de chaîne sur le repère de lien
    Drake. On le lit à q=0 puis on le VÉRIFIE sur des configurations aléatoires — un contrôle
    limité à la ligne start→goal (où un seul axe bouge) mesurerait un cas trop favorable et
    laisserait passer un robot qui bouge faux."""
    _fk, chain, X = _chain_fk(sc)
    laj = {int(k): int(v) for k, v in chain["link_after_joint"].items()}
    n = len(sc.box)

    plant.SetPositions(ctx, np.zeros(7))
    anchors, err = {}, 0.0
    for k, L in enumerate(LINKS):
        Xd0 = plant.EvalBodyPoseInWorld(ctx, plant.GetBodyByName(L)).GetAsMatrix4()
        if k == 0:                                   # base soudée au monde : pose constante
            anchors[L] = {"chain": -1, "C": Xd0}
            continue
        anchors[L] = {"chain": laj[k], "C": np.linalg.inv(X(laj[k], np.zeros(n))) @ Xd0}

    rng = np.random.default_rng(4242)
    lo = np.array([float(a) for a, _ in sc.box])
    hi = np.array([float(b) for _, b in sc.box])
    for _ in range(n_cfg):
        s = rng.uniform(lo, hi)
        plant.SetPositions(ctx, 2.0 * np.arctan(s))
        for k, L in enumerate(LINKS):
            if k == 0:
                continue
            Xd = plant.EvalBodyPoseInWorld(ctx, plant.GetBodyByName(L)).GetAsMatrix4()
            err = max(err, float(np.abs(X(anchors[L]["chain"], s) @ anchors[L]["C"] - Xd).max()))
    return anchors, err


def build(scene_path: str, out_path: str) -> str:
    sc, _ = _scenes.load(scene_path)
    plant, sg, ctx = _plant()
    hulls = _link_hulls(plant, sg)
    missing = [L for L in LINKS if L not in hulls]
    if missing:
        raise RuntimeError(f"géométrie de visu absente pour {missing}")

    anchors, pose_err = _link_anchors(plant, ctx, sc)
    if pose_err > POSE_TOL:
        raise RuntimeError(
            f"ancrage lien↔chaîne : erreur {pose_err:.2e} > {POSE_TOL:.0e} sur 200 configs "
            "aléatoires — export REFUSÉ (un artefact d'argument ne doit pas mentir, A40)")

    # les données de scène : EXACTEMENT la forme que consomme le noyau JS partagé
    locked_ang = sc.robot.locked_angles
    from cnp import certificate as _cert
    data = {
        "joints": [{"offset": [float(_cert.Q(x)) for x in j["offset"]],
                    "axis": [float(_cert.Q(x)) for x in j["axis"]],
                    "locked": locked_ang.get(i)}
                   for i, j in enumerate(sc.robot.joints)],
        "panels": [{"lo": [b[0] for b in bn], "hi": [b[1] for b in bn]}
                   for bn in (_viz._box_bounds(A, b) for (A, b) in sc.obstacles.values())
                   if bn is not None],
        "panel_names": list(sc.obstacles),
        "body_link": sc.body_link,
        "hull": [[float(_cert.Q(c)) for c in v] for v in sc.hull_vertices],
        "start_s": [float(v) for v in sc.start_s],
        "goal_s": [float(v) for v in sc.goal_s],
        "box": [[float(lo), float(hi)] for lo, hi in sc.box],
        # UN nom par joint DÉBLOQUÉ (= une entrée de boîte, = un curseur) : `_spatial_joint_names`
        # en renvoie un par joint de CHAÎNE (19 ici, dont 12 verrouillés de la décomposition).
        # Étiquettes dérivées de l'axe EFFECTIF `locked·axe` (finding S10-quater) : q2 = tangage.
        "joint_names": [nm for nm, _, _ in _viz.joint_limits_deg(sc)],
        "limits_deg": [[lo, hi] for _, lo, hi in _viz.joint_limits_deg(sc)],
        "limits_caption": _viz.limits_caption(sc),
        "delta": float(sc.delta),
        "barrier_dim": _viz._barrier_dim(sc),
        "active_dims": [0, 1, 2],
        "passive_dims": [i for i in range(len(sc.box)) if i not in (0, 1, 2)],
        # géométrie de rendu + ancrage sur la chaîne (row-major, comme le noyau JS)
        "links": [{"name": L, "V": hulls[L].round(5).tolist(), "F": _triangles(hulls[L]),
                   "certified": L == CERTIFIED_LINK,
                   "chain": anchors[L]["chain"],
                   "C": [float(x) for x in anchors[L]["C"].reshape(-1)]} for L in LINKS],
        "body_faces": _triangles(np.array([[float(_cert.Q(c)) for c in v]
                                           for v in sc.hull_vertices])),
        "scene": os.path.basename(scene_path),
        "pose_err": f"{pose_err:.2e}",
    }
    # dims actives RE-MESURÉES (jamais présumées) — la légende « redondance » en dépend
    from cnp import engine as _engine
    prob = _scenes.build_problem(sc)
    act = list(_engine._global_active(_engine.pair_views(prob), prob))
    data["active_dims"] = act
    data["passive_dims"] = [i for i in range(len(sc.box)) if i not in act]

    # le noyau partagé déclare lui-même ``const SC = __SCENE__`` : on l'alimente, on ne
    # re-déclare pas SC dans la page (deux `const SC` = SyntaxError silencieuse).
    kernel = _viz.JS_KINEMATICS_KERNEL.replace(
        "__SCENE__", json.dumps(data, separators=(",", ":")))
    html = (_TEMPLATE
            .replace("__JS_KERNEL__", kernel)
            .replace("__THREE__", THREE_CDN))
    with open(out_path, "w") as f:
        f.write(html)
    print(f"ancrage lien↔chaîne gelée : {pose_err:.2e} sur 200 configs aléatoires "
          f"(<= {POSE_TOL:.0e} exigé)")
    print(f"écrit {out_path}  ({os.path.getsize(out_path)/1024:.0f} ko ; "
          f"Three.js depuis {THREE_CDN})")
    return out_path


_TEMPLATE = r"""<meta charset="utf-8"><title>certified-noplan — vrai iiwa7, 3D interactif</title>
<style>
 :root{--bg:#0f1115;--fg:#e8e8ea;--mut:#9aa0aa;--gold:#e0a93b;--red:#e05252;--grn:#4caf7d}
 html,body{margin:0;height:100%;overflow:hidden;background:var(--bg);color:var(--fg);
   font:13px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
 #cv{position:fixed;inset:0}
 .panel{position:fixed;background:rgba(19,22,29,.93);border:1px solid #2a2f3a;
   border-radius:10px;padding:11px 13px;backdrop-filter:blur(6px)}
 #hud{top:12px;left:12px;max-width:330px}
 #leg{bottom:12px;left:12px;max-width:330px;font-size:11.5px}
 #ctl{top:12px;right:12px;width:330px;max-height:calc(100vh - 24px);overflow:auto}
 h1{font-size:14.5px;margin:0 0 6px}
 .k{color:var(--mut)}
 .chip{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:700}
 .ok{background:#12351f;color:var(--grn);border:1px solid #1d5232}
 .bad{background:#3a1717;color:var(--red);border:1px solid #5a2222}
 .sw{display:inline-block;width:11px;height:11px;border-radius:3px;vertical-align:-1px;
   margin-right:6px}
 .row{display:flex;align-items:center;gap:6px;margin:2px 0}
 .row label{flex:0 0 118px;font-size:11px;color:#c9ced8}
 .row input{flex:1}
 .row .val{flex:0 0 54px;text-align:right;font-variant-numeric:tabular-nums;font-size:11px}
 .star{color:var(--gold)}
 button{background:#20242e;color:var(--fg);border:1px solid #333a47;border-radius:7px;
   padding:5px 9px;cursor:pointer;font-size:11.5px;margin:2px 2px 0 0}
 button:hover{background:#2a2f3a}
 .small{font-size:11px;color:var(--mut)}
 hr{border:0;border-top:1px solid #2a2f3a;margin:9px 0}
</style>
<canvas id="cv"></canvas>
<div class="panel" id="hud">
  <h1>certified-noplan — vrai <span class="k">KUKA iiwa7</span></h1>
  <div id="verdict"></div>
  <div class="small" id="meta" style="margin-top:5px"></div>
</div>
<div class="panel" id="leg">
  <div><span class="sw" style="background:#e0a93b"></span><b>corps certifié</b> — lien 3, coque
    40 sommets DU certificat</div>
  <div><span class="sw" style="background:#9aa2ad"></span>autres liens — silhouettes convexes
    des meshes de visu Drake</div>
  <div><span class="sw" style="background:#8a8f98"></span>obstacle (H-rep exacte)</div>
  <div><span class="sw" style="background:#4a90d9"></span>fantôme start &nbsp;
       <span class="sw" style="background:#3faa78"></span>fantôme goal</div>
  <div class="small" style="margin-top:7px">
    <b>[A40] ce que le certificat couvre :</b> la paire certifiée est <i>(corps surligné,
    obstacle)</i> — et rien d'autre. La preuve porte sur ce corps, dans les limites affichées.
    La <b>cinématique et la collision de cette page</b> sont le code testé contre l'oracle
    Python (0 écart / 694 configurations) ; les liens sont posés par la <b>chaîne du
    certificat</b>, ancrage vérifié à <span id="perr"></span> sur 200 configs aléatoires.
  </div>
</div>
<div class="panel" id="ctl">
  <b>Articulations</b> <span class="small">(butées = limites, A25)</span>
  <div id="sliders"></div>
  <hr>
  <div><b>Poses</b></div>
  <button id="bs">start</button><button id="bg">goal</button>
  <button id="bm">transit (q2≈0)</button><button id="bz">zéro</button>
  <button id="bghost">fantômes</button>
  <hr>
  <div><b>Tentatives d'évasion</b> <span class="small">(le certificat dit : aucune ne
    passe)</span></div>
  <button data-esc="direct">chemin direct</button>
  <button data-esc="yaw">contourner par le lacet</button>
  <button data-esc="distal">jouer la redondance (4 joints distaux)</button>
  <div id="escv" class="small" style="margin-top:5px"></div>
  <hr>
  <div class="small" id="limits"></div>
</div>
<script src="__THREE__"></script>
<script>
__JS_KERNEL__
// ── rendu ───────────────────────────────────────────────────────────────────
const scene=new THREE.Scene(); scene.background=new THREE.Color(0x0f1115);
const cam=new THREE.PerspectiveCamera(42, innerWidth/innerHeight, .05, 100);
const rnd=new THREE.WebGLRenderer({canvas:document.getElementById('cv'),antialias:true});
rnd.setPixelRatio(devicePixelRatio); rnd.setSize(innerWidth, innerHeight);
scene.add(new THREE.HemisphereLight(0xdfe7ff, 0x252a34, 1.0));
const dl=new THREE.DirectionalLight(0xffffff,.85); dl.position.set(2,-2.5,3); scene.add(dl);
const dl2=new THREE.DirectionalLight(0xbfd0ff,.35); dl2.position.set(-2.5,2,1.5); scene.add(dl2);
const grid=new THREE.GridHelper(3,24,0x2c3240,0x1c2029); grid.rotation.x=Math.PI/2;
scene.add(grid);
const SIDE=THREE.DoubleSide;
function meshFrom(V,F,mat){
  const g=new THREE.BufferGeometry(), pos=new Float32Array(F.length*9);
  for(let i=0;i<F.length;i++)for(let k=0;k<3;k++){const v=V[F[i][k]];
    pos[i*9+k*3]=v[0]; pos[i*9+k*3+1]=v[1]; pos[i*9+k*3+2]=v[2];}
  g.setAttribute('position',new THREE.BufferAttribute(pos,3)); g.computeVertexNormals();
  return new THREE.Mesh(g,mat);
}
function setVerts(mesh,V,F){
  const pos=mesh.geometry.attributes.position.array;
  for(let i=0;i<F.length;i++)for(let k=0;k<3;k++){const v=V[F[i][k]];
    pos[i*9+k*3]=v[0]; pos[i*9+k*3+1]=v[1]; pos[i*9+k*3+2]=v[2];}
  mesh.geometry.attributes.position.needsUpdate=true; mesh.geometry.computeVertexNormals();
}
// le noyau JS est en RANGÉES (row-major) ; Three.js attend des COLONNES
function toThree(R){return [R[0],R[4],R[8],R[12], R[1],R[5],R[9],R[13],
                            R[2],R[6],R[10],R[14], R[3],R[7],R[11],R[15]];}
const matLink=new THREE.MeshStandardMaterial({color:0x9aa2ad,roughness:.55,metalness:.2,
  side:SIDE,flatShading:true});
const matBodyOK=new THREE.MeshStandardMaterial({color:0xe0a93b,roughness:.35,metalness:.3,
  emissive:0x4a3608,side:SIDE,flatShading:true});
const matBodyHit=new THREE.MeshStandardMaterial({color:0xe05252,roughness:.35,metalness:.3,
  emissive:0x4a1010,side:SIDE,flatShading:true});
function ghostMat(c){return new THREE.MeshStandardMaterial({color:c,transparent:true,
  opacity:.20,side:SIDE,flatShading:true,depthWrite:false});}

// robot « vivant » : un mesh par lien non certifié, posé par la CHAÎNE DU CERTIFICAT
const live=SC.links.map(L=>{const m=meshFrom(L.V,L.F,matLink.clone());
  m.matrixAutoUpdate=false; m.visible=!L.certified; scene.add(m); return m;});
const bodyMesh=meshFrom(SC.hull, SC.body_faces, matBodyOK); scene.add(bodyMesh);

// fantômes start / goal : le BRAS ENTIER, pas seulement le corps
function makeGhost(s,colour){
  const grp=new THREE.Group(), T=fkChain(s), mat=ghostMat(colour);
  SC.links.forEach(L=>{const m=meshFrom(L.V,L.F,mat);
    m.matrix.fromArray(toThree(L.chain<0?L.C:mul(T[L.chain],L.C)));
    m.matrixAutoUpdate=false; grp.add(m);});
  const b=meshFrom(bodyWorld(s), SC.body_faces,
    new THREE.MeshStandardMaterial({color:0xe0a93b,transparent:true,opacity:.5,side:SIDE,
      flatShading:true}));
  grp.add(b); scene.add(grp); return grp;
}
const ghosts=[makeGhost(SC.start_s,0x4a90d9), makeGhost(SC.goal_s,0x3faa78)];

for(let i=0;i<SC.panels.length;i++){
  const o=SC.panels[i], s=[o.hi[0]-o.lo[0],o.hi[1]-o.lo[1],o.hi[2]-o.lo[2]];
  const b=new THREE.Mesh(new THREE.BoxGeometry(s[0],s[1],s[2]),
    new THREE.MeshStandardMaterial({color:0x8a8f98,roughness:.92,transparent:true,
      opacity:.38,side:SIDE,depthWrite:false}));
  b.position.set(o.lo[0]+s[0]/2,o.lo[1]+s[1]/2,o.lo[2]+s[2]/2); scene.add(b);
  const e=new THREE.LineSegments(new THREE.EdgesGeometry(b.geometry),
    new THREE.LineBasicMaterial({color:0xb9c0cc})); e.position.copy(b.position); scene.add(e);
}
// ── orbite maison (aucune dépendance en plus) ───────────────────────────────
let th=-0.62, ph=1.24, rad=2.75, tgt=new THREE.Vector3(0,0,.52), drag=null;
function place(){cam.position.set(tgt.x+rad*Math.sin(ph)*Math.cos(th),
  tgt.y+rad*Math.sin(ph)*Math.sin(th), tgt.z+rad*Math.cos(ph));
  cam.up.set(0,0,1); cam.lookAt(tgt);}
const onCanvas=e=>e.target.id==='cv';
addEventListener('mousedown',e=>{if(onCanvas(e))drag=[e.clientX,e.clientY];});
addEventListener('mouseup',()=>drag=null);
addEventListener('mousemove',e=>{if(!drag)return;
  th-=(e.clientX-drag[0])*.008; ph=Math.min(3.0,Math.max(.15,ph-(e.clientY-drag[1])*.008));
  drag=[e.clientX,e.clientY]; place();});
addEventListener('wheel',e=>{if(!onCanvas(e))return;
  rad=Math.min(8,Math.max(.7,rad*(1+Math.sign(e.deltaY)*.09))); place();},{passive:true});
addEventListener('resize',()=>{cam.aspect=innerWidth/innerHeight; cam.updateProjectionMatrix();
  rnd.setSize(innerWidth,innerHeight);});
// ── état + collision EN DIRECT (le même code que l'oracle Python) ───────────
let cur=SC.start_s.slice();
function refresh(){
  const T=fkChain(cur);
  SC.links.forEach((L,k)=>{ if(L.certified) return;
    live[k].matrix.fromArray(toThree(L.chain<0?L.C:mul(T[L.chain],L.C)));
    live[k].matrixWorldNeedsUpdate=true;});
  setVerts(bodyMesh, bodyWorld(cur), SC.body_faces);
  const hit=collide(cur);
  bodyMesh.material = hit ? matBodyHit : matBodyOK;
  document.getElementById('verdict').innerHTML =
    '<span class="chip '+(hit?'bad':'ok')+'">'
    +(hit?'corps certifié EN COLLISION':'corps certifié libre')+'</span>'
    +' <span class="small">φ = s'+SC.barrier_dim+' = '+cur[SC.barrier_dim].toFixed(3)
    +(Math.abs(cur[SC.barrier_dim])<=SC.delta?'  → DANS la dalle':'  → hors dalle')+'</span>';
  for(let i=0;i<cur.length;i++){
    const el=document.getElementById('s'+i); if(el) el.value=cur[i];
    const v=document.getElementById('v'+i);
    if(v) v.textContent=(2*Math.atan(cur[i])*180/Math.PI).toFixed(0)+'°';
  }
}
const sl=document.getElementById('sliders');
SC.joint_names.forEach((nm,j)=>{
  const [lo,hi]=SC.box[j], row=document.createElement('div'); row.className='row';
  const star = j===SC.barrier_dim ? ' <span class="star">★</span>' : '';
  const passive = (SC.passive_dims||[]).includes(j) ? ' <span class="k">(passif)</span>' : '';
  row.innerHTML='<label>q'+(j+1)+' '+nm+star+passive+'</label>'
    +'<input type="range" id="s'+j+'" min="'+lo+'" max="'+hi+'" step="0.005">'
    +'<span class="val" id="v'+j+'"></span>';
  sl.appendChild(row);
  row.querySelector('input').oninput=e=>{cur[j]=parseFloat(e.target.value); refresh();};
});
document.getElementById('bs').onclick=()=>{cur=SC.start_s.slice(); refresh();};
document.getElementById('bg').onclick=()=>{cur=SC.goal_s.slice(); refresh();};
document.getElementById('bm').onclick=()=>{cur=SC.start_s.map((v,i)=>
  (v+SC.goal_s[i])/2); refresh();};
document.getElementById('bz').onclick=()=>{cur=cur.map(()=>0); refresh();};
document.getElementById('bghost').onclick=()=>ghosts.forEach(g=>g.visible=!g.visible);
// ── tentatives d'évasion (mêmes trajets que le widget 2-D) ──────────────────
let anim=null;
function play(kind){
  if(anim){clearInterval(anim); anim=null;}
  const N=40, bd=SC.barrier_dim, path=[];
  for(let k=0;k<=N;k++){
    const t=k/N, s=SC.start_s.map((v,i)=>v+(SC.goal_s[i]-v)*t);
    if(kind==='yaw'){ const o=SC.active_dims.find(d=>d!==bd);
      s[o]=SC.box[o][1]*Math.sin(Math.PI*t); }
    if(kind==='distal'){ for(const pj of (SC.passive_dims||[]))
      s[pj]=SC.box[pj][0]+(SC.box[pj][1]-SC.box[pj][0])*(0.5-0.5*Math.cos(6.28*t*(1+pj))); }
    path.push(s);
  }
  let i=0, free=0;
  anim=setInterval(()=>{
    if(i>=path.length){clearInterval(anim); anim=null;
      const nColl=path.length-free;
      document.getElementById('escv').innerHTML =
        (nColl>0 ? '<b style="color:var(--red)">BLOQUÉ</b> — '+nColl+'/'+path.length
                  +' poses du trajet mettent le corps certifié en collision.'
                : 'trajet libre (inattendu — vérifier la scène)');
      return;}
    cur=path[i].slice(); refresh(); if(!collide(cur)) free++; i++;
  }, 45);
}
document.querySelectorAll('[data-esc]').forEach(b=>b.onclick=()=>play(b.dataset.esc));
document.getElementById('limits').textContent=SC.limits_caption;
document.getElementById('perr').textContent=SC.pose_err;
document.getElementById('meta').innerHTML=
  SC.scene+' · obstacle '+SC.panel_names.join(', ')
  +'<br>dims actives '+JSON.stringify(SC.active_dims)+' · distales '
  +JSON.stringify(SC.passive_dims)+' <b>prouvées passives</b>'
  +' · <span class="k">Three.js depuis un CDN</span>';
place(); refresh();
(function loop(){requestAnimationFrame(loop); rnd.render(scene,cam);})();
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
