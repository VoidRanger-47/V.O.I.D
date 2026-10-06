import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/constants.dart';
import '../core/hud_painters.dart';
import '../core/theme.dart';
import '../state/studio_state.dart';

class AgentNetworkView extends StatefulWidget {
  const AgentNetworkView({super.key});

  @override
  State<AgentNetworkView> createState() => _AgentNetworkViewState();
}

class _AgentNetworkViewState extends State<AgentNetworkView> with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  int _selectedAgentIndex = 0;

  final List<_AgentNode> _nodes = [
    _AgentNode(
      name: 'CORE',
      role: 'Executive Router & Task Supervisor',
      state: 'SUPERVISING',
      color: VoidTokens.voidOrange,
      isActive: true,
      load: 0.84,
      offset: const Offset(0.5, 0.45),
    ),
    _AgentNode(
      name: 'CODER',
      role: 'AST Syntax Synthesis & Optimization',
      state: 'WRITING PATCH',
      color: VoidTokens.statusGreen,
      isActive: true,
      load: 0.92,
      offset: const Offset(0.25, 0.22),
    ),
    _AgentNode(
      name: 'MEMORY',
      role: 'Vector & Episodic Knowledge Indexer',
      state: 'VECTOR SYNC',
      color: VoidTokens.statusCyan,
      isActive: true,
      load: 0.65,
      offset: const Offset(0.75, 0.22),
    ),
    _AgentNode(
      name: 'PLANNER',
      role: 'Multi-Phase Task Decomposition',
      state: 'STANDBY',
      color: VoidTokens.statusPurple,
      isActive: false,
      load: 0.20,
      offset: const Offset(0.18, 0.68),
    ),
    _AgentNode(
      name: 'DEBUGGER',
      role: 'Empirical Verification & Trace Analysis',
      state: 'MONITORING',
      color: VoidTokens.statusYellow,
      isActive: true,
      load: 0.45,
      offset: const Offset(0.82, 0.68),
    ),
    _AgentNode(
      name: 'RESEARCH',
      role: 'Neural Web & Documentation Crawling',
      state: 'STANDBY',
      color: VoidTokens.textMedium,
      isActive: false,
      load: 0.10,
      offset: const Offset(0.50, 0.82),
    ),
  ];

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<StudioState>();
    final selected = _nodes[_selectedAgentIndex];

    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final height = constraints.maxHeight;
        final isWide = width >= 850 && height >= 520;
        final isMobile = width < 540;

        return Stack(
          children: [
            // Technical Coordinate Grid
            Positioned.fill(
              child: CustomPaint(
                painter: HudGridPainter(spacing: 36),
              ),
            ),

            // Animated Connection Mesh with Data Pulses
            Positioned.fill(
              child: AnimatedBuilder(
                animation: _pulseController,
                builder: (context, child) {
                  return CustomPaint(
                    painter: _NetworkMeshPainter(
                      nodes: _nodes,
                      pulseProgress: state.reducedMotion ? 0.0 : _pulseController.value,
                      selectedIndex: _selectedAgentIndex,
                      heightScale: isWide ? 1.0 : 0.70,
                    ),
                  );
                },
              ),
            ),

            // Interactive Node Badges
            ..._nodes.asMap().entries.map((entry) {
              final idx = entry.key;
              final node = entry.value;
              final isSelected = idx == _selectedAgentIndex;
              final nodeWidth = isMobile ? 82.0 : 96.0;

              final effectiveHeight = isWide ? height : height * 0.70;
              final x = (node.offset.dx * width - (nodeWidth / 2))
                  .clamp(8.0, width - nodeWidth - 8.0);
              final y = (node.offset.dy * effectiveHeight - 22)
                  .clamp(8.0, height - (isWide ? 60.0 : 150.0));

              return Positioned(
                left: x,
                top: y,
                child: InkWell(
                  onTap: () => setState(() => _selectedAgentIndex = idx),
                  borderRadius: BorderRadius.circular(4),
                  child: Container(
                    width: nodeWidth,
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 5),
                    decoration: BoxDecoration(
                      color: isSelected
                          ? node.color.withOpacity(0.2)
                          : VoidTokens.voidObsidian.withOpacity(0.92),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(
                        color: isSelected ? node.color : VoidTokens.voidSurfaceBorder,
                        width: isSelected ? 1.5 : 1.0,
                      ),
                      boxShadow: isSelected
                          ? [
                              BoxShadow(
                                color: node.color.withOpacity(0.3),
                                blurRadius: 10,
                                spreadRadius: 1,
                              )
                            ]
                          : null,
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Container(
                              width: 6,
                              height: 6,
                              decoration: BoxDecoration(
                                color: node.isActive ? node.color : VoidTokens.textMuted,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 4),
                            Flexible(
                              child: Text(
                                node.name,
                                overflow: TextOverflow.ellipsis,
                                style: VoidTheme.hudLabel(
                                  fontSize: isMobile ? 8.5 : 9.5,
                                  color: isSelected ? VoidTokens.textHigh : node.color,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 2),
                        Text(
                          node.state,
                          overflow: TextOverflow.ellipsis,
                          style: VoidTheme.mono(
                            fontSize: 7.5,
                            color: VoidTokens.textMuted,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }),

            // Node Inspector Overlay Panel (Desktop: top-right; Mobile/Compact: bottom dock)
            if (isWide)
              Positioned(
                top: 20,
                right: 20,
                width: 280,
                child: _buildInspectorCard(selected),
              )
            else
              Positioned(
                bottom: 10,
                left: 10,
                right: 10,
                child: _buildInspectorCard(selected, isCompact: true),
              ),
          ],
        );
      },
    );
  }

  Widget _buildInspectorCard(_AgentNode selected, {bool isCompact = false}) {
    if (isCompact) {
      return HudPanel(
        technicalTag: 'AGENT_NODE // ${selected.name}',
        backgroundColor: const Color(0xF00D0F14),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 7,
                  height: 7,
                  decoration: BoxDecoration(color: selected.color, shape: BoxShape.circle),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'AGENT // ${selected.name}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: VoidTheme.hudLabel(fontSize: 10, color: selected.color),
                  ),
                ),
                const SizedBox(width: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                  decoration: BoxDecoration(
                    color: selected.color.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(2),
                  ),
                  child: Text(
                    selected.state,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: VoidTheme.mono(fontSize: 8.5, color: selected.color),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              selected.role,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: VoidTheme.mono(fontSize: 9.5, color: VoidTokens.textMedium),
            ),
            const SizedBox(height: 4),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              alignment: WrapAlignment.spaceBetween,
              children: [
                Text('COMPUTE: ${(selected.load * 100).toInt()}%',
                    style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.textMuted)),
                Text('BUS: MESH_0${_selectedAgentIndex + 1}',
                    style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.voidOrangeBright)),
                Text('SANDBOX: SECURE',
                    style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.statusGreen)),
              ],
            ),
          ],
        ),
      );
    }

    return HudPanel(
      technicalTag: 'AGENT_NODE // TELEMETRY',
      backgroundColor: const Color(0xDD0D0F14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(color: selected.color, shape: BoxShape.circle),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'AGENT // ${selected.name}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: VoidTheme.hudLabel(fontSize: 11, color: selected.color),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(selected.role, style: VoidTheme.mono(fontSize: 10, color: VoidTokens.textHigh)),
          const Divider(color: VoidTokens.voidSurfaceBorder, height: 16),
          _buildInfoRow('CURRENT STATE', selected.state),
          _buildInfoRow('COMPUTE LOAD', '${(selected.load * 100).toInt()}%'),
          _buildInfoRow('PACKET BUS', 'MESH_CHANNEL_0${_selectedAgentIndex + 1}'),
          _buildInfoRow('SECURITY LEVEL', 'ISOLATED_SANDBOX'),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2.5),
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
          Text(value, style: VoidTheme.mono(fontSize: 9.5, color: VoidTokens.voidOrangeBright)),
        ],
      ),
    );
  }
}

