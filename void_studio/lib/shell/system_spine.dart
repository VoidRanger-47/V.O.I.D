import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/constants.dart';
import '../core/theme.dart';
import '../state/studio_state.dart';

class SystemSpine extends StatefulWidget {
  const SystemSpine({super.key});

  @override
  State<SystemSpine> createState() => _SystemSpineState();
}

class _SystemSpineState extends State<SystemSpine> {
  bool _isHovered = false;

  final List<_SpineItem> _items = const [
    _SpineItem(
      mode: WorkspaceMode.core,
      label: 'VOID CORE',
      tag: '01 // REACT',
      icon: Icons.blur_circular,
      indicator: '◉',
      indicatorColor: VoidTokens.voidOrange,
    ),
    _SpineItem(
      mode: WorkspaceMode.code,
      label: 'CODE STUDIO',
      tag: '02 // EDIT',
      icon: Icons.code,
      indicator: '●',
      indicatorColor: VoidTokens.statusGreen,
    ),
    _SpineItem(
      mode: WorkspaceMode.agents,
      label: 'AGENT NET',
      tag: '03 // COGN',
      icon: Icons.hub,
      indicator: '●',
      indicatorColor: VoidTokens.statusPurple,
    ),
    _SpineItem(
      mode: WorkspaceMode.memory,
      label: 'MEMORY OBS',
      tag: '04 // VECT',
      icon: Icons.account_tree_outlined,
      indicator: '●',
      indicatorColor: VoidTokens.statusCyan,
    ),
    _SpineItem(
      mode: WorkspaceMode.models,
      label: 'NEURAL MON',
      tag: '05 // LLM',
      icon: Icons.memory,
      indicator: '●',
      indicatorColor: VoidTokens.voidOrangeBright,
    ),
    _SpineItem(
      mode: WorkspaceMode.vision,
      label: 'VISION HUD',
      tag: '06 // SENS',
      icon: Icons.camera_alt_outlined,
      indicator: '○',
      indicatorColor: VoidTokens.statusCyan,
    ),
    _SpineItem(
      mode: WorkspaceMode.hardware,
      label: 'EXO DIAG',
      tag: '07 // TELE',
      icon: Icons.precision_manufacturing_outlined,
      indicator: '●',
      indicatorColor: VoidTokens.statusYellow,
    ),
    _SpineItem(
      mode: WorkspaceMode.terminal,
      label: 'SYS CONSOLE',
      tag: '08 // TERM',
      icon: Icons.terminal,
      indicator: '●',
      indicatorColor: VoidTokens.textHigh,
    ),
    _SpineItem(
      mode: WorkspaceMode.logs,
      label: 'TELEMETRY',
      tag: '09 // LOGS',
      icon: Icons.list_alt,
      indicator: '●',
      indicatorColor: VoidTokens.statusGreen,
    ),
    _SpineItem(
      mode: WorkspaceMode.settings,
      label: 'EXO CONFIG',
      tag: '10 // PREF',
      icon: Icons.settings_outlined,
      indicator: '○',
      indicatorColor: VoidTokens.textMuted,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final state = context.watch<StudioState>();

    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOutCubic,
        width: _isHovered ? VoidTokens.spineExpandedWidth : VoidTokens.spineWidth,
        decoration: const BoxDecoration(
          color: VoidTokens.voidObsidian,
          border: Border(
            right: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 1.0),
          ),
        ),
        child: Column(
          children: [
            const SizedBox(height: 12),

            // Top Spine Coordinate Tag
            if (_isHovered)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                child: Row(
                  children: [
                    Text(
                      '// SYSTEM SPINE',
                      style: VoidTheme.hudLabel(fontSize: 8.5, color: VoidTokens.textMuted),
                    ),
                    const Spacer(),
                    Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: VoidTokens.voidOrange,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ],
                ),
              ),

            const SizedBox(height: 6),

            // Navigation Items
            Expanded(
              child: ListView.builder(
                padding: EdgeInsets.zero,
                itemCount: _items.length,
                itemBuilder: (context, index) {
                  final item = _items[index];
                  final isSelected = state.activeMode == item.mode;

                  return _buildSpineButton(
                    item: item,
                    isSelected: isSelected,
                    onTap: () => state.setActiveMode(item.mode),
                  );
                },
              ),
            ),

            // Bottom Core State Pill
            _buildBottomIndicator(state),
            const SizedBox(height: 12),
          ],
        ),
      ),
    );
  }

  Widget _buildSpineButton({
    required _SpineItem item,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      child: Container(
        height: 48,
        margin: const EdgeInsets.symmetric(vertical: 2, horizontal: 6),
        decoration: BoxDecoration(
          color: isSelected ? VoidTokens.voidSurface : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
          border: Border(
            left: BorderSide(
              color: isSelected ? VoidTokens.voidOrange : Colors.transparent,
              width: 3.0,
            ),
          ),
        ),
        child: _isHovered
            ? Row(
                children: [
                  const SizedBox(width: 12),
                  Icon(
                    item.icon,
                    size: 19,
                    color: isSelected ? VoidTokens.voidOrangeBright : VoidTokens.textMedium,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    item.indicator,
                    style: TextStyle(
                      fontSize: 9,
                      color: item.indicatorColor,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item.label,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: VoidTheme.hudLabel(
                            fontSize: 10,
                            color: isSelected ? VoidTokens.textHigh : VoidTokens.textMedium,
                            fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                          ),
                        ),
                        Text(
                          item.tag,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.textMuted),
                        ),
                      ],
                    ),
                  ),
                ],
              )
            : Center(
                child: Stack(
                  clipBehavior: Clip.none,
                  children: [
                    Icon(
                      item.icon,
                      size: 20,
                      color: isSelected ? VoidTokens.voidOrangeBright : VoidTokens.textMedium,
                    ),
                    Positioned(
                      top: -1,
                      right: -3,
                      child: Container(
                        width: 5,
                        height: 5,
                        decoration: BoxDecoration(
                          color: item.indicatorColor,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
      ),
    );
  }

  Widget _buildBottomIndicator(StudioState state) {
    return Container(
      padding: const EdgeInsets.all(8),
      margin: const EdgeInsets.symmetric(horizontal: 8),
      decoration: BoxDecoration(
        color: VoidTokens.voidGraphite,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: VoidTokens.voidSurfaceBorder),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: state.isBackendConnected ? VoidTokens.statusGreen : VoidTokens.statusYellow,
              shape: BoxShape.circle,
            ),
          ),
          if (_isHovered) ...[
            const SizedBox(width: 8),
            Text(
              state.isBackendConnected ? 'CORE ONLINE' : 'SIMULATION',
              style: VoidTheme.mono(fontSize: 9, color: VoidTokens.textMedium),
            ),
          ],
        ],
      ),
    );
  }
}

