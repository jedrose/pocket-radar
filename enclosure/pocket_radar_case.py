"""
Pocket Radar handheld case, v0.1 (parametric, CadQuery)

Layout: "radar gun" style. The radar faces straight forward through a 1.5 mm
radome plate, the 1.12" OLED sits on a 35 deg slanted top facing your eyes,
and a raked pistol grip holds an 18650 cell plus a charge/boost board.
The shell is a left/right clamshell split at X = 0, joined with M3 screws
into heat-set inserts.

Axes: X = left/right, Y = forward (radar boresight), Z = up.
Front face of the case is at Y = 0. All units mm.

Run:  pip install cadquery
      python pocket_radar_case.py   -> fit check, then STEP + STL files in ./out

Status: v0.1. Board dimensions come from datasheets plus estimates; the
values marked MEASURE below still need to be checked with calipers.
"""
import math
import os
import cadquery as cq

# ---------------------------------------------------------------------------
# PARAMETERS  (anything marked MEASURE: check with calipers on your hardware)
# ---------------------------------------------------------------------------
WALL = 2.4            # general wall thickness
CLR = 0.4             # clearance around boards

# --- MR60BHA2 kit (radar module on carrier, XIAO ESP32C6 plugged in behind)
KIT_W = 30.0          # carrier board width  (Seeed spec 30 x 48)
KIT_H = 48.0          # carrier board height
KIT_D = 18.0          # MEASURE: radar face to back of XIAO USB-C (total stack)
KIT_PCB_OFF = 1.2     # MEASURE: radar module face to carrier PCB front face
KIT_PCB_T = 1.6       # carrier PCB thickness
KIT_EDGE_KEEPOUT = 2.5  # MEASURE: component-free strip along left/right board edges
RAIL_GRIP = 2.2       # how far the side rails bite onto the board edges

# --- radar window / radome (TI SWRA705: t = n*lambda_material/2, gap = n*lambda0/2)
FRONT_WALL = 3.0      # front wall thickness around the window
RADOME_T = 1.5        # PLA/PETG (er ~2.7-3.0) half-wave thickness at 60 GHz
AIR_GAP = 2.5         # radome back face to antenna face (lambda0/2 at 60 GHz)
RADOME_W, RADOME_H = 32.0, 48.0   # radome plate size
WIN_W, WIN_H = 26.0, 42.0         # visible window (3 mm lip each side)
WIN_CHAMFER = 1.2

# --- Grove OLED 1.12" SH1107 V3.0 (40 x 40 x 12 per distributor spec)
OLED_W = 40.0
OLED_PANEL_T = 1.6    # MEASURE: glass panel thickness in front of the PCB
OLED_PCB_T = 1.6
OLED_T = 12.0         # total thickness incl. Grove connector on back
OLED_LEDGE = 2.0      # ledge width supporting PCB front at its edges
OLED_LIP = 1.4        # lip behind PCB on left/right edges (captures board)
SCREEN_WIN = 23.0     # window over the 20 x 20 mm active area
SCREEN_WIN_DU = 0.0   # MEASURE: active-area offset from board centre (left/right)
SCREEN_WIN_DV = 0.0   # MEASURE: active-area offset (along slant, + = toward you)
FILTER_W, FILTER_T = 29.0, 1.0    # outer recess for a 1 mm green acrylic filter
SCREEN_TILT = 35.0    # screen angle from horizontal, facing back at you

# --- head shell
HEAD_W = 50.0
HEAD_R = 4.0          # outer edge fillet
BROW_BACK = 34.0      # flat top over the kit before the slant starts
SLANT_MARGIN = 1.0

# --- grip
GRIP_W = 32.0         # left/right
GRIP_D = 40.0         # front/back
GRIP_L = 82.0         # length below the head
GRIP_R = 12.0         # vertical edge rounding
GRIP_BOTTOM_R = 5.0
GRIP_RAKE = 15.0      # deg, bottom swept back like a pistol grip
JUNCTION_R = 3.0      # fillet where grip meets head
GRIP_BACK_INSET = 4.5  # grip back face this far in front of head back face

# --- battery + power board in the grip
CELL_D, CELL_L = 18.6, 68.0   # 18650 incl. ~3 mm for solder tabs
CELL_A0 = 3.0                 # cell top, measured down the grip axis
BOOST_W, BOOST_T, BOOST_L = 23.0, 8.0, 42.0   # e.g. PowerBoost 1000C (22.9 x 36.2)
BOOST_FRONT = 13.5            # board front face, grip-local (clears the rounded corners)
BOOST_USB_YP = 10.3           # MEASURE: charge-port centre, grip-local front/back

