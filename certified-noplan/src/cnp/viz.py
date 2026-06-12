"""viz — Meshcat 3D viewer (minimal, S6) + C-space/partition figures (S11).

S6 ships only ``show_scene`` — a *design-inspection* view of a parsed scene: the
planar builtin arm drawn at its start or goal configuration, plus the obstacles, in
Meshcat. It exists so a human can eyeball, BEFORE certifying, that the scene is the
one we mean to prove (V3, CLAUDE.md rule 11). It proves nothing about soundness — the
certificate + :mod:`cnp.verify` are the only arbiters of mathematical truth.

The full ``cnp viz <cert>`` (partition animation, failed leaves, paper figures) is S11.
"""
from __future__ import annotations

import numpy as np

from . import certificate as _cert
from .ratfk import SympyRatFK


def _config_q_to_s(scene: _cert.Scene, which: str):
    s = scene.start_s if which == "start" else scene.goal_s
    return np.array([float(v) for v in s])


def _fk_and_names(scene: _cert.Scene):
    """Build the FK back-end and the per-joint body names for a planar or spatial
    builtin robot. Returns ``(fk, names, body_name, tip_body_frame_point)``."""
    locked = scene.robot.locked_angles
    q_star = [float(v) for v in scene.robot.q_star]
    kind = scene.robot.kind
    if kind == "planar_revolute":
        fk = SympyRatFK(_cert._planar_joints(scene.robot), locked=locked, q_star=q_star)
        names = [f"link{i}" for i in range(scene.robot.n_joints)]
    elif kind == "spatial_revolute":
        from . import scenes as _scenes
        fk = SympyRatFK(_scenes._spatial_joints(scene.robot), locked=locked,
                        q_star=q_star)
        names = [f"j{i}" for i in range(scene.robot.n_joints)]
    else:
        raise NotImplementedError(f"show_scene for {kind!r} not supported")
    tip = [float(c) for c in scene.hull_vertices[-1]]      # distal hull vertex
    return fk, names, names[scene.body_link], tip


def _joint_world_positions(scene: _cert.Scene, s):
    """World positions of every joint origin + the moving body's distal tip, for the
    arm at s-config ``s`` (planar or spatial builtin; all joints assumed unlocked)."""
    fk, names, body_name, tip = _fk_and_names(scene)
    pts = [fk.body(nm).eval_world_point([0.0, 0.0, 0.0], s) for nm in names]
    pts.append(fk.body(body_name).eval_world_point(tip, s))   # distal tip of the body
    return np.array(pts)


def _box_bounds(A, b):
    """Recover ``[(lo,hi)]`` per axis if ``(A,b)`` is an axis-aligned box, else None."""
    A = np.array([[float(x) for x in row] for row in A])
    b = np.array([float(x) for x in b])
    dim = A.shape[1]
    lo = [None] * dim
    hi = [None] * dim
    for row, bj in zip(A, b):
        nz = np.nonzero(row)[0]
        if len(nz) != 1 or abs(abs(row[nz[0]]) - 1.0) > 1e-9:
            return None
        ax = int(nz[0])
        if row[ax] > 0:
            hi[ax] = bj
        else:
            lo[ax] = -bj
    if any(v is None for v in lo + hi):
        return None
    return list(zip(lo, hi))