class _SpineItem {
  final WorkspaceMode mode;
  final String label;
  final String tag;
  final IconData icon;
  final String indicator;
  final Color indicatorColor;

  const _SpineItem({
    required this.mode,
    required this.label,
    required this.tag,
    required this.icon,
    required this.indicator,
    required this.indicatorColor,
  });
}

/// Adaptive bottom navigation bar for mobile / compact screens
class ExoskeletonBottomNav extends StatelessWidget {
  const ExoskeletonBottomNav({super.key});

  static const List<_SpineItem> _items = [
    _SpineItem(
      mode: WorkspaceMode.core,
      label: 'CORE',
      tag: 'REACT',
      icon: Icons.blur_circular,
      indicator: '◉',
      indicatorColor: VoidTokens.voidOrange,
    ),
    _SpineItem(
      mode: WorkspaceMode.code,
      label: 'CODE',
      tag: 'EDIT',
      icon: Icons.code,
      indicator: '●',
      indicatorColor: VoidTokens.statusGreen,
    ),
    _SpineItem(
      mode: WorkspaceMode.agents,
      label: 'AGENTS',
      tag: 'COGN',
      icon: Icons.hub,
      indicator: '●',
      indicatorColor: VoidTokens.statusPurple,
    ),
    _SpineItem(
      mode: WorkspaceMode.memory,
      label: 'MEMORY',
      tag: 'VECT',
      icon: Icons.account_tree_outlined,
      indicator: '●',
      indicatorColor: VoidTokens.statusCyan,
    ),
    _SpineItem(
      mode: WorkspaceMode.models,
      label: 'MODELS',
      tag: 'LLM',
      icon: Icons.memory,
      indicator: '●',
      indicatorColor: VoidTokens.voidOrangeBright,
    ),
    _SpineItem(
      mode: WorkspaceMode.vision,
      label: 'VISION',
      tag: 'SENS',
      icon: Icons.camera_alt_outlined,
      indicator: '○',
      indicatorColor: VoidTokens.statusCyan,
    ),
    _SpineItem(
      mode: WorkspaceMode.hardware,
      label: 'HARDWARE',
      tag: 'TELE',
      icon: Icons.precision_manufacturing_outlined,
      indicator: '●',
      indicatorColor: VoidTokens.statusYellow,
    ),
    _SpineItem(
      mode: WorkspaceMode.terminal,
      label: 'CONSOLE',
      tag: 'TERM',
      icon: Icons.terminal,
      indicator: '●',
      indicatorColor: VoidTokens.textHigh,
    ),
    _SpineItem(
      mode: WorkspaceMode.logs,
      label: 'LOGS',
      tag: 'LOGS',
      icon: Icons.list_alt,
      indicator: '●',
      indicatorColor: VoidTokens.statusGreen,
    ),
    _SpineItem(
      mode: WorkspaceMode.settings,
      label: 'CONFIG',
      tag: 'PREF',
      icon: Icons.settings_outlined,
      indicator: '○',
      indicatorColor: VoidTokens.textMuted,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final state = context.watch<StudioState>();

    return Container(
      height: VoidTokens.bottomNavHeight,
      decoration: const BoxDecoration(
        color: VoidTokens.voidObsidian,
        border: Border(
          top: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 1.0),
        ),
      ),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        physics: const BouncingScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
        itemCount: _items.length,
        itemBuilder: (context, index) {
          final item = _items[index];
          final isSelected = state.activeMode == item.mode;

          return InkWell(
            onTap: () => state.setActiveMode(item.mode),
            borderRadius: BorderRadius.circular(4),
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 3),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: isSelected ? VoidTokens.voidSurface : Colors.transparent,
                borderRadius: BorderRadius.circular(4),
                border: Border(
                  bottom: BorderSide(
                    color: isSelected ? VoidTokens.voidOrange : Colors.transparent,
                    width: 2.5,
                  ),
                ),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    item.icon,
                    size: 18,
                    color: isSelected ? VoidTokens.voidOrangeBright : VoidTokens.textMedium,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    item.label,
                    style: VoidTheme.hudLabel(
                      fontSize: 8.5,
                      fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                      color: isSelected ? VoidTokens.textHigh : VoidTokens.textMuted,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
