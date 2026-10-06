import 'package:flutter/material.dart';
import '../core/constants.dart';
import '../core/hud_painters.dart';
import '../core/theme.dart';

class MemoryObservatoryView extends StatefulWidget {
  const MemoryObservatoryView({super.key});

  @override
  State<MemoryObservatoryView> createState() => _MemoryObservatoryViewState();
}

class _MemoryObservatoryViewState extends State<MemoryObservatoryView> {
  int _selectedMemoryIdx = 0;
  String _selectedCategory = 'ALL';

  final List<_MemoryNode> _memories = [
    _MemoryNode(
      id: 'MEM-001',
      category: 'USER CONTEXT',
      title: 'User Profile: Lead Architect',
      content: 'Preferences: Strict dark mode, o200k_base tokenizer standards, low latency offline local execution.',
      importance: 0.95,
      frequency: 48,
      timestamp: '2026-10-05 21:40',
      source: 'identity.json',
      offset: const Offset(0.35, 0.35),
      color: VoidTokens.voidOrange,
    ),
    _MemoryNode(
      id: 'MEM-002',
      category: 'EPISODIC',
      title: 'Session Wake Word Resolution',
      content: 'Calibrated acoustic RMS threshold to 250 and added 240ms pre-roll rolling buffer for WASAPI capture.',
      importance: 0.90,
      frequency: 14,
      timestamp: '2026-10-05 22:04',
      source: 'voice_listener.py',
      offset: const Offset(0.55, 0.28),
      color: VoidTokens.statusGreen,
    ),
    _MemoryNode(
      id: 'MEM-003',
      category: 'SEMANTIC',
      title: 'Tokenizer o200k_base Vector Registry',
      content: 'Replaced HuggingFace dependencies with pure tiktoken encoding instance with 200,025 vocabulary items.',
      importance: 0.88,
      frequency: 32,
      timestamp: '2026-10-05 21:18',
      source: 'from_scratch_transformer.py',
      offset: const Offset(0.70, 0.45),
      color: VoidTokens.statusPurple,
    ),
    _MemoryNode(
      id: 'MEM-004',
      category: 'KNOWLEDGE',
      title: 'Android Phone ADB Intent Schema',
      content: 'Direct device intent execution via ADB TCP/IP port 5555 without external cloud dependencies.',
      importance: 0.82,
      frequency: 19,
      timestamp: '2026-10-05 20:50',
      source: 'phone_controller.py',
      offset: const Offset(0.40, 0.65),
      color: VoidTokens.statusCyan,
    ),
    _MemoryNode(
      id: 'MEM-005',
      category: 'SHORT TERM',
      title: 'Workspace Active Mode Buffer',
      content: 'User switched active workspace into Flutter Desktop V.O.I.D. Studio Exoskeleton Environment.',
      importance: 0.70,
      frequency: 5,
      timestamp: '2026-10-05 22:15',
      source: 'session_cache',
      offset: const Offset(0.60, 0.72),
      color: VoidTokens.statusYellow,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final selected = _memories[_selectedMemoryIdx];

    return LayoutBuilder(
      builder: (context, constraints) {
        final isNarrow = constraints.maxWidth < 850;
        final isMobile = constraints.maxWidth < 600;

        // Filter chips bar
        final filterBar = Container(
          height: 40,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          decoration: const BoxDecoration(
            color: VoidTokens.voidObsidian,
            border: Border(
              bottom: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 1.0),
            ),
          ),
          child: Row(
            children: [
              const Icon(Icons.hub_outlined, size: 13, color: VoidTokens.voidOrange),
              const SizedBox(width: 8),
              if (!isMobile) ...[
                Text('MEMORY OBSERVATORY', style: VoidTheme.hudLabel(fontSize: 9.5)),
                const SizedBox(width: 12),
              ],
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  physics: const BouncingScrollPhysics(),
                  child: Row(
                    children: ['ALL', 'EPISODIC', 'SEMANTIC', 'USER CONTEXT', 'KNOWLEDGE'].map((cat) {
                      final isSel = _selectedCategory == cat;
                      return InkWell(
                        onTap: () => setState(() => _selectedCategory = cat),
                        child: Container(
                          margin: const EdgeInsets.symmetric(horizontal: 3),
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: isSel ? VoidTokens.voidOrange.withOpacity(0.15) : Colors.transparent,
                            borderRadius: BorderRadius.circular(2),
                            border: Border.all(
                              color: isSel ? VoidTokens.voidOrange : VoidTokens.voidSurfaceBorder.withOpacity(0.5),
                            ),
                          ),
                          child: Text(
                            cat,
                            style: VoidTheme.mono(
                              fontSize: 8.5,
                              fontWeight: isSel ? FontWeight.w700 : FontWeight.w500,
                              color: isSel ? VoidTokens.voidOrangeBright : VoidTokens.textMuted,
                            ),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ),
              ),
            ],
          ),
        );

        // Visual Graph Canvas
        final graphCanvas = Stack(
          children: [
            // Background grid
            Positioned.fill(
              child: CustomPaint(
                painter: HudGridPainter(spacing: 36),
              ),
            ),

            // Connection Lines
            Positioned.fill(
              child: CustomPaint(
                painter: _MemoryLinksPainter(
                  memories: _memories,
                  selectedIdx: _selectedMemoryIdx,
                ),
              ),
            ),

            // Interactive Memory Nodes
            LayoutBuilder(
              builder: (context, graphConstraints) {
                return Stack(
                  children: _memories.asMap().entries.map((entry) {
                    final idx = entry.key;
                    final node = entry.value;
                    final isSel = idx == _selectedMemoryIdx;

                    final maxX = (graphConstraints.maxWidth - 114.0).clamp(4.0, double.infinity);
                    final maxY = (graphConstraints.maxHeight - 56.0).clamp(4.0, double.infinity);
                    final rawX = node.offset.dx * graphConstraints.maxWidth - 50;
                    final rawY = node.offset.dy * graphConstraints.maxHeight - 25;
                    final x = rawX.clamp(4.0, maxX);
                    final y = rawY.clamp(4.0, maxY);

                    return Positioned(
                      left: x,
                      top: y,
                      child: InkWell(
                        onTap: () => setState(() => _selectedMemoryIdx = idx),
                        borderRadius: BorderRadius.circular(4),
                        child: Container(
                          width: 108,
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            color: isSel ? node.color.withOpacity(0.2) : VoidTokens.voidObsidian,
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(
                              color: isSel ? node.color : VoidTokens.voidSurfaceBorder,
                              width: isSel ? 1.5 : 1.0,
                            ),
                            boxShadow: isSel
                                ? [BoxShadow(color: node.color.withOpacity(0.25), blurRadius: 10)]
                                : null,
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Container(
                                    width: 6,
                                    height: 6,
                                    decoration: BoxDecoration(color: node.color, shape: BoxShape.circle),
                                  ),
                                  const SizedBox(width: 4),
                                  Expanded(
                                    child: Text(
                                      node.id,
                                      style: VoidTheme.hudLabel(fontSize: 8.5, color: node.color),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 2),
                              Text(
                                node.title,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: VoidTheme.mono(fontSize: 9.5, color: VoidTokens.textHigh),
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                );
              },
            ),
          ],
        );

        // Inspector content widget
        final inspectorWidget = Container(
          width: isNarrow ? double.infinity : 320,
          decoration: BoxDecoration(
            color: VoidTokens.voidObsidian,
            border: Border(
              left: isNarrow ? BorderSide.none : const BorderSide(color: VoidTokens.voidSurfaceBorder, width: 1.0),
              top: isNarrow ? const BorderSide(color: VoidTokens.voidSurfaceBorder, width: 1.0) : BorderSide.none,
            ),
          ),
          padding: const EdgeInsets.all(14),
          child: SingleChildScrollView(
            physics: const BouncingScrollPhysics(),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                HudPanel(
                  technicalTag: 'INSPECTOR // ${selected.id}',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        selected.category,
                        style: VoidTheme.hudLabel(fontSize: 8.5, color: selected.color),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        selected.title,
                        style: VoidTheme.mono(fontSize: 12, fontWeight: FontWeight.w700, color: VoidTokens.textHigh),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                Text('RAW MEMORY PAYLOAD', style: VoidTheme.hudLabel(fontSize: 9.5)),
                const SizedBox(height: 6),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: VoidTokens.voidGraphite,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: VoidTokens.voidSurfaceBorder),
                  ),
                  child: Text(
                    selected.content,
                    style: VoidTheme.mono(fontSize: 10.5, color: VoidTokens.textMedium),
                  ),
                ),
                const SizedBox(height: 12),
                Text('METRICS & ATTRIBUTION', style: VoidTheme.hudLabel(fontSize: 9.5)),
                const SizedBox(height: 8),
                _buildMetricItem('IMPORTANCE WEIGHT', '${(selected.importance * 100).toInt()}%'),
                _buildMetricItem('RETRIEVAL FREQUENCY', '${selected.frequency} queries'),
                _buildMetricItem('TIMESTAMP', selected.timestamp),
                _buildMetricItem('SOURCE ATTRIBUTION', selected.source),
                const SizedBox(height: 14),
                ElevatedButton.icon(
                  onPressed: () {},
                  icon: const Icon(Icons.refresh, size: 14, color: VoidTokens.voidBlack),
                  label: Text('RE-EMBED IN VECTOR STORE', style: VoidTheme.hudLabel(fontSize: 9.5, color: VoidTokens.voidBlack)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: VoidTokens.voidOrange,
                    minimumSize: const Size.fromHeight(34),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                  ),
                ),
              ],
            ),
          ),
        );

        if (isNarrow) {
          return Column(
            children: [
              filterBar,
              Expanded(
                flex: 3,
                child: graphCanvas,
              ),
              Expanded(
                flex: 2,
                child: inspectorWidget,
              ),
            ],
          );
        }

        return Row(
          children: [
            Expanded(
              flex: 3,
              child: Column(
                children: [
                  filterBar,
                  Expanded(child: graphCanvas),
                ],
              ),
            ),
            inspectorWidget,
          ],
        );
      },
    );
  }

  Widget _buildMetricItem(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: VoidTheme.mono(fontSize: 9, color: VoidTokens.textMuted),
            ),
          ),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: VoidTheme.mono(fontSize: 10, color: VoidTokens.voidOrangeBright),
            ),
          ),
        ],
      ),
    );
  }
}