def save_planar_figure(scene: _cert.Scene, path: str, poses=None, title=None):
    """Top-down 2-D figure of a planar scene (the natural view for design inspection,
    V3): obstacle teeth as labelled rectangles, the arm drawn at each pose as a thick
    polyline with joint dots. ``poses`` is a list of ``(label, s_array, colour)``;
    defaults to start (blue) and goal (green). Returns ``path``.

    Unlike the 3-D Meshcat view, this reads at a glance for a planar arm and lets us
    show an in-slab pose (where the body link is caught in the comb) next to the free
    start/goal — the story the certificate proves."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    if poses is None:
        poses = [("start", _config_q_to_s(scene, "start"), "#1f77b4"),
                 ("goal", _config_q_to_s(scene, "goal"), "#2ca02c")]

    fig, ax = plt.subplots(figsize=(7, 7))
    for nm, (A, b) in scene.obstacles.items():
        bnds = _box_bounds(A, b)
        if bnds is None:
            continue
        (xlo, xhi), (ylo, yhi) = bnds[0], bnds[1]
        ax.add_patch(Rectangle((xlo, ylo), xhi - xlo, yhi - ylo,
                               facecolor="0.6", edgecolor="0.3", alpha=0.7))
        ax.text((xlo + xhi) / 2, (ylo + yhi) / 2, nm, ha="center", va="center",
                fontsize=9, weight="bold")

    for label, s, colour in poses:
        pts = _joint_world_positions(scene, np.asarray(s, dtype=float))
        ax.plot(pts[:, 0], pts[:, 1], "-", color=colour, lw=3, label=label, zorder=3)
        ax.plot(pts[:, 0], pts[:, 1], "o", color=colour, ms=7, zorder=4)
    ax.plot(0, 0, "ks", ms=9, zorder=5)            # base
    ax.set_aspect("equal")
    ax.grid(True, ls=":", alpha=0.5)
    ax.legend(loc="upper left")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(title or "scene (top-down)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def save_sweep_figure(scene: _cert.Scene, oracle, path, n=9, project=(0, 1),
                      title=None):
    """Top-down 'filmstrip' showing WHY you cannot move from start to goal: draw the
    arm at ``n`` configs interpolated in s-space along the straight start->goal line,
    each coloured by collision (green = free, red = colliding). The free endpoints are
    reachable, but every intermediate pose plows into the obstacle — the motion is
    blocked. (The straight path is just the obvious attempt; the C-space figure shows
    that EVERY path is blocked, since the colliding band spans the whole box.)"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    i, j = project
    st = np.array([float(v) for v in scene.start_s])
    go = np.array([float(v) for v in scene.goal_s])

    fig, ax = plt.subplots(figsize=(7.5, 7))
    for nm, (A, b) in scene.obstacles.items():
        bnds = _box_bounds(A, b)
        if bnds is None:
            continue
        (xlo, xhi), (ylo, yhi) = bnds[i], bnds[j]
        ax.add_patch(Rectangle((xlo, ylo), xhi - xlo, yhi - ylo,
                               facecolor="0.55", edgecolor="0.3", alpha=0.8, zorder=1))
        ax.text((xlo + xhi) / 2, (ylo + yhi) / 2, nm, ha="center", va="center",
                fontsize=8, weight="bold", zorder=6)

    n_coll = 0
    for k in range(n):
        s = st + (go - st) * (k / (n - 1))
        colliding = oracle(s)
        n_coll += colliding
        colour = "#d62728" if colliding else "#2ca02c"
        pts = _joint_world_positions(scene, s)
        ax.plot(pts[:, i], pts[:, j], "-", color=colour,
                lw=2.4, alpha=0.85, zorder=3)
        ax.plot(pts[:, i], pts[:, j], "o", color=colour, ms=4, zorder=4)
    ax.plot(0, 0, "ks", ms=9, zorder=7)
    ax.set_aspect("equal")
    ax.grid(True, ls=":", alpha=0.5)
    ax.set_xlabel(f"axe monde {i} (m)")
    ax.set_ylabel(f"axe monde {j} (m)")
    ax.set_title(title or f"balayage start->goal : {n_coll}/{n} poses en collision "
                          "(rouge) — le mouvement direct traverse l'obstacle")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def save_cspace_figure(scene: _cert.Scene, oracle, path, axes=(0, 1), n=140,
                       fixed=None, title=None, axis_labels=None, paths=None, footer=None):
    """Configuration-space figure (the view that shows 'goal free but UNREACHABLE'):
    a 2-D slice over two s-axes, collision shaded grey, the slab ``{|phi|<=delta}``
    in gold, start (★) and goal (✚) marked. When the slab is a full COLLISION WALL
    spanning the box between start and goal, they sit in different free components —
    no continuous free path connects them. That separation IS the disconnection the
    certificate proves; here the eye can see it (the certificate, not the eye, is the
    proof — CLAUDE.md rule 11).

    ``oracle(s)`` is the collision predicate (e.g. ``scenes.planar_collision_oracle``);
    ``axes`` picks the two plotted s-variables; ``fixed`` sets the others (default 0)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    i, j = axes
    fixed = fixed or {}
    (xlo, xhi) = (float(scene.box[i][0]), float(scene.box[i][1]))
    (ylo, yhi) = (float(scene.box[j][0]), float(scene.box[j][1]))
    xs = np.linspace(xlo, xhi, n)
    ys = np.linspace(ylo, yhi, n)
    grid = np.zeros((n, n))
    s = np.zeros(scene.robot.n)
    for k, v in fixed.items():
        s[k] = v
    for a, sx in enumerate(xs):
        for b, sy in enumerate(ys):
            s[i], s[j] = sx, sy
            grid[b, a] = 1.0 if oracle(s) else 0.0

    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    ax.imshow(grid, origin="lower", extent=[xlo, xhi, ylo, yhi], aspect="auto",
              cmap="Greys", vmin=0, vmax=1.6, alpha=0.85)        # grey = collision

    # slab |phi| <= delta: when phi = s_i (the relay barrier), it is the vertical
    # band |s_i| <= delta on this slice — a full-height COLLISION WALL if disconnected.
    delta = float(scene.delta)
    phi_is_axis_i = set(scene.phi) == {tuple(1 if t == i else 0 for t in range(scene.robot.n))}
    if phi_is_axis_i:
        ax.axvspan(-delta, delta, color="gold", alpha=0.35, zorder=2,
                   label=f"dalle |phi|<={scene.delta}")

    # candidate motion attempts (each a list of (s_i, s_j) waypoints), drawn dashed so
    # the eye sees them plunge into the grey collision wall whatever the detour.
    for lbl, pts in (paths or []):
        pts = np.asarray(pts, dtype=float)
        ax.plot(pts[:, 0], pts[:, 1], "--", lw=2, color="#7f0000", zorder=4, label=lbl)

    st = [float(v) for v in scene.start_s]
    go = [float(v) for v in scene.goal_s]
    ax.plot(st[i], st[j], "*", color="#1f77b4", ms=20, mec="k", zorder=5, label="start")
    ax.plot(go[i], go[j], "P", color="#2ca02c", ms=16, mec="k", zorder=5, label="goal")
    xl, yl = axis_labels or (f"s{i}", f"s{j}")
    ax.set_xlabel(xl)
    ax.set_ylabel(yl)
    ax.legend(loc="upper right", framealpha=0.95, fontsize=8)
    if footer:                                  # A25: explicit joint-limits encadré
        ax.text(0.015, 0.015, footer, transform=ax.transAxes, fontsize=7.0,
                va="bottom", ha="left", zorder=10,
                bbox=dict(boxstyle="round", fc="#fff7e0", ec="#e0c060"))
    ax.set_title(title or "C-space slice (grey = collision)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


_INTERACTIVE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><title>__TITLE__</title>
<style>
 body{font-family:system-ui,Arial,sans-serif;margin:14px;color:#222;background:#fff}
 h1{font-size:16px;margin:0 0 4px} .sub{color:#555;font-size:12px;margin:0 0 10px}
 .views{display:flex;gap:18px;flex-wrap:wrap} .view{flex:0 0 auto}
 .view h2{font-size:13px;margin:0 0 2px} .view .what{font-size:11px;color:#666;margin:0 0 4px}
 canvas{border:1px solid #ccc;background:#fafafa}
 .panel{margin-top:12px;max-width:760px}
 .sld{display:flex;align-items:center;gap:8px;margin:3px 0;font-size:13px}
 .sld label{width:230px} .sld input{flex:1} .sld .val{width:54px;text-align:right;font-variant-numeric:tabular-nums}
 #verdict{font-weight:bold;font-size:15px;margin:8px 0;padding:6px 10px;border-radius:6px;display:inline-block}
 #limits{font-size:12px;color:#333;background:#fff7e0;border:1px solid #e0c060;border-radius:6px;padding:6px 10px;margin:6px 0;max-width:740px}
 .btns{margin:10px 0;display:flex;gap:8px;flex-wrap:wrap}
 button{font-size:13px;padding:6px 10px;border:1px solid #999;border-radius:6px;background:#f0f0f0;cursor:pointer}
 button:hover{background:#e4e4e4} #attempt{font-size:13px;margin-left:6px}
 .legend{font-size:11px;color:#555;margin-top:8px;line-height:1.5}
 .sw{display:inline-block;width:22px;height:0;border-top-width:3px;border-top-style:solid;vertical-align:middle;margin-right:4px}
</style></head><body>
<h1>__TITLE__</h1>
<p class="sub">Artefact de validation INTERACTIF (A24). Bougez les curseurs articulaires ;
le <b>bras supérieur</b> (épais) est le corps certifié, il devient <b>ROUGE</b> en collision.
Les <b>fantômes</b> start (bleu) / goal (vert) sont les deux poses libres à relier. Cet
outil montre l'INTENTION ; la preuve est le certificat (le moteur, pas l'œil — règle 9).</p>
<div class="views">
 <div class="view"><h2>Vue de DESSUS (lacet)</h2>
  <p class="what">plan monde x–y · bras COMPLET (sup. épais = corps ; avant-bras fin = affichage)</p>
  <canvas id="top" width="300" height="420"></canvas></div>
 <div class="view"><h2>Vue de CÔTÉ (tangage / hauteur)</h2>
  <p class="what">plan monde x–z · bras SUPÉRIEUR seul (le corps certifié) + portée max ·
   projection : la collision est calculée en 3D (un bras décalé en lacet peut sembler
   croiser le panneau sans le toucher)</p>
  <canvas id="side" width="300" height="420"></canvas></div>
</div>
<div class="panel">
 <div id="verdict"></div>
 <div id="limits"></div>
 <div id="sliders"></div>
 <div class="btns">
  <button onclick="play('yaw')">Tentative : passage direct (lacet)</button>
  <button onclick="play('pitch')">Tentative : passer par-dessus (tangage)</button>
  <button onclick="play('around')">Tentative : contourner (roll/coude)</button>
  <button onclick="setS(SC.start_s)">→ start</button>
  <button onclick="setS(SC.goal_s)">→ goal</button>
  <span id="attempt"></span>
 </div>
 <div class="legend">
  <div><span class="sw" style="border-color:#1f77b4"></span>fantôme start &nbsp;
       <span class="sw" style="border-color:#2ca02c"></span>fantôme goal &nbsp;
       <span class="sw" style="border-color:#d62728"></span>bras supérieur EN COLLISION &nbsp;
       <span class="sw" style="border-color:#333"></span>bras supérieur libre &nbsp;
       <span class="sw" style="border-color:#bbb"></span>avant-bras (affichage seul)</div>
  <div>Chaque vue déclare ce qu'elle montre (A24). « Par-dessus » échoue par HAUTEUR DU
  MUR (sommet panneau &gt; portée du bras, visible côté) ; « contourner » échoue car le
  corps ne dépend pas du roll/coude (passifs).</div>
 </div>
</div>
<script>
const SC = __SCENE__;
const FORE = __FOREARM__;
// --- tiny linear algebra (4x4) ---
function ident(){return [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1];}
function mul(A,B){let C=new Array(16).fill(0);for(let i=0;i<4;i++)for(let j=0;j<4;j++)for(let k=0;k<4;k++)C[i*4+j]+=A[i*4+k]*B[k*4+j];return C;}
function trans(v){let T=ident();T[3]=v[0];T[7]=v[1];T[11]=v[2];return T;}
function rot(axis,a){ // Rodrigues about unit axis
 let [x,y,z]=axis,n=Math.hypot(x,y,z);x/=n;y/=n;z/=n;
 let c=Math.cos(a),s=Math.sin(a),t=1-c;
 return [t*x*x+c, t*x*y-s*z, t*x*z+s*y,0,
         t*x*y+s*z, t*y*y+c, t*y*z-s*x,0,
         t*x*z-s*y, t*y*z+s*x, t*z*z+c,0, 0,0,0,1];}
function ap(T,p){return [T[0]*p[0]+T[1]*p[1]+T[2]*p[2]+T[3],
                         T[4]*p[0]+T[5]*p[1]+T[6]*p[2]+T[7],
                         T[8]*p[0]+T[9]*p[1]+T[10]*p[2]+T[11]];}
// forward kinematics: unlocked joint q = 2*atan(s); LOCKED joint = fixed angle (no slider);
// s is the UNLOCKED vector (one entry per slider), mapped onto the full joint chain here.
function fkChain(s){let T=ident(),out=[],si=0;for(let i=0;i<SC.joints.length;i++){
  T=mul(T,trans(SC.joints[i].offset));
  let a = SC.joints[i].locked!=null ? SC.joints[i].locked : 2*Math.atan(s[si++]);
  T=mul(T,rot(SC.joints[i].axis, a));
  out.push(T);}return out;}
function armPts(s){ // {base, elbow, hand, upper:[base,elbow]}
  let T=fkChain(s); let L=SC.upper_len;
  let elbow=ap(T[SC.body_link],[L,0,0]);
  let hand=ap(T[T.length-1],[FORE,0,0]);
  return {base:[0,0,0], elbow, hand};}
function collide(s){ // upper arm (base->elbow) vs any panel box
  let a=armPts(s),N=40;
  for(let k=0;k<=N;k++){let t=k/N;
    let p=[a.base[0]+(a.elbow[0]-a.base[0])*t, a.base[1]+(a.elbow[1]-a.base[1])*t, a.base[2]+(a.elbow[2]-a.base[2])*t];
    for(const b of SC.panels){if(p[0]>=b.lo[0]&&p[0]<=b.hi[0]&&p[1]>=b.lo[1]&&p[1]<=b.hi[1]&&p[2]>=b.lo[2]&&p[2]<=b.hi[2])return true;}}
  return false;}
// --- projection: world window x[-0.15,0.85] (across) , v[-0.7,0.7] (up); 1 unit=300px ---
const XMIN=-0.15, VMIN=-0.7, SCALE=300, W=300, H=420;
function px(wx){return (wx-XMIN)*SCALE;}
function py(wv){return H-(wv-VMIN)*SCALE;}
function drawPanel(ctx,ai,vi){ // ai/vi = world axis index for across/up
  ctx.fillStyle="rgba(120,120,120,0.55)";ctx.strokeStyle="#555";
  for(const b of SC.panels){let x0=px(b.lo[ai]),x1=px(b.hi[ai]),y0=py(b.hi[vi]),y1=py(b.lo[vi]);
    ctx.fillRect(x0,y0,x1-x0,y1-y0);ctx.strokeRect(x0,y0,x1-x0,y1-y0);}}
function seg(ctx,p,q,ai,vi,col,w){ctx.strokeStyle=col;ctx.lineWidth=w;ctx.beginPath();
  ctx.moveTo(px(p[ai]),py(p[vi]));ctx.lineTo(px(q[ai]),py(q[vi]));ctx.stroke();}
function drawArm(ctx,s,ai,vi,full,ghost){
  let a=armPts(s),col=collide(s)?"#d62728":(ghost?ghost:"#333");
  seg(ctx,a.base,a.elbow,ai,vi,col,ghost?3:5);            // UPPER ARM = certified body
  if(full){seg(ctx,a.elbow,a.hand,ai,vi,ghost?ghost:"#bbb",ghost?2:3);} // forearm display
}
function drawView(id,ai,vi,full,reach){
  let ctx=document.getElementById(id).getContext("2d");ctx.clearRect(0,0,W,H);
  // axes
  ctx.strokeStyle="#e3e3e3";ctx.lineWidth=1;ctx.beginPath();
  ctx.moveTo(px(0),0);ctx.lineTo(px(0),H);ctx.moveTo(0,py(0));ctx.lineTo(W,py(0));ctx.stroke();
  if(reach){ctx.strokeStyle="#999";ctx.setLineDash([4,4]);ctx.beginPath();
    ctx.arc(px(0),py(0),SC.upper_len*SCALE,0,2*Math.PI);ctx.stroke();ctx.setLineDash([]);}
  drawPanel(ctx,ai,vi);
  drawArm(ctx,SC.start_s,ai,vi,full,"#1f77b4");           // ghosts (labelled below)
  drawArm(ctx,SC.goal_s,ai,vi,full,"#2ca02c");
  drawArm(ctx,cur,ai,vi,full,null);                       // live arm
  ctx.fillStyle="#000";ctx.fillRect(px(0)-4,py(0)-4,8,8); // base
  // ghost labels
  ctx.font="11px sans-serif";let gs=armPts(SC.start_s),gg=armPts(SC.goal_s);
  ctx.fillStyle="#1f77b4";ctx.fillText("start",px(gs.elbow[ai])+3,py(gs.elbow[vi]));
  ctx.fillStyle="#2ca02c";ctx.fillText("goal",px(gg.elbow[ai])+3,py(gg.elbow[vi]));
}
function redraw(){drawView("top",0,1,true,false);drawView("side",0,2,false,true);
  let c=collide(cur);let v=document.getElementById("verdict");
  v.textContent=c?"bras supérieur EN COLLISION":"bras supérieur libre";
  v.style.background=c?"#f6d3d3":"#d6efd6";v.style.color=c?"#7f0000":"#14521a";}
let cur=SC.start_s.slice();
function setS(s){cur=s.slice();for(let i=0;i<cur.length;i++){
  document.getElementById("s"+i).value=cur[i];document.getElementById("v"+i).textContent=cur[i].toFixed(2);}redraw();}
// sliders
document.getElementById("limits").innerHTML="<b>"+SC.limits_caption+"</b> — les BUTÉES des curseurs ci-dessous SONT ces limites articulaires (A25) ; toutes ⊂ (−180°,180°) ⟹ pas de wrap-around. Le cadre des deux vues = l'espace atteignable dans ces limites.";
const NAMES=SC.joint_names;let sl=document.getElementById("sliders");let si=0;
for(let i=0;i<SC.joints.length;i++){let d=document.createElement("div");d.className="sld";
 if(SC.joints[i].locked!=null){                              // LOCKED joint: no slider, announced as such
   let dg=Math.round(SC.joints[i].locked*180/Math.PI);
   d.innerHTML='<label>'+NAMES[i]+' — 🔒 VERROUILLÉ à '+dg+'° (hors C-space certifié)</label>';
   d.style.opacity=0.6;sl.appendChild(d);continue;}
 let j=si;let ld=SC.limits_deg[j];let deg='['+Math.round(ld[0])+'…'+Math.round(ld[1])+'°]';
 d.innerHTML='<label>s'+j+' — '+NAMES[i]+' '+deg+'</label><input id="s'+j+'" type="range" min="'+SC.box[j][0]+'" max="'+SC.box[j][1]+'" step="0.01" value="'+cur[j]+'"><span class="val" id="v'+j+'"></span>';
 sl.appendChild(d);let inp=d.querySelector("input");
 inp.oninput=()=>{cur[j]=parseFloat(inp.value);document.getElementById("v"+j).textContent=cur[j].toFixed(2);redraw();};
 si++;}
// escape attempts: animate a path; report whether ANY pose was free
function play(kind){let path=[],N=24;
 if(kind==='yaw'){for(let k=0;k<=N;k++){let t=k/N;path.push(SC.start_s.map((v,i)=>v+(SC.goal_s[i]-v)*t));}}
 else if(kind==='pitch'){for(let k=0;k<=N;k++){let t=k/N;let s=cur.slice();s[0]=0;s[1]=SC.box[1][0]+(SC.box[1][1]-SC.box[1][0])*t;path.push(s);}}
 else{for(let k=0;k<=N;k++){let t=k/N;let s=cur.slice();s[0]=0;
   if(s.length>2)s[2]=SC.box[2][0]+(SC.box[2][1]-SC.box[2][0])*t;                       // roll across its limits
   if(s.length>3)s[3]=SC.box[3][0]+(SC.box[3][1]-SC.box[3][0])*0.5*(1-Math.cos(6.28*t)); // elbow within its limits
   path.push(s);}}
 let free=0,i=0;document.getElementById("attempt").textContent="…";
 let iv=setInterval(()=>{if(i>=path.length){clearInterval(iv);
    let nColl=path.length-free;
    let lbl={yaw:"passage direct (lacet)",pitch:"passer par-dessus (tangage)",around:"contourner (roll/coude)"}[kind];
    let msg;
    if(kind==='yaw')   // a PATH: blocked iff any pose en route collides (motion interrupted)
      msg = nColl>0 ? ("BLOQUÉ ✗ — "+lbl+" : le trajet traverse "+nColl+"/"+path.length+" poses en collision")
                    : ("libre — trajet sans collision ("+path.length+" poses)");
    else               // an ESCAPE scan in the forbidden band: blocked iff NO pose is free
      msg = free===0 ? ("BLOQUÉ ✗ — "+lbl+" : 0 pose libre sur "+path.length+" (aucune échappatoire)")
                     : ("échappatoire trouvée ("+free+"/"+path.length+" libres)");
    document.getElementById("attempt").textContent=msg;
    return;}
   cur=path[i].slice();if(!collide(cur))free++;
   for(let j=0;j<cur.length;j++){let e=document.getElementById("s"+j);if(e){e.value=cur[j];document.getElementById("v"+j).textContent=cur[j].toFixed(2);}}
   redraw();i++;},60);}
setS(SC.start_s);
</script></body></html>
"""


