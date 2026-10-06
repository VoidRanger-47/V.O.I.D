import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../core/constants.dart';
import '../state/studio_state.dart';
import 'system_rail.dart';
import 'system_spine.dart';
import '../workspace/spatial_workspace.dart';
import '../telemetry/telemetry_stream_view.dart';
import '../terminal/system_console_view.dart';
import '../command/command_palette.dart';

class StudioShell extends StatefulWidget {
  const StudioShell({super.key});

  @override
  State<StudioShell> createState() => _StudioShellState();
}

class _StudioShellState extends State<StudioShell> {
  final FocusNode _shellFocusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _shellFocusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _shellFocusNode.dispose();
    super.dispose();
  }

  void _handleKeyEvent(KeyEvent event) {
    if (event is KeyDownEvent) {
      // Shortcut: Ctrl + Space -> Command Palette
      if (HardwareKeyboard.instance.isControlPressed && event.logicalKey == LogicalKeyboardKey.space) {
        final state = context.read<StudioState>();
        state.openCommandPalette();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<StudioState>();

    return KeyboardListener(
      focusNode: _shellFocusNode,
      onKeyEvent: _handleKeyEvent,
      child: Scaffold(
        backgroundColor: VoidTokens.voidBlack,
        body: LayoutBuilder(
          builder: (context, constraints) {
            final isMobile = constraints.maxWidth < VoidTokens.mobileBreakpoint;
            final isCompactWidth = constraints.maxWidth < VoidTokens.tabletBreakpoint;
            final consoleHeight = math.min(
              VoidTokens.bottomConsoleHeight,
              math.max(160.0, constraints.maxHeight * 0.35),
            );

            return Stack(
              children: [
                Column(
                  children: [
                    // Top System Rail
                    const SystemRail(),

                    // Center Layer: Spine + Workspace + Telemetry Drawer
                    Expanded(
                      child: Row(
                        children: [
                          // Left System Spine (visible on desktop/tablet only)
                          if (!isMobile) const SystemSpine(),

                          // Central Spatial Workspace
                          const Expanded(
                            child: SpatialWorkspace(),
                          ),

                          // Right Telemetry Stream Layer (Docked only on wide screens)
                          if (!isCompactWidth &&
                              state.telemetryDrawerOpen &&
                              state.activeMode != WorkspaceMode.logs)
                            const TelemetryStreamView(width: VoidTokens.telemetryPanelWidth),
                        ],
                      ),
                    ),

                    // Bottom Collapsible Console Layer (Toggled)
                    if (state.bottomPanelOpen && state.activeMode != WorkspaceMode.terminal)
                      SizedBox(
                        height: consoleHeight,
                        child: SystemConsoleView(
                          isExpanded: true,
                          onToggleHeight: () => state.toggleBottomPanel(),
                        ),
                      ),

                    // Bottom HUD Navigation Bar (Mobile / Compact screen ratio)
                    if (isMobile) const ExoskeletonBottomNav(),
                  ],
                ),

                // Slide-over Telemetry Stream Overlay on compact/tablet screens
                if (isCompactWidth &&
                    state.telemetryDrawerOpen &&
                    state.activeMode != WorkspaceMode.logs)
                  Positioned(
                    top: VoidTokens.systemRailHeight,
                    bottom: isMobile ? VoidTokens.bottomNavHeight : 0,
                    right: 0,
                    child: Material(
                      elevation: 16,
                      color: Colors.transparent,
                      child: Container(
                        decoration: BoxDecoration(
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.6),
                              blurRadius: 20,
                              spreadRadius: 4,
                            ),
                          ],
                        ),
                        child: TelemetryStreamView(
                          width: math.min(VoidTokens.telemetryPanelWidth, constraints.maxWidth * 0.85),
                        ),
                      ),
                    ),
                  ),

                // Holographic Command Palette Overlay
                if (state.commandPaletteOpen)
                  const Positioned.fill(
                    child: CommandPalette(),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}
