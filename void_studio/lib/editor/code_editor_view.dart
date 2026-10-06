import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/constants.dart';
import '../core/theme.dart';
import '../state/studio_state.dart';
import 'file_tree.dart';

class CodeEditorView extends StatefulWidget {
  const CodeEditorView({super.key});

  @override
  State<CodeEditorView> createState() => _CodeEditorViewState();
}

class _CodeEditorViewState extends State<CodeEditorView> {
  bool _showSearch = false;
  bool _showFileTree = true;
  final TextEditingController _searchController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  final Map<String, String> _sampleCodebases = {
    'core/router.py': '''# core/router.py
import enum
from typing import Dict, Any, Optional
from core.vram_manager import vram_manager

class ExecutionPath(enum.Enum):
    DIRECT_TINY   = "DIRECT_TINY"
    AGENTIC_PLAN  = "AGENTIC_PLAN"
    VISION_VLM    = "VISION_VLM"

class ExecutiveRouter:
    """V.O.I.D. Cognitive OS Dynamic Dispatch Router."""
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.active_vram = vram_manager.get_available_vram()

    def route_query(self, query: str, context: Dict[str, Any]) -> ExecutionPath:
        # Determine optimal execution path based on complexity & memory
        if "inspect" in query.lower() or "fix" in query.lower():
            return ExecutionPath.AGENTIC_PLAN
        elif context.get("has_image", False):
            return ExecutionPath.VISION_VLM
        return ExecutionPath.DIRECT_TINY

executive_router = ExecutiveRouter()''',
    'void_memory/experience_memory.py': '''# void_memory/experience_memory.py
import time
import numpy as np
from typing import List, Dict, Any

class ExperienceMemory:
    """Episodic and Semantic memory store for V.O.I.D."""
    def __init__(self, dim: int = 1536):
        self.dim = dim
        self.memories = []
        self.vector_index = np.empty((0, dim), dtype=np.float32)

    def store_experience(self, text: str, embedding: np.ndarray, metadata: Dict[str, Any]):
        entry = {
            "id": len(self.memories),
            "text": text,
            "timestamp": time.time(),
            "metadata": metadata
        }
        self.memories.append(entry)
        self.vector_index = np.vstack([self.vector_index, embedding])
        return entry["id"]

    def retrieve_relevant(self, query_vec: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        if len(self.memories) == 0:
            return []
        scores = np.dot(self.vector_index, query_vec)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [self.memories[i] for i in top_indices]''',
  };

