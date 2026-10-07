import 'dart:async';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../core/constants.dart';
import '../core/navigation_helper.dart';
import '../core/theme.dart';
import '../state/studio_state.dart';

class SystemRail extends StatefulWidget {
  const SystemRail({super.key});

  @override
  State<SystemRail> createState() => _SystemRailState();
}

class _SystemRailState extends State<SystemRail> {
  late Timer _clockTimer;
  String _currentTime = '';

  @override
  void initState() {
    super.initState();
    _updateTime();
    _clockTimer = Timer.periodic(const Duration(seconds: 1), (_) => _updateTime());
  }

  void _updateTime() {
    setState(() {
      _currentTime = DateFormat('HH:mm:ss').format(DateTime.now());
    });
  }

  @override
  void dispose() {
    _clockTimer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<StudioState>();

    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final isCompact = width < 720;
        final isVeryNarrow = width < 480;

        return Container(
          height: VoidTokens.systemRailHeight,
          decoration: const BoxDecoration(
            color: VoidTokens.voidBlack,
            border: Border(
              bottom: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 1.0),
            ),
          ),
          padding: EdgeInsets.symmetric(horizontal: width < 380 ? 6.0 : 12.0),
          child: Row(
            children: [
              // V.O.I.D. Main Logo & Studio Identity Mark
              InkWell(
                onTap: () => state.setActiveMode(WorkspaceMode.core),
                borderRadius: BorderRadius.circular(4),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4.0, horizontal: 2.0),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Official V.O.I.D. Main Emblem Logo
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: Image.asset(
                          'assets/images/void_symbol.png',
                          width: 20,
                          height: 20,
                          fit: BoxFit.contain,
                          errorBuilder: (_, __, ___) => Container(
                            width: 20,
                            height: 20,
                            decoration: const BoxDecoration(
                              color: VoidTokens.voidOrange,
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(Icons.blur_on, size: 14, color: VoidTokens.voidBlack),
                          ),
                        ),
                      ),
                      if (width >= 360) ...[
                        const SizedBox(width: 8),
                        // Core Connectivity Glow Dot
                        Container(
                          width: 7,
                          height: 7,
                          decoration: BoxDecoration(
                            color: state.isBackendConnected
                                ? VoidTokens.statusGreen
                                : VoidTokens.voidOrange,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: state.isBackendConnected
                                    ? VoidTokens.statusGreenGlow
                                    : VoidTokens.voidOrangeGlow,
                                blurRadius: 5,
                                spreadRadius: 1,
                              ),
                            ],
                          ),
                        ),
                      ],
                      const SizedBox(width: 7),
                      Text(
                        'V.O.I.D.',
                        style: VoidTheme.hudLabel(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 2.0,
                          color: VoidTokens.voidOrangeBright,
                        ),
                      ),
                      if (!isVeryNarrow) ...[
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                          decoration: BoxDecoration(
                            color: VoidTokens.voidSurface,
                            borderRadius: BorderRadius.circular(2),
                            border: Border.all(color: VoidTokens.voidSurfaceBorder),
                          ),
                          child: Text(
                            isCompact ? 'MK-IV' : 'STUDIO MK-IV',
                            style: VoidTheme.mono(
                              fontSize: 8.5,
                              color: VoidTokens.textMedium,
                              letterSpacing: 1.0,
                            ),
                          ),
                        ),
                        if (width >= 980) ...[
                          const SizedBox(width: 6),
                          Text(
                            '// NEURAL COCKPIT',
                            style: VoidTheme.mono(
                              fontSize: 8.5,
                              color: VoidTokens.textMuted,
                              letterSpacing: 0.8,
                            ),
                          ),
                        ],
                      ],
                    ],
                  ),
                ),
              ),

              // Active Project Pill (if width allows)
              if (width >= 860) ...[
                const SizedBox(width: 14),
                Flexible(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: VoidTokens.voidGraphite,
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: VoidTokens.voidSurfaceBorder),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.folder_outlined, size: 12, color: VoidTokens.voidOrange),
                        const SizedBox(width: 5),
                        Flexible(
                          child: Text(
                            state.activeProject,
                            overflow: TextOverflow.ellipsis,
                            style: VoidTheme.mono(fontSize: 10.5, color: VoidTokens.textHigh),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],

              const Spacer(),

              // Telemetry Quick Stats (Dynamic count based on available width)
              if (width >= 1100) ...[
                _buildQuickStat('CPU', '${state.metrics.cpuPercent.toStringAsFixed(0)}%'),
                const SizedBox(width: 10),
                _buildQuickStat('GPU', '${state.metrics.gpuPercent.toStringAsFixed(0)}%'),
                const SizedBox(width: 10),
                _buildQuickStat('VRAM', '${state.metrics.vramUsedGb.toStringAsFixed(1)}G'),
                const SizedBox(width: 10),
                _buildQuickStat('SYNC', '${state.metrics.stability.toStringAsFixed(1)}%'),
                const SizedBox(width: 14),
              ] else if (width >= 860) ...[
                _buildQuickStat('CPU', '${state.metrics.cpuPercent.toStringAsFixed(0)}%'),
                const SizedBox(width: 8),
                _buildQuickStat('GPU', '${state.metrics.gpuPercent.toStringAsFixed(0)}%'),
                const SizedBox(width: 12),
              ],

              // Global Command Trigger (Ctrl + Space)
              InkWell(
                onTap: () => state.openCommandPalette(),
                borderRadius: BorderRadius.circular(4),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                  decoration: BoxDecoration(
                    color: VoidTokens.voidSurface,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: VoidTokens.voidOrangeDim),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.terminal, size: 13, color: VoidTokens.voidOrangeBright),
                      if (width >= 960) ...[
                        const SizedBox(width: 5),
                        Text(
                          'COMMAND [CTRL+SPACE]',
                          style: VoidTheme.mono(
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            color: VoidTokens.voidOrangeBright,
                          ),
                        ),
                      ] else if (width >= 640) ...[
                        const SizedBox(width: 5),
                        Text(
                          'CMD',
                          style: VoidTheme.mono(
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            color: VoidTokens.voidOrangeBright,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 6),

              // System Clock (hidden on very compact screens)
              if (width >= 620) ...[
                Text(
                  _currentTime,
                  style: VoidTheme.mono(
                    fontSize: 10.5,
                    fontWeight: FontWeight.w600,
                    color: VoidTokens.textMuted,
                  ),
                ),
                const SizedBox(width: 10),
              ],

              // Toggle Performance Mode (hide on ultra-compact screens)
              if (width >= 360) ...[
                IconButton(
                  icon: Icon(
                    state.performanceMode ? Icons.speed : Icons.auto_awesome,
                    size: 15,
                    color: state.performanceMode ? VoidTokens.statusYellow : VoidTokens.voidOrange,
                  ),
                  tooltip: state.performanceMode
                      ? 'Performance Mode Active (Low GPU)'
                      : 'Full Holographic HUD Active',
                  onPressed: () => state.togglePerformanceMode(),
                  padding: const EdgeInsets.all(6),
                  constraints: const BoxConstraints(),
                ),
                const SizedBox(width: 6),
              ],

              // Toggle Telemetry Drawer (hide on compact mobile screens)
              if (width >= 400) ...[
                IconButton(
                  icon: Icon(
                    Icons.analytics_outlined,
                    size: 15,
                    color: state.telemetryDrawerOpen ? VoidTokens.voidOrange : VoidTokens.textMuted,
                  ),
                  tooltip: 'Toggle Telemetry Stream',
                  onPressed: () => state.toggleTelemetryDrawer(),
                  padding: const EdgeInsets.all(6),
                  constraints: const BoxConstraints(),
                ),
                const SizedBox(width: 6),
              ],

              // Return to V.O.I.D. Chat Main Page
              InkWell(
                onTap: () => navigateToVoidChat(),
                borderRadius: BorderRadius.circular(4),
                child: Container(
                  padding: EdgeInsets.symmetric(horizontal: isVeryNarrow ? 5 : 7, vertical: 3.5),
                  decoration: BoxDecoration(
                    color: VoidTokens.voidOrange.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: VoidTokens.voidOrange.withOpacity(0.35)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        Icons.arrow_back_rounded,
                        size: 13,
                        color: VoidTokens.voidOrangeBright,
                      ),
                      if (width >= 860) ...[
                        const SizedBox(width: 4),
                        Text(
                          'MAIN CHAT',
                          style: VoidTheme.mono(
                            fontSize: 9.5,
                            fontWeight: FontWeight.w700,
                            color: VoidTokens.voidOrangeBright,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildQuickStat(String label, String value) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '$label: ',
          style: VoidTheme.mono(fontSize: 9.5, color: VoidTokens.textMuted),
        ),
        Text(
          value,
          style: VoidTheme.mono(
            fontSize: 10.5,
            fontWeight: FontWeight.w700,
            color: VoidTokens.voidOrangeBright,
          ),
        ),
      ],
    );
  }
}