class _NetworkMeshPainter extends CustomPainter {
  final List<_AgentNode> nodes;
  final double pulseProgress;
  final int selectedIndex;
  final double heightScale;

  _NetworkMeshPainter({
    required this.nodes,
    required this.pulseProgress,
    required this.selectedIndex,
    this.heightScale = 1.0,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final effectiveHeight = size.height * heightScale;
    final core = nodes[0];
    final corePos = Offset(core.offset.dx * size.width, core.offset.dy * effectiveHeight);

    final linePaint = Paint()
      ..color = VoidTokens.hudLine
      ..strokeWidth = 1.0
      ..style = PaintingStyle.stroke;

    final pulsePaint = Paint()
      ..color = VoidTokens.voidOrangeBright
      ..style = PaintingStyle.fill;

    // Connect CORE to all other nodes
    for (int i = 1; i < nodes.length; i++) {
      final target = nodes[i];
      final targetPos = Offset(target.offset.dx * size.width, target.offset.dy * effectiveHeight);

      // Technical line
      canvas.drawLine(corePos, targetPos, linePaint);

      // Data pulse animation traveling along connection
      if (target.isActive) {
        final t = (pulseProgress + (i * 0.2)) % 1.0;
        final pulsePos = Offset(
          corePos.dx + (targetPos.dx - corePos.dx) * t,
          corePos.dy + (targetPos.dy - corePos.dy) * t,
        );
        canvas.drawCircle(pulsePos, 3.5, pulsePaint);
      }
    }

    // Connect Planner -> Coder & Coder -> Debugger
    final coderPos = Offset(nodes[1].offset.dx * size.width, nodes[1].offset.dy * effectiveHeight);
    final plannerPos = Offset(nodes[3].offset.dx * size.width, nodes[3].offset.dy * effectiveHeight);
    final debuggerPos = Offset(nodes[4].offset.dx * size.width, nodes[4].offset.dy * effectiveHeight);

    canvas.drawLine(plannerPos, coderPos, linePaint);
    canvas.drawLine(coderPos, debuggerPos, linePaint);

    // Pulse on Planner -> Coder
    final tPlanner = pulseProgress % 1.0;
    final pulsePlanner = Offset(
      plannerPos.dx + (coderPos.dx - plannerPos.dx) * tPlanner,
      plannerPos.dy + (coderPos.dy - plannerPos.dy) * tPlanner,
    );
    canvas.drawCircle(pulsePlanner, 3.0, pulsePaint);
  }

  @override
  bool shouldRepaint(covariant _NetworkMeshPainter oldDelegate) => true;
}

class _AgentNode {
  final String name;
  final String role;
  final String state;
  final Color color;
  final bool isActive;
  final double load;
  final Offset offset;

  _AgentNode({
    required this.name,
    required this.role,
    required this.state,
    required this.color,
    required this.isActive,
    required this.load,
    required this.offset,
  });
}
