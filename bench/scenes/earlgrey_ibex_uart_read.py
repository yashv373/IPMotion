"""Scene for the Earlgrey full-diagram story (deterministic: no AI-written code)."""
from ipmotion.player import FullDiagramScene


class EarlgreyIbexUartRead(FullDiagramScene):
    STORY = "bench/stories/earlgrey_ibex_uart_read.yaml"
