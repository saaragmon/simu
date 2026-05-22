"""
Generate simulation diagrams for the Queuechella project.

Produces two PNG files:
  event_diagram.png        – תרשים אירועים (full event graph)
  checkin_end_diagram.png  – תרשים טיפול: אירוע סיום Check-In (SECURITY_END)
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
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
            wrap=True, multialignment='center')


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
                fontsize=7, color='#555555',
                bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                          edgecolor='none', alpha=0.85))


# ═══════════════════════════════════════════════════════════════════════════════
#  DIAGRAM 1 – תרשים אירועים
# ═══════════════════════════════════════════════════════════════════════════════

def draw_event_diagram():
    fig, ax = plt.subplots(figsize=(18, 13))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 13)
    ax.axis('off')
    fig.patch.set_facecolor('#F8F9FA')

    fig.suptitle('תרשים אירועים – סימולציית פסטיבל Queuechella',
                 fontsize=15, fontweight='bold', color='#2C3E50', y=0.97)

    # ── Node positions and labels ─────────────────────────────────────────
    BW, BH = 2.3, 0.65   # box width / height
    DW, DH = 2.4, 0.65   # diamond width / height

    # Colors
    C_EVT   = '#2980B9'   # regular event
    C_SCHED = '#27AE60'   # scheduled/timed event
    C_DEC   = '#E67E22'   # decision
    C_END   = '#8E44AD'   # terminal

    # --- Row 0: legend ---
    legend_items = [
        mpatches.Patch(facecolor=C_EVT,   label='אירוע רגיל'),
        mpatches.Patch(facecolor=C_SCHED, label='אירוע מתוזמן'),
        mpatches.Patch(facecolor=C_DEC,   label='החלטה / מסלול'),
        mpatches.Patch(facecolor=C_END,   label='אירוע סיום'),
    ]
    ax.legend(handles=legend_items, loc='upper left', fontsize=8.5,
              framealpha=0.9, ncol=4, bbox_to_anchor=(0.02, 0.97))

    # --- ARRIVAL & ENTRY ---
    draw_box(ax, (2.0, 11.5), BW, BH, 'הגעה\n(ARRIVE)', C_EVT)
    draw_box(ax, (5.5, 11.5), BW, BH, 'סיום סריקת כרטיס\n(SCAN_END)', C_SCHED)
    draw_box(ax, (9.0, 11.5), BW, BH, 'סיום בדיקה ביטחונית\n(SECURITY_END)', C_SCHED)

    # ARRIVE → SCAN_END
    arrow(ax, (3.15, 11.5), (4.35, 11.5), 'שרת פנוי')
    # ARRIVE → self (queue)
    arrow(ax, (2.0, 11.17), (2.0, 10.83),
          style='arc3,rad=-0.6', label='תור כניסה')
    # SCAN_END → SECURITY_END
    arrow(ax, (6.65, 11.5), (7.85, 11.5))

    # SECURITY_END → SCAN_END (next in queue)
    ax.annotate('', xy=(5.5, 11.83), xytext=(9.0, 11.83),
                arrowprops=dict(arrowstyle='->', color='#7F8C8D',
                                lw=1.1, connectionstyle='arc3,rad=-0.3'))
    ax.text(7.25, 12.3, 'הבא בתור', ha='center', fontsize=7.5, color='#7F8C8D',
            style='italic')

    # --- NEXT ACTIVITY ---
    draw_diamond(ax, (9.0, 9.8), DW, DH, 'פעילות הבאה\n(NEXT)', C_DEC)
    arrow(ax, (9.0, 11.17), (9.0, 10.12))

    # --- ACTIVITIES BRANCH ---
    # Show venues
    draw_box(ax, (2.0, 8.3), BW, BH, 'המתנה להופעה\n(SHOW_QUEUE)', '#2471A3')
    arrow(ax, (7.8, 9.8), (3.15, 8.3), style='arc3,rad=0.15', label='הופעה')

    # Service stations
    draw_box(ax, (6.5, 8.3), BW, BH, 'עמדת שירות\n(SERVICE_QUEUE)', '#2471A3')
    arrow(ax, (9.0, 9.47), (6.5, 8.63))

    # DJ Stage
    draw_box(ax, (11.0, 8.3), BW, BH, 'DJ Stage\n(DJ_QUEUE)', '#2471A3')
    arrow(ax, (10.2, 9.8), (11.0, 8.63), style='arc3,rad=-0.1', label='אלקטרוני')

    # Lunch
    draw_box(ax, (15.5, 8.3), BW, BH, 'ארוחת צהריים\n(LUNCH)', '#2471A3')
    arrow(ax, (10.2, 9.8), (14.35, 8.3), style='arc3,rad=-0.2', label='13:00–15:00')

    # Leave (no more activities)
    draw_box(ax, (9.0, 8.3), 2.0, BH, 'עזיבה\n(ENTITY_LEAVE)', C_END)
    # dashed arrow for "no more activities"
    ax.annotate('', xy=(9.0, 8.63), xytext=(9.0, 9.47),
                arrowprops=dict(arrowstyle='->', color=C_END, lw=1.2,
                                linestyle='dashed'))
    ax.text(9.5, 9.05, 'אין פעילויות', ha='left', fontsize=7, color=C_END, style='italic')

    # --- SHOW PROCESSING ---
    draw_box(ax, (2.0, 6.7), BW, BH, 'תחילת הופעה\n(SHOW_START)', C_SCHED)
    draw_box(ax, (2.0, 5.1), BW, BH, 'סיום הופעה\n(SHOW_END)', C_SCHED)
    # early leave
    draw_box(ax, (5.0, 6.7), BW*0.9, BH, 'יציאה מוקדמת\n(EARLY_LEAVE)', '#1A5276')

    arrow(ax, (2.0, 7.97), (2.0, 7.03))         # SHOW_QUEUE → SHOW_START
    arrow(ax, (2.0, 6.37), (2.0, 5.43))          # SHOW_START → SHOW_END
    # SHOW_START → EARLY_LEAVE (back-10, p=0.5, at t+15min)
    arrow(ax, (3.15, 6.7), (3.95, 6.7), label='אחורי 10\np=0.5, t+15')
    # SHOW_END → NEXT
    ax.annotate('', xy=(7.8, 9.8), xytext=(2.0, 5.43),
                arrowprops=dict(arrowstyle='->', color='#2980B9',
                                lw=1.1, connectionstyle='arc3,rad=0.3'))
    # EARLY_LEAVE → NEXT
    ax.annotate('', xy=(7.8, 9.8), xytext=(5.0, 7.03),
                arrowprops=dict(arrowstyle='->', color='#2980B9',
                                lw=1.1, connectionstyle='arc3,rad=0.2'))

    # --- SERVICE STATIONS PROCESSING ---
    draw_box(ax, (6.5, 6.7), BW, BH, 'סיום שירות\n(SVC_END)', C_SCHED)
    draw_box(ax, (6.5, 5.1), BW, BH, 'נטישת תור\n(ABANDON)', '#C0392B')

    arrow(ax, (6.5, 7.97), (6.5, 7.03))          # SERVICE_QUEUE → SVC_END
    # patience timeout → ABANDON
    ax.annotate('', xy=(6.5, 5.43), xytext=(6.5, 7.97),
                arrowprops=dict(arrowstyle='->', color='#C0392B',
                                lw=1.1, linestyle='dashed',
                                connectionstyle='arc3,rad=-0.5'))
    ax.text(7.6, 6.5, f'patience\nexpires', ha='left', fontsize=7,
            color='#C0392B', style='italic')

    # SVC_END → NEXT
    ax.annotate('', xy=(8.2, 9.8), xytext=(6.5, 7.03),
                arrowprops=dict(arrowstyle='->', color='#2980B9', lw=1.1,
                                connectionstyle='arc3,rad=0.2'))
    # SVC_END → SVC_END (next in queue)
    arrow(ax, (7.65, 6.7), (8.5, 6.7),
          label='הבא בתור', color='#7F8C8D')
    ax.annotate('', xy=(6.5, 7.03), xytext=(8.5, 7.03),
                arrowprops=dict(arrowstyle='->', color='#7F8C8D', lw=1.0,
                                connectionstyle='arc3,rad=-0.4'))
    # ABANDON → NEXT
    ax.annotate('', xy=(8.2, 9.8), xytext=(6.5, 5.43),
                arrowprops=dict(arrowstyle='->', color='#C0392B', lw=1.1,
                                connectionstyle='arc3,rad=0.35'))

    # satisfaction penalty note
    ax.text(5.2, 4.75, '↓ satisfaction', ha='center', fontsize=7,
            color='#C0392B', style='italic')

    # --- DJ STAGE ---
    draw_box(ax, (11.0, 6.7), BW, BH, 'כניסה ל-DJ Stage\n(DJ_ADMIT)', C_SCHED)
    draw_box(ax, (11.0, 5.1), BW, BH, 'יציאה מ-DJ Stage\n(DJ_LEAVE)', C_SCHED)
    draw_box(ax, (11.0, 3.5), BW*0.9, BH, 'נטישה (ABANDON)\nסבלנות נגמרה', '#C0392B')

    arrow(ax, (11.0, 7.97), (11.0, 7.03))
    arrow(ax, (11.0, 6.37), (11.0, 5.43))
    # abandon from DJ queue
    ax.annotate('', xy=(11.0, 3.83), xytext=(11.0, 7.97),
                arrowprops=dict(arrowstyle='->', color='#C0392B', lw=1.1,
                                linestyle='dashed',
                                connectionstyle='arc3,rad=-0.5'))
    # DJ_LEAVE → NEXT
    ax.annotate('', xy=(10.2, 9.8), xytext=(11.0, 5.43),
                arrowprops=dict(arrowstyle='->', color='#2980B9', lw=1.1,
                                connectionstyle='arc3,rad=-0.2'))
    # try admit queued after DJ_LEAVE
    arrow(ax, (11.0, 5.43), (11.0, 7.03),
          label='הבא בתור\nמתקבל', color='#7F8C8D')

    # --- FOOD PROCESS ---
    draw_box(ax, (15.5, 6.7), BW, BH, 'סיום הזמנה\n(FOOD_ORDER_END)', C_SCHED)
    draw_box(ax, (15.5, 5.1), BW, BH, 'אוכל מוכן\n(FOOD_PREP_END)', C_SCHED)
    draw_box(ax, (15.5, 3.5), BW, BH, 'סיום אכילה\n(EAT_END)', C_SCHED)

    arrow(ax, (15.5, 7.97), (15.5, 7.03))
    arrow(ax, (15.5, 6.37), (15.5, 5.43))
    arrow(ax, (15.5, 4.77), (15.5, 3.83))
    # EAT_END → NEXT
    ax.annotate('', xy=(10.2, 9.8), xytext=(15.5, 3.83),
                arrowprops=dict(arrowstyle='->', color='#2980B9', lw=1.1,
                                connectionstyle='arc3,rad=0.3'))
    # bad meal note
    ax.text(16.85, 5.1, '↓ sat 0.6\n(p=0.4)', ha='center', fontsize=7,
            color='#C0392B', style='italic')

    # --- ART BREAK ---
    draw_box(ax, (3.5, 3.5), BW*0.85, BH*0.9, 'הפסקת אמן\n(ART_BREAK_END)',
             '#117A65', fontsize=8)
    ax.text(3.5, 3.05, 'כל 10 ציורים\n→ 15 דק הפסקה', ha='center',
            fontsize=7, color='#117A65', style='italic')

    # --- DAY END ---
    draw_box(ax, (9.0, 6.7), 2.0, BH, 'סוף יום\n(DAY_END)', '#7D3C98')

    # --- Satisfaction note (bottom) ---
    ax.text(9.0, 1.2,
            'מדד שביעות רצון: מתעדכן בסיום כל הופעה, צילום, ציור פנים, אוכל, ונטישת תור\n'
            'ערך התחלתי=5 | מינימום=0 | מקסימום=10',
            ha='center', va='center', fontsize=8.5, color='#2C3E50',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#EBF5FB',
                      edgecolor='#2980B9', linewidth=1.2))

    plt.tight_layout()
    plt.savefig('event_diagram.png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print("✓ Saved: event_diagram.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  DIAGRAM 2 – תרשים טיפול: אירוע סיום Check-In (SECURITY_END)
# ═══════════════════════════════════════════════════════════════════════════════

def draw_checkin_end_diagram():
    fig, ax = plt.subplots(figsize=(10, 16))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 16)
    ax.axis('off')
    fig.patch.set_facecolor('#F8F9FA')

    fig.suptitle('תרשים טיפול: אירוע סיום Check-In (SECURITY_END)',
                 fontsize=13, fontweight='bold', color='#2C3E50', y=0.98)
    ax.set_title('מתרחש כאשר: סריקת כרטיס + בדיקה ביטחונית הסתיימו',
                 fontsize=9, color='#555', pad=4)

    BW, BH = 4.5, 0.7
    DW, DH = 4.5, 0.8

    # Color palette
    C_START = '#1A5276'
    C_PROC  = '#2980B9'
    C_DEC   = '#E67E22'
    C_YES   = '#27AE60'
    C_NO    = '#C0392B'
    C_END_A = '#8E44AD'
    CX = 5.0   # center x

    def proc(y, txt, color=C_PROC, fs=9):
        draw_box(ax, (CX, y), BW, BH, txt, color, fontsize=fs)

    def dec(y, txt):
        draw_diamond(ax, (CX, y), DW, DH, txt, C_DEC, fontsize=8.5)

    def vert(y1, y2, color='#2C3E50'):
        ax.annotate('', xy=(CX, y2), xytext=(CX, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.4))

    def side_arrow(start, end, label, color, label_side='right'):
        ax.annotate('', xy=end, xytext=start,
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.3))
        mx = (start[0]+end[0])/2
        my = (start[1]+end[1])/2
        offset = 0.25 if label_side == 'right' else -0.25
        ax.text(mx + offset, my, label, ha='center', va='center',
                fontsize=8, color=color, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                          edgecolor='none', alpha=0.9))

    # ── Step 1: Event trigger ──────────────────────────────────────────────
    draw_box(ax, (CX, 15.2), BW, BH,
             'אירוע: SECURITY_END מופעל\n(בדיקה ביטחונית הסתיימה)', C_START)

    vert(14.85, 14.2)

    # ── Step 2: Free server ────────────────────────────────────────────────
    proc(13.85, 'שחרור שרת[server_idx]\nבשערי הכניסה (entry.end_service)')
    vert(13.5, 12.85)

    # ── Step 3: Decision – is queue non-empty? ─────────────────────────────
    dec(12.5, 'האם יש\nישויות בתור הכניסה?')

    # YES path (right side)
    # Arrow right from diamond
    ax.annotate('', xy=(8.5, 12.5), xytext=(7.25, 12.5),
                arrowprops=dict(arrowstyle='->', color=C_YES, lw=1.3))
    ax.text(7.87, 12.65, 'כן', fontsize=9, color=C_YES, fontweight='bold')

    # YES box
    draw_box(ax, (8.5, 11.5), 2.8, BH,
             'הוצא ישות\nמתחילת התור', C_YES, fontsize=8.5)
    draw_box(ax, (8.5, 10.5), 2.8, BH,
             'חשב זמן המתנה:\nwait = clock – join_time', C_YES, fontsize=8.5)
    draw_box(ax, (8.5, 9.5), 2.8, BH,
             'הצמד לשרת שהתפנה\nentry.start_service(next, idx)', C_YES, fontsize=8.5)
    draw_box(ax, (8.5, 8.5), 2.8, BH,
             'תזמן SCAN_END\n(+ sample_ticket_scan())', C_YES, fontsize=8.5)

    ax.annotate('', xy=(8.5, 11.17), xytext=(8.5, 11.83),
                arrowprops=dict(arrowstyle='->', color=C_YES, lw=1.2))
    ax.annotate('', xy=(8.5, 10.17), xytext=(8.5, 10.83),
                arrowprops=dict(arrowstyle='->', color=C_YES, lw=1.2))
    ax.annotate('', xy=(8.5, 9.17), xytext=(8.5, 9.83),
                arrowprops=dict(arrowstyle='->', color=C_YES, lw=1.2))

    # NO path (left side)
    ax.annotate('', xy=(2.75, 12.5), xytext=(2.75, 12.5),)  # placeholder
    ax.annotate('', xy=(2.0, 12.5), xytext=(2.75, 12.5),
                arrowprops=dict(arrowstyle='->', color=C_NO, lw=1.3))
    ax.text(2.37, 12.65, 'לא', fontsize=9, color=C_NO, fontweight='bold')
    draw_box(ax, (1.5, 11.5), 2.2, BH,
             'שרת נשאר\nבמצב פנוי', C_NO, fontsize=8.5)

    # Both paths merge at step 4
    # YES path merges down
    ax.annotate('', xy=(5.0, 7.3), xytext=(8.5, 8.17),
                arrowprops=dict(arrowstyle='->', color='#7F8C8D', lw=1.2,
                                connectionstyle='arc3,rad=0.3'))
    # NO path merges down
    ax.annotate('', xy=(5.0, 7.3), xytext=(1.5, 11.17),
                arrowprops=dict(arrowstyle='->', color='#7F8C8D', lw=1.2,
                                connectionstyle='arc3,rad=-0.3'))

    # ── Step 4: Build activity list ───────────────────────────────────────
    proc(6.95, 'בנה רשימת פעילויות לישות\n_build_entity_activities(entity)', C_PROC)

    ax.text(7.0, 6.4,
            'FriendsGroup: [MainStage, SideStage, DJStage] + כל העמדות (לפי תור קצר)\n'
            'Couple: הופעה/עמדה לסירוגין (ללא DJ)\n'
            'Single: MerchTent → 2×Main → 2×Side → 1×DJ',
            ha='left', va='center', fontsize=7.5, color='#2C3E50',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#EBF5FB',
                      edgecolor='#2980B9', alpha=0.9))

    vert(6.6, 5.95)

    # ── Step 5: Schedule NEXT ─────────────────────────────────────────────
    proc(5.6, 'תזמן אירוע NEXT_ACTIVITY\n(delay = 0)', '#117A65')
    vert(5.25, 4.6)

    # ── Step 6: Update satisfaction (ticket purchase) ─────────────────────
    proc(4.25, 'עדכן הכנסות:\nכרטיס 500₪ / כרטיס+לינה 700₪', '#6C3483')
    vert(3.9, 3.25)

    # ── Step 7: Record stats ──────────────────────────────────────────────
    proc(2.9, 'עדכן סטטיסטיקות:\nסה"כ ישויות, אנשים, הכנסות', '#17202A')
    vert(2.55, 1.9)

    # ── End ───────────────────────────────────────────────────────────────
    draw_box(ax, (CX, 1.55), BW, BH,
             'טיפול באירוע הסתיים\nהמערכת ממשיכה לאירוע הבא בתור', C_END_A)

    # ── Side note ─────────────────────────────────────────────────────────
    ax.text(0.3, 2.5,
            'הערה:\nאחרי SCAN_END\nמגיע SECURITY_END.\nשניהם על אותו שרת.',
            ha='left', va='center', fontsize=7.5, color='#555',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FDFEFE',
                      edgecolor='#AAB7B8', alpha=0.95))

    plt.tight_layout()
    plt.savefig('checkin_end_diagram.png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print("✓ Saved: checkin_end_diagram.png")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    draw_event_diagram()
    draw_checkin_end_diagram()
    print("\nBoth diagrams saved. Insert into Colab with:")
    print("  from IPython.display import Image")
    print("  Image('event_diagram.png')")
    print("  Image('checkin_end_diagram.png')")
