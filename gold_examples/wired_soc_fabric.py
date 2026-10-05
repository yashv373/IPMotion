"""A small SoC fabric, wired entirely with the library router. This is the shape of a correct answer.

Structure is a generic AMBA-style SoC interconnect: a CPU and a DMA master on one bus, a crossbar, and memory
and peripheral slaves, as described in ARM's "AMBA AXI and ACE Protocol Specification" and the standard
master/interconnect/slave organisation. See docs/SOURCES.md.

Why this example exists: every other example places its wires by hand, with coordinates worked out by a human.
A model cannot do that, and when it tries, the wire runs across whatever sits between the two blocks and hides
its name. This example does nothing by hand --

    blocks = [cpu, dma, xbar, sram, rom, uart, spi]
    self.add(wire(cpu, xbar, avoid=blocks))

  * ONE CALL PER CONNECTION. wire() finds a route around everything in `avoid` and draws the arrowhead.
  * PASS EVERY BLOCK IN avoid. The wire's own two ends are skipped automatically, so one list works for all.
  * NOTHING IS POSITIONED BY HAND. There is not a single literal wire coordinate in this file.
  * REGION, THEN BLOCKS, THEN WIRES. The library layers them: region behind, wires behind the blocks, blocks on
    top, so a wire can never cover a block's name.
"""
from manim import Scene

from ipmotion_lib import Banner, DomainGroup, IPBlock, Theme, ui_text, wire

ACTIVE = "#FFD700"
DATA = "#00FFF0"


class WiredSocFabric(Scene):
    def construct(self):
        theme = Theme()

        banner = Banner("A small SoC fabric: every wire routed by the library", theme)
        banner.move_to([0, 3.5, 0])
        self.add(banner)

        soc = DomainGroup("SoC interconnect domain", 0, -0.15, 11.6, 4.9, "#141D28", stroke="#64748B")
        self.add(soc)

        # ---- masters on the left, crossbar in the middle, slaves on the right ----
        cpu = IPBlock("CPU (RV32)", theme, width=2.1, height=0.9)
        cpu.move_to([-4.3, 1.15, 0])
        dma = IPBlock("DMA Engine", theme, width=2.1, height=0.9)
        dma.move_to([-4.3, -1.35, 0])
        xbar = IPBlock("AXI Crossbar", theme, width=1.5, height=3.3)
        xbar.move_to([-1.1, -0.1, 0])
        sram = IPBlock("Main SRAM", theme, width=2.2, height=0.8)
        sram.move_to([2.6, 1.35, 0])
        rom = IPBlock("Boot ROM", theme, width=2.2, height=0.8)
        rom.move_to([2.6, 0.25, 0])
        uart = IPBlock("UART", theme, width=2.2, height=0.8)
        uart.move_to([2.6, -0.85, 0])
        spi = IPBlock("SPI Host", theme, width=2.2, height=0.8)
        spi.move_to([2.6, -1.95, 0])

        blocks = [cpu, dma, xbar, sram, rom, uart, spi]
        for b in blocks:
            self.add(b)

        # ---- one call per connection, and not a single wire coordinate written by hand ----
        links = {
            "cpu": wire(cpu, xbar, avoid=blocks, heads="both"),
            "dma": wire(dma, xbar, avoid=blocks, heads="both"),
            "sram": wire(xbar, sram, avoid=blocks, heads="both"),
            "rom": wire(xbar, rom, avoid=blocks),
            "uart": wire(xbar, uart, avoid=blocks, heads="both"),
            "spi": wire(xbar, spi, avoid=blocks, heads="both"),
            # a long one: the DMA talks to the SRAM directly, and the route has to get past the crossbar
            "dma_sram": wire(dma, sram, avoid=blocks),
        }
        for w in links.values():
            self.add(w)

        note = ui_text("every wire above was placed by wire(), not by hand", 16, theme.muted)
        note.move_to([0, -3.15, 0])
        self.add(note)

        self.wait(1.0)
        for text, lit, link in (
            ("The CPU issues a read on the fabric", cpu, "cpu"),
            ("The crossbar selects the Main SRAM", xbar, "sram"),
            ("The SRAM returns the data", sram, "sram"),
            ("Meanwhile the DMA moves a block to the same SRAM", dma, "dma_sram"),
            ("A peripheral write reaches the UART", uart, "uart"),
        ):
            self.play(banner.update_text(text, theme, ACTIVE),
                      lit.bg.animate.set_color(ACTIVE),
                      links[link].animate.set_color(DATA), run_time=0.8)
            self.wait(1.2)
            self.play(lit.bg.animate.set_color(theme.panel),
                      links[link].animate.set_color("#9CA3AF"), run_time=0.5)

        self.play(banner.update_text("Seven blocks, seven links, no coordinates typed by hand", theme, DATA),
                  run_time=0.8)
        self.wait(2.5)
