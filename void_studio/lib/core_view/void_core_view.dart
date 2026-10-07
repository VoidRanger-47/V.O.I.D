import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/constants.dart';
import '../core/hud_painters.dart';
import '../core/theme.dart';
import '../state/studio_state.dart';

class VoidCoreView extends StatefulWidget {
  const VoidCoreView({super.key});

  @override
  State<VoidCoreView> createState() => _VoidCoreViewState();
}

class _VoidCoreViewState extends State<VoidCoreView> with SingleTickerProviderStateMixin {
  late AnimationController _animController;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 12),
    )..repeat();
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<StudioState>();

    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final height = constraints.maxHeight;
        final isWide = width >= 860 && height >= 560;

        // Dynamic reactor size that adapts to any screen ratio
        final reactorSize = (math.min(width * 0.60, height * 0.42)).clamp(160.0, 300.0);

        return Stack(
          children: [
            // Technical Background Grid
            Positioned.fill(
              child: CustomPaint(
                painter: HudGridPainter(spacing: 38),
              ),
            ),

            // Scrollable Center Reactor Content
            Center(
              child: SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Rotating Neural Reactor Canvas
                    SizedBox(
                      width: reactorSize,
                      height: reactorSize,
                      child: AnimatedBuilder(
                        animation: _animController,
                        builder: (context, child) {
                          return CustomPaint(
                            painter: _NeuralReactorPainter(
                              progress: state.reducedMotion ? 0.5 : _animController.value,
                              coreState: state.coreState,
                              performanceMode: state.performanceMode,
                            ),
                            child: Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  ClipRRect(
                                    borderRadius: BorderRadius.circular(4),
                                    child: Image.asset(
                                      'assets/images/void_symbol.png',
                                      width: reactorSize < 200 ? 30 : 42,
                                      height: reactorSize < 200 ? 30 : 42,
                                      fit: BoxFit.contain,
                                      errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                                    ),
                                  ),
                                  const SizedBox(height: 5),
                                  Text(
                                    'CORE MK-IV',
                                    style: VoidTheme.hudLabel(
                                      fontSize: reactorSize < 200 ? 10.5 : 12,
                                      letterSpacing: 2.0,
                                      color: _getStateColor(state.coreState),
                                    ),
                                  ),
                                  const SizedBox(height: 3),
                                  Text(
                                    state.coreState.name.toUpperCase(),
                                    style: VoidTheme.mono(
                                      fontSize: reactorSize < 200 ? 10 : 11.5,
                                      fontWeight: FontWeight.w700,
                                      color: VoidTokens.textHigh,
                                      letterSpacing: 1.5,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    '${state.metrics.tokensPerSec.toStringAsFixed(1)} TOK/S',
                                    style: VoidTheme.mono(
                                      fontSize: reactorSize < 200 ? 8.5 : 10,
                                      color: VoidTokens.textMuted,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                    ),

                    const SizedBox(height: 22),

                    // Interactive State Switcher
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 720),
                      child: Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        alignment: WrapAlignment.center,
                        children: CoreState.values.map((s) {
                          final isSelected = state.coreState == s;
                          final color = _getStateColor(s);

                          return InkWell(
                            onTap: () => state.setCoreState(s),
                            borderRadius: BorderRadius.circular(4),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4.5),
                              decoration: BoxDecoration(
                                color: isSelected ? color.withOpacity(0.18) : VoidTokens.voidGraphite,
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(
                                  color: isSelected ? color : VoidTokens.voidSurfaceBorder,
                                ),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Container(
                                    width: 5,
                                    height: 5,
                                    decoration: BoxDecoration(color: color, shape: BoxShape.circle),
                                  ),
                                  const SizedBox(width: 5),
                                  Text(
                                    s.name.toUpperCase(),
                                    style: VoidTheme.mono(
                                      fontSize: 9.5,
                                      fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                                      color: isSelected ? VoidTokens.textHigh : VoidTokens.textMedium,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          );
                        }).toList(),
                      ),
                    ),

                    const SizedBox(height: 18),

                    // Studio Operational Purpose & Missions Overview
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 720),
                      child: HudPanel(
                        technicalTag: 'SYS.STUDIO_MISSION // COCKPIT PURPOSE',
                        backgroundColor: VoidTokens.voidObsidian,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                ClipRRect(
                                  borderRadius: BorderRadius.circular(4),
                                  child: Image.asset(
                                    'assets/images/void_symbol.png',
                                    width: 20,
                                    height: 20,
                                    fit: BoxFit.contain,
                                    errorBuilder: (_, __, ___) => const Icon(Icons.blur_on, size: 18, color: VoidTokens.voidOrange),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    'V.O.I.D. STUDIO PURPOSE & OPERATIONS BRIEFING',
                                    style: VoidTheme.hudLabel(
                                      fontSize: 11,
                                      fontWeight: FontWeight.w800,
                                      color: VoidTokens.voidOrangeBright,
                                      letterSpacing: 1.0,
                                    ),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'V.O.I.D. Studio MK-IV is the autonomous engineering cockpit and neural observatory of the V.O.I.D. Cognitive Operating System. It provides a specialized multi-panel environment for executing code workflows, directing autonomous subagents, monitoring neural inference rates, exploring vector memories, and analyzing live vision streams.',
                              style: VoidTheme.mono(
                                fontSize: 10.5,
                                color: VoidTokens.textHigh,
                              ),
                            ),
                            const SizedBox(height: 12),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: [
                                _buildPurposeChip(
                                  icon: Icons.code,
                                  title: 'CODE STUDIO',
                                  desc: 'Spatial IDE & File Tree',
                                  onTap: () => state.setActiveMode(WorkspaceMode.code),
                                ),
                                _buildPurposeChip(
                                  icon: Icons.hub_outlined,
                                  title: 'AGENT MESH',
                                  desc: 'Autonomous Orchestration',
                                  onTap: () => state.setActiveMode(WorkspaceMode.agents),
                                ),
                                _buildPurposeChip(
                                  icon: Icons.memory,
                                  title: 'MEMORY OBSERVATORY',
                                  desc: 'Vector & Recall Graph',
                                  onTap: () => state.setActiveMode(WorkspaceMode.memory),
                                ),
                                _buildPurposeChip(
                                  icon: Icons.show_chart,
                                  title: 'NEURAL MONITORS',
                                  desc: 'Loss & Token Throughput',
                                  onTap: () => state.setActiveMode(WorkspaceMode.models),
                                ),
                                _buildPurposeChip(
                                  icon: Icons.visibility,
                                  title: 'VISION HUD',
                                  desc: 'Optical Perception Feeds',
                                  onTap: () => state.setActiveMode(WorkspaceMode.vision),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),

                    // On compact / portrait screens, place the telemetry cards here in-line
                    if (!isWide) ...[
                      const SizedBox(height: 20),
                      ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 600),
                        child: Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          alignment: WrapAlignment.center,
                          children: [
                            SizedBox(
                              width: width < 420 ? width - 32 : 240,
                              child: _buildReactorTelemetryCard(),
                            ),
                            SizedBox(
                              width: width < 420 ? width - 32 : 240,
                              child: _buildGpuTelemetryCard(state),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),

            // Corner Telemetry HUD Overlays (Desktop & wide aspect ratio only)
            if (isWide) ...[
              Positioned(
                top: 20,
                left: 20,
                child: _buildReactorTelemetryCard(),
              ),
              Positioned(
                bottom: 20,
                right: 20,
                child: _buildGpuTelemetryCard(state),
              ),
            ],
          ],
        );
      },
    );
  }

  Widget _buildReactorTelemetryCard() {
    return HudPanel(
      technicalTag: 'SYS.REACTOR_CORE',
      backgroundColor: const Color(0xDD0A0D12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('NEURAL FREQUENCY', style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.textMuted)),
          const SizedBox(height: 2),
          Text('3.84 GHz // TACTICAL', style: VoidTheme.mono(fontSize: 10.5, color: VoidTokens.voidOrangeBright)),
          const SizedBox(height: 5),
          Text('COGNITIVE COHERENCE', style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.textMuted)),
          const SizedBox(height: 2),
          Text('99.84% [OPTIMAL]', style: VoidTheme.mono(fontSize: 10.5, color: VoidTokens.statusGreen)),
        ],
      ),
    );
  }

  Widget _buildGpuTelemetryCard(StudioState state) {
    return HudPanel(
      technicalTag: 'SYS.GPU_STREAM',
      backgroundColor: const Color(0xDD0A0D12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('COMPUTE LATENCY', style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.textMuted)),
          const SizedBox(height: 2),
          Text('${state.metrics.latencyMs.toStringAsFixed(0)} ms', style: VoidTheme.mono(fontSize: 10.5, color: VoidTokens.statusCyan)),
          const SizedBox(height: 5),
          Text('KV CACHE STATUS', style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.textMuted)),
          const SizedBox(height: 2),
          Text('2,048 / 8,192 TOKENS', style: VoidTheme.mono(fontSize: 10.5, color: VoidTokens.textHigh)),
        ],
      ),
    );
  }

  Widget _buildPurposeChip({
    required IconData icon,
    required String title,
    required String desc,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: VoidTokens.voidSurface,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: VoidTokens.voidSurfaceBorder),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: VoidTokens.voidOrange),
            const SizedBox(width: 7),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: VoidTheme.hudLabel(
                    fontSize: 9.5,
                    fontWeight: FontWeight.w700,
                    color: VoidTokens.voidOrangeBright,
                  ),
                ),
                Text(
                  desc,
                  style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.textMuted),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Color _getStateColor(CoreState s) {
    switch (s) {
      case CoreState.idle:
        return VoidTokens.voidOrange;
      case CoreState.thinking:
        return VoidTokens.statusPurple;
      case CoreState.generating:
        return VoidTokens.statusCyan;
      case CoreState.executing:
        return VoidTokens.statusGreen;
      case CoreState.learning:
        return VoidTokens.statusYellow;
      case CoreState.vision:
        return VoidTokens.statusCyan;
      case CoreState.error:
        return VoidTokens.statusRed;
      case CoreState.offline:
        return VoidTokens.textMuted;
    }
  }
}