def _spatial_joint_names(scene: _cert.Scene):
    """Physical name per unlocked joint of a spatial builtin (yaw/pitch/roll by axis,
    the joint just after the body link is the elbow)."""
    def nm(ax):
        ax = tuple(round(float(v)) for v in ax)
        return {(0, 0, 1): "lacet (z)", (0, 1, 0): "tangage (y)",
                (1, 0, 0): "roll (x)"}.get(ax, "rotation")
    names = [nm([float(_cert.Q(x)) for x in j["axis"]]) for j in scene.robot.joints]
    return [n if i != scene.body_link + 1 else "coude (y)" for i, n in enumerate(names)]


def joint_limits_deg(scene: _cert.Scene):
    """``[(name, lo_deg, hi_deg)]`` per unlocked joint. The s-box IS the joint-limit box
    (SPEC §2, all ⊂ (−π,π)); angles via ``q = 2·arctan(s)``. Makes the limits explicit
    (A25) on every figure / slider / verdict."""
    import math
    if scene.robot.kind == "spatial_revolute":
        names = _spatial_joint_names(scene)
    else:
        names = [f"q{i}" for i in range(scene.robot.n)]
    return [(names[i], math.degrees(2 * math.atan(float(lo))),
             math.degrees(2 * math.atan(float(hi))))
            for i, (lo, hi) in enumerate(scene.box)]


