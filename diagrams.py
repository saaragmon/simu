"""
Generate simulation diagrams for the Queuechella project.

Produces two PNG files:
  event_diagram.png        – Event Diagram (full event graph)
  checkin_end_diagram.png  – Event Handling Diagram: SECURITY_END (end of check-in)
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np


# ─── Drawing primitives ───────────────────────────────────────────────────────

def draw_box(ax, xy, w, h, label, color='#4A90D9', text_color='white',
             fontsize=9, style='round,pad=0.1', zorder=3):
    x, y = xy
    box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                         boxstyle=style,
                         facecolor=color, edgecolor='#2C3E50',
                         linewidth=1.4, zorder=zorder)
    ax.add_patch(box)
    ax.text(x, y, label, ha='center', va='center',
            fontsize=fontsize, color=text_color,
            fontweight='bold', zorder=zorder+1,
            multialignment='center')


def draw_diamond(ax, xy, w, h, label, color='#E67E22', text_color='white',
                 fontsize=8.5, zorder=3):
    x, y = xy
    dx, dy = w/2, h/2
    diamond = plt.Polygon([(x, y+dy), (x+dx, y), (x, y-dy), (x-dx, y)],
                           facecolor=color, edgecolor='#2C3E50',
                           linewidth=1.4, zorder=zorder)
    ax.add_patch(diamond)
    ax.text(x, y, label, ha='center', va='center',
            fontsize=fontsize, color=text_color,
            fontweight='bold', zorder=zorder+1, multialignment='center')


def arrow(ax, start, end, label='', color='#2C3E50', lw=1.3,
          style='arc3,rad=0', zorder=2):
    ax.annotate('', xy=end, xytext=start,
                arrowprops=dict(arrowstyle='->', color=color,
                                lw=lw, connectionstyle=style),
                zorder=zorder)
    if label:
        mx = (start[0] + end[0]) / 2
        my = (start[1] + end[1]) / 2
        ax.text(mx, my, label, ha='center', va='center',
                fontsize=7, color='#444444',
                bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                          edgecolor='none', alpha=0.85))


# ═══════════════════════════════════════════════════════════════════════════════
#  DIAGRAM 1 – Event Diagram
# ═══════════════════════════════════════════════════════════════════════════════

def draw_event_diagram():
    fig, ax = plt.subplots(figsize=(18, 13))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 13)
    ax.axis('off')
    fig.patch.set_facecolor('#F8F9FA')

    fig.suptitle('Event Diagram – Queuechella Festival Simulation',
                 fontsize=15, fontweight='bold', color='#2C3E50', y=0.97)

    BW, BH = 2.3, 0.65
    DW, DH = 2.4, 0.65

    C_EVT   = '#2980B9'   # regular event
    C_SCHED = '#27AE60'   # scheduled / timed event
    C_DEC   = '#E67E22'   # decision / routing
    C_END   = '#8E44AD'   # terminal event
    C_QUEUE = '#2471A3'   # queue / waiting state

    legend_items = [
        mpatches.Patch(facecolor=C_EVT,   label='Regular event'),
        mpatches.Patch(facecolor=C_SCHED, label='Scheduled / timed event'),
        mpatches.Patch(facecolor=C_DEC,   label='Routing decision'),
        mpatches.Patch(facecolor=C_END,   label='Terminal event'),
        mpatches.Patch(facecolor=C_QUEUE, label='Queue / waiting state'),
    ]
    ax.legend(handles=legend_items, loc='upper left', fontsize=8.5,
              framealpha=0.9, ncol=5, bbox_to_anchor=(0.01, 0.97))

    # ── ARRIVAL & ENTRY ───────────────────────────────────────────────────
    draw_box(ax, (2.0, 11.5), BW, BH, 'Entity Arrival\n(ARRIVE)', C_EVT)
    draw_box(ax, (5.5, 11.5), BW, BH, 'Ticket Scan Complete\n(SCAN_END)', C_SCHED)
    draw_box(ax, (9.0, 11.5), BW, BH, 'Security Check Complete\n(SECURITY_END)', C_SCHED)

    arrow(ax, (3.15, 11.5), (4.35, 11.5), 'server free')
    arrow(ax, (2.0, 11.17), (2.0, 10.83), style='arc3,rad=-0.6', label='joins entry queue')
    arrow(ax, (6.65, 11.5), (7.85, 11.5))

    # SECURITY_END triggers SCAN_END for next in queue
    ax.annotate('', xy=(5.5, 11.83), xytext=(9.0, 11.83),
                arrowprops=dict(arrowstyle='->', color='#7F8C8D',
                                lw=1.1, connectionstyle='arc3,rad=-0.3'))
    ax.text(7.25, 12.3, 'next in queue', ha='center', fontsize=7.5,
            color='#7F8C8D', style='italic')

    # ── NEXT ACTIVITY ROUTER ──────────────────────────────────────────────
    draw_diamond(ax, (9.0, 9.8), DW, DH, 'Next Activity\n(NEXT)', C_DEC)
    arrow(ax, (9.0, 11.17), (9.0, 10.12))

    # ── ACTIVITY BRANCHES ─────────────────────────────────────────────────
    draw_box(ax, (2.0, 8.3), BW, BH, 'Wait for Show\n(SHOW_QUEUE)', C_QUEUE)
    arrow(ax, (7.8, 9.8), (3.15, 8.3), style='arc3,rad=0.15', label='show activity')

    draw_box(ax, (6.5, 8.3), BW, BH, 'Service Station\n(SERVICE_QUEUE)', C_QUEUE)
    arrow(ax, (9.0, 9.47), (6.5, 8.63))

    draw_box(ax, (11.0, 8.3), BW, BH, 'DJ Stage Queue\n(DJ_QUEUE)', C_QUEUE)
    arrow(ax, (10.2, 9.8), (11.0, 8.63), style='arc3,rad=-0.1', label='electronic')

    draw_box(ax, (15.5, 8.3), BW, BH, 'Lunch Break\n(LUNCH)', C_QUEUE)
    arrow(ax, (10.2, 9.8), (14.35, 8.3), style='arc3,rad=-0.2', label='13:00–15:00, p=0.7')

    # No more activities → leave
    draw_box(ax, (9.0, 8.3), 2.1, BH, 'Entity Leaves\n(ENTITY_LEAVE)', C_END)
    ax.annotate('', xy=(9.0, 8.63), xytext=(9.0, 9.47),
                arrowprops=dict(arrowstyle='->', color=C_END, lw=1.2,
                                linestyle='dashed'))
    ax.text(9.55, 9.05, 'no more activities', ha='left', fontsize=7,
            color=C_END, style='italic')

    # ── SHOW PROCESSING ───────────────────────────────────────────────────
    draw_box(ax, (2.0, 6.7), BW, BH, 'Show Starts\n(SHOW_START)', C_SCHED)
    draw_box(ax, (2.0, 5.1), BW, BH, 'Show Ends\n(SHOW_END)', C_SCHED)
    draw_box(ax, (5.0, 6.7), BW*0.9, BH, 'Early Exit\n(EARLY_LEAVE)', '#1A5276')

    arrow(ax, (2.0, 7.97), (2.0, 7.03))
    arrow(ax, (2.0, 6.37), (2.0, 5.43))
    arrow(ax, (3.15, 6.7), (3.95, 6.7), label='back-10, p=0.5\nt+15 min')

    ax.annotate('', xy=(7.8, 9.8), xytext=(2.0, 5.43),
                arrowprops=dict(arrowstyle='->', color=C_EVT, lw=1.1,
                                connectionstyle='arc3,rad=0.3'))
    ax.annotate('', xy=(7.8, 9.8), xytext=(5.0, 7.03),
                arrowprops=dict(arrowstyle='->', color=C_EVT, lw=1.1,
                                connectionstyle='arc3,rad=0.2'))

    # satisfaction note for show
    ax.text(0.35, 5.8,
            'p=0.5: score += (G-1)/2 + (T-1)/19\np=0.5: satisfaction -= 1.0',
            ha='left', fontsize=7, color='#555', style='italic')

    # ── SERVICE STATIONS ──────────────────────────────────────────────────
    draw_box(ax, (6.5, 6.7), BW, BH, 'Service Complete\n(SVC_END)', C_SCHED)
    draw_box(ax, (6.5, 5.1), BW, BH, 'Queue Abandon\n(ABANDON)', '#C0392B')

    arrow(ax, (6.5, 7.97), (6.5, 7.03))
    ax.annotate('', xy=(6.5, 5.43), xytext=(6.5, 7.97),
                arrowprops=dict(arrowstyle='->', color='#C0392B',
                                lw=1.1, linestyle='dashed',
                                connectionstyle='arc3,rad=-0.5'))
    ax.text(7.65, 6.5, 'patience\nexpires', ha='left', fontsize=7,
            color='#C0392B', style='italic')

    ax.annotate('', xy=(8.2, 9.8), xytext=(6.5, 7.03),
                arrowprops=dict(arrowstyle='->', color=C_EVT, lw=1.1,
                                connectionstyle='arc3,rad=0.2'))
    # SVC_END triggers next-in-queue service
    arrow(ax, (7.65, 6.7), (8.5, 6.7), label='next in queue', color='#7F8C8D')
    ax.annotate('', xy=(6.5, 7.03), xytext=(8.5, 7.03),
                arrowprops=dict(arrowstyle='->', color='#7F8C8D', lw=1.0,
                                connectionstyle='arc3,rad=-0.4'))
    ax.annotate('', xy=(8.2, 9.8), xytext=(6.5, 5.43),
                arrowprops=dict(arrowstyle='->', color='#C0392B', lw=1.1,
                                connectionstyle='arc3,rad=0.35'))
    ax.text(5.2, 4.75, '↓ satisfaction penalty', ha='center', fontsize=7,
            color='#C0392B', style='italic')

    # ── DJ STAGE ─────────────────────────────────────────────────────────
    draw_box(ax, (11.0, 6.7), BW, BH, 'Admitted to DJ Stage\n(DJ_ADMIT)', C_SCHED)
    draw_box(ax, (11.0, 5.1), BW, BH, 'Leaves DJ Stage\n(DJ_LEAVE)', C_SCHED)
    draw_box(ax, (11.0, 3.5), BW*0.9, BH, 'Abandon Queue\n(ABANDON)', '#C0392B')

    arrow(ax, (11.0, 7.97), (11.0, 7.03))
    arrow(ax, (11.0, 6.37), (11.0, 5.43))
    ax.annotate('', xy=(11.0, 3.83), xytext=(11.0, 7.97),
                arrowprops=dict(arrowstyle='->', color='#C0392B', lw=1.1,
                                linestyle='dashed',
                                connectionstyle='arc3,rad=-0.5'))
    ax.annotate('', xy=(10.2, 9.8), xytext=(11.0, 5.43),
                arrowprops=dict(arrowstyle='->', color=C_EVT, lw=1.1,
                                connectionstyle='arc3,rad=-0.2'))
    # DJ_LEAVE triggers next-in-queue admission
    arrow(ax, (11.0, 5.43), (11.0, 7.03),
          label='admit next\nfrom queue', color='#7F8C8D')

    # ── FOOD PROCESS ──────────────────────────────────────────────────────
    draw_box(ax, (15.5, 6.7), BW, BH, 'Order Complete\n(FOOD_ORDER_END)', C_SCHED)
    draw_box(ax, (15.5, 5.1), BW, BH, 'Food Ready\n(FOOD_PREP_END)', C_SCHED)
    draw_box(ax, (15.5, 3.5), BW, BH, 'Eating Done\n(EAT_END)', C_SCHED)

    arrow(ax, (15.5, 7.97), (15.5, 7.03))
    arrow(ax, (15.5, 6.37), (15.5, 5.43))
    arrow(ax, (15.5, 4.77), (15.5, 3.83))
    ax.annotate('', xy=(10.2, 9.8), xytext=(15.5, 3.83),
                arrowprops=dict(arrowstyle='->', color=C_EVT, lw=1.1,
                                connectionstyle='arc3,rad=0.3'))
    ax.text(16.85, 5.1, '↓ sat 0.6\n(p=0.4)', ha='center', fontsize=7,
            color='#C0392B', style='italic')

    # ── BODY ART BREAK ────────────────────────────────────────────────────
    draw_box(ax, (3.5, 3.5), BW*0.85, BH*0.9, 'Artist Break\n(ART_BREAK_END)',
             '#117A65', fontsize=8)
    ax.text(3.5, 3.05, 'after every 10 drawings\n→ 15 min break', ha='center',
            fontsize=7, color='#117A65', style='italic')

    # ── DAY END ───────────────────────────────────────────────────────────
    draw_box(ax, (9.0, 6.7), 2.1, BH, 'End of Day\n(DAY_END)', '#7D3C98')

    # ── Bottom note ───────────────────────────────────────────────────────
    ax.text(9.0, 1.2,
            'Satisfaction score: updated after each show, photo, body art, food, and queue abandon\n'
            'Initial value = 5  |  Minimum = 0  |  Maximum = 10',
            ha='center', va='center', fontsize=8.5, color='#2C3E50',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#EBF5FB',
                      edgecolor='#2980B9', linewidth=1.2))

    plt.tight_layout()
    plt.savefig('event_diagram.png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print("Saved: event_diagram.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  DIAGRAM 2 – Event Handling: SECURITY_END (end of check-in)
# ═══════════════════════════════════════════════════════════════════════════════

def draw_checkin_end_diagram():
    fig, ax = plt.subplots(figsize=(10, 16))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 16)
    ax.axis('off')
    fig.patch.set_facecolor('#F8F9FA')

    fig.suptitle('Event Handling Diagram: End of Check-In (SECURITY_END)',
                 fontsize=13, fontweight='bold', color='#2C3E50', y=0.98)
    ax.set_title('Triggered when: ticket scan + security check both complete',
                 fontsize=9, color='#555', pad=4)

    BW, BH = 4.5, 0.7
    DW, DH = 4.5, 0.8

    C_START = '#1A5276'
    C_PROC  = '#2980B9'
    C_DEC   = '#E67E22'
    C_YES   = '#27AE60'
    C_NO    = '#C0392B'
    C_END_C = '#8E44AD'
    CX = 5.0

    def proc(y, txt, color=C_PROC, fs=9):
        draw_box(ax, (CX, y), BW, BH, txt, color, fontsize=fs)

    def dec(y, txt):
        draw_diamond(ax, (CX, y), DW, DH, txt, C_DEC, fontsize=8.5)

    def vert(y1, y2, color='#2C3E50'):
        ax.annotate('', xy=(CX, y2), xytext=(CX, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.4))

    # ── Step 1: Event fires ───────────────────────────────────────────────
    draw_box(ax, (CX, 15.2), BW, BH,
             'Event SECURITY_END fires\n(security check complete)', C_START)
    vert(14.85, 14.2)

    # ── Step 2: Release server ────────────────────────────────────────────
    proc(13.85, 'Release server[server_idx]\nat entry gate  (entry.end_service)')
    vert(13.5, 12.85)

    # ── Step 3: Decision ─────────────────────────────────────────────────
    dec(12.5, 'Entity waiting\nin entry queue?')

    # YES branch (right)
    ax.annotate('', xy=(8.5, 12.5), xytext=(7.25, 12.5),
                arrowprops=dict(arrowstyle='->', color=C_YES, lw=1.3))
    ax.text(7.87, 12.68, 'YES', fontsize=9, color=C_YES, fontweight='bold')

    draw_box(ax, (8.5, 11.5), 2.8, BH,
             'Dequeue next entity\nfrom front of queue', C_YES, fontsize=8.5)
    draw_box(ax, (8.5, 10.5), 2.8, BH,
             'Compute wait time:\nwait = clock – join_time', C_YES, fontsize=8.5)
    draw_box(ax, (8.5, 9.5), 2.8, BH,
             'Assign to freed server\nentry.start_service(next, idx)', C_YES, fontsize=8.5)
    draw_box(ax, (8.5, 8.5), 2.8, BH,
             'Schedule SCAN_END\n(delay = sample_ticket_scan())', C_YES, fontsize=8.5)

    ax.annotate('', xy=(8.5, 11.17), xytext=(8.5, 11.83),
                arrowprops=dict(arrowstyle='->', color=C_YES, lw=1.2))
    ax.annotate('', xy=(8.5, 10.17), xytext=(8.5, 10.83),
                arrowprops=dict(arrowstyle='->', color=C_YES, lw=1.2))
    ax.annotate('', xy=(8.5, 9.17), xytext=(8.5, 9.83),
                arrowprops=dict(arrowstyle='->', color=C_YES, lw=1.2))

    # NO branch (left)
    ax.annotate('', xy=(2.0, 12.5), xytext=(2.75, 12.5),
                arrowprops=dict(arrowstyle='->', color=C_NO, lw=1.3))
    ax.text(2.37, 12.68, 'NO', fontsize=9, color=C_NO, fontweight='bold')
    draw_box(ax, (1.5, 11.5), 2.2, BH,
             'Server remains\nidle', C_NO, fontsize=8.5)

    # Both paths converge to step 4
    ax.annotate('', xy=(5.0, 7.3), xytext=(8.5, 8.17),
                arrowprops=dict(arrowstyle='->', color='#7F8C8D', lw=1.2,
                                connectionstyle='arc3,rad=0.3'))
    ax.annotate('', xy=(5.0, 7.3), xytext=(1.5, 11.17),
                arrowprops=dict(arrowstyle='->', color='#7F8C8D', lw=1.2,
                                connectionstyle='arc3,rad=-0.3'))

    # ── Step 4: Build activity list ───────────────────────────────────────
    proc(6.95, 'Build entity activity list\n_build_entity_activities(entity)', C_PROC)

    ax.text(7.05, 6.35,
            'FriendsGroup:  [MainStage, SideStage, DJStage] + all stations (shortest queue)\n'
            'Couple:         alternating show / station  (no DJStage)\n'
            'Single:         MerchTent → 2×MainStage → 2×SideStage → 1×DJStage',
            ha='left', va='center', fontsize=7.5, color='#2C3E50',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#EBF5FB',
                      edgecolor='#2980B9', alpha=0.9))
    vert(6.6, 5.95)

    # ── Step 5: Schedule NEXT_ACTIVITY ───────────────────────────────────
    proc(5.6, 'Schedule NEXT_ACTIVITY event\n(delay = 0)', '#117A65')
    vert(5.25, 4.6)

    # ── Step 6: Record ticket revenue ────────────────────────────────────
    proc(4.25, 'Record ticket revenue\n500 ILS  /  700 ILS (ticket + lodging)', '#6C3483')
    vert(3.9, 3.25)

    # ── Step 7: Update statistics ─────────────────────────────────────────
    proc(2.9, 'Update simulation statistics\n(total entities, people, revenue)', '#17202A')
    vert(2.55, 1.9)

    # ── End ───────────────────────────────────────────────────────────────
    draw_box(ax, (CX, 1.55), BW, BH,
             'Event handling complete\nSimulation advances to next event', C_END_C)

    # ── Side note ─────────────────────────────────────────────────────────
    ax.text(0.25, 2.8,
            'Note:\nSCAN_END runs first\non same server,\nthen SECURITY_END\nfires immediately\nafter.',
            ha='left', va='center', fontsize=7.5, color='#555',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FDFEFE',
                      edgecolor='#AAB7B8', alpha=0.95))

    plt.tight_layout()
    plt.savefig('checkin_end_diagram.png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print("Saved: checkin_end_diagram.png")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    draw_event_diagram()
    draw_checkin_end_diagram()
    print("\nBoth diagrams saved. Insert into Colab with:")
    print("  from IPython.display import Image")
    print("  Image('event_diagram.png')")
    print("  Image('checkin_end_diagram.png')")