  @override
  void dispose() {
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<StudioState>();
    final code = _sampleCodebases[state.activeFile] ??
        '# ${state.activeFile}\n\n# Loaded from V.O.I.D. workspace.\nprint("Module initialized.")';

    final lines = code.split('\n');

    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final isCompact = width < 768;
        final showMinimap = width >= 640;

        return Stack(
          children: [
            Row(
              children: [
                // Left Intelligent File Tree (docked on desktop/tablet)
                if (!isCompact && _showFileTree) const FileTree(),

                // Right Editor Canvas
                Expanded(
                  child: Column(
                    children: [
                      // Editor Tab Bar & Controls
                      Container(
                        height: 36,
                        decoration: const BoxDecoration(
                          color: VoidTokens.voidObsidian,
                          border: Border(
                            bottom: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 1.0),
                          ),
                        ),
                        child: Row(
                          children: [
                            // Toggle File Tree Button
                            IconButton(
                              icon: Icon(
                                _showFileTree ? Icons.menu_open : Icons.menu,
                                size: 16,
                                color: _showFileTree ? VoidTokens.voidOrange : VoidTokens.textMuted,
                              ),
                              tooltip: 'Toggle File Tree',
                              onPressed: () => setState(() => _showFileTree = !_showFileTree),
                              padding: const EdgeInsets.symmetric(horizontal: 10),
                              constraints: const BoxConstraints(),
                            ),

                            // Active Tab
                            Flexible(
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10),
                                decoration: const BoxDecoration(
                                  color: VoidTokens.voidGraphite,
                                  border: Border(
                                    top: BorderSide(color: VoidTokens.voidOrange, width: 2.0),
                                    right: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 1.0),
                                  ),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const Icon(Icons.code, size: 13, color: VoidTokens.voidOrange),
                                    const SizedBox(width: 6),
                                    Flexible(
                                      child: Text(
                                        state.activeFile.split('/').last,
                                        overflow: TextOverflow.ellipsis,
                                        style: VoidTheme.mono(
                                          fontSize: 11,
                                          fontWeight: FontWeight.w600,
                                          color: VoidTokens.textHigh,
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 6),
                                    const Icon(Icons.close, size: 12, color: VoidTokens.textMuted),
                                  ],
                                ),
                              ),
                            ),

                            const Spacer(),

                            // Search Trigger
                            IconButton(
                              icon: Icon(
                                Icons.search,
                                size: 15,
                                color: _showSearch ? VoidTokens.voidOrange : VoidTokens.textMuted,
                              ),
                              tooltip: 'Find / Replace (Ctrl+F)',
                              onPressed: () => setState(() => _showSearch = !_showSearch),
                              padding: const EdgeInsets.symmetric(horizontal: 8),
                              constraints: const BoxConstraints(),
                            ),

                            // Diagnostics Indicator
                            if (width >= 480)
                              Container(
                                margin: const EdgeInsets.only(right: 10),
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: VoidTokens.statusGreen.withOpacity(0.12),
                                  borderRadius: BorderRadius.circular(2),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const Icon(Icons.check_circle_outline, size: 11, color: VoidTokens.statusGreen),
                                    const SizedBox(width: 4),
                                    Text('0 ERRORS', style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.statusGreen)),
                                  ],
                                ),
                              ),
                          ],
                        ),
                      ),

                      // Search Bar (if visible)
                      if (_showSearch)
                        Container(
                          height: 34,
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          decoration: const BoxDecoration(
                            color: VoidTokens.voidSurface,
                            border: Border(
                              bottom: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 1.0),
                            ),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.search, size: 13, color: VoidTokens.voidOrange),
                              const SizedBox(width: 8),
                              Expanded(
                                child: TextField(
                                  controller: _searchController,
                                  style: VoidTheme.mono(fontSize: 11, color: VoidTokens.textHigh),
                                  decoration: const InputDecoration(
                                    border: InputBorder.none,
                                    isDense: true,
                                    hintText: 'Search identifier in active buffer...',
                                    hintStyle: TextStyle(fontSize: 11, color: VoidTokens.textMuted),
                                  ),
                                ),
                              ),
                              IconButton(
                                icon: const Icon(Icons.close, size: 13, color: VoidTokens.textMuted),
                                onPressed: () => setState(() => _showSearch = false),
                              ),
                            ],
                          ),
                        ),

                      // Breadcrumb Path
                      Container(
                        height: 22,
                        padding: const EdgeInsets.symmetric(horizontal: 14),
                        alignment: Alignment.centerLeft,
                        decoration: const BoxDecoration(
                          color: VoidTokens.voidBlack,
                          border: Border(
                            bottom: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 0.5),
                          ),
                        ),
                        child: Text(
                          'VOID // ${state.activeFile.replaceAll('/', ' > ')}',
                          overflow: TextOverflow.ellipsis,
                          style: VoidTheme.mono(fontSize: 9, color: VoidTokens.textMuted),
                        ),
                      ),

                      // Code Body (Line numbers + Syntax text + Optional Minimap)
                      Expanded(
                        child: Row(
                          children: [
                            // Code Area with Line Numbers
                            Expanded(
                              child: ListView.builder(
                                controller: _scrollController,
                                padding: const EdgeInsets.symmetric(vertical: 8),
                                itemCount: lines.length,
                                itemBuilder: (context, index) {
                                  final line = lines[index];
                                  final lineNum = index + 1;

                                  return Padding(
                                    padding: const EdgeInsets.symmetric(vertical: 1.2),
                                    child: Row(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        // Line Number
                                        SizedBox(
                                          width: 38,
                                          child: Text(
                                            '$lineNum',
                                            textAlign: TextAlign.right,
                                            style: VoidTheme.mono(
                                              fontSize: 10.5,
                                              color: VoidTokens.textMuted.withOpacity(0.6),
                                            ),
                                          ),
                                        ),
                                        const SizedBox(width: 12),

                                        // Syntax Highlighted Text
                                        Expanded(
                                          child: _buildSyntaxLine(line),
                                        ),
                                      ],
                                    ),
                                  );
                                },
                              ),
                            ),

                            // Minimap Strip (only on wide enough displays)
                            if (showMinimap)
                              Container(
                                width: 44,
                                decoration: const BoxDecoration(
                                  color: VoidTokens.voidObsidian,
                                  border: Border(
                                    left: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 0.5),
                                  ),
                                ),
                                child: ListView.builder(
                                  itemCount: lines.length,
                                  itemBuilder: (context, idx) {
                                    final line = lines[idx];
                                    final length = line.trim().length.clamp(2, 40);
                                    return Container(
                                      height: 3,
                                      margin: const EdgeInsets.symmetric(vertical: 1, horizontal: 3),
                                      alignment: Alignment.centerLeft,
                                      child: Container(
                                        width: length.toDouble(),
                                        height: 1.5,
                                        color: line.trim().startsWith('#')
                                            ? VoidTokens.textMuted.withOpacity(0.3)
                                            : line.trim().startsWith('class') || line.trim().startsWith('def')
                                                ? VoidTokens.voidOrange.withOpacity(0.6)
                                                : VoidTokens.textMedium.withOpacity(0.25),
                                      ),
                                    );
                                  },
                                ),
                              ),
                          ],
                        ),
                      ),

                      // Bottom Editor Status Rail
                      Container(
                        height: 24,
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        decoration: const BoxDecoration(
                          color: VoidTokens.voidObsidian,
                          border: Border(
                            top: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 0.5),
                          ),
                        ),
                        child: Row(
                          children: [
                            Text('LN ${lines.length}, COL 1', style: VoidTheme.mono(fontSize: 9, color: VoidTokens.textMuted)),
                            const SizedBox(width: 12),
                            Text('UTF-8', style: VoidTheme.mono(fontSize: 9, color: VoidTokens.textMuted)),
                            if (width >= 560) ...[
                              const SizedBox(width: 12),
                              Text('PYTHON 3.11 [CUDA 12.4]', style: VoidTheme.mono(fontSize: 9, color: VoidTokens.statusCyan)),
                            ],
                            const Spacer(),
                            Text('SPACES: 4', style: VoidTheme.mono(fontSize: 9, color: VoidTokens.textMuted)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),

            // Slide-over FileTree drawer for mobile/compact screens
            if (isCompact && _showFileTree)
              Positioned(
                top: 0,
                bottom: 0,
                left: 0,
                child: Material(
                  elevation: 16,
                  color: Colors.transparent,
                  child: Container(
                    width: 250,
                    decoration: BoxDecoration(
                      color: VoidTokens.voidObsidian,
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.7),
                          blurRadius: 16,
                          spreadRadius: 2,
                        ),
                      ],
                    ),
                    child: Stack(
                      children: [
                        const FileTree(),
                        Positioned(
                          top: 6,
                          right: 6,
                          child: IconButton(
                            icon: const Icon(Icons.close, size: 14, color: VoidTokens.textMuted),
                            onPressed: () => setState(() => _showFileTree = false),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }

  Widget _buildSyntaxLine(String text) {
    if (text.trim().startsWith('#')) {
      return Text(text, style: VoidTheme.mono(fontSize: 11.5, color: const Color(0xFF6A737D)));
    }

    final words = text.split(' ');
    final spans = <TextSpan>[];

    for (int i = 0; i < words.length; i++) {
      final w = words[i];
      Color color = VoidTokens.textHigh;

      if (['import', 'from', 'class', 'def', 'return', 'if', 'elif', 'else', 'or', 'and', 'not', 'in', 'as'].contains(w)) {
        color = VoidTokens.voidOrangeBright;
      } else if (['self', 'None', 'True', 'False'].contains(w)) {
        color = VoidTokens.statusPurple;
      } else if (w.startsWith('"') || w.startsWith("'") || w.endsWith('"') || w.endsWith("'")) {
        color = VoidTokens.statusGreen;
      } else if (w.contains('(')) {
        color = VoidTokens.statusCyan;
      }

      spans.add(TextSpan(text: '$w ', style: VoidTheme.mono(fontSize: 11.5, color: color)));
    }

    return RichText(text: TextSpan(children: spans));
  }
}
