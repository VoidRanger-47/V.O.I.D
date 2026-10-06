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
          padding: const EdgeInsets.symmetric(horizontal: 12.0),
          child: Row(
            children: [
              // V.O.I.D. Studio Brand Mark
              InkWell(
                onTap: () => state.setActiveMode(WorkspaceMode.core),
                borderRadius: BorderRadius.circular(4),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4.0, horizontal: 2.0),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 9,
                        height: 9,
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
                              blurRadius: 6,
                              spreadRadius: 1,
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
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
              ] else if (width >= 780) ...[
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
                  padding: EdgeInsets.symmetric(
                    horizontal: isVeryNarrow ? 6 : 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: VoidTokens.voidSurface,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: VoidTokens.voidOrangeDim),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.terminal, size: 13, color: VoidTokens.voidOrangeBright),
                      if (!isVeryNarrow) ...[
                        const SizedBox(width: 5),
                        Text(
                          width >= 960 ? 'COMMAND [CTRL+SPACE]' : 'CMD',
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

              // System Clock (hidden on very compact screens)
              if (width >= 620) ...[
                const SizedBox(width: 12),
                Text(
                  _currentTime,
                  style: VoidTheme.mono(
                    fontSize: 10.5,
                    fontWeight: FontWeight.w600,
                    color: VoidTokens.textMuted,
                  ),
                ),
              ],

              const SizedBox(width: 10),

              // Toggle Performance Mode
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

              // Toggle Telemetry Drawer
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

              // Return to V.O.I.D. Chat Main Page
              IconButton(
                icon: const Icon(
                  Icons.arrow_back_rounded,
                  size: 15,
                  color: VoidTokens.voidOrangeBright,
                ),
                tooltip: 'Return to V.O.I.D. Chat (/)',
                onPressed: () => navigateToVoidChat(),
                padding: const EdgeInsets.all(6),
                constraints: const BoxConstraints(),
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