# --- ports and switch
USB_W, USB_H = 13.0, 7.5      # plug opening (fits USB-C and micro-USB overmolds)
USB_RECESS = 1.2              # outside counterbore so the plug seats fully
KIT_USB_X = 0.0               # MEASURE: XIAO USB-C centre, left/right
SWITCH_D = 7.2                # round panel switch (7 mm latching push button)
SWITCH_YZ = (-45.0, 12.0)     # on the left side, under your thumb

# --- fasteners: M3 x 10 into M3 heat-set inserts
INSERT_D, INSERT_DEPTH = 4.0, 6.0
SCREW_D, HEAD_CB_D, CB_STOP = 3.4, 6.2, 5.0
BOSS_D = 7.0

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

# ---------------------------------------------------------------------------
# DERIVED GEOMETRY
# ---------------------------------------------------------------------------
th = math.radians(SCREEN_TILT)
S, C = math.sin(th), math.cos(th)

Y_AF = -(FRONT_WALL + AIR_GAP)            # antenna face
Y_PCB_F = Y_AF - KIT_PCB_OFF              # carrier PCB front
Y_PCB_B = Y_PCB_F - KIT_PCB_T             # carrier PCB back
Y_KIT_B = Y_AF - KIT_D                    # back of the kit stack
Z_K0 = WALL + 0.6
Z_K1 = Z_K0 + KIT_H
Z_KC = (Z_K0 + Z_K1) / 2
H_F = Z_K1 + 0.6 + WALL                   # head front height (outer)

Y_SL = -BROW_BACK                         # slant start (outer surface)
CRADLE_HALF = OLED_W / 2 + CLR + 2.2      # OLED cradle half-size
S_C = SLANT_MARGIN + CRADLE_HALF          # OLED centre along slant
L_SL = S_C + CRADLE_HALF + SLANT_MARGIN   # slant length
Y_B = Y_SL - L_SL * C                     # head back face
Z_B = H_F - L_SL * S                      # head back top edge

T_DIR = cq.Vector(0, -C, -S)              # down the slant (toward you)
N_IN = cq.Vector(0, S, -C)                # into the body, normal to slant
X_DIR = cq.Vector(1, 0, 0)


def slant_point(s, w):
    """Point s mm down the slant, w mm inward from the OUTER top surface."""
    return cq.Vector(0, Y_SL, H_F) + T_DIR * s + N_IN * w


OLED_PLANE = cq.Plane(origin=slant_point(S_C, WALL), xDir=X_DIR, normal=N_IN)
# OLED_PLANE local coords: x = u (left/right), y = v (down slant), z = w (inward)

GRIP_YC = Y_B + GRIP_BACK_INSET + GRIP_D / 2
HW_HEAD = HEAD_W / 2 - WALL
HW_GRIP = GRIP_W / 2 - WALL
G_IN_D = GRIP_D / 2 - WALL                # grip inner half-depth


def grip_pt(yp, a):
    """Grip-local (yp forward from grip axis, a down the axis) -> global (Y, Z)."""
    phi = math.radians(-GRIP_RAKE)
    y, z = yp, -a
    return (GRIP_YC + y * math.cos(phi) - z * math.sin(phi),
            y * math.sin(phi) + z * math.cos(phi))


def to_grip(shape):
    return shape.rotate((0, GRIP_YC, 0), (1, GRIP_YC, 0), -GRIP_RAKE)


