import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../core/constants.dart';
import '../core/theme.dart';
import '../services/backend_service.dart';

class SystemConsoleView extends StatefulWidget {
  final bool isExpanded;
  final VoidCallback onToggleHeight;

  const SystemConsoleView({
    super.key,
    required this.isExpanded,
    required this.onToggleHeight,
  });

  @override
  State<SystemConsoleView> createState() => _SystemConsoleViewState();
}

class _SystemConsoleViewState extends State<SystemConsoleView> {
  final TextEditingController _inputController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  final List<_ConsoleLine> _lines = [
    _ConsoleLine(
      type: _LineType.system,
      text: 'V.O.I.D. Studio System Console v4.2 [Windows-x64 / Core v2.4]',
    ),
    _ConsoleLine(
      type: _LineType.system,
      text: 'Type "help", "status", "test", "run", or any engineering command.',
    ),
  ];

  @override
  void dispose() {
    _inputController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _handleSubmit() async {
    final text = _inputController.text.trim();
    if (text.isEmpty) return;

    _inputController.clear();
    setState(() {
      _lines.add(_ConsoleLine(type: _LineType.command, text: '> $text'));
    });

    _scrollToBottom();

    // Built-in commands & backend delegation
    if (text.toLowerCase() == 'clear') {
      setState(() => _lines.clear());
      return;
    }

    if (text.toLowerCase() == 'help') {
      setState(() {
        _lines.add(_ConsoleLine(
          type: _LineType.output,
          text: 'Available Commands:\n  status     - Query V.O.I.D. system health & VRAM metrics\n  clear      - Clear console buffer\n  agents     - Query active agent mesh\n  memory     - Inspect experience vector store\n  run        - Execute active project test suite',
        ));
      });
      _scrollToBottom();
      return;
    }

    // Delegate to backend service
    final output = await BackendService.instance.executeCommand(text);
    setState(() {
      _lines.add(_ConsoleLine(type: _LineType.output, text: output));
    });
    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isMobile = constraints.maxWidth < 600;

        return Container(
          decoration: const BoxDecoration(
            color: VoidTokens.voidBlack,
            border: Border(
              top: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 1.0),
            ),
          ),
          child: Column(
            children: [
              // Console Header Rail
              Container(
                height: 32,
                padding: const EdgeInsets.symmetric(horizontal: 10),
                decoration: const BoxDecoration(
                  color: VoidTokens.voidObsidian,
                  border: Border(
                    bottom: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 0.5),
                  ),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.terminal, size: 13, color: VoidTokens.voidOrange),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        isMobile ? 'CONSOLE // TTY' : 'SYSTEM CONSOLE // DIAGNOSTIC TTY',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: VoidTheme.hudLabel(fontSize: 9.5),
                      ),
                    ),
                    // Quick command chips
                    if (constraints.maxWidth >= 480) ...[
                      _buildQuickChip('STATUS'),
                      const SizedBox(width: 4),
                      _buildQuickChip('CLEAR'),
                      const SizedBox(width: 4),
                      _buildQuickChip('HELP'),
                      const SizedBox(width: 8),
                    ],
                    IconButton(
                      icon: Icon(
                        widget.isExpanded ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up,
                        size: 16,
                        color: VoidTokens.textMedium,
                      ),
                      tooltip: widget.isExpanded ? 'Collapse Console' : 'Expand Console',
                      onPressed: widget.onToggleHeight,
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                  ],
                ),
              ),

              // Output Stream
              Expanded(
                child: ListView.builder(
                  controller: _scrollController,
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  itemCount: _lines.length,
                  itemBuilder: (context, index) {
                    final line = _lines[index];
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2.0),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            line.time,
                            style: VoidTheme.mono(fontSize: 9.5, color: VoidTokens.textMuted),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              line.text,
                              style: VoidTheme.mono(
                                fontSize: 10.5,
                                color: line.type == _LineType.command
                                    ? VoidTokens.voidOrangeBright
                                    : line.type == _LineType.system
                                        ? VoidTokens.statusCyan
                                        : VoidTokens.textHigh,
                              ),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),

              // Input Line
              Container(
                height: 36,
                padding: const EdgeInsets.symmetric(horizontal: 10),
                decoration: const BoxDecoration(
                  color: VoidTokens.voidObsidian,
                  border: Border(
                    top: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 0.5),
                  ),
                ),
                child: Row(
                  children: [
                    Text(
                      isMobile ? '> ' : r'VOID@STUDIO:~$ ',
                      style: VoidTheme.mono(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: VoidTokens.voidOrange,
                      ),
                    ),
                    const SizedBox(width: 4),
                    Expanded(
                      child: TextField(
                        controller: _inputController,
                        onSubmitted: (_) => _handleSubmit(),
                        style: VoidTheme.mono(fontSize: 11, color: VoidTokens.textHigh),
                        decoration: InputDecoration(
                          border: InputBorder.none,
                          isDense: true,
                          contentPadding: EdgeInsets.zero,
                          hintText: isMobile ? 'Type command...' : 'Enter engineering command or action...',
                          hintStyle: const TextStyle(
                            fontFamily: 'Consolas',
                            fontSize: 11,
                            color: VoidTokens.textMuted,
                          ),
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.send, size: 14, color: VoidTokens.voidOrange),
                      onPressed: _handleSubmit,
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildQuickChip(String cmd) {
    return InkWell(
      onTap: () {
        _inputController.text = cmd.toLowerCase();
        _handleSubmit();
      },
      borderRadius: BorderRadius.circular(2),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: VoidTokens.voidGraphite,
          borderRadius: BorderRadius.circular(2),
          border: Border.all(color: VoidTokens.voidSurfaceBorder),
        ),
        child: Text(
          cmd,
          style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.textMuted),
        ),
      ),
    );
  }
}

enum _LineType { command, output, system }

class _ConsoleLine {
  final String time;
  final String text;
  final _LineType type;

  _ConsoleLine({
    required this.text,
    this.type = _LineType.output,
  }) : time = DateFormat('HH:mm:ss').format(DateTime.now());
}
