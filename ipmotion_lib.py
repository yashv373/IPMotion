import numpy as np
from manim import *
from dataclasses import dataclass

config.background_color="#05050A"

# ==========================================
# SECTION 1: Core Infrastructure
# ==========================================
@dataclass(frozen=True)
class Theme:
    background:str="#05050A"
    panel:str="#0A1118"
    panel_2:str="#0D1620"
    stroke:str="#3A506B"
    text:str="#E2E8F0"
    muted:str="#64748B"
    active:str="#00FFF0"
    success:str="#39FF14"
    warning:str="#FFD700"
    error:str="#FF003C"

def ui_text(text, size, color, weight=NORMAL):
    return Text(text, font="Consolas", font_size=size, color=color, weight=weight)

class DomainGroup(VGroup):
    def __init__(self, title, x, y, w, h, fill, stroke=None, dashed=False):
        super().__init__()
        if stroke is None: stroke = fill
        if dashed:
            rect = RoundedRectangle(width=w, height=h, corner_radius=0.1, stroke_color=stroke, stroke_width=2, fill_opacity=0)
            self.bg = DashedVMobject(rect, num_dashes=80)
        else:
            self.bg = RoundedRectangle(width=w, height=h, corner_radius=0.1, fill_color=fill, fill_opacity=1.0, stroke_width=0)
        
        self.bg.move_to([x, y, 0])
        self.txt = Text(title, color="#94A3B8", font="Arial", weight=BOLD, font_size=24)
        self.txt.move_to(self.bg.get_corner(UL) + RIGHT*0.2 + DOWN*0.4, aligned_edge=LEFT)
        self.add(self.bg, self.txt)

class GlowBox(VGroup):
    def __init__(self, width, height, color, fill_color, stroke_width=2.0, corner_radius=0.15, dotted=False):
        super().__init__()
        self.box = RoundedRectangle(width=width, height=height, corner_radius=corner_radius, 
                                  stroke_color=color, stroke_width=stroke_width,
                                  fill_color=fill_color, fill_opacity=0.9)
        if dotted:
            self.box = DashedVMobject(self.box, num_dashes=30)
            
        self.glow1 = RoundedRectangle(width=width, height=height, corner_radius=corner_radius, 
                                    stroke_color=color, stroke_width=stroke_width*3, fill_opacity=0).set_opacity(0.4)
        self.glow2 = RoundedRectangle(width=width, height=height, corner_radius=corner_radius, 
                                    stroke_color=color, stroke_width=stroke_width*6, fill_opacity=0).set_opacity(0.2)
        
        if dotted:
            self.glow1 = DashedVMobject(self.glow1, num_dashes=30)
            self.glow2 = DashedVMobject(self.glow2, num_dashes=30)

        self.add(self.glow2, self.glow1, self.box)
    
    def set_color(self, color):
        self.box.set_stroke(color)
        self.glow1.set_stroke(color)
        self.glow2.set_stroke(color)
        return self

class IPBlock(VGroup):
    def __init__(self, title, theme, width=2.5, height=1.5, fill=None, stroke=None, text_color=None, dotted=False, ind=False, font="Consolas", ports=None):
        super().__init__()
        f = fill if fill else theme.panel
        s = stroke if stroke else theme.stroke
        tc = text_color if text_color else theme.text
        
        self.bg = GlowBox(width, height, s, f, dotted=dotted)
        # Fallback for empty title
        if not title:
            title = " "
        self.txt = Text(title, font=font, font_size=16, color=tc, weight=BOLD, line_spacing=0.6).move_to(self.bg)
        
        max_w = width - 0.2
        max_h = height - 0.2
        if self.txt.width > max_w and self.txt.width > 0:
            self.txt.scale(max_w / self.txt.width)
        if self.txt.height > max_h and self.txt.height > 0:
            self.txt.scale(max_h / self.txt.height)
            
        self.add(self.bg, self.txt)
        
        if ind:
            sq = Square(side_length=0.2, fill_color="#F59E0B", fill_opacity=1.0, stroke_width=0)
            sq.move_to(self.bg.box.get_corner(UL) + RIGHT*0.2 + DOWN*0.2)
            self.add(sq)
            
        if ports:
            for p in ports:
                ptxt = Text(p.get("label", ""), font="Consolas", font_size=10, color="#94A3B8")
                edge = p.get("edge", "RIGHT")
                if edge == "RIGHT":
                    ptxt.move_to(self.bg.box.get_right() + LEFT*0.2)
                elif edge == "LEFT":
                    ptxt.move_to(self.bg.box.get_left() + RIGHT*0.2)
                elif edge == "UP":
                    ptxt.move_to(self.bg.box.get_top() + DOWN*0.15)
                elif edge == "DOWN":
                    ptxt.move_to(self.bg.box.get_bottom() + UP*0.15)
                self.add(ptxt)

class Wire(VGroup):
    def __init__(self, start_obj=None, end_obj=None, start_edge=DOWN, end_edge=UP, manhattan=False, color="#6B7280", waypoints=None):
        super().__init__()
        
        if waypoints is not None:
            for i in range(len(waypoints) - 1):
                if i == len(waypoints) - 2:
                    self.add(Arrow(waypoints[i], waypoints[i+1], color=color, stroke_width=4, buff=0, max_tip_length_to_length_ratio=0.1))
                else:
                    self.add(Line(waypoints[i], waypoints[i+1], color=color, stroke_width=4))
            return
            
        start_pt = start_obj.get_edge_center(start_edge)
        end_pt = end_obj.get_edge_center(end_edge)
        
        if manhattan:
            mid_pt1 = [start_pt[0], (start_pt[1] + end_pt[1])/2, 0]
            mid_pt2 = [end_pt[0], (start_pt[1] + end_pt[1])/2, 0]
            if (start_edge[0] != 0) and (end_edge[1] != 0):
                mid_pt1 = [end_pt[0], start_pt[1], 0]
            self.add(
                Line(start_pt, mid_pt1, color=color, stroke_width=4),
                Line(mid_pt1, mid_pt2, color=color, stroke_width=4),
                Arrow(mid_pt2, end_pt, color=color, stroke_width=4, buff=0, max_tip_length_to_length_ratio=0.1)
            )
        else:
            self.add(Arrow(start_pt, end_pt, color=color, stroke_width=4, buff=0, max_tip_length_to_length_ratio=0.1))

class DirectRoute(VGroup):
    def __init__(self, source_box, target_box, color):
        super().__init__()
        self.line = Arrow(source_box.get_right(), target_box.get_left(), buff=0.15, color=color, stroke_width=4.0)
        self.glow = Arrow(source_box.get_right(), target_box.get_left(), buff=0.15, color=color, stroke_width=12.0).set_opacity(0.2)
        self.add(self.glow, self.line)

    def transfer(self, label, color, theme, run_time=1.0):
        pkt_bg = GlowBox(0.8, 0.4, color, color)
        pkt = VGroup(pkt_bg, ui_text(label, 12, theme.background, BOLD))
        pkt.move_to(self.line.get_start())
        return Succession(
            FadeIn(pkt, run_time=0.2),
            pkt.animate(run_time=run_time).move_to(self.line.get_end()),
            FadeOut(pkt, run_time=0.2),
        )

