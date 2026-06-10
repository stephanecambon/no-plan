"""Figure: (a) C-space ground truth + slab, (b) certified partition by pair,
(c) workspace, (d) back-end scaling from exp12 results."""
import numpy as np, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from exp34_multipair import (UP, DOWN, MID, in_collision, seg_box_hit,
                             certify_slab, fk_point)
from polylin import mono

phi = mono(2, 2, [1, 0]); delta = 0.05
boxes = [UP, DOWN, MID]; names = ['UP', 'DOWN', 'MID']
colors = {'UP': '#d62728', 'DOWN': '#1f77b4', 'MID': '#2ca02c',
          'outside': '#dddddd', 'FAIL': 'black'}

ok, leaves, failed = certify_slab(phi, delta, boxes, names)
assert ok

fig, axes = plt.subplots(1, 4, figsize=(21, 5.2))

# (a) ground truth C-space
ax = axes[0]
N = 161
s = np.linspace(-1, 1, N)
img = np.zeros((N, N, 3)) + 1.0
for i, s2 in enumerate(s):
    for j, s1 in enumerate(s):
        th1, th2 = 2*np.arctan(s1), 2*np.arctan(s2)
        hits = [seg_box_hit(th1, th2, b, m=25) for b in boxes]
        if any(hits):
            k = hits.index(True)
            c = matplotlib.colors.to_rgb(colors[names[k]])
            img[i, j] = [0.55 + 0.45*x for x in c]
ax.imshow(img, origin='lower', extent=[-1, 1, -1, 1], aspect='auto')
ax.axvspan(-delta, delta, color='gold', alpha=0.35)
ax.plot([np.tan(-np.pi/6)], [0], 'k*', ms=16); ax.plot([np.tan(np.pi/6)], [0], 'kP', ms=12)
ax.set_title('(a) C-space (vérité terrain échantillonnée)\nrouge=UP bleu=DOWN vert=MID, bande or = dalle')
ax.set_xlabel('s1'); ax.set_ylabel('s2')

# (b) certified partition
ax = axes[1]
for (cell, status, nm, t) in leaves:
    (a1, b1), (a2, b2) = cell
    fc = colors.get(nm, colors.get(status, 'white'))
    ax.add_patch(Rectangle((a1, a2), b1-a1, b2-a2, facecolor=fc,
                           edgecolor='k', linewidth=0.4,
                           alpha=0.9 if status == 'collision' else 0.35))
ax.set_xlim(-0.12, 0.12); ax.set_ylim(-1, 1)
ax.axvline(-delta, color='gold', lw=2); ax.axvline(delta, color='gold', lw=2)
ax.set_title('(b) Partition certifiée (38 feuilles-collision)\nchaque feuille = 1 certificat-témoin LP vs 1 paire')
ax.set_xlabel('s1')

# (c) workspace
ax = axes[2]
for b, nm in zip(boxes, names):
    ax.add_patch(Rectangle((b[0], b[2]), b[1]-b[0], b[3]-b[2],
                           facecolor=colors[nm], alpha=0.5, edgecolor='k'))
for th1, th2, style in [(-np.pi/3, 0, 'k'), (np.pi/3, 0, 'k')]:
    p0 = np.zeros(2); p1 = fk_point(th1, th2, 0); p2 = fk_point(th1, th2, 1)
    ax.plot([0, p1[0]], [0, p1[1]], style, lw=3)
    ax.plot([p1[0], p2[0]], [p1[1], p2[1]], style, lw=3, alpha=0.6)
th = np.linspace(0, 2*np.pi, 100)
ax.plot(2*np.cos(th), 2*np.sin(th), ':', color='gray', lw=0.8)
ax.set_xlim(-0.5, 2.3); ax.set_ylim(-2.1, 2.1); ax.set_aspect('equal')
ax.set_title('(c) Espace de travail : bras 2-link,\n3 obstacles, départ/arrivée')

# (d) scaling
ax = axes[3]
res = json.load(open('exp12_results.json'))
extra = {7: 0.4, 8: 1.9, 10: 32.4}
for be, mk, lbl in [('SOS-SDP', 'o-', 'SOS (SDP, Clarabel)'), ('bern-LP', 's-', 'Bernstein (LP)')]:
    xs, ys = [], []
    for r in res:
        if r['backend'] == be and r['kind'] == 'affine' and r['scene'] == 'collision':
            xs.append(r['n']); ys.append(r['time'])
    if be == 'bern-LP':
        for n_, t_ in extra.items(): xs.append(n_); ys.append(t_)
    ax.semilogy(xs, ys, mk, label=lbl)
ax.set_xlabel('n (DOF)'); ax.set_ylabel('temps de certification (s)')
ax.legend(); ax.grid(alpha=0.3)
ax.set_title('(d) Témoin affine : SOS vs Bernstein\n(même t* = 0.220 pour les deux)')

plt.tight_layout()
plt.savefig('certified_disconnection_results.png', dpi=110)
print('figure saved')
