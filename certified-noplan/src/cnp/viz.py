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
  <button onclick="play('distal')">Tentative : contourner via les distaux (redondance)</button>
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
  MUR (sommet panneau &gt; portée du bras, visible côté) ; « contourner via les distaux »
  échoue car le corps proximal certifié ne dépend PAS des joints distaux (passifs) — la
  redondance ne le libère pas (thèse du flagship).</div>
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
function armPts(s){ // base(origine monde) -> shoulder(corps proximal) -> elbow(corps distal) -> hand
  let T=fkChain(s); let L=SC.upper_len;
  let shoulder=ap(T[SC.body_link],[0,0,0]);   // proximal end of the certified body (link body_link)
  let elbow=ap(T[SC.body_link],[L,0,0]);       // distal end of the certified body
  let hand=ap(T[T.length-1],[FORE,0,0]);
  return {base:[0,0,0], shoulder, elbow, hand};}
function collide(s){ // certified body = segment shoulder->elbow (link body_link); mirrors the Python oracle
  let a=armPts(s),N=40;                         // N+1=41 samples == collision_oracle(n_samples=41)
  for(let k=0;k<=N;k++){let t=k/N;
    let p=[a.shoulder[0]+(a.elbow[0]-a.shoulder[0])*t, a.shoulder[1]+(a.elbow[1]-a.shoulder[1])*t, a.shoulder[2]+(a.elbow[2]-a.shoulder[2])*t];
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
  seg(ctx,a.base,a.shoulder,ai,vi,ghost?ghost:"#aaa",ghost?2:3);  // lower arm (base->shoulder) = display
  seg(ctx,a.shoulder,a.elbow,ai,vi,col,ghost?3:6);                // UPPER ARM (shoulder->elbow) = CERTIFIED body
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
 else if(kind==='distal' && SC.passive_dims){for(let k=0;k<=N;k++){let t=k/N;let s=cur.slice();s[0]=0; // in the band
   for(const pj of SC.passive_dims){s[pj]=SC.box[pj][0]+(SC.box[pj][1]-SC.box[pj][0])*(0.5-0.5*Math.cos(6.28*t*(1+pj)));} // sweep ALL distal joints (redundancy)
   path.push(s);}}
 else{for(let k=0;k<=N;k++){let t=k/N;let s=cur.slice();s[0]=0;
   if(s.length>2)s[2]=SC.box[2][0]+(SC.box[2][1]-SC.box[2][0])*t;                       // roll across its limits
   if(s.length>3)s[3]=SC.box[3][0]+(SC.box[3][1]-SC.box[3][0])*0.5*(1-Math.cos(6.28*t)); // elbow within its limits
   path.push(s);}}
 let free=0,i=0;document.getElementById("attempt").textContent="…";
 let iv=setInterval(()=>{if(i>=path.length){clearInterval(iv);
    let nColl=path.length-free;
    let lbl={yaw:"passage direct (lacet)",pitch:"passer par-dessus (tangage)",around:"contourner (roll/coude)",distal:"contourner via les distaux (redondance)"}[kind];
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


# ── S10-quinquies: interactive for the REAL iiwa7 flagship — body = faithful 40-vertex convex
# hull (NOT a segment), collision = GJK(hull, H-rep box) reproducing scenes.convex_collision_oracle
# (A43/A40 invariant, tested under node). Separator = q2 shoulder PITCH; obstacle = overhead shelf.
_INTERACTIVE_TEMPLATE_HULL = r"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><title>__TITLE__</title>
<style>
 body{font-family:system-ui,Arial,sans-serif;margin:14px;color:#222;background:#fff}
 h1{font-size:16px;margin:0 0 4px} .sub{color:#555;font-size:12px;margin:0 0 10px;max-width:900px}
 .views{display:flex;gap:18px;flex-wrap:wrap} .view{flex:0 0 auto}
 .view h2{font-size:13px;margin:0 0 2px} .view .what{font-size:11px;color:#666;margin:0 0 4px;max-width:320px}
 canvas{border:1px solid #ccc;background:#fafafa}
 .panel{margin-top:12px;max-width:820px}
 .sld{display:flex;align-items:center;gap:8px;margin:3px 0;font-size:13px}
 .sld label{width:250px} .sld input{flex:1} .sld .val{width:54px;text-align:right;font-variant-numeric:tabular-nums}
 #verdict{font-weight:bold;font-size:15px;margin:8px 0;padding:6px 10px;border-radius:6px;display:inline-block}
 #limits{font-size:12px;color:#333;background:#fff7e0;border:1px solid #e0c060;border-radius:6px;padding:6px 10px;margin:6px 0;max-width:800px}
 .btns{margin:10px 0;display:flex;gap:8px;flex-wrap:wrap}
 button{font-size:13px;padding:6px 10px;border:1px solid #999;border-radius:6px;background:#f0f0f0;cursor:pointer}
 button:hover{background:#e4e4e4} #attempt{font-size:13px;margin-left:6px}
 .legend{font-size:11px;color:#555;margin-top:8px;line-height:1.5;max-width:820px}
 .sw{display:inline-block;width:22px;height:0;border-top-width:3px;border-top-style:solid;vertical-align:middle;margin-right:4px}
 .bx{display:inline-block;width:16px;height:11px;vertical-align:middle;margin-right:4px;border:1px solid #555}
</style></head><body>
<h1>__TITLE__</h1>
<p class="sub">Artefact de validation INTERACTIF (A24) — VRAI KUKA iiwa7. Bougez les 7 curseurs
articulaires ; le <b>corps proximal certifié</b> est la <b>silhouette convexe fidèle (40 sommets)</b>
du lien 3, elle devient <b>ROUGE</b> en collision avec l'<b>étagère en surplomb</b>. La collision est
calculée en 3D par GJK (coque ∩ boîte H-rep), reproduisant l'oracle corps-convexe Python (invariant
A40 testé sous node). Les <b>fantômes</b> start (bleu) / goal (vert) sont les deux poses basses libres
à relier. Cet outil montre l'INTENTION ; la preuve est le certificat (règle 9).</p>
<div class="views">
 <div class="view"><h2>Vue de CÔTÉ (x–z) — LE tangage q2</h2>
  <p class="what">plan monde x–z. C'est la vue qui compte : on voit l'<b>espace libre SOUS
   l'étagère</b> où reposent start/goal, et le corps qui MONTE dans l'étagère quand q2→0
   (bras droit vertical). Chaîne iiwa complète (fine) + corps certifié (silhouette pleine).</p>
  <canvas id="side" width="360" height="420"></canvas></div>
 <div class="view"><h2>Vue de DESSUS (x–y) — lacet q1</h2>
  <p class="what">plan monde x–y. Le lacet de base q1 fait pivoter le bras ; le corps compact
   reste près de l'axe. La collision est calculée en 3D (une silhouette peut sembler croiser
   l'étagère en projection sans la toucher, ou l'inverse).</p>
  <canvas id="top" width="360" height="360"></canvas></div>
</div>
<div class="panel">
 <div id="verdict"></div>
 <div id="limits"></div>
 <div id="sliders"></div>
 <div class="btns">
  <button onclick="play('direct')">Tentative : passage direct (tangage q2 : start→goal)</button>
  <button onclick="play('under')">Tentative : passer dessous en restant incliné (balayer lacet+roll)</button>
  <button onclick="play('distal')">Tentative : contourner via les distaux (redondance 7-DOF)</button>
  <button onclick="setS(SC.start_s)">→ start</button>
  <button onclick="setS(SC.goal_s)">→ goal</button>
  <span id="attempt"></span>
 </div>
 <div class="legend">
  <div><span class="sw" style="border-color:#1f77b4"></span>fantôme start &nbsp;
       <span class="sw" style="border-color:#2ca02c"></span>fantôme goal &nbsp;
       <span class="sw" style="border-color:#d62728"></span>corps EN COLLISION &nbsp;
       <span class="sw" style="border-color:#333"></span>corps libre &nbsp;
       <span class="bx" style="background:rgba(120,120,120,0.5)"></span>étagère en surplomb (H-rep)</div>
  <div>Chaque vue déclare ce qu'elle montre (A24). La THÈSE du flagship : pour changer le SIGNE
  du pitch d'épaule q2 (start q2&lt;0 → goal q2&gt;0) il faut passer par q2≈0 (bras droit), où le
  corps proximal percute l'étagère — et AUCUN des 4 joints distaux (passifs, en aval du lien 3) ne
  l'en sort. La redondance 7-DOF est inutile ici : c'est ce que le certificat prouve, pas l'œil.</div>
 </div>
</div>
<script>
const SC = __SCENE__;
// ── 3-vector + 4x4 helpers ──
function ident(){return [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1];}
function mul(A,B){let C=new Array(16).fill(0);for(let i=0;i<4;i++)for(let j=0;j<4;j++)for(let k=0;k<4;k++)C[i*4+j]+=A[i*4+k]*B[k*4+j];return C;}
function trans(v){let T=ident();T[3]=v[0];T[7]=v[1];T[11]=v[2];return T;}
function rot(axis,a){let [x,y,z]=axis,n=Math.hypot(x,y,z);x/=n;y/=n;z/=n;
 let c=Math.cos(a),s=Math.sin(a),t=1-c;
 return [t*x*x+c,t*x*y-s*z,t*x*z+s*y,0, t*x*y+s*z,t*y*y+c,t*y*z-s*x,0, t*x*z-s*y,t*y*z+s*x,t*z*z+c,0, 0,0,0,1];}
function ap(T,p){return [T[0]*p[0]+T[1]*p[1]+T[2]*p[2]+T[3], T[4]*p[0]+T[5]*p[1]+T[6]*p[2]+T[7], T[8]*p[0]+T[9]*p[1]+T[10]*p[2]+T[11]];}
function sub(a,b){return [a[0]-b[0],a[1]-b[1],a[2]-b[2]];}
function neg(a){return [-a[0],-a[1],-a[2]];}
function dot(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
function cross(a,b){return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];}
// forward kinematics: unlocked joint q = 2*atan(s) (s = the UNLOCKED slider vector), locked joint
// = its fixed angle. Returns the cumulative transform AFTER each chain joint (frame j{i}).
function fkChain(s){let T=ident(),out=[],si=0;for(let i=0;i<SC.joints.length;i++){
  T=mul(T,trans(SC.joints[i].offset));
  let a = SC.joints[i].locked!=null ? SC.joints[i].locked : 2*Math.atan(s[si++]);
  T=mul(T,rot(SC.joints[i].axis, a)); out.push(T);}return out;}
function bodyWorld(s){let T=fkChain(s),F=T[SC.body_link];return SC.hull.map(v=>ap(F,v));} // 40 world verts
function skeleton(s){let T=fkChain(s),pts=[[0,0,0]];for(let i=0;i<=SC.body_link;i++)pts.push(ap(T[i],[0,0,0]));
  pts.push(ap(T[T.length-1],[0,0,0]));return pts;}   // base -> ... -> body frame -> distal tip (display)
// ── GJK: does the convex hull of world verts W intersect the AABB [lo,hi]? (== convex_collision_oracle) ──
function supHull(W,d){let bi=0,bd=dot(W[0],d);for(let k=1;k<W.length;k++){let x=dot(W[k],d);if(x>bd){bd=x;bi=k;}}return W[bi];}
function supBox(lo,hi,d){return [d[0]>=0?hi[0]:lo[0], d[1]>=0?hi[1]:lo[1], d[2]>=0?hi[2]:lo[2]];}
function msup(W,lo,hi,d){return sub(supHull(W,d), supBox(lo,hi,neg(d)));} // Minkowski A⊖B support
function tprod(a,b,c){return cross(cross(a,b),c);}                        // (a×b)×c
function gjk(W,lo,hi){
 let d=[1,0,0], s=[msup(W,lo,hi,d)]; d=neg(s[0]);
 for(let it=0;it<64;it++){
   if(dot(d,d)<1e-30) return true;
   let a=msup(W,lo,hi,d);
   if(dot(a,d)<0) return false;                                          // a not past origin along d ⇒ disjoint
   s.push(a);
   // evolve simplex toward the origin (line / triangle / tetrahedron)
   if(s.length===2){let[b,A]=[s[0],s[1]],ab=sub(b,A),ao=neg(A);
     if(dot(ab,ao)>0){d=tprod(ab,ao,ab); if(dot(d,d)<1e-30)d=Math.abs(ab[0])<0.9?cross(ab,[1,0,0]):cross(ab,[0,1,0]);}
     else{s=[A];d=ao;}}
   else if(s.length===3){let[c,b,A]=[s[0],s[1],s[2]],ab=sub(b,A),ac=sub(c,A),ao=neg(A),abc=cross(ab,ac);
     if(dot(cross(abc,ac),ao)>0){ if(dot(ac,ao)>0){s=[c,A];d=tprod(ac,ao,ac);} else{s=[b,A];d=(dot(ab,ao)>0)?tprod(ab,ao,ab):ao;} }
     else if(dot(cross(ab,abc),ao)>0){ s=[b,A];d=(dot(ab,ao)>0)?tprod(ab,ao,ab):ao; }
     else{ if(dot(abc,ao)>0){d=abc;} else{s=[b,c,A];d=neg(abc);} }}
   else{let[dd,c,b,A]=[s[0],s[1],s[2],s[3]],ao=neg(A),
     abc=cross(sub(b,A),sub(c,A)), acd=cross(sub(c,A),sub(dd,A)), adb=cross(sub(dd,A),sub(b,A));
     let over=false;
     if(dot(abc,ao)>0){s=[c,b,A];d=abc;over=true;}
     else if(dot(acd,ao)>0){s=[dd,c,A];d=acd;over=true;}
     else if(dot(adb,ao)>0){s=[b,dd,A];d=adb;over=true;}
     if(!over) return true;}                                             // origin enclosed ⇒ intersect
 }
 return true;
}
function collide(s){let W=bodyWorld(s);for(const p of SC.panels){if(gjk(W,p.lo,p.hi))return true;}return false;}
// ── 2-D convex hull (monotone chain) for drawing the projected silhouette ──
function hull2d(P){if(P.length<3)return P;P=P.slice().sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
 let cr=(o,a,b)=>(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0]),L=[],U=[];
 for(const p of P){while(L.length>=2&&cr(L[L.length-2],L[L.length-1],p)<=0)L.pop();L.push(p);}
 for(let i=P.length-1;i>=0;i--){const p=P[i];while(U.length>=2&&cr(U[U.length-2],U[U.length-1],p)<=0)U.pop();U.push(p);}
 return L.slice(0,-1).concat(U.slice(0,-1));}
// ── per-view projection: world window -> canvas px ──
const VIEW={side:{ai:0,vi:2,amin:-0.55,amax:0.55,vmin:0.0,vmax:1.15,w:360,h:420},
            top:{ai:0,vi:1,amin:-0.55,amax:0.55,vmin:-0.55,vmax:0.55,w:360,h:360}};
function mapx(V,wa){return (wa-V.amin)/(V.amax-V.amin)*V.w;}
function mapy(V,wv){return V.h-(wv-V.vmin)/(V.vmax-V.vmin)*V.h;}
function drawPanels(ctx,V){ctx.fillStyle="rgba(120,120,120,0.5)";ctx.strokeStyle="#555";
 for(const b of SC.panels){let x0=mapx(V,b.lo[V.ai]),x1=mapx(V,b.hi[V.ai]),y0=mapy(V,b.hi[V.vi]),y1=mapy(V,b.lo[V.vi]);
   ctx.fillRect(x0,y0,x1-x0,y1-y0);ctx.strokeRect(x0,y0,x1-x0,y1-y0);}}
function drawSilhouette(ctx,V,s,col,ghost){
 let W=bodyWorld(s),P=W.map(w=>[mapx(V,w[V.ai]),mapy(V,w[V.vi])]),h=hull2d(P);
 ctx.beginPath();ctx.moveTo(h[0][0],h[0][1]);for(let i=1;i<h.length;i++)ctx.lineTo(h[i][0],h[i][1]);ctx.closePath();
 if(ghost){ctx.strokeStyle=col;ctx.lineWidth=2;ctx.stroke();}
 else{ctx.fillStyle=col+"cc";ctx.fill();ctx.strokeStyle="#222";ctx.lineWidth=1;ctx.stroke();}}
function drawSkeleton(ctx,V,s,col){let sk=skeleton(s);ctx.strokeStyle=col;ctx.lineWidth=1.5;ctx.beginPath();
 ctx.moveTo(mapx(V,sk[0][V.ai]),mapy(V,sk[0][V.vi]));for(let i=1;i<sk.length;i++)ctx.lineTo(mapx(V,sk[i][V.ai]),mapy(V,sk[i][V.vi]));ctx.stroke();}
function drawView(id){let V=VIEW[id],ctx=document.getElementById(id).getContext("2d");ctx.clearRect(0,0,V.w,V.h);
 ctx.strokeStyle="#e9e9e9";ctx.lineWidth=1;ctx.beginPath();
 ctx.moveTo(mapx(V,0),0);ctx.lineTo(mapx(V,0),V.h);ctx.moveTo(0,mapy(V,0));ctx.lineTo(V.w,mapy(V,0));ctx.stroke();
 drawPanels(ctx,V);
 // "space under the shelf" cue on the side view (A20): dashed underside line + label
 if(id==="side"){let z0=SC.panels[0].lo[2],y=mapy(V,z0);ctx.strokeStyle="#a06000";ctx.setLineDash([5,4]);
   ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(V.w,y);ctx.stroke();ctx.setLineDash([]);
   ctx.fillStyle="#a06000";ctx.font="11px sans-serif";ctx.fillText("dessous d'étagère z="+z0.toFixed(2)+" — espace libre en-dessous",6,y+13);}
 drawSkeleton(ctx,V,SC.start_s,"#9ec6e6");drawSkeleton(ctx,V,SC.goal_s,"#a9dab0");drawSkeleton(ctx,V,cur,"#555");
 drawSilhouette(ctx,V,SC.start_s,"#1f77b4",true);drawSilhouette(ctx,V,SC.goal_s,"#2ca02c",true);
 drawSilhouette(ctx,V,cur,collide(cur)?"#d62728":"#333",false);
 ctx.fillStyle="#000";ctx.fillRect(mapx(V,0)-3,mapy(V,0)-3,6,6);
 let gs=bodyWorld(SC.start_s)[0],gg=bodyWorld(SC.goal_s)[0];
 ctx.font="11px sans-serif";ctx.fillStyle="#1f77b4";ctx.fillText("start",mapx(V,gs[V.ai])+4,mapy(V,gs[V.vi]));
 ctx.fillStyle="#2ca02c";ctx.fillText("goal",mapx(V,gg[V.ai])+4,mapy(V,gg[V.vi])+11);}
function redraw(){drawView("side");drawView("top");
 let c=collide(cur),v=document.getElementById("verdict");
 v.textContent=c?"corps proximal EN COLLISION avec l'étagère":"corps proximal libre";
 v.style.background=c?"#f6d3d3":"#d6efd6";v.style.color=c?"#7f0000":"#14521a";}
let cur=SC.start_s.slice();
function setS(s){cur=s.slice();for(let i=0;i<cur.length;i++){let e=document.getElementById("s"+i);
  if(e){e.value=cur[i];document.getElementById("v"+i).textContent=cur[i].toFixed(2);}}redraw();}
document.getElementById("limits").innerHTML="<b>"+SC.limits_caption+"</b> — les BUTÉES des curseurs SONT ces limites articulaires (A25) ; toutes ⊂ (−180°,180°) ⟹ pas de wrap-around. Étiquettes d'axes PHYSIQUES (axe effectif locked·axe, pas l'axe-chaîne replié) : q2 est bien le TANGAGE (pitch) d'épaule.";
const NAMES=SC.joint_names;let sl=document.getElementById("sliders");let si=0;
for(let i=0;i<SC.joints.length;i++){let d=document.createElement("div");d.className="sld";
 if(SC.joints[i].locked!=null){let dg=Math.round(SC.joints[i].locked*180/Math.PI);
   d.innerHTML='<label>joint '+i+' — 🔒 VERROUILLÉ à '+dg+'° (décomposition, hors C-space certifié)</label>';
   d.style.opacity=0.5;sl.appendChild(d);continue;}
 let j=si;let ld=SC.limits_deg[j];let deg='['+Math.round(ld[0])+'…'+Math.round(ld[1])+'°]';
 let star=(j===SC.barrier_dim)?' ★ SÉPARATEUR':'';
 d.innerHTML='<label>s'+j+' — q'+(j+1)+' '+NAMES[i]+' '+deg+star+'</label><input id="s'+j+'" type="range" min="'+SC.box[j][0]+'" max="'+SC.box[j][1]+'" step="0.01" value="'+cur[j]+'"><span class="val" id="v'+j+'"></span>';
 sl.appendChild(d);let inp=d.querySelector("input");
 inp.oninput=()=>{cur[j]=parseFloat(inp.value);document.getElementById("v"+j).textContent=cur[j].toFixed(2);redraw();};
 si++;}
// escape attempts. 'direct' = a PATH (blocked iff ANY pose collides). 'under'/'distal' = ESCAPE
// scans inside the forbidden band (blocked iff NO pose is free — no way out).
function play(kind){let path=[],N=28,bd=SC.barrier_dim,delta=SC.delta;
 if(kind==='direct'){for(let k=0;k<=N;k++){let t=k/N;path.push(SC.start_s.map((v,i)=>v+(SC.goal_s[i]-v)*t));}}
 else if(kind==='under'){for(let k=0;k<=N;k++){let t=k/N;let s=cur.slice();
   s[bd]=(-delta+2*delta*(k%7)/6);                                       // stay INSIDE the forbidden band
   if(s.length>0)s[0]=SC.box[0][0]+(SC.box[0][1]-SC.box[0][0])*t;         // sweep lacet q1
   if(s.length>2)s[2]=SC.box[2][0]+(SC.box[2][1]-SC.box[2][0])*(0.5-0.5*Math.cos(6.28*t)); // sweep roll q3
   path.push(s);}}
 else{for(let k=0;k<=N;k++){let t=k/N;let s=cur.slice();s[bd]=0;         // 'distal': at band centre
   for(const pj of (SC.passive_dims||[]))s[pj]=SC.box[pj][0]+(SC.box[pj][1]-SC.box[pj][0])*(0.5-0.5*Math.cos(6.28*t*(1+pj)));
   path.push(s);}}
 let free=0,i=0;document.getElementById("attempt").textContent="…";
 let iv=setInterval(()=>{if(i>=path.length){clearInterval(iv);let nColl=path.length-free;
    let lbl={direct:"passage direct (tangage q2)",under:"passer dessous en restant incliné",distal:"contourner via les distaux (redondance)"}[kind];
    let msg;
    if(kind==='direct') msg = nColl>0 ? ("BLOQUÉ ✗ — "+lbl+" : le trajet traverse "+nColl+"/"+path.length+" poses en collision")
                                      : ("libre — trajet sans collision ("+path.length+" poses)");
    else msg = free===0 ? ("BLOQUÉ ✗ — "+lbl+" : 0 pose libre sur "+path.length+" (aucune échappatoire)")
                        : ("échappatoire trouvée ("+free+"/"+path.length+" libres)");
    document.getElementById("attempt").textContent=msg;return;}
   cur=path[i].slice();if(!collide(cur))free++;
   for(let j=0;j<cur.length;j++){let e=document.getElementById("s"+j);if(e){e.value=cur[j];document.getElementById("v"+j).textContent=cur[j].toFixed(2);}}
   redraw();i++;},55);}
setS(SC.start_s);
</script></body></html>
"""


def _rot3(ax, ang):
    """3×3 rotation matrix about (possibly non-unit) axis ``ax`` by ``ang`` rad (Rodrigues)."""
    import math
    x, y, z = ax
    n = math.hypot(x, y, z)
    if n == 0:
        return np.eye(3)
    x, y, z = x / n, y / n, z / n
    c, s, t = math.cos(ang), math.sin(ang), 1 - math.cos(ang)
    return np.array([[t * x * x + c, t * x * y - s * z, t * x * z + s * y],
                     [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
                     [t * x * z - s * y, t * y * z + s * x, t * z * z + c]])


def _effective_axes(scene: _cert.Scene):
    """World-frame rotation axis of each CHAIN joint at the REFERENCE config (unlocked
    joints at 0, locked joints at their fixed angle). The octahedral decomposition of the
    real iiwa parks every VARIABLE joint's *chain* axis at a bare ``z`` — the physical joint
    TYPE (yaw/pitch/roll) only emerges once the preceding LOCKED rotations are applied
    (finding S10-quater: reading the raw chain axis mislabels the shoulder-pitch q2 as a
    ``lacet (z)`` — a viz that lies, A40). We accumulate the reference rotation and return
    ``R_{0..i-1} · axis_i`` per joint. For a fully-unlocked chain every accumulated rotation
    is identity at the reference, so effective ≡ raw axis (S3/S5/S2b labels unchanged)."""
    locked = scene.robot.locked_angles
    R = np.eye(3)
    out = []
    for i, j in enumerate(scene.robot.joints):
        ax = [float(_cert.Q(x)) for x in j["axis"]]
        out.append(tuple(R @ np.array(ax, dtype=float)))
        R = R @ _rot3(ax, locked.get(i, 0.0))
    return out


def _spatial_joint_names(scene: _cert.Scene):
    """Physical name per CHAIN joint of a spatial builtin, keyed on the joint's EFFECTIVE
    world axis (``locked·axis``, not the raw chain axis — finding S10-quater). z→lacet
    (yaw), y→tangage (pitch), x→roll; the unlocked joint just after the certified body link
    is named the elbow (kept for the simple S3/S5 scenes; on the real iiwa that slot is a
    locked decomposition joint, so the rule is a no-op there and q4 reads as its pitch)."""
    def word(effax):
        a = tuple(abs(round(float(v))) for v in effax)          # TYPE ignores axis sign
        return {(0, 0, 1): "lacet (z)", (0, 1, 0): "tangage (y)",
                (1, 0, 0): "roll (x)"}.get(a, "rotation")
    names = [word(e) for e in _effective_axes(scene)]
    bl1 = scene.body_link + 1
    if 0 <= bl1 < len(names) and bl1 not in scene.robot.locked_angles:
        names[bl1] = "coude (y)"
    return names


def joint_limits_deg(scene: _cert.Scene):
    """``[(name, lo_deg, hi_deg)]`` per UNLOCKED joint (one per slider / per s-box axis). The
    s-box IS the joint-limit box (SPEC §2, all ⊂ (−π,π)); angles via ``q = 2·arctan(s)``.
    Makes the limits explicit (A25) on every figure / slider / verdict. Names come from the
    EFFECTIVE-axis labels of the *unlocked* chain joints (finding S10-quater: the box has one
    entry per unlocked joint, so we must skip the locked decomposition joints, not index the
    first ``n`` chain joints)."""
    import math
    if scene.robot.kind == "spatial_revolute":
        allnames = _spatial_joint_names(scene)
        locked = scene.robot.locked_angles
        names = [allnames[i] for i in range(len(allnames)) if i not in locked]
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


def _barrier_dim(scene: _cert.Scene):
    """The single s-dim the barrier φ depends on (linear single-var barrier ⇒ one nonzero
    coeff dim), or ``None`` if φ is not a single-variable barrier."""
    dims = {i for e, c in scene.phi.items() for i in range(len(e)) if e[i] and _cert.Q(c) != 0}
    return dims.pop() if len(dims) == 1 else None


def export_interactive_html(scene: _cert.Scene, path: str, forearm_length: float = 0.3,
                            title: str = None, active_dims=None, body_mode: str = "segment") -> str:
    """Export a SELF-CONTAINED interactive HTML (zero dependencies) for a spatial scene
    (A24): joint sliders, two world projections (top x–y for yaw, side x–z for pitch/
    height), live collision of the certified UPPER-ARM body (turns red), labelled
    start/goal ghosts on BOTH views, and buttons that animate the natural escape attempts
    (yaw swing / over-the-top / around) and report the verdict. Forward kinematics is
    recomputed in JS from the scene's joint axes/offsets, so the file needs no server and
    no libraries. It shows INTENTION; the certificate is the proof (rule 9).

    ``active_dims`` (optional tuple, e.g. ``(0,1,2)`` from ``engine.pair_views``): when given,
    the third escape attempt sweeps the PASSIVE (distal) joints — demonstrating that no distal
    setting frees the proximal body ("portée robuste à la redondance"). Without it, that button
    keeps the legacy roll/elbow sweep.

    ``body_mode`` selects the body model and collision layer (both JS-recomputed, dependency-free):
    ``"segment"`` (default) draws the certified body as a SEGMENT and collides by sampling it
    (matches :func:`scenes.collision_oracle` — the iiwa-LIKE / planar scenes); ``"hull"`` draws
    the faithful K-vertex convex SILHOUETTE and collides by GJK(hull, H-rep box), reproducing
    :func:`scenes.convex_collision_oracle` (the REAL iiwa7 flagship, S10-quinquies, A43/A40). The
    hull mode also stars the barrier joint and animates the pitch/shelf escape attempts.

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

    n = len(scene.box)
    passive = ([i for i in range(n) if i not in tuple(active_dims)]
               if active_dims is not None else None)
    data = {
        "joints": joints, "panels": panels, "body_link": scene.body_link,
        "upper_len": float(scene.hull_vertices[-1][0]),
        "start_s": [float(v) for v in scene.start_s],
        "goal_s": [float(v) for v in scene.goal_s],
        "box": [[float(lo), float(hi)] for lo, hi in scene.box],
        "joint_names": names,
        "limits_deg": [[lo, hi] for _, lo, hi in lims],        # A25: explicit joint limits
        "limits_caption": limits_caption(scene),
        "active_dims": list(active_dims) if active_dims is not None else None,
        "passive_dims": passive,                               # distal joints proven passive
    }
    if body_mode == "hull":
        # REAL iiwa flagship (S10-quinquies): the certified body is the faithful 40-vertex convex
        # hull; collision is GJK(hull, H-rep box) reproducing scenes.convex_collision_oracle (A43).
        data["hull"] = [[float(_cert.Q(c)) for c in v] for v in scene.hull_vertices]
        data["delta"] = float(scene.delta)
        data["barrier_dim"] = _barrier_dim(scene)
        template = _INTERACTIVE_TEMPLATE_HULL
    elif body_mode == "segment":
        template = _INTERACTIVE_TEMPLATE
    else:
        raise ValueError(f"body_mode must be 'segment' or 'hull', got {body_mode!r}")
    html = (template
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