class ManhattanRoute(VGroup):
    def __init__(self, points, color):
        super().__init__()
        self.pts = points
        self.path = VGroup()
        self.glow_path = VGroup()
        for i in range(len(points) - 1):
            if i == len(points) - 2:
                self.path.add(Arrow(points[i], points[i+1], buff=0, color=color, stroke_width=4.0))
                self.glow_path.add(Arrow(points[i], points[i+1], buff=0, color=color, stroke_width=12.0).set_opacity(0.2))
            else:
                self.path.add(Line(points[i], points[i+1], color=color, stroke_width=4.0))
                self.glow_path.add(Line(points[i], points[i+1], color=color, stroke_width=12.0).set_opacity(0.2))
        self.add(self.glow_path, self.path)

    def transfer(self, label, color, theme, run_time=1.5):
        pkt_bg = GlowBox(0.8, 0.4, color, color)
        pkt = VGroup(pkt_bg, ui_text(label, 12, theme.background, BOLD))
        pkt.move_to(self.pts[0])
        anims = [FadeIn(pkt, run_time=0.2)]
        segment_time = (run_time - 0.4) / (len(self.pts) - 1)
        for i in range(1, len(self.pts)):
            anims.append(pkt.animate(run_time=segment_time).move_to(self.pts[i]))
        anims.append(FadeOut(pkt, run_time=0.2))
        return Succession(*anims)

class Banner(VGroup):
    def __init__(self, title, theme):
        super().__init__()
        self.bg = GlowBox(14.0, 0.8, theme.stroke, theme.panel)
        self.txt = ui_text(title, 24, theme.text, BOLD).move_to(self.bg)
        self.add(self.bg, self.txt)

    def update_text(self, new_title, theme, color=None):
        c = color if color else theme.text
        new_txt = ui_text(new_title, 24, c, BOLD).move_to(self.bg)
        return AnimationGroup(
            Transform(self.txt, new_txt),
            self.bg.animate.set_color(c) if color else Wait(0.1)
        )

# ==========================================
# SECTION 2: Base Component Class
# ==========================================
class HWComponent(VGroup):
    """Base class for all hardware symbol presets."""
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__()
        self.pins = {}  # name -> Dot
        self.theme = theme or Theme()
        self._color = color or self.theme.active
        self._label = label
        self._scale = scale
    
    def _add_pin(self, name, pos):
        dot = Dot(pos, radius=0.01, fill_opacity=0)
        self.add(dot)
        self.pins[name] = dot
        
    def get_pin(self, name):
        """Get the world-space position of a named pin."""
        if name in self.pins:
            return self.pins[name].get_center()
        raise KeyError(f"Pin '{name}' not found. Available: {list(self.pins.keys())}")
    
    def _build_label(self, pos=ORIGIN, font_size=14):
        if self._label:
            txt = Text(self._label, font='Consolas', font_size=font_size, 
                      color=self.theme.text, weight=BOLD)
            txt.move_to(pos)
            # Auto-shrink if too wide
            if txt.width > 0.8 * self._scale:
                txt.scale(0.8 * self._scale / txt.width)
            self.add(txt)
            self.txt = txt

