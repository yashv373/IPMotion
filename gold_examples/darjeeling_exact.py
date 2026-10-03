import sys, os
from manim import *

config.background_color = WHITE
config.pixel_width = 1920
config.pixel_height = 1080
config.frame_width = 30

BLUE_1GHZ = "#86D6E2"
PURP_250MHZ = "#997BB5"
GRAY_LOGIC = "#A6A6A6"
BG_WRAPPER = "#FFFFFF"
BG_IP = "#F0F0F0"
BG_DOMAIN = "#DFDFDF"
BLUE_STROKE = "#1E40AF"
ORANGE_IND = "#F59E0B"
WIRE_GRAY = "#6B7280"

class DarjeelingExact(Scene):
    def construct(self):
        all_elements = Group()

        def make_box(text, x, y, w, h, fill, text_color=BLACK, stroke=None, dotted=False, ind=False, font_size=20):
            if stroke is None:
                stroke = fill
            
            rect = RoundedRectangle(width=w, height=h, corner_radius=0.1, 
                                    fill_color=fill, fill_opacity=1.0, 
                                    stroke_color=stroke, stroke_width=3)
            if dotted:
                rect = DashedVMobject(rect, num_dashes=30)
                
            txt = Text(text, color=text_color, font="Arial", weight=BOLD, line_spacing=0.6, font_size=font_size)
            max_w = w - 0.2
            max_h = h - 0.2
            if txt.width > max_w:
                txt.scale(max_w / txt.width)
            if txt.height > max_h:
                txt.scale(max_h / txt.height)
                
            group = VGroup(rect, txt)
            if ind:
                sq = Square(side_length=0.2, fill_color=ORANGE_IND, fill_opacity=1.0, stroke_width=0)
                sq.move_to(rect.get_corner(UL) + RIGHT*0.2 + DOWN*0.2)
                group.add(sq)
                
            group.move_to([x, -y, 0])
            all_elements.add(group)
            return group

        def make_mux(x, y, w, h, fill, stroke):
            p1 = [x - w/2, -y + h/2, 0]
            p2 = [x + w/2, -y + h/2, 0]
            p3 = [x + w/3, -y - h/2, 0]
            p4 = [x - w/3, -y - h/2, 0]
            poly = Polygon(p1, p2, p3, p4, fill_color=fill, fill_opacity=1.0, stroke_color=stroke, stroke_width=2)
            all_elements.add(poly)
            return poly

        def draw_wire(start_obj, end_obj, start_edge=DOWN, end_edge=UP, manhattan=False, color=WIRE_GRAY):
            start_pt = start_obj.get_edge_center(start_edge)
            end_pt = end_obj.get_edge_center(end_edge)
            
            if manhattan:
                mid_pt1 = [start_pt[0], (start_pt[1] + end_pt[1])/2, 0]
                mid_pt2 = [end_pt[0], (start_pt[1] + end_pt[1])/2, 0]
                # If moving horizontally first
                if start_edge in [LEFT, RIGHT] and end_edge in [UP, DOWN]:
                    mid_pt1 = [end_pt[0], start_pt[1], 0]
                    path = VGroup(
                        Line(start_pt, mid_pt1, color=color, stroke_width=4),
                        Arrow(mid_pt1, end_pt, color=color, stroke_width=4, buff=0, max_tip_length_to_length_ratio=0.1)
                    )
                else:
                    path = VGroup(
                        Line(start_pt, mid_pt1, color=color, stroke_width=4),
                        Line(mid_pt1, mid_pt2, color=color, stroke_width=4),
                        Arrow(mid_pt2, end_pt, color=color, stroke_width=4, buff=0, max_tip_length_to_length_ratio=0.1)
                    )
                all_elements.add(path)
                return path
            else:
                arr = Arrow(start_pt, end_pt, color=color, stroke_width=4, buff=0, max_tip_length_to_length_ratio=0.1)
                all_elements.add(arr)
                return arr

        # Grid system
        BW = 2.4
        BH = 1.0
        DX = 0.4
        DY = 0.4
        
        C0, C1, C2, C3 = 0, 2.8, 5.6, 8.4
        R0, R1, R2, R3, R4, R5, R6, R7 = 0, 1.4, 2.8, 4.2, 5.6, 7.0, 8.4, 9.8
        
        C4, C5, C6 = 12.0, 14.4, 16.8
        
        # --- Background Domains ---
        wrap = RoundedRectangle(width=23.5, height=18.5, corner_radius=0, fill_color=BG_WRAPPER, fill_opacity=1, stroke_color=BLACK, stroke_width=3)
        wrap.move_to([8.4, -6.5, 0])
        wrap_txt = Text("SoC Integration Wrapper (chip_darjeeling_*)", color=BLACK, font="Arial", weight=BOLD, font_size=28)
        wrap_txt.move_to(wrap.get_corner(UL) + RIGHT*0.2 + DOWN*0.4, aligned_edge=LEFT)
        all_elements.add(wrap, wrap_txt)
        
        ip_bg = RoundedRectangle(width=22.5, height=14.0, corner_radius=0, fill_color=BG_IP, fill_opacity=1, stroke_width=0)
        ip_bg.move_to([8.4, -5.5, 0])
        ip_txt = Text("OpenTitan Integrated IP (top_darjeeling)", color=BLACK, font="Arial", weight=BOLD, font_size=24)
        ip_txt.move_to(ip_bg.get_corner(UL) + RIGHT*0.2 + DOWN*0.4, aligned_edge=LEFT)
        all_elements.add(ip_bg, ip_txt)
        
        hi_bg = RoundedRectangle(width=11.6, height=11.2, corner_radius=0, fill_color=BG_DOMAIN, fill_opacity=1, stroke_width=0)
        hi_bg.move_to([4.2, -4.9, 0])
        hi_txt = Text("Hi-Speed Domain", color=BLACK, font="Arial", weight=BOLD, font_size=24)
        hi_txt.move_to(hi_bg.get_corner(UL) + RIGHT*0.2 + DOWN*0.4, aligned_edge=LEFT)
        all_elements.add(hi_bg, hi_txt)
        
        lo_bg = RoundedRectangle(width=8.8, height=11.2, corner_radius=0, fill_color=BG_DOMAIN, fill_opacity=1, stroke_width=0)
        lo_bg.move_to([14.4, -4.9, 0])
        lo_txt = Text("Low-Speed Domain", color=BLACK, font="Arial", weight=BOLD, font_size=24)
        lo_txt.move_to(lo_bg.get_corner(UL) + RIGHT*0.2 + DOWN*0.4, aligned_edge=LEFT)
        all_elements.add(lo_bg, lo_txt)

        # --- Hi-Speed Domain Blocks ---
        ibex = make_box("Ibex Core\n(RV32IMCB)", (C0+C1)/2, (R0+R1)/2, BW*2+DX, BH*2+DY, BLUE_1GHZ)
        intr = make_box("Interrupt\nController", C2, R0, BW, BH, BLUE_1GHZ)
        rom  = make_box("ROM\nPartitions 1/2", C3, R0, BW, BH, BLUE_1GHZ)
        msram= make_box("Main SRAM", C2, R1, BW, BH, BLUE_1GHZ)
        mbsram=make_box("Shared\nMailbox SRAM", C3, R1, BW, BH, BLUE_1GHZ)
        
        main_xbar = make_box("Main TL-UL\nCrossbar", (C0+C3)/2, R2, BW*4+DX*3, BH, BLUE_1GHZ)
        
        otbn = make_box("OTBN", C0, R3, BW, BH, BLUE_1GHZ)
        kmac = make_box("KMAC", C1, R3, BW, BH, BLUE_1GHZ)
        edn  = make_box("EDN 0 / 1", C2, R3, BW, BH, BLUE_1GHZ)
        csrng= make_box("CSRNG", C3, R3, BW, BH, BLUE_1GHZ)
        
        keymgr = make_box("Key Manager\nDPE", C0, R4, BW, BH, BLUE_1GHZ)
        hmac   = make_box("HMAC", C1, R4, BW, BH, BLUE_1GHZ)
        aes    = make_box("AES", C2, R4, BW, BH, BLUE_1GHZ)
        dbgmod = make_box("Debug\nModule", C3, R4, BW, BH, BLUE_1GHZ)
        
        dma    = make_box("DMA", C0, R5, BW, BH, BLUE_1GHZ)
        
        # SoC Proxy is taller to fit the Mux and Base Addr Trans inside it visually
        proxy  = make_box("SoC Proxy", C1, R5-0.2, BW, BH*1.4, BLUE_1GHZ)
        mux    = make_mux(C1, R5+0.1, 1.4, 0.3, BLUE_1GHZ, BLUE_STROKE)
        base_addr = make_box("Base Addr Translation", C1, R5+0.55, BW-0.2, 0.4, BLUE_1GHZ, stroke=BLUE_STROKE, font_size=12)
        
        mbox   = make_box("9 x Mailboxes", C2, R5, BW, BH, BLUE_1GHZ)
        jtagmb = make_box("JTAG Mailbox", C3, R5, BW, BH, BLUE_1GHZ)
        
        mbx_xbar = make_box("Mbx TL-UL\nCrossbar", C2, R6, BW, BH, BLUE_1GHZ)
        dbg_xbar = make_box("Dbg TL-UL\nCrossbar", C3, R6, BW, BH, BLUE_1GHZ, stroke=BLUE_STROKE)
        
        acc = make_box("Access Ctrl\nRange Check", C0+1.4, R7, BW, BH, BLUE_1GHZ, stroke=BLUE_STROKE)
        racl= make_box("RACL\nControl", C2, R7, BW, BH, BLUE_1GHZ, stroke=BLUE_STROKE)
        
        # --- Low-Speed Domain Blocks ---
        timers = make_box("Timers", C4, R0, BW, BH, PURP_250MHZ, WHITE, ind=True)
        retsram= make_box("Retention\nSRAM", C4, R1, BW, BH, PURP_250MHZ, WHITE)
        alert  = make_box("Alert Handler", C4, R3, BW, BH, PURP_250MHZ, WHITE)
        otp    = make_box("OTP (Fuse)\nController", C4, R4, BW, BH, PURP_250MHZ, WHITE)
        socdbg = make_box("SoC Debug\nController", C4, R5, BW, BH, PURP_250MHZ, WHITE, stroke=BLUE_STROKE)
        lifecycle = make_box("Life Cycle\nController", C4, R6, BW, BH, PURP_250MHZ, WHITE)
        
        peri_xbar = make_box("Peri\nTL-UL\nCross\nbar", C5, (R0+R6)/2, 1.6, BH*7+DY*6, PURP_250MHZ, WHITE)
        
        gpio   = make_box("32bit GPIO", C6, R0, BW, BH, PURP_250MHZ, WHITE)
        spid   = make_box("1x SPI Device", C6, R1, BW, BH, PURP_250MHZ, WHITE)
        spih   = make_box("1 x SPI Host", C6, R2, BW, BH, PURP_250MHZ, WHITE)
        uart   = make_box("1 x UART /\n1x I2C", C6, R3, BW, BH, PURP_250MHZ, WHITE)
        pinmux = make_box("Pinmux", C6, R4, BW, BH, PURP_250MHZ, WHITE)
        sensor = make_box("Sensor\nControl", C6, R5, BW, BH, PURP_250MHZ, WHITE, ind=True)
        pwr    = make_box("Pwr &\nClk/Rst Mgrs", C6, R6, BW, BH, PURP_250MHZ, WHITE, ind=True)
        
        # --- Bottom Blocks ---
        ctn_xbar = make_box("CTN TL-UL\nCrossbar", (C0+C3)/2, 11.2, BW*4+DX*3, BH, BLUE_1GHZ)
        jtag_tap = make_box("JTAG TAP", C4, 11.2, BW, BH, BLUE_1GHZ, stroke=BLUE_STROKE)
        ana_top  = make_box("Analog Sensor\nTop", C6, 11.2, BW, BH, BLUE_1GHZ, stroke=BLUE_STROKE, ind=True)
        
        padring  = make_box("Padring", C5, 13.0, BW*3+DX*2, BH*1.2, GRAY_LOGIC)
        
        ctn_sram = make_box("Shared CTN\nSRAM", 0.5, 13.0, BW, BH, BLUE_1GHZ)
        ctn_peri = make_box("Shared\nPeripherals", C2, 13.0, BW, BH, BLUE_1GHZ, dotted=True)
        ctn_pinmux=make_box("Shared\nPinmux", C3, 13.0, BW, BH, PURP_250MHZ, WHITE, dotted=True)

        ext_peri = make_box("External\nPeripherals", 13.2, 14.8, BW, BH, BG_WRAPPER, dotted=True)
        ext_spi  = make_box("External SPI\nFlash", 16.8, 14.8, BW, BH, BG_WRAPPER, dotted=True)

        # --- WIRING (Static grey arrows) ---
        draw_wire(ibex, main_xbar, DOWN, UP)
        draw_wire(intr, main_xbar, DOWN, UP)
        draw_wire(msram, main_xbar, DOWN, UP)
        
        draw_wire(main_xbar, otbn, DOWN, UP)
        draw_wire(main_xbar, kmac, DOWN, UP)
        draw_wire(main_xbar, edn, DOWN, UP)
        draw_wire(main_xbar, csrng, DOWN, UP)
        
        draw_wire(keymgr, dma, DOWN, UP)
        
        # DMA to Mux (manhattan right then down)
        draw_wire(dma, mux, RIGHT, UP, manhattan=True)
        
        # Main Xbar to proxy
        draw_wire(main_xbar, proxy, DOWN, UP, manhattan=True) 
        
        # Mux to Base Addr
        draw_wire(mux, base_addr, DOWN, UP)
        
        # Base Addr to Access Ctrl (manhattan)
        draw_wire(base_addr, acc, DOWN, UP, manhattan=True)
        
        # Access Ctrl to CTN Xbar
        draw_wire(acc, ctn_xbar, DOWN, UP)
        
        # CTN Xbar down
        draw_wire(ctn_xbar, ctn_sram, DOWN, UP, manhattan=True)
        draw_wire(ctn_xbar, ctn_peri, DOWN, UP)
        draw_wire(ctn_xbar, ctn_pinmux, DOWN, UP, manhattan=True)
        
        # Main Xbar to Peri Xbar
        draw_wire(main_xbar, peri_xbar, RIGHT, LEFT, manhattan=True)
        
        # Peri Xbar to Left and Right
        draw_wire(peri_xbar, timers, LEFT, RIGHT)
        draw_wire(peri_xbar, gpio, RIGHT, LEFT)
        draw_wire(peri_xbar, alert, LEFT, RIGHT)
        draw_wire(peri_xbar, pinmux, RIGHT, LEFT)
        draw_wire(peri_xbar, pwr, RIGHT, LEFT)

        # Scale and center everything to fix the cropped frame issue
        # Use scale_to_fit_height to guarantee it fits safely within the frame_height (16.875)
        all_elements.scale_to_fit_height(14.5)
        all_elements.center()
        
        self.add(all_elements)

        # Animation flow
        req = Circle(radius=0.3, fill_color="#FF4444", fill_opacity=1, stroke_width=2, stroke_color=BLACK)
        req_lbl = Text("REQ", color=WHITE, font_size=18, font="Arial", weight=BOLD).move_to(req)
        token = VGroup(req, req_lbl)
        
        self.wait(1)
        
        # Flow padring -> CTN -> Access Ctrl -> Base Addr (Mux) -> Proxy -> Main Xbar -> Ibex
        token.move_to(padring.get_left() + LEFT*0.5)
        self.play(FadeIn(token))
        
        self.play(token.animate.move_to(ctn_xbar.get_bottom()))
        self.play(token.animate.move_to(acc.get_bottom()))
        
        self.play(acc[0].animate.set_fill("#FF4444", opacity=0.8), run_time=0.3)
        self.play(acc[0].animate.set_fill(BLUE_1GHZ, opacity=1.0), run_time=0.3)
        
        self.play(token.animate.move_to(base_addr.get_bottom()))
        self.play(token.animate.move_to(mux.get_center()))
        self.play(token.animate.move_to(proxy.get_top()))
        
        self.play(token.animate.move_to(main_xbar.get_bottom()))
        self.play(token.animate.move_to(ibex.get_bottom()))
        
        self.play(ibex[0].animate.set_fill("#44FF44", opacity=0.8), run_time=0.5)
        self.play(ibex[0].animate.set_fill(BLUE_1GHZ, opacity=1.0), run_time=0.5)
        
        self.play(FadeOut(token))
        self.wait(2)
