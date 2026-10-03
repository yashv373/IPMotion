from manim import *
from ipmotion_lib import *

class SymbolShowcase(Scene):
    def construct(self):
        theme = Theme()
        all_elements = Group()

        # ═══ Entities ═══
        if 'and' in SHAPE_REGISTRY and SHAPE_REGISTRY['and'] is not None:
            g1 = SHAPE_REGISTRY['and'](label='AND', theme=theme, color=theme.active)
            g1.move_to([-10, 4, 0])
        else:
            g1 = IPBlock('AND', theme, width=2.5, height=1.5, fill=theme.active, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            g1.move_to([-10, 4, 0])
        all_elements.add(g1)
        if 'or' in SHAPE_REGISTRY and SHAPE_REGISTRY['or'] is not None:
            g2 = SHAPE_REGISTRY['or'](label='OR', theme=theme, color=theme.success)
            g2.move_to([-7, 4, 0])
        else:
            g2 = IPBlock('OR', theme, width=2.5, height=1.5, fill=theme.success, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            g2.move_to([-7, 4, 0])
        all_elements.add(g2)
        if 'nand' in SHAPE_REGISTRY and SHAPE_REGISTRY['nand'] is not None:
            g3 = SHAPE_REGISTRY['nand'](label='NAND', theme=theme, color=theme.warning)
            g3.move_to([-4, 4, 0])
        else:
            g3 = IPBlock('NAND', theme, width=2.5, height=1.5, fill=theme.warning, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            g3.move_to([-4, 4, 0])
        all_elements.add(g3)
        if 'nor' in SHAPE_REGISTRY and SHAPE_REGISTRY['nor'] is not None:
            g4 = SHAPE_REGISTRY['nor'](label='NOR', theme=theme, color=theme.error)
            g4.move_to([-1, 4, 0])
        else:
            g4 = IPBlock('NOR', theme, width=2.5, height=1.5, fill=theme.error, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            g4.move_to([-1, 4, 0])
        all_elements.add(g4)
        if 'xor' in SHAPE_REGISTRY and SHAPE_REGISTRY['xor'] is not None:
            g5 = SHAPE_REGISTRY['xor'](label='XOR', theme=theme, color=theme.active)
            g5.move_to([2, 4, 0])
        else:
            g5 = IPBlock('XOR', theme, width=2.5, height=1.5, fill=theme.active, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            g5.move_to([2, 4, 0])
        all_elements.add(g5)
        if 'not' in SHAPE_REGISTRY and SHAPE_REGISTRY['not'] is not None:
            g6 = SHAPE_REGISTRY['not'](label='NOT', theme=theme, color=theme.muted)
            g6.move_to([5, 4, 0])
        else:
            g6 = IPBlock('NOT', theme, width=2.5, height=1.5, fill=theme.muted, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            g6.move_to([5, 4, 0])
        all_elements.add(g6)
        if 'buffer' in SHAPE_REGISTRY and SHAPE_REGISTRY['buffer'] is not None:
            g7 = SHAPE_REGISTRY['buffer'](label='BUF', theme=theme, color=theme.text)
            g7.move_to([8, 4, 0])
        else:
            g7 = IPBlock('BUF', theme, width=2.5, height=1.5, fill=theme.text, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            g7.move_to([8, 4, 0])
        all_elements.add(g7)
        if 'mux' in SHAPE_REGISTRY and SHAPE_REGISTRY['mux'] is not None:
            d1 = SHAPE_REGISTRY['mux'](label='MUX', theme=theme, color=theme.active)
            d1.move_to([-10, 1, 0])
        else:
            d1 = IPBlock('MUX', theme, width=2.5, height=1.5, fill=theme.active, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            d1.move_to([-10, 1, 0])
        all_elements.add(d1)
        if 'demux' in SHAPE_REGISTRY and SHAPE_REGISTRY['demux'] is not None:
            d2 = SHAPE_REGISTRY['demux'](label='DEMUX', theme=theme, color=theme.success)
            d2.move_to([-7, 1, 0])
        else:
            d2 = IPBlock('DEMUX', theme, width=2.5, height=1.5, fill=theme.success, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            d2.move_to([-7, 1, 0])
        all_elements.add(d2)
        if 'adder' in SHAPE_REGISTRY and SHAPE_REGISTRY['adder'] is not None:
            d3 = SHAPE_REGISTRY['adder'](label='ADD', theme=theme, color=theme.warning)
            d3.move_to([-4, 1, 0])
        else:
            d3 = IPBlock('ADD', theme, width=2.5, height=1.5, fill=theme.warning, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            d3.move_to([-4, 1, 0])
        all_elements.add(d3)
        if 'alu' in SHAPE_REGISTRY and SHAPE_REGISTRY['alu'] is not None:
            d4 = SHAPE_REGISTRY['alu'](label='ALU', theme=theme, color=theme.error)
            d4.move_to([-1, 1, 0])
        else:
            d4 = IPBlock('ALU', theme, width=2.5, height=1.5, fill=theme.error, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            d4.move_to([-1, 1, 0])
        all_elements.add(d4)
        if 'comparator' in SHAPE_REGISTRY and SHAPE_REGISTRY['comparator'] is not None:
            d5 = SHAPE_REGISTRY['comparator'](label='==', theme=theme, color=theme.active)
            d5.move_to([2, 1, 0])
        else:
            d5 = IPBlock('==', theme, width=2.5, height=1.5, fill=theme.active, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            d5.move_to([2, 1, 0])
        all_elements.add(d5)
        if 'dff' in SHAPE_REGISTRY and SHAPE_REGISTRY['dff'] is not None:
            s1 = SHAPE_REGISTRY['dff'](label='DFF', theme=theme, color=theme.active)
            s1.move_to([-10, -2, 0])
        else:
            s1 = IPBlock('DFF', theme, width=2.5, height=1.5, fill=theme.active, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            s1.move_to([-10, -2, 0])
        all_elements.add(s1)
        if 'sr_latch' in SHAPE_REGISTRY and SHAPE_REGISTRY['sr_latch'] is not None:
            s2 = SHAPE_REGISTRY['sr_latch'](label='SR', theme=theme, color=theme.success)
            s2.move_to([-7, -2, 0])
        else:
            s2 = IPBlock('SR', theme, width=2.5, height=1.5, fill=theme.success, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            s2.move_to([-7, -2, 0])
        all_elements.add(s2)
        if 'regfile' in SHAPE_REGISTRY and SHAPE_REGISTRY['regfile'] is not None:
            s3 = SHAPE_REGISTRY['regfile'](label='REG', theme=theme, color=theme.warning)
            s3.move_to([-4, -2, 0])
        else:
            s3 = IPBlock('REG', theme, width=2.5, height=1.5, fill=theme.warning, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            s3.move_to([-4, -2, 0])
        all_elements.add(s3)
        if 'fifo' in SHAPE_REGISTRY and SHAPE_REGISTRY['fifo'] is not None:
            s4 = SHAPE_REGISTRY['fifo'](label='FIFO', theme=theme, color=theme.error)
            s4.move_to([-1, -2, 0])
        else:
            s4 = IPBlock('FIFO', theme, width=2.5, height=1.5, fill=theme.error, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            s4.move_to([-1, -2, 0])
        all_elements.add(s4)
        if 'fifo_2d' in SHAPE_REGISTRY and SHAPE_REGISTRY['fifo_2d'] is not None:
            s5 = SHAPE_REGISTRY['fifo_2d'](label='FIFO2D', theme=theme, color=theme.active)
            s5.move_to([3, -2, 0])
        else:
            s5 = IPBlock('FIFO2D', theme, width=2.5, height=1.5, fill=theme.active, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            s5.move_to([3, -2, 0])
        all_elements.add(s5)
        if 'nmos' in SHAPE_REGISTRY and SHAPE_REGISTRY['nmos'] is not None:
            a1 = SHAPE_REGISTRY['nmos'](label='NMOS', theme=theme, color=theme.active)
            a1.move_to([-10, -5, 0])
        else:
            a1 = IPBlock('NMOS', theme, width=2.5, height=1.5, fill=theme.active, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            a1.move_to([-10, -5, 0])
        all_elements.add(a1)
        if 'pmos' in SHAPE_REGISTRY and SHAPE_REGISTRY['pmos'] is not None:
            a2 = SHAPE_REGISTRY['pmos'](label='PMOS', theme=theme, color=theme.success)
            a2.move_to([-7, -5, 0])
        else:
            a2 = IPBlock('PMOS', theme, width=2.5, height=1.5, fill=theme.success, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            a2.move_to([-7, -5, 0])
        all_elements.add(a2)
        if 'resistor' in SHAPE_REGISTRY and SHAPE_REGISTRY['resistor'] is not None:
            a3 = SHAPE_REGISTRY['resistor'](label='R1', theme=theme, color=theme.warning)
            a3.move_to([-4, -5, 0])
        else:
            a3 = IPBlock('R1', theme, width=2.5, height=1.5, fill=theme.warning, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            a3.move_to([-4, -5, 0])
        all_elements.add(a3)
        if 'capacitor' in SHAPE_REGISTRY and SHAPE_REGISTRY['capacitor'] is not None:
            a4 = SHAPE_REGISTRY['capacitor'](label='C1', theme=theme, color=theme.error)
            a4.move_to([-1, -5, 0])
        else:
            a4 = IPBlock('C1', theme, width=2.5, height=1.5, fill=theme.error, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            a4.move_to([-1, -5, 0])
        all_elements.add(a4)
        if 'ground' in SHAPE_REGISTRY and SHAPE_REGISTRY['ground'] is not None:
            a5 = SHAPE_REGISTRY['ground'](label='GND', theme=theme, color=theme.muted)
            a5.move_to([2, -5, 0])
        else:
            a5 = IPBlock('GND', theme, width=2.5, height=1.5, fill=theme.muted, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            a5.move_to([2, -5, 0])
        all_elements.add(a5)
        if 'vdd' in SHAPE_REGISTRY and SHAPE_REGISTRY['vdd'] is not None:
            a6 = SHAPE_REGISTRY['vdd'](label='VDD', theme=theme, color=theme.error)
            a6.move_to([5, -5, 0])
        else:
            a6 = IPBlock('VDD', theme, width=2.5, height=1.5, fill=theme.error, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            a6.move_to([5, -5, 0])
        all_elements.add(a6)
        if 'switch' in SHAPE_REGISTRY and SHAPE_REGISTRY['switch'] is not None:
            a7 = SHAPE_REGISTRY['switch'](label='SW', theme=theme, color=theme.text)
            a7.move_to([8, -5, 0])
        else:
            a7 = IPBlock('SW', theme, width=2.5, height=1.5, fill=theme.text, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            a7.move_to([8, -5, 0])
        all_elements.add(a7)
        if 'bus' in SHAPE_REGISTRY and SHAPE_REGISTRY['bus'] is not None:
            i1 = SHAPE_REGISTRY['bus'](label='BUS', theme=theme, color=theme.active)
            i1.move_to([-8, -8, 0])
        else:
            i1 = IPBlock('BUS', theme, width=2.5, height=1.5, fill=theme.active, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            i1.move_to([-8, -8, 0])
        all_elements.add(i1)
        if 'crossbar' in SHAPE_REGISTRY and SHAPE_REGISTRY['crossbar'] is not None:
            i2 = SHAPE_REGISTRY['crossbar'](label='XBAR', theme=theme, color=theme.success)
            i2.move_to([-3, -8, 0])
        else:
            i2 = IPBlock('XBAR', theme, width=2.5, height=1.5, fill=theme.success, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            i2.move_to([-3, -8, 0])
        all_elements.add(i2)
        if 'box' in SHAPE_REGISTRY and SHAPE_REGISTRY['box'] is not None:
            f1 = SHAPE_REGISTRY['box'](label='FALLBACK', theme=theme, color=theme.panel)
            f1.move_to([3, -8, 0])
        else:
            f1 = IPBlock('FALLBACK', theme, width=4, height=2, fill=theme.panel, stroke=theme.stroke, text_color=theme.text, dotted=False, ind=False, ports=[])
            f1.move_to([3, -8, 0])
        all_elements.add(f1)

        # ═══ Wires (Static) ═══
        w1 = Wire(g1, g2, start_edge=RIGHT, end_edge=LEFT, manhattan=False, color=theme.muted)
        all_elements.add(w1)

        # ═══ Connections ═══

        # ═══ Banner ═══
        banner = Banner("IPMotion V5 Symbol Library Showcase", theme)
        # Banner stays outside all_elements so it doesn't scale with the block diagram
        banner.move_to([0, 7.5, 0])

        # ═══ Auto-Scaling ═══
        # Fits the entire topology safely within the frame before animating
        all_elements.scale_to_fit_height(config.frame_height * 0.9)
        all_elements.center()
        # Shift down slightly to make room for banner
        all_elements.shift(DOWN * (config.frame_height * 0.05))

        # ═══ Draw Scene ═══
        self.play(FadeIn(banner))
        self.play(FadeIn(all_elements))
        self.wait(0.5)

        # ═══ Cycle 1 ═══
        self.play(banner.update_text("Highlight Logic Gates", theme))
        self.play(g1.bg.animate.set_color(theme.error), g2.bg.animate.set_color(theme.error))
        self.wait(0.5)

        # ═══ Cycle 2 ═══
        self.play(banner.update_text("Highlight Datapath", theme))
        self.play(d3.bg.animate.set_color(theme.active), d4.bg.animate.set_color(theme.active))
        self.wait(0.5)

        self.wait(1)