def box(x0, x1, y0, y1, z0, z1):
    return (cq.Workplane("XY")
            .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def gbox(x0, x1, yp0, yp1, a0, a1):
    """Box in grip-local coords (a measured downward), placed on the grip."""
    return to_grip(box(x0, x1, GRIP_YC + yp0, GRIP_YC + yp1, -a1, -a0))


def xcyl(y, z, r, x0, x1):
    """Cylinder along X at (y, z) from x0 to x1."""
    return (cq.Workplane("YZ").workplane(offset=x0).center(y, z)
            .circle(r).extrude(x1 - x0))


def local_box(plane, u0, u1, v0, v1, w0, w1):
    return (cq.Workplane(plane)
            .center((u0 + u1) / 2, (v0 + v1) / 2)
            .workplane(offset=w0)
            .rect(u1 - u0, v1 - v0)
            .extrude(w1 - w0))


# ---------------------------------------------------------------------------
# SHELL
# ---------------------------------------------------------------------------
def head_profile():
    return [(0, 0), (0, H_F), (Y_SL, H_F), (Y_B, Z_B), (Y_B, 0)]


def build_outer():
    head = (cq.Workplane("YZ").polyline(head_profile()).close()
            .extrude(HEAD_W / 2, both=True))
    head = head.edges().fillet(HEAD_R)
    grip = (cq.Workplane("XY").box(GRIP_W, GRIP_D, GRIP_L + 8, centered=(True, True, False))
            .translate((0, GRIP_YC, -GRIP_L)))
    grip = grip.edges("|Z").fillet(GRIP_R)
    grip = grip.faces("<Z").edges().fillet(GRIP_BOTTOM_R)
    grip = to_grip(grip)
    # keep the grip from poking out of the head's top
    grip = grip.intersect(box(-50, 50, -200, 50, -200, Z_B - 1))
    body = head.union(grip)
    try:  # blend the grip into the head
        sel = cq.selectors.BoxSelector((-GRIP_W / 2 - 2, Y_B + HEAD_R + 0.2, -0.8),
                                       (GRIP_W / 2 + 2, -8, 0.8))
        body = body.edges(sel).fillet(JUNCTION_R)
    except Exception as e:
        print("junction fillet skipped:", e)
    return body


def build_inner():
    head = (cq.Workplane("YZ").polyline(head_profile()).close()
            .offset2D(-WALL, "intersection")
            .extrude(HW_HEAD, both=True))
    head = head.cut(box(-50, 50, -FRONT_WALL, 10, -10, 100))
    gi = (cq.Workplane("XY").box(GRIP_W - 2 * WALL, GRIP_D - 2 * WALL,
                                 GRIP_L - WALL + 10, centered=(True, True, False))
          .translate((0, GRIP_YC, -(GRIP_L - WALL))))
    gi = gi.edges("|Z").fillet(GRIP_R - WALL)
    gi = to_grip(gi)
    # only trim the part that pokes up into the head; below Z=0 the raked grip
    # is allowed to sweep back past the head's back face
    clip = box(-50, 50, -300, 50, -300, 0).union(
        box(-50, 50, Y_B + WALL, -FRONT_WALL, 0, WALL + 6))
    gi = gi.intersect(clip)
    return head.union(gi)


# ---------------------------------------------------------------------------
# INTERNAL FEATURES
# ---------------------------------------------------------------------------
def kit_rails():
    """Side rails with a slot that captures the carrier PCB's left/right edges."""
    x_in = KIT_W / 2 - RAIL_GRIP          # rail inner face (bites onto board)
    x_slot = KIT_W / 2 + CLR              # slot bottom
    x_out = HW_HEAD + 0.5                 # rails run out to the side wall so they
                                          # print up from the bed (no supports)
    y_front, y_back = -FRONT_WALL, Y_PCB_B - 0.3 - 2.0
    parts = None
    for sgn in (-1, 1):
        xa, xb = sorted((sgn * x_in, sgn * x_out))
        rail = box(xa, xb, y_back, y_front, WALL - 0.5, Z_K1 + 0.7)
        sa, sb = sorted((sgn * x_in - sgn * 1, sgn * x_slot))
        rail = rail.cut(box(sa, sb, Y_PCB_B - 0.3, Y_PCB_F + 0.3, Z_K0, Z_K1 + 5))
        parts = rail if parts is None else parts.union(rail)
    return parts


def oled_cradle():
    """Frame under the slant: ledge in front of the PCB, slot, and side lips."""
    half = OLED_W / 2 + CLR
    w_pcb0 = OLED_PANEL_T - 0.1
    w_pcb1 = OLED_PANEL_T + OLED_PCB_T + 0.3
    w_lip1 = w_pcb1 + 1.6
    p = OLED_PLANE
    c = local_box(p, -CRADLE_HALF, CRADLE_HALF, -CRADLE_HALF, CRADLE_HALF, -1.0, w_lip1)
    led = half - OLED_LEDGE
    c = c.cut(local_box(p, -led, led, -led, led, -2, w_pcb0))          # panel opening
    c = c.cut(local_box(p, -half, half, -half, half, w_pcb0, w_pcb1))  # PCB slot
    lip = half - OLED_LIP
    c = c.cut(local_box(p, -lip, lip, -CRADLE_HALF - 1, CRADLE_HALF + 1, w_pcb1, w_lip1 + 1))
    return c


def battery_cradle():
    """Saddles and end stops that capture an 18650 against the grip's back wall."""
    yc = -G_IN_D + 0.4 + CELL_D / 2       # cell axis, grip-local
    r = CELL_D / 2 + 0.25
    top_edge = yc + CELL_D / 2 - 0.2
    parts = None
    for a in (CELL_A0 + 11, CELL_A0 + 49):
        sad = gbox(-HW_GRIP, HW_GRIP, -G_IN_D - 1, top_edge, a, a + 2.0)
        cyl = to_grip(cq.Workplane("XY").workplane(offset=-(a + 5))
                      .center(0, GRIP_YC + yc).circle(r).extrude(10))
        sad = sad.cut(cyl)
        parts = sad if parts is None else parts.union(sad)
    a_bot = CELL_A0 + CELL_L + 0.3
    stop = gbox(-HW_GRIP, HW_GRIP, -G_IN_D - 1, top_edge, a_bot, a_bot + 1.8)
    stop = stop.cut(gbox(-2.5, 2.5, top_edge - 4, top_edge + 1, a_bot - 1, a_bot + 3))
    a_top = CELL_A0 - 0.3
    stop2 = gbox(-HW_GRIP, HW_GRIP, -G_IN_D - 1, yc - 2, a_top - 1.8, a_top)
    return parts.union(stop).union(stop2)


# boss positions: (Y, Z, half-width of interior there)
def boss_list():
    head_boss = [
        (Y_KIT_B - 0.2 - BOSS_D / 2, WALL + BOSS_D / 2 - 0.4, HW_HEAD),     # front-bottom
        (Y_B + WALL + BOSS_D / 2 - 0.5, WALL + BOSS_D / 2 - 0.4, HW_HEAD),  # back-bottom
        (Y_KIT_B - 0.3 - BOSS_D / 2, Z_K1 - 6.0, HW_HEAD),                  # top, between kit and OLED
    ]
    gy, gz = grip_pt(-G_IN_D + 7.5, GRIP_L - WALL - BOSS_D / 2 + 0.5)
    gy2, gz2 = grip_pt(G_IN_D - BOSS_D / 2 - 1.5, 20.0)
    grip_boss = [(gy, gz, HW_GRIP), (gy2, gz2, HW_GRIP)]
    return head_boss + grip_boss


def bosses():
    parts = None
    for (y, z, hw) in boss_list():
        b = xcyl(y, z, BOSS_D / 2, -hw - 1, hw + 1)
        parts = b if parts is None else parts.union(b)
    return parts


# ---------------------------------------------------------------------------
# CUTS
# ---------------------------------------------------------------------------
def radar_cuts():
    pocket = box(-RADOME_W / 2 - 0.1, RADOME_W / 2 + 0.1,
                 -FRONT_WALL, -(FRONT_WALL - RADOME_T - 0.1),
                 Z_KC - RADOME_H / 2 - 0.1, Z_KC + RADOME_H / 2 + 0.1)
    win = box(-WIN_W / 2, WIN_W / 2, -FRONT_WALL + 0.5, 1, Z_KC - WIN_H / 2, Z_KC + WIN_H / 2)
    ch = (cq.Workplane("XZ", origin=(0, 0.01, 0)).center(0, Z_KC)
          .rect(WIN_W + 2 * WIN_CHAMFER, WIN_H + 2 * WIN_CHAMFER)
          .workplane(offset=WIN_CHAMFER).rect(WIN_W, WIN_H).loft())
    return pocket.union(win).union(ch)


def screen_cuts():
    p = cq.Plane(origin=slant_point(S_C, 0), xDir=X_DIR, normal=N_IN)
    win = local_box(p, SCREEN_WIN_DU - SCREEN_WIN / 2, SCREEN_WIN_DU + SCREEN_WIN / 2,
                    SCREEN_WIN_DV - SCREEN_WIN / 2, SCREEN_WIN_DV + SCREEN_WIN / 2,
                    -1, WALL + 0.5)
    rec = local_box(p, SCREEN_WIN_DU - FILTER_W / 2, SCREEN_WIN_DU + FILTER_W / 2,
                    SCREEN_WIN_DV - FILTER_W / 2, SCREEN_WIN_DV + FILTER_W / 2,
                    -1, FILTER_T)
    return win.union(rec)


def rrect_z(cx, cy, w, h, r, z0, z1):
    return (cq.Workplane("XY").workplane(offset=z0).center(cx, cy)
            .rect(w, h).extrude(z1 - z0).edges("|Z").fillet(r))


Y_KIT_USB = Y_PCB_B - 8.5 - 1.0 - 1.6     # header + XIAO PCB + half the receptacle


def port_cuts():
    kit = rrect_z(KIT_USB_X, Y_KIT_USB, USB_W, USB_H, 3.0, -1, WALL + 1)
    kit = kit.union(rrect_z(KIT_USB_X, Y_KIT_USB, USB_W + 4, USB_H + 4, 4.0, -1, USB_RECESS))
    # charge port through the grip butt (built in grip-local frame, then raked)
    a_in = GRIP_L - WALL
    g = (cq.Workplane("XY").workplane(offset=-(GRIP_L + 2)).center(0, GRIP_YC + BOOST_USB_YP)
         .rect(USB_W, USB_H).extrude(WALL + 3).edges("|Z").fillet(3.0))
    g = g.union(cq.Workplane("XY").workplane(offset=-(GRIP_L + 2))
                .center(0, GRIP_YC + BOOST_USB_YP).rect(USB_W + 4, USB_H + 4)
                .extrude(2 + USB_RECESS).edges("|Z").fillet(4.0))
    g = to_grip(g)
    sw = xcyl(SWITCH_YZ[0], SWITCH_YZ[1], SWITCH_D / 2, -HEAD_W / 2 - 1, -HW_HEAD + 0.5)
    return kit.union(g).union(sw)


# ---------------------------------------------------------------------------
# COMPONENT STAND-INS (for fit checks and the assembly view)
# ---------------------------------------------------------------------------
def components():
    ko = KIT_W / 2 - KIT_EDGE_KEEPOUT
    module = box(-12.5, 12.5, Y_PCB_F, Y_AF, Z_K0, Z_K1)
    pcb = box(-KIT_W / 2, KIT_W / 2, Y_PCB_B, Y_PCB_F, Z_K0, Z_K1)
    back = box(-ko, ko, Y_KIT_B, Y_PCB_B, Z_K0, Z_K1)
    kit = module.union(pcb).union(back)

    p = OLED_PLANE
    h = OLED_W / 2
    panel = local_box(p, -h + 3, h - 3, -h + 3, h - 3, 0, OLED_PANEL_T)
    opcb = local_box(p, -h, h, -h, h, OLED_PANEL_T, OLED_PANEL_T + OLED_PCB_T)
    oback = local_box(p, -h + 1.6, h - 1.6, -h + 1, h - 1,
                      OLED_PANEL_T + OLED_PCB_T, OLED_T)
    oled = panel.union(opcb).union(oback)

    yc = -G_IN_D + 0.4 + CELL_D / 2
    cell = to_grip(cq.Workplane("XY").workplane(offset=-(CELL_A0 + CELL_L))
                   .center(0, GRIP_YC + yc).circle(CELL_D / 2).extrude(CELL_L))
    yb1 = BOOST_FRONT
    boost = gbox(-BOOST_W / 2, BOOST_W / 2, yb1 - BOOST_T, yb1,
                 GRIP_L - WALL - BOOST_L - 0.2, GRIP_L - WALL - 0.2)
    radome = box(-RADOME_W / 2 + 0.2, RADOME_W / 2 - 0.2,
                 -FRONT_WALL, -FRONT_WALL + RADOME_T,
                 Z_KC - RADOME_H / 2 + 0.2, Z_KC + RADOME_H / 2 - 0.2)
    switch = xcyl(SWITCH_YZ[0], SWITCH_YZ[1], 5.0, -HW_HEAD, -HW_HEAD + 14)
    return {"kit": kit, "oled": oled, "cell": cell, "boost": boost,
            "switch": switch, "radome": radome}


# ---------------------------------------------------------------------------
# BUILD
# ---------------------------------------------------------------------------
def build():
    outer = build_outer()
    inner = build_inner()
    shell = outer.cut(inner)
    feats = kit_rails().union(oled_cradle()).union(battery_cradle()).union(bosses())
    feats = feats.intersect(outer)
    body = shell.union(feats)
    body = body.cut(radar_cuts()).cut(screen_cuts()).cut(port_cuts())

    left = body.intersect(box(-60, 0, -250, 50, -250, 150))
    right = body.intersect(box(0, 60, -250, 50, -250, 150))
    for (y, z, hw) in boss_list():
        right = right.cut(xcyl(y, z, INSERT_D / 2, -0.1, INSERT_DEPTH))
        left = left.cut(xcyl(y, z, SCREW_D / 2, -hw - WALL - 3, 0.1))
        left = left.cut(xcyl(y, z, HEAD_CB_D / 2, -hw - WALL - 3, -CB_STOP))

    radome = (cq.Workplane("XY").rect(RADOME_W - 0.4, RADOME_H - 0.4)
              .extrude(RADOME_T).edges("|Z").fillet(1.5))   # prints flat
    return {"left": left, "right": right, "radome_part": radome, "outer": outer}


def fit_check(parts, comps):
    """Intersect every component stand-in with both shell halves; report overlaps."""
    ok = True
    for name, c in comps.items():
        if name == "radome":
            continue
        for side in ("left", "right"):
            try:
                v = parts[side].intersect(c).val().Volume()
            except Exception:
                v = 0.0
            if v > 0.5:
                ok = False
                print(f"  CLASH: {name} vs shell_{side}: {v:.1f} mm^3")
        try:
            out = c.cut(parts["outer"]).val().Volume()
        except Exception:
            out = 0.0
        if out > 0.5:
            ok = False
            print(f"  CLASH: {name} pokes out of the case: {out:.1f} mm^3")
    print("fit check:", "no overlaps" if ok else "PROBLEMS FOUND")
    return ok


def summary():
    print(f"head: {HEAD_W:.1f} W x {-Y_B:.1f} D x {H_F:.1f} H  (back face {Z_B:.1f} tall)")
    gy, gz = grip_pt(0, GRIP_L)
    print(f"grip bottom centre at Y={gy:.1f} Z={gz:.1f}; overall height {H_F - gz:.1f}")
    print(f"antenna face Y={Y_AF:.2f}, PCB {Y_PCB_F:.2f}..{Y_PCB_B:.2f}, kit back {Y_KIT_B:.2f}")
    print(f"kit USB-C centre Y={Y_KIT_USB:.2f}")
    print("bosses:", [(round(y, 1), round(z, 1)) for y, z, _ in boss_list()])


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    summary()
    parts = build()
    comps = components()
    fit_check(parts, comps)
    # STLs come out already in print orientation: each half lies on its outer
    # side face with the inside facing up (only the grip needs supports under it)
    def on_bed(wp, ang):
        wp = wp.rotate((0, 0, 0), (0, 1, 0), ang)
        bb = wp.val().BoundingBox()
        return wp.translate((-bb.xmin, -bb.ymin, -bb.zmin))
    cq.exporters.export(on_bed(parts["left"], -90), os.path.join(OUT_DIR, "shell_left_PRINT.stl"), tolerance=0.02, angularTolerance=0.15)
    cq.exporters.export(on_bed(parts["right"], 90), os.path.join(OUT_DIR, "shell_right_PRINT.stl"), tolerance=0.02, angularTolerance=0.15)
    cq.exporters.export(parts["radome_part"], os.path.join(OUT_DIR, "radome_1p5mm_PRINT.stl"))

    asm = cq.Assembly(name="pocket_radar_case_v0_1")
    asm.add(parts["left"], name="shell_left", color=cq.Color(0.20, 0.22, 0.20))
    asm.add(parts["right"], name="shell_right", color=cq.Color(0.28, 0.30, 0.27))
    asm.add(comps["radome"], name="radome", color=cq.Color(0.55, 0.75, 0.55, 0.6))
    asm.add(comps["kit"], name="ref_MR60BHA2_kit", color=cq.Color(0.1, 0.3, 0.7))
    asm.add(comps["oled"], name="ref_grove_oled", color=cq.Color(0.05, 0.05, 0.05))
    asm.add(comps["cell"], name="ref_18650", color=cq.Color(0.8, 0.2, 0.2))
    asm.add(comps["boost"], name="ref_boost_board", color=cq.Color(0.1, 0.5, 0.2))
    asm.add(comps["switch"], name="ref_switch", color=cq.Color(0.7, 0.7, 0.7))
    asm.save(os.path.join(OUT_DIR, "pocket_radar_case_v0_1.step"))
    print("done ->", OUT_DIR)
