import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/constants.dart';
import '../core/hud_painters.dart';
import '../core/theme.dart';
import '../state/studio_state.dart';
import '../core_view/void_core_view.dart';
import '../editor/code_editor_view.dart';
import '../agents/engineering_agent_view.dart';
import '../agents/agent_network_view.dart';
import '../memory/memory_observatory_view.dart';
import '../models/neural_monitor_view.dart';
import '../hardware/hardware_diagnostics_view.dart';
import '../vision/vision_hud_view.dart';
import '../terminal/system_console_view.dart';
import '../telemetry/telemetry_stream_view.dart';

class SpatialWorkspace extends StatefulWidget {
  const SpatialWorkspace({super.key});

  @override
  State<SpatialWorkspace> createState() => _SpatialWorkspaceState();
}

class _SpatialWorkspaceState extends State<SpatialWorkspace> {
  int _agentSubTab = 0; // 0: Engineering Agent, 1: Agent Mesh

  @override
  Widget build(BuildContext context) {
    final state = context.watch<StudioState>();

    Widget content;

    switch (state.activeMode) {
      case WorkspaceMode.core:
        content = const VoidCoreView();
        break;
      case WorkspaceMode.code:
        content = const CodeEditorView();
        break;
      case WorkspaceMode.agents:
        content = Column(
          children: [
            // Agent Submode Switcher
            Container(
              height: 34,
              padding: const EdgeInsets.symmetric(horizontal: 14),
              decoration: const BoxDecoration(
                color: VoidTokens.voidObsidian,
                border: Border(
                  bottom: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 1.0),
                ),
              ),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                physics: const BouncingScrollPhysics(),
                child: Row(
                  children: [
                    _buildSubTab('01 // ENGINEERING AGENT', 0),
                    const SizedBox(width: 14),
                    _buildSubTab('02 // AGENT MESH TOPOLOGY', 1),
                  ],
                ),
              ),
            ),
            Expanded(
              child: _agentSubTab == 0
                  ? const EngineeringAgentView()
                  : const AgentNetworkView(),
            ),
          ],
        );
        break;
      case WorkspaceMode.memory:
        content = const MemoryObservatoryView();
        break;
      case WorkspaceMode.models:
        content = const NeuralMonitorView();
        break;
      case WorkspaceMode.vision:
        content = const VisionHudView();
        break;
      case WorkspaceMode.hardware:
        content = const HardwareDiagnosticsView();
        break;
      case WorkspaceMode.terminal:
        content = SystemConsoleView(
          isExpanded: true,
          onToggleHeight: () {},
        );
        break;
      case WorkspaceMode.logs:
        content = Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 700),
            child: const Padding(
              padding: EdgeInsets.symmetric(horizontal: 12),
              child: TelemetryStreamView(),
            ),
          ),
        );
        break;
      case WorkspaceMode.settings:
        content = _buildSettingsView(state);
        break;
    }

    return Container(
      color: VoidTokens.voidBlack,
      child: content,
    );
  }

  Widget _buildSubTab(String title, int index) {
    final isSel = _agentSubTab == index;
    return InkWell(
      onTap: () => setState(() => _agentSubTab = index),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(
              color: isSel ? VoidTokens.voidOrange : Colors.transparent,
              width: 2.0,
            ),
          ),
        ),
        child: Text(
          title,
          style: VoidTheme.hudLabel(
            fontSize: 9.5,
            color: isSel ? VoidTokens.voidOrangeBright : VoidTokens.textMuted,
          ),
        ),
      ),
    );
  }

  Widget _buildSettingsView(StudioState state) {
    return Center(
      child: SingleChildScrollView(
        physics: const BouncingScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 580),
          child: HudPanel(
            technicalTag: 'SYS.STUDIO_CONFIGURATION',
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('EXOSKELETON STUDIO PREFERENCES', style: VoidTheme.hudLabel(fontSize: 12)),
                const Divider(color: VoidTokens.voidSurfaceBorder, height: 24),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  activeColor: VoidTokens.voidOrange,
                  title: Text('PERFORMANCE MODE (LOW GPU)', style: VoidTheme.mono(fontSize: 12, color: VoidTokens.textHigh)),
                  subtitle: Text('Disables continuous particle and canvas redraw loops to prioritize VRAM for LLM inference.',
                      style: VoidTheme.mono(fontSize: 9.5, color: VoidTokens.textMuted)),
                  value: state.performanceMode,
                  onChanged: (_) => state.togglePerformanceMode(),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  activeColor: VoidTokens.voidOrange,
                  title: Text('REDUCED MOTION', style: VoidTheme.mono(fontSize: 12, color: VoidTokens.textHigh)),
                  subtitle: Text('Halts holographic rotational animations in HUD panels and reactor core.',
                      style: VoidTheme.mono(fontSize: 9.5, color: VoidTokens.textMuted)),
                  value: state.reducedMotion,
                  onChanged: (_) => state.toggleReducedMotion(),
                ),
                const SizedBox(height: 12),
                Text('LOCAL BACKEND SERVER ENDPOINT', style: VoidTheme.mono(fontSize: 10, color: VoidTokens.textMuted)),
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  decoration: BoxDecoration(
                    color: VoidTokens.voidObsidian,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: VoidTokens.voidSurfaceBorder),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          'http://127.0.0.1:5000',
                          style: VoidTheme.mono(fontSize: 12, color: VoidTokens.voidOrangeBright),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: state.isBackendConnected
                              ? VoidTokens.statusGreen.withOpacity(0.15)
                              : VoidTokens.statusYellow.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(2),
                        ),
                        child: Text(
                          state.isBackendConnected ? 'CONNECTED' : 'STANDBY',
                          style: VoidTheme.mono(
                            fontSize: 9,
                            color: state.isBackendConnected ? VoidTokens.statusGreen : VoidTokens.statusYellow,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