def limits_caption(scene: _cert.Scene) -> str:
    """One-line caption of the joint limits, e.g. ``limites : lacet ±70° · coude 0–109°``."""
    parts = []
    for n, lo, hi in joint_limits_deg(scene):
        nm = n.split(" (")[0]
        if abs(lo + hi) < 1.0:                                  # symmetric about 0
            parts.append(f"{nm} ±{round(max(abs(lo), abs(hi)))}°")
        else:
            parts.append(f"{nm} {round(lo)}–{round(hi)}°")
    return "limites articulaires : " + " · ".join(parts)


def export_interactive_html(scene: _cert.Scene, path: str, forearm_length: float = 0.3,
                            title: str = None) -> str:
    """Export a SELF-CONTAINED interactive HTML (zero dependencies) for a spatial scene
    (A24): joint sliders, two world projections (top x–y for yaw, side x–z for pitch/
    height), live collision of the certified UPPER-ARM body (turns red), labelled
    start/goal ghosts on BOTH views, and buttons that animate the natural escape attempts
    (yaw swing / over-the-top / around in roll+elbow) and report the verdict. Forward
    kinematics is recomputed in JS from the scene's joint axes/offsets, so the file needs
    no server and no libraries. It shows INTENTION; the certificate is the proof (rule 9).

    Returns ``path``. Spatial builtin only (the planar scenes read fine as 2-D figures)."""
    import json

    if scene.robot.kind != "spatial_revolute":
        raise NotImplementedError(
            "interactive HTML is for spatial scenes; planar scenes use the 2-D figures")

    locked_ang = scene.robot.locked_angles                     # {joint_idx: angle_rad}
    joints = [{"offset": [float(_cert.Q(x)) for x in j["offset"]],
               "axis": [float(_cert.Q(x)) for x in j["axis"]],
               "locked": locked_ang.get(i)}                     # angle (rad) if locked, else None
              for i, j in enumerate(scene.robot.joints)]
    panels = []
    for (A, b) in scene.obstacles.values():
        bnds = _box_bounds(A, b)
        if bnds is None:
            continue
        panels.append({"lo": [lo for lo, _ in bnds], "hi": [hi for _, hi in bnds]})

    names = _spatial_joint_names(scene)
    lims = joint_limits_deg(scene)                              # (name, lo_deg, hi_deg)

    data = {
        "joints": joints, "panels": panels, "body_link": scene.body_link,
        "upper_len": float(scene.hull_vertices[-1][0]),
        "start_s": [float(v) for v in scene.start_s],
        "goal_s": [float(v) for v in scene.goal_s],
        "box": [[float(lo), float(hi)] for lo, hi in scene.box],
        "joint_names": names,
        "limits_deg": [[lo, hi] for _, lo, hi in lims],        # A25: explicit joint limits
        "limits_caption": limits_caption(scene),
    }
    html = (_INTERACTIVE_TEMPLATE
            .replace("__SCENE__", json.dumps(data))
            .replace("__FOREARM__", repr(float(forearm_length)))
            .replace("__TITLE__", title or "scène spatiale — validation interactive"))
    with open(path, "w") as f:
        f.write(html)
    return path


