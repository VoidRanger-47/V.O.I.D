import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/constants.dart';
import '../core/theme.dart';
import '../state/studio_state.dart';

class FileTree extends StatelessWidget {
  const FileTree({super.key});

  final List<_ProjectModule> _modules = const [
    _ProjectModule(
      name: 'core',
      status: 'ONLINE',
      statusColor: VoidTokens.statusGreen,
      icon: '●',
      files: ['router.py', 'agent.py', 'vram_manager.py', 'task_lifecycle.py'],
    ),
    _ProjectModule(
      name: 'void_memory',
      status: 'ONLINE',
      statusColor: VoidTokens.statusGreen,
      icon: '●',
      files: ['experience_memory.py', 'system_identity.json'],
    ),
    _ProjectModule(
      name: 'models',
      status: 'ACTIVE',
      statusColor: VoidTokens.voidOrangeBright,
      icon: '⚡',
      files: ['from_scratch_transformer.py', 'checkpoint.pt'],
    ),
    _ProjectModule(
      name: 'void_voice',
      status: 'ONLINE',
      statusColor: VoidTokens.statusGreen,
      icon: '●',
      files: ['wakeword/detector.py', 'stt/transcriber.py', 'tts/piper_engine.py'],
    ),
    _ProjectModule(
      name: 'vision',
      status: 'STANDBY',
      statusColor: VoidTokens.statusCyan,
      icon: '○',
      files: ['detector.py', 'camera_stream.py'],
    ),
    _ProjectModule(
      name: 'skills',
      status: 'LOADED',
      statusColor: VoidTokens.statusPurple,
      icon: '●',
      files: ['agentic.py', 'coding.py', 'system_control.py'],
    ),
    _ProjectModule(
      name: 'tests',
      status: '6 PASSING',
      statusColor: VoidTokens.statusGreen,
      icon: '✓',
      files: ['test_web_voice.py', 'test_tokenizer.py'],
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final state = context.watch<StudioState>();

    return Container(
      width: 230,
      decoration: const BoxDecoration(
        color: VoidTokens.voidObsidian,
        border: Border(
          right: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 1.0),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: const BoxDecoration(
              color: VoidTokens.voidGraphite,
              border: Border(
                bottom: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 1.0),
              ),
            ),
            child: Row(
              children: [
                const Icon(Icons.account_tree_outlined, size: 14, color: VoidTokens.voidOrange),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'PROJECT EXPLORER',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: VoidTheme.hudLabel(fontSize: 9.5),
                  ),
                ),
                const SizedBox(width: 6),
                Text('GIT: MAIN', style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.statusGreen)),
              ],
            ),
          ),

          // Module & File List
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 4),
              itemCount: _modules.length,
              itemBuilder: (context, index) {
                final mod = _modules[index];
                return _buildModuleGroup(context, mod, state);
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildModuleGroup(BuildContext context, _ProjectModule mod, StudioState state) {
    return Theme(
      data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
      child: ExpansionTile(
        initiallyExpanded: true,
        tilePadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 0),
        visualDensity: VisualDensity.compact,
        leading: Text(
          mod.icon,
          style: TextStyle(color: mod.statusColor, fontSize: 11),
        ),
        title: Row(
          children: [
            Expanded(
              child: Text(
                mod.name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: VoidTheme.mono(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: VoidTokens.textHigh,
                ),
              ),
            ),
            const SizedBox(width: 4),
            Text(
              mod.status,
              style: VoidTheme.mono(fontSize: 8, color: mod.statusColor),
            ),
          ],
        ),
        children: mod.files.map((file) {
          final fullPath = '${mod.name}/$file';
          final isSelected = state.activeFile == fullPath;

          return InkWell(
            onTap: () => state.setActiveFile(fullPath),
            child: Container(
              padding: const EdgeInsets.only(left: 32, right: 12, top: 4, bottom: 4),
              decoration: BoxDecoration(
                color: isSelected ? VoidTokens.voidSurface : Colors.transparent,
                border: Border(
                  left: BorderSide(
                    color: isSelected ? VoidTokens.voidOrange : Colors.transparent,
                    width: 2.0,
                  ),
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    file.endsWith('.py') ? Icons.code : Icons.description_outlined,
                    size: 13,
                    color: isSelected ? VoidTokens.voidOrangeBright : VoidTokens.textMuted,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      file,
                      overflow: TextOverflow.ellipsis,
                      style: VoidTheme.mono(
                        fontSize: 10.5,
                        color: isSelected ? VoidTokens.textHigh : VoidTokens.textMedium,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}

class _ProjectModule {
  final String name;
  final String status;
  final Color statusColor;
  final String icon;
  final List<String> files;

  const _ProjectModule({
    required this.name,
    required this.status,
    required this.statusColor,
    required this.icon,
    required this.files,
  });
}
