import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../core/constants.dart';
import '../core/hud_painters.dart';
import '../core/theme.dart';
import '../state/studio_state.dart';

class CommandPalette extends StatefulWidget {
  const CommandPalette({super.key});

  @override
  State<CommandPalette> createState() => _CommandPaletteState();
}

class _CommandPaletteState extends State<CommandPalette> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();

  final List<_CommandItem> _commands = [
    _CommandItem('Run project test suite', 'EXECUTE', Icons.play_arrow, WorkspaceMode.terminal),
    _CommandItem('Open memory observatory', 'NAVIGATE', Icons.account_tree_outlined, WorkspaceMode.memory),
    _CommandItem('Analyze active code file', 'AGENT', Icons.auto_awesome, WorkspaceMode.agents),
    _CommandItem('Start vision perception HUD', 'VISION', Icons.camera_alt_outlined, WorkspaceMode.vision),
    _CommandItem('Show GPU & neural telemetry', 'TELEMETRY', Icons.memory, WorkspaceMode.models),
    _CommandItem('Exoskeleton hardware chassis diagnostics', 'DIAGNOSE', Icons.precision_manufacturing_outlined, WorkspaceMode.hardware),
    _CommandItem('Inspect VOID neural reactor core', 'CORE', Icons.blur_circular, WorkspaceMode.core),
    _CommandItem('Open system engineering console', 'TERMINAL', Icons.terminal, WorkspaceMode.terminal),
  ];

  String _query = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<StudioState>();
    final filtered = _commands
        .where((c) => c.title.toLowerCase().contains(_query.toLowerCase()) ||
            c.tag.toLowerCase().contains(_query.toLowerCase()))
        .toList();

    return LayoutBuilder(
      builder: (context, constraints) {
        final isMobile = constraints.maxWidth < 600;
        final topPadding = isMobile ? 24.0 : 80.0;

        return KeyboardListener(
          focusNode: FocusNode(),
          onKeyEvent: (event) {
            if (event is KeyDownEvent && event.logicalKey == LogicalKeyboardKey.escape) {
              state.closeCommandPalette();
            }
          },
          child: GestureDetector(
            onTap: () => state.closeCommandPalette(),
            child: Container(
              color: Colors.black.withOpacity(0.65),
              alignment: Alignment.topCenter,
              padding: EdgeInsets.only(top: topPadding, left: 16, right: 16),
              child: GestureDetector(
                onTap: () {}, // Prevent click propagation to background
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 580),
                  child: HudPanel(
                    technicalTag: 'V.O.I.D. COMMAND PALETTE // CTRL+SPACE',
                    backgroundColor: VoidTokens.voidObsidian,
                    borderColor: VoidTokens.voidOrange,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // Input Bar
                        Row(
                          children: [
                            const Icon(Icons.search, size: 18, color: VoidTokens.voidOrangeBright),
                            const SizedBox(width: 10),
                            Expanded(
                              child: TextField(
                                controller: _controller,
                                focusNode: _focusNode,
                                onChanged: (val) => setState(() => _query = val),
                                style: VoidTheme.mono(fontSize: 13, color: VoidTokens.textHigh),
                                decoration: InputDecoration(
                                  hintText: isMobile ? 'Type a command...' : 'Type a command, query, or workspace target...',
                                  hintStyle: const TextStyle(
                                    fontFamily: 'Consolas',
                                    fontSize: 12,
                                    color: VoidTokens.textMuted,
                                  ),
                                  border: InputBorder.none,
                                  isDense: true,
                                ),
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: VoidTokens.voidGraphite,
                                borderRadius: BorderRadius.circular(2),
                                border: Border.all(color: VoidTokens.voidSurfaceBorder),
                              ),
                              child: Text(isMobile ? 'ESC' : 'ESC TO CLOSE', style: VoidTheme.mono(fontSize: 9, color: VoidTokens.textMuted)),
                            ),
                          ],
                        ),

                    const Divider(color: VoidTokens.voidSurfaceBorder, height: 20),

                    // Command Suggestions
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxHeight: 300),
                      child: ListView.builder(
                        shrinkWrap: true,
                        itemCount: filtered.length,
                        itemBuilder: (context, index) {
                          final cmd = filtered[index];
                          return InkWell(
                            onTap: () {
                              state.setActiveMode(cmd.mode);
                              state.closeCommandPalette();
                            },
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                              margin: const EdgeInsets.symmetric(vertical: 2),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Row(
                                children: [
                                  Icon(cmd.icon, size: 16, color: VoidTokens.voidOrange),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Text(
                                      cmd.title,
                                      style: VoidTheme.mono(fontSize: 12, color: VoidTokens.textHigh),
                                    ),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: VoidTokens.voidSurface,
                                      borderRadius: BorderRadius.circular(2),
                                    ),
                                    child: Text(
                                      cmd.tag,
                                      style: VoidTheme.hudLabel(fontSize: 8.5),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
      },
    );
  }
}

class _CommandItem {
  final String title;
  final String tag;
  final IconData icon;
  final WorkspaceMode mode;

  _CommandItem(this.title, this.tag, this.icon, this.mode);
}