# ==========================================
# SECTION 3: Logic Gates
# ==========================================
class ANDGate(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        pts = []
        pts.append([-0.6*s, -0.4*s, 0])
        pts.append([-0.6*s, 0.4*s, 0])
        pts.append([0.0*s, 0.4*s, 0])
        for angle in np.linspace(PI/2, -PI/2, 20):
            pts.append([0.4*s * np.cos(angle), 0.4*s * np.sin(angle), 0])
        pts.append([0.0*s, -0.4*s, 0])
        
        self.body = Polygon(*pts, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        pin_a_pos = np.array([-0.6*s, 0.2*s, 0])
        pin_b_pos = np.array([-0.6*s, -0.2*s, 0])
        pin_out_end = np.array([0.4*s, 0, 0])
        pin_out_stub = np.array([0.6*s, 0, 0])
        
        self.add(Line(pin_a_pos + LEFT*0.2*s, pin_a_pos, color=c, stroke_width=2))
        self.add(Line(pin_b_pos + LEFT*0.2*s, pin_b_pos, color=c, stroke_width=2))
        self.add(Line(pin_out_end, pin_out_stub, color=c, stroke_width=2))
        
        self._add_pin('a', pin_a_pos + LEFT*0.2*s)
        self._add_pin('b', pin_b_pos + LEFT*0.2*s)
        self._add_pin('out', pin_out_stub)
        self._add_pin('pin_a', pin_a_pos + LEFT*0.2*s)
        self._add_pin('pin_b', pin_b_pos + LEFT*0.2*s)
        self._add_pin('pin_out', pin_out_stub)
        
        self.bg = self.body
        self._build_label(ORIGIN, font_size=12)

class ORGate(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        pts = []
        # Concave left
        for angle in np.linspace(-PI/4, PI/4, 15):
            pts.append([-0.8*s + 0.4*s * np.cos(angle), 0.4*s * np.sin(angle)/np.sin(PI/4), 0])
        # Top curve to tip
        for x in np.linspace(-0.517*s, 0.6*s, 15):
            y = 0.4*s * (1 - ((x + 0.517*s)/(1.117*s))**1.5)
            pts.append([x, y, 0])
        # Bottom curve to tip (reversed)
        for x in np.linspace(0.6*s, -0.517*s, 15):
            y = -0.4*s * (1 - ((x + 0.517*s)/(1.117*s))**1.5)
            pts.append([x, y, 0])
            
        self.body = Polygon(*pts, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        pin_a_pos = np.array([-0.45*s, 0.2*s, 0])
        pin_b_pos = np.array([-0.45*s, -0.2*s, 0])
        pin_out_end = np.array([0.6*s, 0, 0])
        pin_out_stub = np.array([0.8*s, 0, 0])
        
        self.add(Line(pin_a_pos + LEFT*0.35*s, pin_a_pos, color=c, stroke_width=2))
        self.add(Line(pin_b_pos + LEFT*0.35*s, pin_b_pos, color=c, stroke_width=2))
        self.add(Line(pin_out_end, pin_out_stub, color=c, stroke_width=2))
        
        self._add_pin('a', pin_a_pos + LEFT*0.35*s)
        self._add_pin('b', pin_b_pos + LEFT*0.35*s)
        self._add_pin('out', pin_out_stub)
        self._add_pin('pin_a', pin_a_pos + LEFT*0.35*s)
        self._add_pin('pin_b', pin_b_pos + LEFT*0.35*s)
        self._add_pin('pin_out', pin_out_stub)
        
        self.bg = self.body
        self._build_label(LEFT*0.1*s, font_size=12)

class NANDGate(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        pts = []
        pts.append([-0.6*s, -0.4*s, 0])
        pts.append([-0.6*s, 0.4*s, 0])
        pts.append([0.0*s, 0.4*s, 0])
        for angle in np.linspace(PI/2, -PI/2, 20):
            pts.append([0.4*s * np.cos(angle), 0.4*s * np.sin(angle), 0])
        pts.append([0.0*s, -0.4*s, 0])
        
        self.body = Polygon(*pts, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        bubble = Circle(radius=0.08*s, color=c, fill_color=c, fill_opacity=0.15, stroke_width=2.5).move_to([0.48*s, 0, 0])
        self.add(self.body, bubble)
        
        pin_a_pos = np.array([-0.6*s, 0.2*s, 0])
        pin_b_pos = np.array([-0.6*s, -0.2*s, 0])
        pin_out_stub = np.array([0.76*s, 0, 0])
        
        self.add(Line(pin_a_pos + LEFT*0.2*s, pin_a_pos, color=c, stroke_width=2))
        self.add(Line(pin_b_pos + LEFT*0.2*s, pin_b_pos, color=c, stroke_width=2))
        self.add(Line(bubble.get_right(), pin_out_stub, color=c, stroke_width=2))
        
        self._add_pin('a', pin_a_pos + LEFT*0.2*s)
        self._add_pin('b', pin_b_pos + LEFT*0.2*s)
        self._add_pin('out', pin_out_stub)
        self._add_pin('pin_a', pin_a_pos + LEFT*0.2*s)
        self._add_pin('pin_b', pin_b_pos + LEFT*0.2*s)
        self._add_pin('pin_out', pin_out_stub)
        
        self.bg = self.body
        self._build_label(ORIGIN, font_size=12)

class NORGate(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        pts = []
        for angle in np.linspace(-PI/4, PI/4, 15):
            pts.append([-0.8*s + 0.4*s * np.cos(angle), 0.4*s * np.sin(angle)/np.sin(PI/4), 0])
        for x in np.linspace(-0.517*s, 0.6*s, 15):
            y = 0.4*s * (1 - ((x + 0.517*s)/(1.117*s))**1.5)
            pts.append([x, y, 0])
        for x in np.linspace(0.6*s, -0.517*s, 15):
            y = -0.4*s * (1 - ((x + 0.517*s)/(1.117*s))**1.5)
            pts.append([x, y, 0])
            
        self.body = Polygon(*pts, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        bubble = Circle(radius=0.08*s, color=c, fill_color=c, fill_opacity=0.15, stroke_width=2.5).move_to([0.68*s, 0, 0])
        self.add(self.body, bubble)
        
        pin_a_pos = np.array([-0.45*s, 0.2*s, 0])
        pin_b_pos = np.array([-0.45*s, -0.2*s, 0])
        pin_out_stub = np.array([0.96*s, 0, 0])
        
        self.add(Line(pin_a_pos + LEFT*0.35*s, pin_a_pos, color=c, stroke_width=2))
        self.add(Line(pin_b_pos + LEFT*0.35*s, pin_b_pos, color=c, stroke_width=2))
        self.add(Line(bubble.get_right(), pin_out_stub, color=c, stroke_width=2))
        
        self._add_pin('a', pin_a_pos + LEFT*0.35*s)
        self._add_pin('b', pin_b_pos + LEFT*0.35*s)
        self._add_pin('out', pin_out_stub)
        self._add_pin('pin_a', pin_a_pos + LEFT*0.35*s)
        self._add_pin('pin_b', pin_b_pos + LEFT*0.35*s)
        self._add_pin('pin_out', pin_out_stub)
        
        self.bg = self.body
        self._build_label(LEFT*0.1*s, font_size=12)

class XORGate(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        # Main body (like OR)
        pts = []
        for angle in np.linspace(-PI/4, PI/4, 15):
            pts.append([-0.8*s + 0.4*s * np.cos(angle), 0.4*s * np.sin(angle)/np.sin(PI/4), 0])
        for x in np.linspace(-0.517*s, 0.6*s, 15):
            y = 0.4*s * (1 - ((x + 0.517*s)/(1.117*s))**1.5)
            pts.append([x, y, 0])
        for x in np.linspace(0.6*s, -0.517*s, 15):
            y = -0.4*s * (1 - ((x + 0.517*s)/(1.117*s))**1.5)
            pts.append([x, y, 0])
            
        self.body = Polygon(*pts, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        
        # Extra curve
        extra_curve = []
        for angle in np.linspace(-PI/4, PI/4, 15):
            extra_curve.append([-0.9*s + 0.4*s * np.cos(angle), 0.4*s * np.sin(angle)/np.sin(PI/4), 0])
        extra_curve_line = VMobject()
        extra_curve_line.set_points_as_corners(extra_curve)
        extra_curve_line.set_color(c).set_stroke(width=2.5)
        
        self.add(self.body, extra_curve_line)
        
        pin_a_pos = np.array([-0.61*s, 0.2*s, 0])
        pin_b_pos = np.array([-0.61*s, -0.2*s, 0])
        pin_out_end = np.array([0.6*s, 0, 0])
        pin_out_stub = np.array([0.8*s, 0, 0])
        
        self.add(Line(pin_a_pos + LEFT*0.19*s, pin_a_pos, color=c, stroke_width=2))
        self.add(Line(pin_b_pos + LEFT*0.19*s, pin_b_pos, color=c, stroke_width=2))
        self.add(Line(pin_out_end, pin_out_stub, color=c, stroke_width=2))
        
        self._add_pin('a', pin_a_pos + LEFT*0.19*s)
        self._add_pin('b', pin_b_pos + LEFT*0.19*s)
        self._add_pin('out', pin_out_stub)
        self._add_pin('pin_a', pin_a_pos + LEFT*0.19*s)
        self._add_pin('pin_b', pin_b_pos + LEFT*0.19*s)
        self._add_pin('pin_out', pin_out_stub)
        
        self.bg = self.body
        self._build_label(LEFT*0.1*s, font_size=12)

class NOTGate(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        pts = [[-0.4*s, 0.4*s, 0], [0.4*s, 0, 0], [-0.4*s, -0.4*s, 0]]
        self.body = Polygon(*pts, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        bubble = Circle(radius=0.08*s, color=c, fill_color=c, fill_opacity=0.15, stroke_width=2.5).move_to([0.48*s, 0, 0])
        self.add(self.body, bubble)
        
        pin_in_pos = np.array([-0.4*s, 0, 0])
        pin_out_stub = np.array([0.76*s, 0, 0])
        
        self.add(Line(pin_in_pos + LEFT*0.2*s, pin_in_pos, color=c, stroke_width=2))
        self.add(Line(bubble.get_right(), pin_out_stub, color=c, stroke_width=2))
        
        self._add_pin('in', pin_in_pos + LEFT*0.2*s)
        self._add_pin('out', pin_out_stub)
        self._add_pin('pin_in', pin_in_pos + LEFT*0.2*s)
        self._add_pin('pin_out', pin_out_stub)
        
        self.bg = self.body
        self._build_label(LEFT*0.1*s, font_size=12)

class BufferGate(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        pts = [[-0.4*s, 0.4*s, 0], [0.4*s, 0, 0], [-0.4*s, -0.4*s, 0]]
        self.body = Polygon(*pts, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        pin_in_pos = np.array([-0.4*s, 0, 0])
        pin_out_stub = np.array([0.6*s, 0, 0])
        
        self.add(Line(pin_in_pos + LEFT*0.2*s, pin_in_pos, color=c, stroke_width=2))
        self.add(Line(np.array([0.4*s, 0, 0]), pin_out_stub, color=c, stroke_width=2))
        
        self._add_pin('in', pin_in_pos + LEFT*0.2*s)
        self._add_pin('out', pin_out_stub)
        self._add_pin('pin_in', pin_in_pos + LEFT*0.2*s)
        self._add_pin('pin_out', pin_out_stub)
        
        self.bg = self.body
        self._build_label(LEFT*0.1*s, font_size=12)

# ==========================================
# SECTION 4: Datapath Components
# ==========================================
class MuxSymbol(HWComponent):
    def __init__(self, label='MUX', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        w, h = 0.6*s, 1.2*s
        p1 = [-w/2, h/2, 0]
        p2 = [w/2, h/3, 0]
        p3 = [w/2, -h/3, 0]
        p4 = [-w/2, -h/2, 0]
        self.body = Polygon(p1, p2, p3, p4, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        p_in0 = np.array([-w/2, h/4, 0])
        p_in1 = np.array([-w/2, -h/4, 0])
        p_out = np.array([w/2, 0, 0])
        p_sel = np.array([0, -h*5/12, 0])
        
        self.add(Line(p_in0 + LEFT*0.2*s, p_in0, color=c, stroke_width=2))
        self.add(Line(p_in1 + LEFT*0.2*s, p_in1, color=c, stroke_width=2))
        self.add(Line(p_out, p_out + RIGHT*0.2*s, color=c, stroke_width=2))
        self.add(Line(p_sel + DOWN*0.2*s, p_sel, color=c, stroke_width=2))
        
        self._add_pin('in_0', p_in0 + LEFT*0.2*s)
        self._add_pin('in_1', p_in1 + LEFT*0.2*s)
        self._add_pin('out', p_out + RIGHT*0.2*s)
        self._add_pin('sel', p_sel + DOWN*0.2*s)
        
        self.bg = self.body
        self._build_label(ORIGIN, font_size=12)

class DemuxSymbol(HWComponent):
    def __init__(self, label='DEMUX', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        w, h = 0.6*s, 1.2*s
        p1 = [-w/2, h/3, 0]
        p2 = [w/2, h/2, 0]
        p3 = [w/2, -h/2, 0]
        p4 = [-w/2, -h/3, 0]
        self.body = Polygon(p1, p2, p3, p4, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        p_in = np.array([-w/2, 0, 0])
        p_out0 = np.array([w/2, h/4, 0])
        p_out1 = np.array([w/2, -h/4, 0])
        p_sel = np.array([0, -h*5/12, 0])
        
        self.add(Line(p_in + LEFT*0.2*s, p_in, color=c, stroke_width=2))
        self.add(Line(p_out0, p_out0 + RIGHT*0.2*s, color=c, stroke_width=2))
        self.add(Line(p_out1, p_out1 + RIGHT*0.2*s, color=c, stroke_width=2))
        self.add(Line(p_sel + DOWN*0.2*s, p_sel, color=c, stroke_width=2))
        
        self._add_pin('in', p_in + LEFT*0.2*s)
        self._add_pin('out_0', p_out0 + RIGHT*0.2*s)
        self._add_pin('out_1', p_out1 + RIGHT*0.2*s)
        self._add_pin('sel', p_sel + DOWN*0.2*s)
        
        self.bg = self.body
        self._build_label(ORIGIN, font_size=12)

class AdderSymbol(HWComponent):
    def __init__(self, label='+', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        w, h = 0.8*s, 1.2*s
        pts = [
            [-w/2, h/2, 0],
            [w/2, h/4, 0],
            [w/2, -h/4, 0],
            [-w/2, -h/2, 0],
            [-w/2, -h/4, 0],
            [-w/4, 0, 0],
            [-w/2, h/4, 0]
        ]
        self.body = Polygon(*pts, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        pa = np.array([-w/2, h/3, 0])
        pb = np.array([-w/2, -h/3, 0])
        psum = np.array([w/2, 0, 0])
        pcout = np.array([0, h*3/8, 0])
        
        self.add(Line(pa + LEFT*0.2*s, pa, color=c, stroke_width=2))
        self.add(Line(pb + LEFT*0.2*s, pb, color=c, stroke_width=2))
        self.add(Line(psum, psum + RIGHT*0.2*s, color=c, stroke_width=2))
        self.add(Line(pcout + UP*0.2*s, pcout, color=c, stroke_width=2))
        
        self._add_pin('a', pa + LEFT*0.2*s)
        self._add_pin('b', pb + LEFT*0.2*s)
        self._add_pin('sum', psum + RIGHT*0.2*s)
        self._add_pin('cout', pcout + UP*0.2*s)
        
        self.bg = self.body
        self._build_label(ORIGIN, font_size=16)

class ALUSymbol(HWComponent):
    def __init__(self, label='ALU', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        w, h = 0.8*s, 1.4*s
        pts = [
            [-w/2, h/2, 0],
            [w/2, h/3, 0],
            [w/2, -h/3, 0],
            [-w/2, -h/2, 0],
            [-w/2, -h/6, 0],
            [-w/4, 0, 0],
            [-w/2, h/6, 0]
        ]
        self.body = Polygon(*pts, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        pa = np.array([-w/2, h/3, 0])
        pb = np.array([-w/2, -h/3, 0])
        pres = np.array([w/2, 0, 0])
        pflags = np.array([w/4, h*5/12, 0])
        
        self.add(Line(pa + LEFT*0.2*s, pa, color=c, stroke_width=2))
        self.add(Line(pb + LEFT*0.2*s, pb, color=c, stroke_width=2))
        self.add(Line(pres, pres + RIGHT*0.2*s, color=c, stroke_width=2))
        self.add(Line(pflags, pflags + UP*0.2*s, color=c, stroke_width=2))
        
        self._add_pin('a', pa + LEFT*0.2*s)
        self._add_pin('b', pb + LEFT*0.2*s)
        self._add_pin('result', pres + RIGHT*0.2*s)
        self._add_pin('flags', pflags + UP*0.2*s)
        
        self.bg = self.body
        self._build_label(ORIGIN, font_size=14)

class ComparatorSymbol(HWComponent):
    def __init__(self, label='=', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        self.body = Rectangle(width=0.8*s, height=1.0*s, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        pa = np.array([-0.4*s, 0.2*s, 0])
        pb = np.array([-0.4*s, -0.2*s, 0])
        pout = np.array([0.4*s, 0, 0])
        
        self.add(Line(pa + LEFT*0.2*s, pa, color=c, stroke_width=2))
        self.add(Line(pb + LEFT*0.2*s, pb, color=c, stroke_width=2))
        self.add(Line(pout, pout + RIGHT*0.2*s, color=c, stroke_width=2))
        
        self._add_pin('a', pa + LEFT*0.2*s)
        self._add_pin('b', pb + LEFT*0.2*s)
        self._add_pin('out', pout + RIGHT*0.2*s)
        
        self.bg = self.body
        self._build_label(ORIGIN, font_size=18)

# ==========================================
# SECTION 5: Storage Components
# ==========================================
class DFlipFlop(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        w, h = 0.8*s, 1.2*s
        self.body = Rectangle(width=w, height=h, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        clk_tri = Polygon([-w/2, -h/4+0.1*s, 0], [-w/2+0.15*s, -h/4, 0], [-w/2, -h/4-0.1*s, 0], stroke_color=c, stroke_width=2)
        self.add(clk_tri)
        
        pd = np.array([-w/2, h/4, 0])
        pclk = np.array([-w/2, -h/4, 0])
        pq = np.array([w/2, h/4, 0])
        pqb = np.array([w/2, -h/4, 0])
        
        self.add(Line(pd + LEFT*0.2*s, pd, color=c, stroke_width=2))
        self.add(Line(pclk + LEFT*0.2*s, pclk, color=c, stroke_width=2))
        self.add(Line(pq, pq + RIGHT*0.2*s, color=c, stroke_width=2))
        
        q_bar_bubble = Circle(radius=0.05*s, color=c, stroke_width=2).move_to(pqb + RIGHT*0.05*s)
        self.add(q_bar_bubble)
        self.add(Line(q_bar_bubble.get_right(), pqb + RIGHT*0.2*s, color=c, stroke_width=2))
        
        self.add(Text("D", font="Consolas", font_size=12*s, color=c).move_to(pd + RIGHT*0.15*s))
        self.add(Text("Q", font="Consolas", font_size=12*s, color=c).move_to(pq + LEFT*0.15*s))
        self.add(Text("Q'", font="Consolas", font_size=12*s, color=c).move_to(pqb + LEFT*0.15*s))
        
        self._add_pin('d', pd + LEFT*0.2*s)
        self._add_pin('clk', pclk + LEFT*0.2*s)
        self._add_pin('q', pq + RIGHT*0.2*s)
        self._add_pin('q_bar', pqb + RIGHT*0.2*s)
        
        self.bg = self.body
        self._build_label(ORIGIN, font_size=12)

class SRLatch(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        w, h = 0.8*s, 1.2*s
        self.body = Rectangle(width=w, height=h, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        ps = np.array([-w/2, h/4, 0])
        pr = np.array([-w/2, -h/4, 0])
        pq = np.array([w/2, h/4, 0])
        pqb = np.array([w/2, -h/4, 0])
        
        self.add(Line(ps + LEFT*0.2*s, ps, color=c, stroke_width=2))
        self.add(Line(pr + LEFT*0.2*s, pr, color=c, stroke_width=2))
        self.add(Line(pq, pq + RIGHT*0.2*s, color=c, stroke_width=2))
        
        q_bar_bubble = Circle(radius=0.05*s, color=c, stroke_width=2).move_to(pqb + RIGHT*0.05*s)
        self.add(q_bar_bubble)
        self.add(Line(q_bar_bubble.get_right(), pqb + RIGHT*0.2*s, color=c, stroke_width=2))
        
        self.add(Text("S", font="Consolas", font_size=12*s, color=c).move_to(ps + RIGHT*0.15*s))
        self.add(Text("R", font="Consolas", font_size=12*s, color=c).move_to(pr + RIGHT*0.15*s))
        self.add(Text("Q", font="Consolas", font_size=12*s, color=c).move_to(pq + LEFT*0.15*s))
        self.add(Text("Q'", font="Consolas", font_size=12*s, color=c).move_to(pqb + LEFT*0.15*s))
        
        self._add_pin('s', ps + LEFT*0.2*s)
        self._add_pin('r', pr + LEFT*0.2*s)
        self._add_pin('q', pq + RIGHT*0.2*s)
        self._add_pin('q_bar', pqb + RIGHT*0.2*s)
        
        self.bg = self.body
        self._build_label(ORIGIN, font_size=12)

class RegisterFile(HWComponent):
    def __init__(self, label='RegFile', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        w, h = 1.0*s, 1.4*s
        self.body = Rectangle(width=w, height=h, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        # Draw some stacked rectangles inside
        for i in range(4):
            rect = Rectangle(width=w-0.2*s, height=h/5-0.05*s, stroke_color=c, stroke_width=1)
            rect.move_to([0, h/2 - (i+1)*(h/5), 0])
            self.add(rect)
            
        paddr = np.array([-w/2, h/4, 0])
        pwe = np.array([-w/2, 0, 0])
        pdin = np.array([-w/2, -h/4, 0])
        pdout = np.array([w/2, 0, 0])
        
        self.add(Line(paddr + LEFT*0.2*s, paddr, color=c, stroke_width=2))
        self.add(Line(pwe + LEFT*0.2*s, pwe, color=c, stroke_width=2))
        self.add(Line(pdin + LEFT*0.2*s, pdin, color=c, stroke_width=2))
        self.add(Line(pdout, pdout + RIGHT*0.2*s, color=c, stroke_width=2))
        
        self._add_pin('addr', paddr + LEFT*0.2*s)
        self._add_pin('we', pwe + LEFT*0.2*s)
        self._add_pin('data_in', pdin + LEFT*0.2*s)
        self._add_pin('data_out', pdout + RIGHT*0.2*s)
        
        self.bg = self.body
        self._build_label([0, h/2 + 0.2*s, 0], font_size=12)

class FifoQueue(HWComponent):
    def __init__(self, depth=4, label='FIFO', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        cell_w, cell_h = 1.0 * s, 0.6 * s
        
        total_w = depth * cell_w
        start_x = -total_w/2 + cell_w/2
        
        self.body = VGroup()
        self.cells = []
        for i in range(depth):
            x = start_x + i * cell_w
            box = Rectangle(
                width=cell_w, height=cell_h,
                stroke_color=c, stroke_width=1.5,
                fill_color=self.theme.panel_2, fill_opacity=1.0
            ).move_to([x, 0, 0])
            txt = Text("-", font="Consolas", font_size=int(16*s), color=self.theme.muted, weight=BOLD).move_to(box)
            self.body.add(box, txt)
            self.cells.append((box, txt))
            
        self.add(self.body)
        
        penq = np.array([-total_w/2, 0, 0])
        pdeq = np.array([total_w/2, 0, 0])
        
        self.add(Line(penq + LEFT*0.3*s, penq, color=c, stroke_width=2.5))
        self.add(Line(pdeq, pdeq + RIGHT*0.3*s, color=c, stroke_width=2.5))
        
        self._add_pin('enq', penq + LEFT*0.3*s)
        self._add_pin('deq', pdeq + RIGHT*0.3*s)
        
        self.bg = self.cells[0][0]  # Just bind to first cell box for anims
        self._build_label([0, cell_h/2 + 0.3*s, 0], font_size=int(14*s))

class Fifo2D(HWComponent):
    def __init__(self, rows=3, cols=3, label='FIFO 2D', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        cell_w, cell_h = 0.8 * s, 0.6 * s
        
        total_w = cols * cell_w
        total_h = rows * cell_h
        
        start_y = total_h/2 - cell_h/2
        start_x = -total_w/2 + cell_w/2
        
        self.body = VGroup()
        self.cells = []
        for r in range(rows):
            row_cells = []
            for col in range(cols):
                x = start_x + col * cell_w
                y = start_y - r * cell_h
                box = Rectangle(
                    width=cell_w, height=cell_h,
                    stroke_color=c, stroke_width=1.5,
                    fill_color=self.theme.panel_2, fill_opacity=1.0
                ).move_to([x, y, 0])
                txt = Text("-", font="Consolas", font_size=int(12*s), color=self.theme.muted, weight=BOLD).move_to(box)
                self.body.add(box, txt)
                row_cells.append((box, txt))
            self.cells.append(row_cells)
                
        self.add(self.body)
        
        pwr = np.array([-total_w/2, total_h/4, 0])
        prd = np.array([total_w/2, -total_h/4, 0])
        
        self.add(Line(pwr + LEFT*0.3*s, pwr, color=c, stroke_width=2.5))
        self.add(Line(prd, prd + RIGHT*0.3*s, color=c, stroke_width=2.5))
        
        self._add_pin('wr', pwr + LEFT*0.3*s)
        self._add_pin('rd', prd + RIGHT*0.3*s)
        
        self.bg = self.cells[0][0][0]
        self._build_label([0, total_h/2 + 0.3*s, 0], font_size=int(14*s))

# ==========================================
# SECTION 6: Analog / Electrical Components
# ==========================================
class NMOSTransistor(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        self.body = VGroup()
        # Channel (right vertical bar)
        self.body.add(Line([0, 0.4*s, 0], [0, -0.4*s, 0], color=c, stroke_width=4))
        # Gate poly (left vertical bar)
        self.body.add(Line([-0.12*s, 0.4*s, 0], [-0.12*s, -0.4*s, 0], color=c, stroke_width=4))
        self.add(self.body)
        
        # Pins
        pgate = np.array([-0.12*s, 0, 0])
        pdrain = np.array([0, 0.4*s, 0])
        psource = np.array([0, -0.4*s, 0])
        
        # Stubs
        self.add(Line(pgate + LEFT*0.3*s, pgate, color=c, stroke_width=2.5))
        self.add(Line(pdrain + UP*0.3*s, pdrain, color=c, stroke_width=2.5))
        self.add(Line(psource + DOWN*0.3*s, psource, color=c, stroke_width=2.5))
        
        # NMOS Arrow on Source (pointing down/out)
        arrow_poly = Polygon(
            [0, -0.4*s, 0],
            [-0.15*s, -0.4*s + 0.2*s, 0],
            [0, -0.4*s + 0.2*s, 0],
            fill_color=c, fill_opacity=1, stroke_width=0
        )
        # Shift it slightly down so it sits on the line
        arrow_poly.shift(DOWN*0.1*s + LEFT*0.02*s)
        
        # Actually, let's just make a simple triangle pointing down
        tri = Polygon(
            [-0.1*s, -0.4*s, 0],
            [0.1*s, -0.4*s, 0],
            [0, -0.55*s, 0],
            fill_color=c, fill_opacity=1, stroke_width=0
        )
        self.add(tri)
        
        self._add_pin('gate', pgate + LEFT*0.3*s)
        self._add_pin('drain', pdrain + UP*0.3*s)
        self._add_pin('source', psource + DOWN*0.3*s)
        
        self.bg = self.body
        self._build_label([0.4*s, 0, 0], font_size=int(12*s))

class PMOSTransistor(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        self.body = VGroup()
        # Channel (right vertical bar)
        self.body.add(Line([0, 0.4*s, 0], [0, -0.4*s, 0], color=c, stroke_width=4))
        # Gate poly (left vertical bar)
        self.body.add(Line([-0.12*s, 0.4*s, 0], [-0.12*s, -0.4*s, 0], color=c, stroke_width=4))
        self.add(self.body)
        
        # Bubble on gate
        bubble_r = 0.08 * s
        bubble_c = np.array([-0.12*s - bubble_r, 0, 0])
        bubble = Circle(radius=bubble_r, color=c, stroke_width=2.5).move_to(bubble_c)
        self.add(bubble)
        
        # Pins
        pgate = bubble_c + LEFT*bubble_r
        psource = np.array([0, 0.4*s, 0])
        pdrain = np.array([0, -0.4*s, 0])
        
        # Stubs
        self.add(Line(pgate + LEFT*0.22*s, pgate, color=c, stroke_width=2.5))
        self.add(Line(psource + UP*0.3*s, psource, color=c, stroke_width=2.5))
        self.add(Line(pdrain + DOWN*0.3*s, pdrain, color=c, stroke_width=2.5))
        
        # PMOS Arrow on Source (top line, pointing down/in)
        tri = Polygon(
            [-0.1*s, 0.55*s, 0],
            [0.1*s, 0.55*s, 0],
            [0, 0.4*s, 0],
            fill_color=c, fill_opacity=1, stroke_width=0
        )
        self.add(tri)
        
        self._add_pin('gate', pgate + LEFT*0.22*s)
        self._add_pin('source', psource + UP*0.3*s)
        self._add_pin('drain', pdrain + DOWN*0.3*s)
        
        self.bg = self.body
        self._build_label([0.4*s, 0, 0], font_size=int(12*s))

class Resistor(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        pts = [[-0.4*s, 0, 0], [-0.3*s, 0.15*s, 0], [-0.1*s, -0.15*s, 0], 
               [0.1*s, 0.15*s, 0], [0.3*s, -0.15*s, 0], [0.4*s, 0, 0]]
        
        self.body = VMobject()
        self.body.set_points_as_corners(pts)
        self.body.set_color(c).set_stroke(width=2.5)
        self.add(self.body)
        
        pp = np.array([-0.4*s, 0, 0])
        pn = np.array([0.4*s, 0, 0])
        
        self.add(Line(pp + LEFT*0.2*s, pp, color=c, stroke_width=2))
        self.add(Line(pn, pn + RIGHT*0.2*s, color=c, stroke_width=2))
        
        self._add_pin('p', pp + LEFT*0.2*s)
        self._add_pin('n', pn + RIGHT*0.2*s)
        
        self.bg = self.body
        self._build_label([0, 0.3*s, 0], font_size=10)

class Capacitor(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        self.body = VGroup(
            Line([-0.05*s, 0.3*s, 0], [-0.05*s, -0.3*s, 0], color=c, stroke_width=3),
            Line([0.05*s, 0.3*s, 0], [0.05*s, -0.3*s, 0], color=c, stroke_width=3)
        )
        self.add(self.body)
        
        pp = np.array([-0.05*s, 0, 0])
        pn = np.array([0.05*s, 0, 0])
        
        self.add(Line(pp + LEFT*0.35*s, pp, color=c, stroke_width=2))
        self.add(Line(pn, pn + RIGHT*0.35*s, color=c, stroke_width=2))
        
        self._add_pin('p', pp + LEFT*0.35*s)
        self._add_pin('n', pn + RIGHT*0.35*s)
        
        self.bg = self.body
        self._build_label([0, 0.4*s, 0], font_size=10)

class Ground(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        self.body = VGroup(
            Line([-0.3*s, 0, 0], [0.3*s, 0, 0], color=c, stroke_width=2),
            Line([-0.2*s, -0.1*s, 0], [0.2*s, -0.1*s, 0], color=c, stroke_width=2),
            Line([-0.1*s, -0.2*s, 0], [0.1*s, -0.2*s, 0], color=c, stroke_width=2)
        )
        self.add(self.body)
        
        pterm = np.array([0, 0, 0])
        self.add(Line(pterm + UP*0.3*s, pterm, color=c, stroke_width=2))
        
        self._add_pin('terminal', pterm + UP*0.3*s)
        
        self.bg = self.body
        self._build_label([0, -0.4*s, 0], font_size=10)

class VDD(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        self.body = Line([-0.3*s, 0, 0], [0.3*s, 0, 0], color=c, stroke_width=3)
        self.add(self.body)
        
        pterm = np.array([0, 0, 0])
        self.add(Line(pterm + DOWN*0.3*s, pterm, color=c, stroke_width=2))
        
        self._add_pin('terminal', pterm + DOWN*0.3*s)
        
        self.bg = self.body
        self._build_label([0, 0.2*s, 0], font_size=10)

class Switch(HWComponent):
    def __init__(self, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        p1 = np.array([-0.2*s, 0, 0])
        p2 = np.array([0.2*s, 0.2*s, 0])
        
        self.body = Line(p1, p2, color=c, stroke_width=2.5)
        self.add(self.body)
        
        c1 = Circle(radius=0.03*s, color=c).move_to(p1)
        c2 = Circle(radius=0.03*s, color=c).move_to([0.2*s, 0, 0])
        self.add(c1, c2)
        
        pp = np.array([-0.23*s, 0, 0])
        pn = np.array([0.23*s, 0, 0])
        
        self.add(Line(pp + LEFT*0.17*s, pp, color=c, stroke_width=2))
        self.add(Line(pn, pn + RIGHT*0.17*s, color=c, stroke_width=2))
        
        self._add_pin('p', pp + LEFT*0.17*s)
        self._add_pin('n', pn + RIGHT*0.17*s)
        
        self.bg = self.body
        self._build_label([0, 0.4*s, 0], font_size=10)

# ==========================================
# SECTION 7: Interconnect Components
# ==========================================
class BusBar(HWComponent):
    def __init__(self, length=2.0, taps=3, vertical=False, label='BUS', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        l = length * s
        
        if vertical:
            self.body = Line([0, l/2, 0], [0, -l/2, 0], color=c, stroke_width=6)
            self.add(self.body)
            
            for i in range(taps):
                y = l/2 - (i + 1) * (l / (taps + 1))
                self._add_pin(f'tap_{i}', np.array([0, y, 0]))
        else:
            self.body = Line([-l/2, 0, 0], [l/2, 0, 0], color=c, stroke_width=6)
            self.add(self.body)
            
            for i in range(taps):
                x = -l/2 + (i + 1) * (l / (taps + 1))
                self._add_pin(f'tap_{i}', np.array([x, 0, 0]))
                
        self.bg = self.body
        self._build_label(ORIGIN, font_size=12)

class CrossbarSwitch(HWComponent):
    def __init__(self, n_inputs=4, n_outputs=4, label='XBAR', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        w = n_inputs * 0.4 * s
        h = n_outputs * 0.4 * s
        
        self.body = Rectangle(width=w, height=h, fill_color=c, fill_opacity=0.1, stroke_color=c, stroke_width=2)
        self.add(self.body)
        
        # Draw grid
        for i in range(n_inputs):
            x = -w/2 + (i + 0.5) * (w / n_inputs)
            self.add(Line([x, h/2, 0], [x, -h/2, 0], color=c, stroke_width=1, stroke_opacity=0.5))
            
            pin_pos = np.array([x, h/2, 0])
            self.add(Line(pin_pos + UP*0.2*s, pin_pos, color=c, stroke_width=2))
            self._add_pin(f'in_{i}', pin_pos + UP*0.2*s)
            
        for i in range(n_outputs):
            y = h/2 - (i + 0.5) * (h / n_outputs)
            self.add(Line([-w/2, y, 0], [w/2, y, 0], color=c, stroke_width=1, stroke_opacity=0.5))
            
            pin_pos = np.array([w/2, y, 0])
            self.add(Line(pin_pos, pin_pos + RIGHT*0.2*s, color=c, stroke_width=2))
            self._add_pin(f'out_{i}', pin_pos + RIGHT*0.2*s)
            
        self.bg = self.body
        self._build_label([0, -h/2 - 0.2*s, 0], font_size=12)

# ==========================================
# SECTION 8: SkyWater 130nm & Custom Macros
# ==========================================
class ICG(HWComponent):
    def __init__(self, label='ICG', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        w, h = 0.8*s, 1.2*s
        self.body = Rectangle(width=w, height=h, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        latch_txt = Text("L", font="Consolas", font_size=12*s, color=c).move_to([-w/4, 0, 0])
        and_txt = Text("&", font="Consolas", font_size=12*s, color=c).move_to([w/4, 0, 0])
        self.add(latch_txt, and_txt)
        
        p_clk = np.array([-w/2, -h/4, 0])
        p_en = np.array([-w/2, h/4, 0])
        p_clk_out = np.array([w/2, 0, 0])
        
        self.add(Line(p_clk + LEFT*0.2*s, p_clk, color=c, stroke_width=2))
        self.add(Line(p_en + LEFT*0.2*s, p_en, color=c, stroke_width=2))
        self.add(Line(p_clk_out, p_clk_out + RIGHT*0.2*s, color=c, stroke_width=2))
        
        self._add_pin('clk_in', p_clk + LEFT*0.2*s)
        self._add_pin('en', p_en + LEFT*0.2*s)
        self._add_pin('clk_out', p_clk_out + RIGHT*0.2*s)
        
        self.bg = self.body
        self._build_label(ORIGIN, font_size=12)

class ScanDFF(HWComponent):
    def __init__(self, label='SDFF', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        w, h = 0.8*s, 1.4*s
        self.body = Rectangle(width=w, height=h, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        clk_tri = Polygon([-w/2, -h/4+0.1*s, 0], [-w/2+0.15*s, -h/4, 0], [-w/2, -h/4-0.1*s, 0], stroke_color=c, stroke_width=2)
        self.add(clk_tri)
        
        pd = np.array([-w/2, h/4, 0])
        psi = np.array([-w/2, h/8, 0])
        pse = np.array([-w/2, 0, 0])
        pclk = np.array([-w/2, -h/4, 0])
        pq = np.array([w/2, h/4, 0])
        
        self.add(Line(pd + LEFT*0.2*s, pd, color=c, stroke_width=2))
        self.add(Line(psi + LEFT*0.2*s, psi, color=c, stroke_width=2))
        self.add(Line(pse + LEFT*0.2*s, pse, color=c, stroke_width=2))
        self.add(Line(pclk + LEFT*0.2*s, pclk, color=c, stroke_width=2))
        self.add(Line(pq, pq + RIGHT*0.2*s, color=c, stroke_width=2))
        
        self._add_pin('d', pd + LEFT*0.2*s)
        self._add_pin('si', psi + LEFT*0.2*s)
        self._add_pin('se', pse + LEFT*0.2*s)
        self._add_pin('clk', pclk + LEFT*0.2*s)
        self._add_pin('q', pq + RIGHT*0.2*s)
        
        self.bg = self.body
        self._build_label(ORIGIN, font_size=12)

class LevelShifter(HWComponent):
    def __init__(self, label='LS', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        w, h = 0.8*s, 1.2*s
        self.body = Rectangle(width=w, height=h, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        self.add(Line([0, h/2, 0], [0, -h/2, 0], color=c, stroke_width=2.5))
        
        pin_in = np.array([-w/2, 0, 0])
        pin_out = np.array([w/2, 0, 0])
        
        self.add(Line(pin_in + LEFT*0.2*s, pin_in, color=c, stroke_width=2))
        self.add(Line(pin_out, pin_out + RIGHT*0.2*s, color=c, stroke_width=2))
        
        self._add_pin('in', pin_in + LEFT*0.2*s)
        self._add_pin('out', pin_out + RIGHT*0.2*s)
        
        self.bg = self.body
        self._build_label(ORIGIN, font_size=12)

class IsolationCell(HWComponent):
    def __init__(self, label='ISO', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        pts = []
        pts.append([-0.6*s, -0.4*s, 0])
        pts.append([-0.6*s, 0.4*s, 0])
        pts.append([0.0*s, 0.4*s, 0])
        for angle in np.linspace(PI/2, -PI/2, 20):
            pts.append([0.4*s * np.cos(angle), 0.4*s * np.sin(angle), 0])
        pts.append([0.0*s, -0.4*s, 0])
        
        self.body = Polygon(*pts, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        pin_in = np.array([-0.6*s, 0, 0])
        pin_en = np.array([0, 0.4*s, 0])
        pin_out_stub = np.array([0.6*s, 0, 0])
        
        self.add(Line(pin_in + LEFT*0.2*s, pin_in, color=c, stroke_width=2))
        self.add(Line(pin_en + UP*0.2*s, pin_en, color=c, stroke_width=2))
        self.add(Line(np.array([0.4*s, 0, 0]), pin_out_stub, color=c, stroke_width=2))
        
        self._add_pin('in', pin_in + LEFT*0.2*s)
        self._add_pin('iso_en', pin_en + UP*0.2*s)
        self._add_pin('out', pin_out_stub)
        
        self.bg = self.body
        self._build_label([0, -0.2*s, 0], font_size=12)

class TieCell(HWComponent):
    def __init__(self, label='1', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        w, h = 0.4*s, 0.4*s
        self.body = Rectangle(width=w, height=h, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        pin_out = np.array([w/2, 0, 0])
        self.add(Line(pin_out, pin_out + RIGHT*0.2*s, color=c, stroke_width=2))
        
        self._add_pin('out', pin_out + RIGHT*0.2*s)
        
        self.bg = self.body
        self._build_label(ORIGIN, font_size=12)

class AOIGate(HWComponent):
    def __init__(self, label='AOI', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        w, h = 0.8*s, 1.2*s
        self.body = Rectangle(width=w, height=h, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        pin_a1 = np.array([-w/2, h/4, 0])
        pin_a2 = np.array([-w/2, h/8, 0])
        pin_b1 = np.array([-w/2, -h/8, 0])
        pin_b2 = np.array([-w/2, -h/4, 0])
        pin_out = np.array([w/2, 0, 0])
        
        self.add(Line(pin_a1 + LEFT*0.2*s, pin_a1, color=c, stroke_width=2))
        self.add(Line(pin_a2 + LEFT*0.2*s, pin_a2, color=c, stroke_width=2))
        self.add(Line(pin_b1 + LEFT*0.2*s, pin_b1, color=c, stroke_width=2))
        self.add(Line(pin_b2 + LEFT*0.2*s, pin_b2, color=c, stroke_width=2))
        self.add(Line(pin_out, pin_out + RIGHT*0.2*s, color=c, stroke_width=2))
        
        bubble = Circle(radius=0.08*s, color=c, stroke_width=2.5).move_to(pin_out + RIGHT*0.08*s)
        self.add(bubble)
        self.add(Line(bubble.get_right(), pin_out + RIGHT*0.2*s, color=c, stroke_width=2))
        
        self._add_pin('a1', pin_a1 + LEFT*0.2*s)
        self._add_pin('a2', pin_a2 + LEFT*0.2*s)
        self._add_pin('b1', pin_b1 + LEFT*0.2*s)
        self._add_pin('b2', pin_b2 + LEFT*0.2*s)
        self._add_pin('out', pin_out + RIGHT*0.2*s)
        
        self.bg = self.body
        self._build_label(ORIGIN, font_size=12)

class OAIGate(HWComponent):
    def __init__(self, label='OAI', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        
        w, h = 0.8*s, 1.2*s
        self.body = Rectangle(width=w, height=h, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        pin_a1 = np.array([-w/2, h/4, 0])
        pin_a2 = np.array([-w/2, h/8, 0])
        pin_b1 = np.array([-w/2, -h/8, 0])
        pin_b2 = np.array([-w/2, -h/4, 0])
        pin_out = np.array([w/2, 0, 0])
        
        self.add(Line(pin_a1 + LEFT*0.2*s, pin_a1, color=c, stroke_width=2))
        self.add(Line(pin_a2 + LEFT*0.2*s, pin_a2, color=c, stroke_width=2))
        self.add(Line(pin_b1 + LEFT*0.2*s, pin_b1, color=c, stroke_width=2))
        self.add(Line(pin_b2 + LEFT*0.2*s, pin_b2, color=c, stroke_width=2))
        self.add(Line(pin_out, pin_out + RIGHT*0.2*s, color=c, stroke_width=2))
        
        bubble = Circle(radius=0.08*s, color=c, stroke_width=2.5).move_to(pin_out + RIGHT*0.08*s)
        self.add(bubble)
        self.add(Line(bubble.get_right(), pin_out + RIGHT*0.2*s, color=c, stroke_width=2))
        
        self._add_pin('a1', pin_a1 + LEFT*0.2*s)
        self._add_pin('a2', pin_a2 + LEFT*0.2*s)
        self._add_pin('b1', pin_b1 + LEFT*0.2*s)
        self._add_pin('b2', pin_b2 + LEFT*0.2*s)
        self._add_pin('out', pin_out + RIGHT*0.2*s)
        
        self.bg = self.body
        self._build_label(ORIGIN, font_size=12)

class CustomMacro(HWComponent):
    def __init__(self, width=2.0, height=2.0, custom_pins=None, label='', theme=None, color=None, scale=1.0):
        super().__init__(label, theme, color, scale)
        s = scale
        c = self._color
        w = width * s
        h = height * s
        
        self.body = Rectangle(width=w, height=h, fill_color=c, fill_opacity=0.15, stroke_color=c, stroke_width=2.5)
        self.add(self.body)
        
        if custom_pins is None:
            custom_pins = {}
            
        edge_pins = {'TOP': [], 'BOTTOM': [], 'LEFT': [], 'RIGHT': []}
        if isinstance(custom_pins, dict):
            for name, edge in custom_pins.items():
                if edge in edge_pins:
                    edge_pins[edge].append(name)
        elif isinstance(custom_pins, list):
            for pin in custom_pins:
                if isinstance(pin, dict):
                    name = pin.get('name')
                    edge = pin.get('edge', 'LEFT')
                    if edge in edge_pins:
                        edge_pins[edge].append(name)
                        
        for edge, pins in edge_pins.items():
            n = len(pins)
            if n == 0: continue
            
            for i, name in enumerate(pins):
                if edge == 'TOP':
                    x = -w/2 + (i + 1) * w / (n + 1)
                    pos = np.array([x, h/2, 0])
                    self.add(Line(pos, pos + UP*0.2*s, color=c, stroke_width=2))
                    self._add_pin(name, pos + UP*0.2*s)
                elif edge == 'BOTTOM':
                    x = -w/2 + (i + 1) * w / (n + 1)
                    pos = np.array([x, -h/2, 0])
                    self.add(Line(pos, pos + DOWN*0.2*s, color=c, stroke_width=2))
                    self._add_pin(name, pos + DOWN*0.2*s)
                elif edge == 'LEFT':
                    y = h/2 - (i + 1) * h / (n + 1)
                    pos = np.array([-w/2, y, 0])
                    self.add(Line(pos, pos + LEFT*0.2*s, color=c, stroke_width=2))
                    self._add_pin(name, pos + LEFT*0.2*s)
                elif edge == 'RIGHT':
                    y = h/2 - (i + 1) * h / (n + 1)
                    pos = np.array([w/2, y, 0])
                    self.add(Line(pos, pos + RIGHT*0.2*s, color=c, stroke_width=2))
                    self._add_pin(name, pos + RIGHT*0.2*s)

        self.bg = self.body
        self._build_label(ORIGIN, font_size=12)

# ==========================================
# SECTION 9: Shape Registry
# ==========================================
SHAPE_REGISTRY = {
    # Logic
    'and': ANDGate,
    'or': ORGate,
    'nand': NANDGate,
    'nor': NORGate,
    'xor': XORGate,
    'not': NOTGate,
    'buffer': BufferGate,
    # Datapath
    'mux': MuxSymbol,
    'demux': DemuxSymbol,
    'adder': AdderSymbol,
    'alu': ALUSymbol,
    'comparator': ComparatorSymbol,
    # Storage
    'dff': DFlipFlop,
    'sr_latch': SRLatch,
    'regfile': RegisterFile,
    'fifo': FifoQueue,
    'fifo_2d': Fifo2D,
    # Analog
    'nmos': NMOSTransistor,
    'pmos': PMOSTransistor,
    'resistor': Resistor,
    'capacitor': Capacitor,
    'ground': Ground,
    'vdd': VDD,
    'switch': Switch,
    # Interconnect
    'bus': BusBar,
    'crossbar': CrossbarSwitch,
    # SkyWater 130nm & Custom
    'icg': ICG,
    'sdff': ScanDFF,
    'level_shifter': LevelShifter,
    'iso_cell': IsolationCell,
    'tie': TieCell,
    'aoi': AOIGate,
    'oai': OAIGate,
    'custom': CustomMacro,
    # Fallback
    'box': None,
}
