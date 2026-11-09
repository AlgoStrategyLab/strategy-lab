"""Render the article's data tables as PNGs (Medium strips HTML tables)."""
import json, os
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

_OUT = None


def make_renderer(outdir):
    """Bind the renderer to one strategy's tables/ directory."""
    global _OUT
    _OUT = Path(outdir); _OUT.mkdir(parents=True, exist_ok=True)
    return render
C = {"blue":"#2a78d6","orange":"#eb6834","ink":"#0b0b0b","ink2":"#52514e",
     "grid":"#e6e5e2","surface":"#fcfcfb","band":"#f4f3f0","head":"#eceae6"}
plt.rcParams.update({"font.family":"DejaVu Sans"})

def render(name, headers, rows, title=None, col_w=None, highlight_col=None, fontsize=10.5):
    ncol = len(headers); nrow = len(rows)
    col_w = col_w or [1.0/ncol]*ncol
    row_h = 0.40; head_h = 0.52; title_h = 0.46 if title else 0.08
    width = 11.0
    height = title_h + head_h + nrow*row_h + 0.18
    fig = plt.figure(figsize=(width, height), dpi=160, facecolor=C["surface"])
    ax = fig.add_axes([0,0,1,1]); ax.set_xlim(0,1); ax.set_ylim(0,height); ax.axis("off")
    ax.add_patch(plt.Rectangle((0,0),1,height,color=C["surface"],zorder=0))
    y = height - title_h
    if title:
        ax.text(0.012, height-0.30, title, fontsize=12.5, fontweight="bold", color=C["ink"], va="center")
    # header band
    ax.add_patch(plt.Rectangle((0.008, y-head_h), 0.984, head_h, color=C["head"], zorder=1))
    x_edges=[0.015]
    for w in col_w: x_edges.append(x_edges[-1]+w*0.97)
    for i,h in enumerate(headers):
        ha = "left" if i==0 else "right"
        xx = x_edges[i]+0.004 if i==0 else x_edges[i+1]-0.006
        ax.text(xx, y-head_h/2, h, fontsize=fontsize, fontweight="bold", color=C["ink"], va="center", ha=ha, zorder=3)
    y -= head_h
    for r,row in enumerate(rows):
        if r % 2 == 1:
            ax.add_patch(plt.Rectangle((0.008, y-row_h), 0.984, row_h, color=C["band"], zorder=1))
        for i,cell in enumerate(row):
            ha = "left" if i==0 else "right"
            xx = x_edges[i]+0.004 if i==0 else x_edges[i+1]-0.006
            bold = (i==0 and ncol==2) or (highlight_col is not None and i==highlight_col)
            col = C["blue"] if (highlight_col is not None and i==highlight_col) else C["ink"] if i==0 else C["ink2"]
            ax.text(xx, y-row_h/2, str(cell), fontsize=fontsize, color=col,
                    fontweight="bold" if bold else "normal", va="center", ha=ha, zorder=3)
        ax.plot([0.008,0.992],[y-row_h,y-row_h], color=C["grid"], lw=0.7, zorder=2)
        y -= row_h
    fig.savefig(_OUT/f"{name}.png", facecolor=C["surface"]); plt.close(fig)
    print("wrote", name)