class _MemoryLinksPainter extends CustomPainter {
  final List<_MemoryNode> memories;
  final int selectedIdx;

  _MemoryLinksPainter({required this.memories, required this.selectedIdx});

  @override
  void paint(Canvas canvas, Size size) {
    final sel = memories[selectedIdx];
    final selPos = Offset(sel.offset.dx * size.width, sel.offset.dy * size.height);

    final linePaint = Paint()
      ..color = VoidTokens.hudLine
      ..strokeWidth = 1.0;

    for (int i = 0; i < memories.length; i++) {
      if (i == selectedIdx) continue;
      final target = memories[i];
      final targetPos = Offset(target.offset.dx * size.width, target.offset.dy * size.height);
      canvas.drawLine(selPos, targetPos, linePaint);
    }
  }

  @override
  bool shouldRepaint(covariant _MemoryLinksPainter oldDelegate) => true;
}

class _MemoryNode {
  final String id;
  final String category;
  final String title;
  final String content;
  final double importance;
  final int frequency;
  final String timestamp;
  final String source;
  final Offset offset;
  final Color color;

  _MemoryNode({
    required this.id,
    required this.category,
    required this.title,
    required this.content,
    required this.importance,
    required this.frequency,
    required this.timestamp,
    required this.source,
    required this.offset,
    required this.color,
  });
}
