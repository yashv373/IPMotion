import sys, os
from manim import *
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ipmotion_lib import *

class DarjeelingFull(Scene):
    def construct(self):
        theme = Theme()
        
        # We will put all elements in a group to scale them to fit the screen
        all_elements = VGroup()

        # Helper to make blocks faster
        def make_block(label, x, y, w=1.6, h=0.8, color=theme.stroke):
            b = IPBlock(label, theme, width=w, height=h)
            b.bg.set_color(color)
            b.move_to([x, y, 0])
            all_elements.add(b)
            return b

        def make_domain(label, x, y, w, h, color):
            rect = RoundedRectangle(width=w, height=h, corner_radius=0.2, stroke_color=color, stroke_width=2, fill_color=color, fill_opacity=0.1)
            rect.move_to([x, y, 0])
            t = ui_text(label, 16, color, BOLD).move_to([x, y + h/2 - 0.3, 0])
            all_elements.add(rect, t)
            return rect

        # --- DOMAINS ---
        hi_speed = make_domain("Hi-Speed Domain", -3, 0.5, 7.5, 8.5, theme.active)
        lo_speed = make_domain("Low-Speed Domain", 4.5, 0.5, 6.5, 8.5, "#A855F7") # Purple

        # --- HI-SPEED DOMAIN BLOCKS ---
        # Row 1
        ibex = make_block("Ibex Core\n(RV32IMCB)", -4.5, 3.5, w=2.5, h=1.5, color=theme.active)
        intr = make_block("Interrupt\nController", -2, 3.85, h=0.8)
        rom  = make_block("ROM Partitions", 0, 3.85, h=0.8)
        msram= make_block("Main SRAM", -2, 2.85, h=0.8)
        mbsram=make_block("Shared Mailbox", 0, 2.85, h=0.8)

        # Row 2 (Main TL-UL Crossbar)
        main_xbar = make_block("Main TL-UL Crossbar", -2.25, 1.5, w=7, h=1.0, color=theme.active)

        # Row 3
        otbn = make_block("OTBN", -5, 0.2)
        kmac = make_block("KMAC", -3, 0.2)
        edn  = make_block("EDN 0/1", -1, 0.2)
        csrng= make_block("CSRNG", 1, 0.2)

        # Row 4
        keymgr = make_block("Key Manager", -5, -0.8)
        hmac   = make_block("HMAC", -3, -0.8)
        aes    = make_block("AES", -1, -0.8)
        dbgmod = make_block("Debug Module", 1, -0.8)

        # Row 5
        dma    = make_block("DMA", -5, -1.8)
        proxy  = make_block("SoC Proxy", -3, -1.8)
        mbox   = make_block("9x Mailboxes", -1, -1.8)
        jtagmb = make_block("JTAG Mailbox", 1, -1.8)

        # Row 6
        acc    = make_block("Access Ctrl", -4, -3.0, w=1.8, h=0.8)
        racl   = make_block("RACL Control", -2, -3.0, w=1.8, h=0.8)
        mbx_xbar= make_block("Mbx Crossbar", -0.5, -2.8, w=1.5, h=0.8, color=theme.active)
        dbg_xbar= make_block("Dbg Crossbar", 1.2, -2.8, w=1.5, h=0.8, color=theme.active)

        # --- LOW-SPEED DOMAIN BLOCKS ---
        peri_xbar = make_block("Peri TL-UL\nCrossbar", 3.0, 0.5, w=1.2, h=7.5, color="#A855F7")
        
        # Left of Peri XBar
        timers = make_block("Timers", 1.5, 3.5, color="#A855F7")
        retsram= make_block("Retention SRAM", 1.5, 2.3, color="#A855F7")
        alert  = make_block("Alert Handler", 1.5, 0.5, color="#A855F7")
        otp    = make_block("OTP Controller", 1.5, -0.7, color="#A855F7")
        socdbg = make_block("SoC Debug", 1.5, -1.9, color="#A855F7")
        lifecycle = make_block("Life Cycle", 1.5, -3.1, color="#A855F7")

        # Right of Peri XBar
        gpio   = make_block("32bit GPIO", 5.5, 3.5, color="#A855F7")
        spid   = make_block("SPI Device", 5.5, 2.5, color="#A855F7")
        spih   = make_block("SPI Host", 5.5, 1.3, color="#A855F7")
        uart   = make_block("UART / I2C", 5.5, 0.1, color="#A855F7")
        pinmux = make_block("Pinmux", 5.5, -1.1, color="#A855F7")
        sensor = make_block("Sensor Control", 5.5, -2.3, color="#A855F7")
        pwr    = make_block("Pwr/Clk Mgr", 5.5, -3.5, color="#A855F7")

        # --- CTN & PADRING (Bottom) ---
        ctn_xbar = make_block("CTN TL-UL Crossbar", -2.5, -4.5, w=7, h=0.8, color=theme.active)
        jtag_tap = make_block("JTAG TAP", 3.0, -4.5, color=theme.active)
        ana_top  = make_block("Analog Sensor", 5.5, -4.5, color=theme.active)

        padring  = make_block("Padring", 4.5, -5.8, w=4, h=1.0, color=theme.muted)
        
        ctn_sram = make_block("CTN SRAM", -4.5, -5.8, color=theme.active)
        ctn_peri = make_block("Shared Peripherals", -2.0, -5.8, color=theme.active)
        ctn_pinmux=make_block("Shared Pinmux", 0.5, -5.8, color="#A855F7")

        # --- CONNECTIONS (simplified logic) ---
        # We will just draw lines for the main datapath to avoid cluttering the visual
        def connect(b1, b2, color=theme.stroke):
            l = Line(b1.get_center(), b2.get_center(), color=color, stroke_width=2).set_z_index(-1)
            all_elements.add(l)
            return l

        connect(ibex, main_xbar)
        connect(intr, main_xbar)
        connect(msram, main_xbar)
        connect(main_xbar, otbn)
        connect(main_xbar, kmac)
        connect(main_xbar, edn)
        connect(main_xbar, csrng)
        
        connect(keymgr, dma)
        connect(proxy, acc)
        connect(acc, ctn_xbar)
        connect(ctn_xbar, ctn_sram)
        
        connect(main_xbar, peri_xbar)
        
        # Scale to fit camera
        all_elements.scale(0.55)
        all_elements.center()

        # Banner
        banner = Banner("OpenTitan Darjeeling SoC Integration", theme)
        banner.bg.scale(0.8) # fit the screen width
        banner.move_to([0, 3.5, 0])

        self.add(all_elements, banner)

        # Animate a flow
        pkt_bg = GlowBox(0.4, 0.3, theme.success, theme.success)
        pkt = VGroup(pkt_bg, ui_text("REQ", 10, theme.background, BOLD))
        
        self.play(FadeIn(all_elements, banner))
        self.wait(1)

        # Host request from Padring -> CTN -> Proxy -> Main Xbar -> Ibex
        pkt.move_to(padring.get_left())
        self.play(banner.update_text("External Host issues Secure Request", theme, theme.active))
        self.play(FadeIn(pkt))
        self.play(pkt.animate.move_to(ctn_xbar.get_bottom()))
        self.play(pkt.animate.move_to(acc.get_bottom()))
        self.play(pkt.animate.move_to(proxy.get_bottom()))
        
        self.play(banner.update_text("SoC Proxy decodes request", theme, theme.warning))
        self.play(proxy.bg.animate.set_color(theme.warning))
        self.play(pkt.animate.move_to(main_xbar.get_bottom()))
        
        self.play(banner.update_text("Routed to Ibex Core", theme, theme.active))
        self.play(pkt.animate.move_to(ibex.get_bottom()))
        self.play(ibex.bg.animate.set_color(theme.success))
        self.play(FadeOut(pkt))
        
        self.wait(2)
