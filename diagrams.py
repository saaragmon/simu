"""
Generate simulation diagrams for the Queuechella project – blue theme.

Produces two PNG files:
  event_diagram.png        – Event Diagram (full event graph)
  checkin_end_diagram.png  – Event Handling Diagram: SECURITY_END
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

# ── Blue palette ──────────────────────────────────────────────────────────────
B_DARKEST = '#0D2845'   # very dark navy  – borders, arrows, titles
B_DARK    = '#1A4A7A'   # dark blue       – start / end nodes
B_MID     = '#2166AC'   # medium blue     – process nodes
B_BRIGHT  = '#3A85C4'   # bright blue     – decision diamonds
B_LIGHT   = '#5B9BD5'   # light blue      – queue / waiting nodes
B_PALE    = '#7FB3D9'   # pale blue       – scheduled / timed nodes
B_TINT    = '#D6EAF8'   # very light blue – note backgrounds
B_BG      = '#EBF5FB'   # near-white blue – figure background


# ── Drawing helpers ───────────────────────────────────────────────────────────

def draw_box(ax, xy, w, h, label,
             color=B_MID, text_color='white',
             fontsize=9, style='round,pad=0.12', zorder=3):
    x, y = xy
    ax.add_patch(FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle=style,
        facecolor=color, edgecolor=B_DARKEST,
        linewidth=1.5, zorder=zorder))
    ax.text(x, y, label, ha='center', va='center',
            fontsize=fontsize, color=text_color,
            fontweight='bold', zorder=zorder + 1,
            multialignment='center')


def draw_diamond(ax, xy, w, h, label,
                 color=B_BRIGHT, text_color='white',
                 fontsize=8.5, zorder=3):
    x, y = xy
    dx, dy = w / 2, h / 2
    ax.add_patch(plt.Polygon(
        [(x, y+dy), (x+dx, y), (x, y-dy), (x-dx, y)],
        facecolor=color, edgecolor=B_DARKEST,
        linewidth=1.5, zorder=zorder))
    ax.text(x, y, label, ha='center', va='center',
            fontsize=fontsize, color=text_color,
            fontweight='bold', zorder=zorder + 1,
            multialignment='center')


def arr(ax, start, end, label='', lw=1.4,
        style='arc3,rad=0', color=B_DARKEST, zorder=2):
    ax.annotate('', xy=end, xytext=start,
                arrowprops=dict(arrowstyle='->', color=color,
                                lw=lw, connectionstyle=style),
                zorder=zorder)
    if label:
        mx, my = (start[0]+end[0])/2, (start[1]+end[1])/2
        ax.text(mx, my, label, ha='center', va='center',
                fontsize=7, color=B_DARKEST,
                bbox=dict(boxstyle='round,pad=0.15',
                          facecolor=B_TINT, edgecolor='none', alpha=0.9))


def note_box(ax, x, y, text, fontsize=7):
    ax.text(x, y, text, ha='left', va='center',
            fontsize=fontsize, color=B_DARK, style='italic',
            bbox=dict(boxstyle='round,pad=0.25',
                      facecolor=B_TINT, edgecolor=B_LIGHT,
                      linewidth=0.8, alpha=0.95))


# ═══════════════════════════════════════════════════════════════════════════════
#  DIAGRAM 1 – Event Diagram
# ═══════════════════════════════════════════════════════════════════════════════

def draw_event_diagram():
    fig, ax = plt.subplots(figsize=(18, 13))
    ax.set_xlim(0, 18);  ax.set_ylim(0, 13);  ax.axis('off')
    fig.patch.set_facecolor(B_BG);  ax.set_facecolor(B_BG)

    fig.suptitle('Event Diagram – Queuechella Festival Simulation',
                 fontsize=15, fontweight='bold', color=B_DARKEST, y=0.97)

    BW, BH = 2.3, 0.65

    legend_items = [
        mpatches.Patch(facecolor=B_DARK,   edgecolor=B_DARKEST, label='Start / End event'),
        mpatches.Patch(facecolor=B_MID,    edgecolor=B_DARKEST, label='Process event'),
        mpatches.Patch(facecolor=B_BRIGHT, edgecolor=B_DARKEST, label='Routing decision'),
        mpatches.Patch(facecolor=B_LIGHT,  edgecolor=B_DARKEST, label='Queue / waiting'),
        mpatches.Patch(facecolor=B_PALE,   edgecolor=B_DARKEST, label='Scheduled / timed'),
    ]
    ax.legend(handles=legend_items, loc='upper left', fontsize=8.5,
              framealpha=0.9, ncol=5, bbox_to_anchor=(0.01, 0.97),
              facecolor=B_TINT, edgecolor=B_LIGHT)

    # ── ENTRY CHAIN ───────────────────────────────────────────────────────
    draw_box(ax, (2.0, 11.5), BW, BH, 'Entity Arrival\n(ARRIVE)',                B_DARK)
    draw_box(ax, (5.5, 11.5), BW, BH, 'Ticket Scan Complete\n(SCAN_END)',        B_PALE)
    draw_box(ax, (9.0, 11.5), BW, BH, 'Security Check Complete\n(SECURITY_END)', B_PALE)

    arr(ax, (3.15, 11.5),  (4.35, 11.5),  'server free')
    arr(ax, (2.0,  11.17), (2.0,  10.83), style='arc3,rad=-0.6', label='join queue')
    arr(ax, (6.65, 11.5),  (7.85, 11.5))

    ax.annotate('', xy=(5.5, 11.83), xytext=(9.0, 11.83),
                arrowprops=dict(arrowstyle='->', color=B_PALE,
                                lw=1.2, connectionstyle='arc3,rad=-0.3'))
    ax.text(7.25, 12.3, 'next in queue', ha='center',
            fontsize=7.5, color=B_DARK, style='italic')

    # ── ROUTING DIAMOND ───────────────────────────────────────────────────
    draw_diamond(ax, (9.0, 9.8), 2.4, 0.65, 'Next Activity\n(NEXT)', B_BRIGHT)
    arr(ax, (9.0, 11.17), (9.0, 10.12))

    # ── FOUR BRANCHES ─────────────────────────────────────────────────────
    draw_box(ax, (2.0,  8.3), BW, BH,  'Wait for Show\n(SHOW_QUEUE)',      B_LIGHT)
    draw_box(ax, (6.5,  8.3), BW, BH,  'Service Station\n(SERVICE_QUEUE)', B_LIGHT)
    draw_box(ax, (11.0, 8.3), BW, BH,  'DJ Stage Queue\n(DJ_QUEUE)',       B_LIGHT)
    draw_box(ax, (15.5, 8.3), BW, BH,  'Lunch Break\n(LUNCH)',             B_LIGHT)
    draw_box(ax, (9.0,  8.3), 2.1, BH, 'Entity Leaves\n(ENTITY_LEAVE)',    B_DARK)

    arr(ax, (7.8,  9.8),  (3.15, 8.3),  style='arc3,rad=0.15',  label='show activity')
    arr(ax, (9.0,  9.47), (6.5,  8.63))
    arr(ax, (10.2, 9.8),  (11.0, 8.63), style='arc3,rad=-0.1',  label='electronic')
    arr(ax, (10.2, 9.8),  (14.35,8.3),  style='arc3,rad=-0.2',  label='13:00–15:00  p=0.7')

    ax.annotate('', xy=(9.0, 8.63), xytext=(9.0, 9.47),
                arrowprops=dict(arrowstyle='->', color=B_DARK, lw=1.3,
                                linestyle='dashed'))
    ax.text(9.55, 9.05, 'no more activities',
            ha='left', fontsize=7, color=B_DARK, style='italic')

    # ── SHOW PATH ─────────────────────────────────────────────────────────
    draw_box(ax, (2.0, 6.7), BW,    BH, 'Show Starts\n(SHOW_START)', B_PALE)
    draw_box(ax, (2.0, 5.1), BW,    BH, 'Show Ends\n(SHOW_END)',     B_PALE)
    draw_box(ax, (5.0, 6.7), BW*.9, BH, 'Early Exit\n(EARLY_LEAVE)', B_MID)

    arr(ax, (2.0, 7.97), (2.0, 7.03))
    arr(ax, (2.0, 6.37), (2.0, 5.43))
    arr(ax, (3.15, 6.7), (3.95, 6.7), label='back-10\np=0.5, t+15')

    ax.annotate('', xy=(7.8, 9.8), xytext=(2.0, 5.43),
                arrowprops=dict(arrowstyle='->', color=B_MID, lw=1.2,
                                connectionstyle='arc3,rad=0.3'))
    ax.annotate('', xy=(7.8, 9.8), xytext=(5.0, 7.03),
                arrowprops=dict(arrowstyle='->', color=B_MID, lw=1.2,
                                connectionstyle='arc3,rad=0.2'))
    note_box(ax, 0.2, 5.8,
             'p=0.5: score += (G-1)/2 + (T-1)/19\n'
             'p=0.5: satisfaction -= 1.0')

    # ── SERVICE PATH ──────────────────────────────────────────────────────
    draw_box(ax, (6.5, 6.7), BW, BH, 'Service Complete\n(SVC_END)', B_PALE)
    draw_box(ax, (6.5, 5.1), BW, BH, 'Queue Abandon\n(ABANDON)',    B_MID)

    arr(ax, (6.5, 7.97), (6.5, 7.03))
    ax.annotate('', xy=(6.5, 5.43), xytext=(6.5, 7.97),
                arrowprops=dict(arrowstyle='->', color=B_PALE, lw=1.1,
                                linestyle='dashed',
                                connectionstyle='arc3,rad=-0.5'))
    ax.text(7.65, 6.5, 'patience expires',
            ha='left', fontsize=7, color=B_DARK, style='italic')

    ax.annotate('', xy=(8.2, 9.8), xytext=(6.5, 7.03),
                arrowprops=dict(arrowstyle='->', color=B_MID, lw=1.2,
                                connectionstyle='arc3,rad=0.2'))
    arr(ax, (7.65, 6.7), (8.5, 6.7), label='next in queue', color=B_PALE)
    ax.annotate('', xy=(6.5, 7.03), xytext=(8.5, 7.03),
                arrowprops=dict(arrowstyle='->', color=B_PALE, lw=1.0,
                                connectionstyle='arc3,rad=-0.4'))
    ax.annotate('', xy=(8.2, 9.8), xytext=(6.5, 5.43),
                arrowprops=dict(arrowstyle='->', color=B_MID, lw=1.2,
                                connectionstyle='arc3,rad=0.35'))
    ax.text(5.1, 4.75, '↓ satisfaction penalty',
            ha='center', fontsize=7, color=B_DARK, style='italic')

    # ── DJ PATH ───────────────────────────────────────────────────────────
    draw_box(ax, (11.0, 6.7), BW,    BH, 'Admitted to DJ Stage\n(DJ_ADMIT)', B_PALE)
    draw_box(ax, (11.0, 5.1), BW,    BH, 'Leaves DJ Stage\n(DJ_LEAVE)',      B_PALE)
    draw_box(ax, (11.0, 3.5), BW*.9, BH, 'Abandon Queue\n(ABANDON)',         B_MID)

    arr(ax, (11.0, 7.97), (11.0, 7.03))
    arr(ax, (11.0, 6.37), (11.0, 5.43))
    ax.annotate('', xy=(11.0, 3.83), xytext=(11.0, 7.97),
                arrowprops=dict(arrowstyle='->', color=B_PALE, lw=1.1,
                                linestyle='dashed',
                                connectionstyle='arc3,rad=-0.5'))
    ax.annotate('', xy=(10.2, 9.8), xytext=(11.0, 5.43),
                arrowprops=dict(arrowstyle='->', color=B_MID, lw=1.2,
                                connectionstyle='arc3,rad=-0.2'))
    arr(ax, (11.0, 5.43), (11.0, 7.03),
        label='admit next\nfrom queue', color=B_PALE)

    # ── FOOD PATH ─────────────────────────────────────────────────────────
    draw_box(ax, (15.5, 6.7), BW, BH, 'Order Complete\n(FOOD_ORDER_END)', B_PALE)
    draw_box(ax, (15.5, 5.1), BW, BH, 'Food Ready\n(FOOD_PREP_END)',      B_PALE)
    draw_box(ax, (15.5, 3.5), BW, BH, 'Eating Done\n(EAT_END)',           B_PALE)

    arr(ax, (15.5, 7.97), (15.5, 7.03))
    arr(ax, (15.5, 6.37), (15.5, 5.43))
    arr(ax, (15.5, 4.77), (15.5, 3.83))
    ax.annotate('', xy=(10.2, 9.8), xytext=(15.5, 3.83),
                arrowprops=dict(arrowstyle='->', color=B_MID, lw=1.2,
                                connectionstyle='arc3,rad=0.3'))
    ax.text(16.85, 5.1, '↓ sat 0.6\n(p=0.4)',
            ha='center', fontsize=7, color=B_DARK, style='italic')

    # ── MISC ──────────────────────────────────────────────────────────────
    draw_box(ax, (3.5, 3.5), BW*.85, BH*.9,
             'Artist Break\n(ART_BREAK_END)', B_MID, fontsize=8)
    ax.text(3.5, 3.05, 'after 10 drawings → 15 min',
            ha='center', fontsize=7, color=B_DARK, style='italic')

    draw_box(ax, (9.0, 6.7), 2.1, BH, 'End of Day\n(DAY_END)', B_DARK)

    ax.text(9.0, 1.2,
            'Satisfaction updated after: each show · photo · body art · food · queue abandon'
            '     |     Initial = 5  ·  Min = 0  ·  Max = 10',
            ha='center', va='center', fontsize=8.5, color=B_DARKEST,
            bbox=dict(boxstyle='round,pad=0.4', facecolor=B_TINT,
                      edgecolor=B_LIGHT, linewidth=1.3))

    plt.tight_layout()
    plt.savefig('event_diagram.png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print('Saved: event_diagram.png')


# ═══════════════════════════════════════════════════════════════════════════════
#  DIAGRAM 2 – Event Handling: SECURITY_END
# ═══════════════════════════════════════════════════════════════════════════════

def draw_checkin_end_diagram():
    fig, ax = plt.subplots(figsize=(10, 16))
    ax.set_xlim(0, 10);  ax.set_ylim(0, 16);  ax.axis('off')
    fig.patch.set_facecolor(B_BG);  ax.set_facecolor(B_BG)

    fig.suptitle('Event Handling: End of Check-In  (SECURITY_END)',
                 fontsize=13, fontweight='bold', color=B_DARKEST, y=0.98)
    ax.set_title('Triggered when: ticket scan + security check both complete',
                 fontsize=9, color=B_DARK, pad=4)

    BW, BH = 4.5, 0.7
    CX = 5.0

    def proc(y, txt, col=B_MID, fs=9):
        draw_box(ax, (CX, y), BW, BH, txt, col, fontsize=fs)

    def vert(y1, y2):
        ax.annotate('', xy=(CX, y2), xytext=(CX, y1),
                    arrowprops=dict(arrowstyle='->', color=B_DARKEST, lw=1.5))

    # Step 1
    draw_box(ax, (CX, 15.2), BW, BH,
             'Event SECURITY_END fires\n(security check complete)', B_DARK)
    vert(14.85, 14.2)

    # Step 2
    proc(13.85, 'Release server[server_idx]\nat EntryGate  (entry.end_service)')
    vert(13.5, 12.85)

    # Step 3: Decision
    draw_diamond(ax, (CX, 12.5), 4.5, 0.8,
                 'Entity waiting\nin entry queue?', B_BRIGHT)

    # YES branch
    ax.annotate('', xy=(8.5, 12.5), xytext=(7.25, 12.5),
                arrowprops=dict(arrowstyle='->', color=B_MID, lw=1.4))
    ax.text(7.87, 12.68, 'YES', fontsize=9, color=B_DARK, fontweight='bold')

    yes_steps = [
        (11.5, 'Dequeue next entity\nfrom front of queue'),
        (10.5, 'Compute wait time:\nwait = clock – join_time'),
        (9.5,  'Assign to freed server\nentry.start_service(next, idx)'),
        (8.5,  'Schedule SCAN_END\n(delay = sample_ticket_scan())'),
    ]
    for yi, txt in yes_steps:
        draw_box(ax, (8.5, yi), 2.8, BH, txt, B_MID, fontsize=8.5)
    for y_top, y_bot in [(11.83, 11.17), (10.83, 10.17), (9.83, 9.17)]:
        ax.annotate('', xy=(8.5, y_bot), xytext=(8.5, y_top),
                    arrowprops=dict(arrowstyle='->', color=B_MID, lw=1.3))

    # NO branch
    ax.annotate('', xy=(2.0, 12.5), xytext=(2.75, 12.5),
                arrowprops=dict(arrowstyle='->', color=B_LIGHT, lw=1.4))
    ax.text(2.37, 12.68, 'NO', fontsize=9, color=B_DARK, fontweight='bold')
    draw_box(ax, (1.5, 11.5), 2.2, BH,
             'Server remains\nidle', B_LIGHT, fontsize=8.5)

    # Merge
    ax.annotate('', xy=(CX, 7.3), xytext=(8.5, 8.17),
                arrowprops=dict(arrowstyle='->', color=B_PALE, lw=1.3,
                                connectionstyle='arc3,rad=0.3'))
    ax.annotate('', xy=(CX, 7.3), xytext=(1.5, 11.17),
                arrowprops=dict(arrowstyle='->', color=B_PALE, lw=1.3,
                                connectionstyle='arc3,rad=-0.3'))

    # Step 4
    proc(6.95, 'Build entity activity list\n_build_entity_activities(entity)')
    ax.text(7.05, 6.35,
            'FriendsGroup:  [MainStage, SideStage, DJStage] + all stations (shortest queue)\n'
            'Couple:          show / station alternating  (no DJStage)\n'
            'Single:          MerchTent → 2×MainStage → 2×SideStage → 1×DJStage',
            ha='left', va='center', fontsize=7.5, color=B_DARKEST,
            bbox=dict(boxstyle='round,pad=0.3', facecolor=B_TINT,
                      edgecolor=B_LIGHT, alpha=0.95))
    vert(6.6, 5.95)

    # Step 5
    proc(5.6, 'Schedule NEXT_ACTIVITY event\n(delay = 0)', B_BRIGHT)
    vert(5.25, 4.6)

    # Step 6
    proc(4.25, 'Record ticket revenue\n500 ILS  /  700 ILS (ticket + lodging)')
    vert(3.9, 3.25)

    # Step 7
    proc(2.9, 'Update simulation statistics\n(entities, people, revenue)')
    vert(2.55, 1.9)

    # End
    draw_box(ax, (CX, 1.55), BW, BH,
             'Event handling complete\nSimulation advances to next event', B_DARK)

    # Side note
    note_box(ax, 0.2, 2.8,
             'Note:\nSCAN_END fires first\non same server,\nthen SECURITY_END\nfollows immediately.')

    plt.tight_layout()
    plt.savefig('checkin_end_diagram.png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print('Saved: checkin_end_diagram.png')


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    draw_event_diagram()
    draw_checkin_end_diagram()
    print('\nInsert into Colab with:')
    print('  from IPython.display import Image')
    print('  Image("event_diagram.png")')
    print('  Image("checkin_end_diagram.png")')
