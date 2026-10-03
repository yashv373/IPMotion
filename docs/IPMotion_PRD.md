# IPMotion: Product Requirements & Architecture Document

## 1. Product Vision
**IPMotion** is an AI-powered pipeline designed to automate the generation of high-quality, presentation-ready Manim animations for complex hardware IP concepts (e.g., AXI handshakes, FIFOs, Control Logic). 

### The Problem (Why)
Creating hardware visualization animations manually using Manim is incredibly tedious. Even when using an AI assistant (like Copilot/ChatGPT), generating a single animation requires extensive prompt engineering, manual visual corrections, and rigorous layout discipline. As documented in our internal study, a from-scratch script (Master Read) required **~50 iterations**, and a derivative script (Master Write) required **~24 iterations**. 

### The Solution (What & How)
IPMotion aims to eliminate manual iteration by building an automated, software-defined pipeline. It evolves the workflow from a "human-in-the-loop chat session" to an autonomous "Renderer-in-the-Loop" (RITL) engine that compiles, renders, and self-corrects hardware diagrams on the fly.

---

## 2. The Baseline: Manual AI-Assisted Workflow
Before building IPMotion, the baseline process relied on manual AI interaction (documented in the FDU AXI case study):
1. **Inputs:** User provides a block diagram (MS Paint) and a functional description.
2. **First Generation:** AI generates an initial Python script.
3. **Aesthetic Iteration:** User renders the script, takes screenshots, annotates visual errors (overlapping text, misaligned wires) in Paint, and feeds it back to the AI. *Rule: Fix aesthetics before logic.*
4. **Technical Iteration:** User feeds back logic corrections (e.g., "Change FD_DONE to toggle 0->1").
5. **Version Control:** Strict versioning (`v18`, `v19`) is maintained manually, always providing the full baseline script as context to prevent LLM regressions.

**Limitations:** Extremely high human effort. The AI lacks visual spatial awareness, requiring the user to manually act as the "layout engine."

---

## 3. Phase 1: JSON Compiler & Auto-Router
**Goal:** Abstract the Manim code into a declarative JSON schema. The user defines the hardware netlist (blocks and connections), and the compiler automatically places and routes it.

### Architecture
*   `ipmotion_lib.py`: A robust object-oriented Manim symbol library containing standard cells (IEEE gates, FIFOs, IPBlocks, PMOS/NMOS with dot conventions).
*   `ipmotion.py`: A JSON parser that translates entities and connections into Manim objects.
*   `autorouter.py`: A probabilistic layout and routing engine.

### The Attempt (Determinism vs. Probability)
*   **Determinism:** Instantiating blocks from the JSON was deterministic and worked perfectly. `IPBlock("Master")` reliably generated the correct shapes.
*   **Probabilistic Routing:** We attempted to solve the layout using algorithms:
    *   *Topological Placement:* Used `NetworkX` multipartite layouts.
    *   *Pathfinding:* Used the `A* algorithm` with bend penalties (5.0-10.0), obstacle padding (0.2), and grid resolutions (0.1).

### The Failure & Pivot
Fully autonomous placement from a netlist is an unsolved EDA problem, and applying it to visualization failed completely:
*   **Loss of Semantic Hierarchy:** The router placed blocks based on graph math, completely ignoring the logical flow of hardware (e.g., Master on the left, Slave on the right).
*   **Spaghetti Routing:** The A* algorithm produced microscopic zig-zags. Wires snapped to boundaries incorrectly, resulting in arrows pointing to empty space. 
*   **Conclusion:** Algorithmic routing is too rigid. We needed an engine that possessed "semantic intuition" about how hardware diagrams should look.

---

## 4. Phase 2: The RAG Shift (Self-Healing LLM Pipeline)
**Goal:** Abandon algorithmic routing and return to LLM generation, but eliminate the human bottleneck by giving the LLM an "Open-Book" database and an automated feedback loop.

### Research & Rationale
Research into state-of-the-art tools (e.g., `manimAnimationAgent`) revealed that LLMs write excellent Manim code *if* they are heavily grounded in exact examples. Instead of writing a custom router, we can use **Retrieval-Augmented Generation (RAG)** to feed the LLM our exact `ipmotion_lib.py` classes and past successful scripts. 

### Current Architecture (IPMotion v2)
1. **`indexer.py` (The Knowledge Base)**
   *   Parses `ipmotion_lib.py` class-by-class.
   *   Ingests the user's "gold examples" (e.g., the finalized 50-iteration Master Read script).
   *   Embeds these chunks into a local `ChromaDB` vector store using `sentence-transformers`.
2. **`rag_pipeline.py` (The Prompt Engine)**
   *   Takes a user request (e.g., *"Animate an AXI4 read handshake"*).
   *   Retrieves the 8 most relevant context chunks from ChromaDB.
   *   Constructs a massive context prompt so the LLM knows exactly how to use our custom classes (preventing hallucinations of standard Manim APIs).
3. **`runner.py` (Renderer-in-the-Loop)**
   *   Calls the LLM (Gemini Flash/Pro) to generate the script.
   *   Executes `manim render` silently in the background.
   *   **Self-Healing:** If Manim throws a Python traceback (e.g., overlapping coordinates, undefined classes), `runner.py` extracts the error and feeds it back to the LLM: *"This script failed with this error. Fix it."* (Loops up to 8 times).

### Results
*   **Success:** The system successfully generated an AXI4 Read Handshake completely autonomously. 
*   **Layout Quality:** Because the LLM was grounded in past `FDU` scripts, it used `VGroup.arrange()` and exact edge coordinates (`.get_right()`) instead of algorithmic grids, resulting in clean, human-like layouts.
*   **Obstacles Overcome:** Handled API rate limits (Gemini free tier restrictions) by swapping model strings (`gemini-3.8-flash`) and caching successful outputs. 

---

## 5. Future Roadmap: The Continuous Learning Flywheel
Currently, standard RAG is static (it only knows what was manually indexed). The final evolution of IPMotion is **Agentic Memory**.

**The Self-Improving Loop:**
1. `runner.py` generates and renders a script successfully.
2. The user reviews the output. If minor tweaks are needed, the user edits the Python file.
3. Upon user approval, the system moves the finalized script into a `verified_examples/` directory.
4. `indexer.py` is triggered automatically, embedding the new script into ChromaDB.
5. **Result:** The system grows incrementally smarter. If the system struggles with a Crossbar Switch on Day 1, by Day 5 it has the exact syntax for a Crossbar Switch permanently etched into its RAG memory, ensuring 0-shot success in the future.