class _NeuralReactorPainter extends CustomPainter {
  final double progress;
  final CoreState coreState;
  final bool performanceMode;

  _NeuralReactorPainter({
    required this.progress,
    required this.coreState,
    required this.performanceMode,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = size.width / 2;

    final primaryColor = _getColor();
    final rotationAngle = progress * 2 * math.pi;

    // Outer Segmented Gear Ring
    final outerPaint = Paint()
      ..color = primaryColor.withOpacity(0.35)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;

    canvas.drawCircle(center, maxRadius - 10, outerPaint);

    // Segmented Arcs
    const int numSegments = 16;
    for (int i = 0; i < numSegments; i++) {
      final angle = (i * 2 * math.pi / numSegments) + rotationAngle * 0.5;
      final p1 = Offset(
        center.dx + (maxRadius - 18) * math.cos(angle),
        center.dy + (maxRadius - 18) * math.sin(angle),
      );
      final p2 = Offset(
        center.dx + (maxRadius - 10) * math.cos(angle),
        center.dy + (maxRadius - 10) * math.sin(angle),
      );
      canvas.drawLine(p1, p2, outerPaint);
    }

    // Mid Concentric Counter-Rotating Ring
    final midRadius = maxRadius * 0.70;
    final midPaint = Paint()
      ..color = primaryColor.withOpacity(0.55)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: midRadius),
      -rotationAngle,
      math.pi * 1.3,
      false,
      midPaint,
    );
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: midRadius),
      -rotationAngle + math.pi,
      math.pi * 0.4,
      false,
      midPaint,
    );

    // Inner Glowing Core
    final innerRadius = maxRadius * 0.45;
    final innerPaint = Paint()
      ..color = primaryColor.withOpacity(0.15)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(center, innerRadius, innerPaint);

    final innerBorder = Paint()
      ..color = primaryColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    canvas.drawCircle(center, innerRadius, innerBorder);

    // Center Crosshairs
    final crossHairPaint = Paint()
      ..color = primaryColor.withOpacity(0.4)
      ..strokeWidth = 1.0;
    canvas.drawLine(
      Offset(center.dx - innerRadius - 8, center.dy),
      Offset(center.dx + innerRadius + 8, center.dy),
      crossHairPaint,
    );
    canvas.drawLine(
      Offset(center.dx, center.dy - innerRadius - 8),
      Offset(center.dx, center.dy + innerRadius + 8),
      crossHairPaint,
    );
  }

  Color _getColor() {
    switch (coreState) {
      case CoreState.idle:
        return VoidTokens.voidOrange;
      case CoreState.thinking:
        return VoidTokens.statusPurple;
      case CoreState.generating:
        return VoidTokens.statusCyan;
      case CoreState.executing:
        return VoidTokens.statusGreen;
      case CoreState.learning:
        return VoidTokens.statusYellow;
      case CoreState.vision:
        return VoidTokens.statusCyan;
      case CoreState.error:
        return VoidTokens.statusRed;
      case CoreState.offline:
        return VoidTokens.textMuted;
    }
  }

  @override
  bool shouldRepaint(covariant _NeuralReactorPainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.coreState != coreState ||
        oldDelegate.performanceMode != performanceMode;
  }
}