_CONFIG_COLOUR = {"start": 0x1f77b4, "goal": 0x2ca02c}   # start = blue, goal = green


def _draw_robot(vis, scene, config, colour):
    """Draw the arm at one config as a polyline skeleton + joint spheres."""
    import meshcat.geometry as g
    import meshcat.transformations as tf

    pts = _joint_world_positions(scene, _config_q_to_s(scene, config))
    root = vis["robot"][config]
    root["links"].set_object(
        g.Line(g.PointsGeometry(pts.T.astype(np.float32)),
               g.LineBasicMaterial(color=colour, linewidth=4)))
    for i, p in enumerate(pts):
        node = root["joints"][str(i)]
        node.set_object(g.Sphere(0.04), g.MeshLambertMaterial(color=colour))
        node.set_transform(tf.translation_matrix(list(p)))


def show_scene(scene: _cert.Scene, config: str = "both"):
    """Open ONE Meshcat view of ``scene`` and the obstacles, drawing the arm at the
    requested config(s): ``"both"`` (default — start in blue AND goal in green in the
    same scene, so the two poses are compared without launching two servers),
    ``"start"`` or ``"goal"`` for a single pose. Returns the viewer URL (string)."""
    import meshcat
    import meshcat.geometry as g
    import meshcat.transformations as tf

    vis = meshcat.Visualizer()
    vis.delete()

    # --- obstacles (boxes) ---
    for nm, (A, b) in scene.obstacles.items():
        bounds = _box_bounds(A, b)
        if bounds is None:                      # non-box H-rep: skip with no crash
            continue
        size = [hi - lo for lo, hi in bounds]
        center = [0.5 * (lo + hi) for lo, hi in bounds]
        node = vis["obstacles"][nm]
        node.set_object(g.Box(size),
                        g.MeshLambertMaterial(color=0xB0B0B0, opacity=0.55,
                                              transparent=True))
        node.set_transform(tf.translation_matrix(center))

    # --- robot poses ---
    if config == "sweep":
        # A fan of poses interpolated start->goal in s-space; colliding ones (which a
        # straight motion would have to pass through) are red, free ones green. Shows
        # WHY the direct motion is blocked (the C-space figure shows ALL paths are).
        from . import scenes as _scenes
        oracle = _scenes.collision_oracle(scene)
        st = np.array([float(v) for v in scene.start_s])
        go = np.array([float(v) for v in scene.goal_s])
        n = 11
        for k in range(n):
            s = st + (go - st) * (k / (n - 1))
            colour = 0xd62728 if oracle(s) else 0x2ca02c
            pts = _joint_world_positions(scene, s)
            node = vis["sweep"][str(k)]
            node["links"].set_object(
                g.Line(g.PointsGeometry(pts.T.astype(np.float32)),
                       g.LineBasicMaterial(color=colour)))
            for i, p in enumerate(pts):
                jn = node["joints"][str(i)]
                jn.set_object(g.Sphere(0.02), g.MeshLambertMaterial(color=colour))
                jn.set_transform(tf.translation_matrix(list(p)))
    else:
        for cfg in (["start", "goal"] if config == "both" else [config]):
            _draw_robot(vis, scene, cfg, _CONFIG_COLOUR[cfg])

    return vis.url()
