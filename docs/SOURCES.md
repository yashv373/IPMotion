# Sources and credits

Every reference diagram and every structure IPMotion animates is taken from published work, so the technical
accuracy of the picture is not ours to invent. This file is the citation list. If a diagram is added, it is
added here in the same commit.

## Reference block diagrams (`opentitan_archs/`)

The three OpenTitan top-level block diagrams are the work of lowRISC and the OpenTitan project, used under the
Apache License 2.0. They are reproduced for study and comparison; we redraw them, we do not claim them.

| File | Diagram | Source |
|---|---|---|
| `top_darjeeling_block_diagram.png` | OpenTitan Darjeeling top level | OpenTitan project, lowRISC &mdash; https://opentitan.org |
| `top_earlgrey_block_diagram.png` | OpenTitan Earlgrey top level | OpenTitan project, lowRISC &mdash; https://opentitan.org |
| `peppermint.png` | OpenTitan Peppermint (iRoT / Secure Enclave) | OpenTitan project, lowRISC &mdash; https://opentitan.org |

OpenTitan is licensed under Apache-2.0: https://github.com/lowRISC/opentitan/blob/master/LICENSE

## Structures animated from the literature (`gold_examples/`)

| Example | Structure | Citation |
|---|---|---|
| `systolic_array_mac.py` | 4x4 output-stationary systolic MAC array | H.T. Kung and C.E. Leiserson, "Systolic Arrays (for VLSI)", Sparse Matrix Proceedings, 1978. N.P. Jouppi et al., "In-Datacenter Performance Analysis of a Tensor Processing Unit", ISCA 2017. |
| `axi_read_handshake.py` | AXI4 read address / read data handshake | ARM, "AMBA AXI and ACE Protocol Specification" (AXI4), sections on the AR and R channels. |

## What is ours

The drawing code, the layout engine, the geometric linter, the conformance and fidelity checks, the colour
scheme and the animation choices. The hand-transcribed `bench/truth/*.yaml` notes are our reading of the
published pictures, and they are notes about those pictures, not a substitute for them.

## Rule

A new animation gets its structure from a published, citable source &mdash; a specification, a paper, or a
project's own documentation &mdash; and lands in this file with that citation. We do not invent hardware.
