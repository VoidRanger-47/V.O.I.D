import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/providers/settings_provider.dart';
import '../widgets/cyber_card.dart';
import '../widgets/cyber_button.dart';
import '../widgets/hud_status_badge.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final TextEditingController _urlCtrl = TextEditingController();
  final TextEditingController _modelPullCtrl = TextEditingController();
  double _speechSpeed = 1.0;
  bool _autoSpeak = false;
  double _temperature = 0.7;

  @override
  void initState() {
    super.initState();
    final settings = context.read<SettingsProvider>();
    _urlCtrl.text = settings.baseUrl;
  }

  @override
  void dispose() {
    _urlCtrl.dispose();
    _modelPullCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();

    return Scaffold(
      backgroundColor: AppColors.bgApp,
      appBar: AppBar(
        backgroundColor: AppColors.bgApp,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        title: Row(
          children: [
            const Icon(Icons.tune, color: AppColors.accent, size: 18),
            const SizedBox(width: 8),
            Text(
              'SYSTEM CONFIGURATION',
              style: GoogleFonts.inter(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.5,
                color: AppColors.textPrimary,
              ),
            ),
          ],
        ),
        bottom: const PreferredSize(
          preferredSize: Size.fromHeight(1),
          child: Divider(color: AppColors.borderHairline, height: 1),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          // 1. Connection Status Card
          CyberCard(
            borderColor: settings.isConnected
                ? AppColors.statusGreen.withOpacity(0.5)
                : AppColors.statusRed.withOpacity(0.5),
            child: Row(
              children: [
                Icon(
                  settings.isConnected ? Icons.check_circle_outline : Icons.error_outline,
                  color: settings.isConnected ? AppColors.statusGreen : AppColors.statusRed,
                  size: 24,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'BACKEND CONNECTIVITY',
                        style: GoogleFonts.jetBrainsMono(
                          color: AppColors.textSecondary,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1.0,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        settings.isConnected
                            ? 'Connected to V.O.I.D. Server'
                            : 'Disconnected from Host Server',
                        style: GoogleFonts.inter(
                          color: AppColors.textPrimary,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
                HudStatusBadge(
                  label: settings.isConnected ? 'ONLINE' : 'OFFLINE',
                  isActive: settings.isConnected,
                  activeColor: settings.isConnected ? AppColors.statusGreen : AppColors.statusRed,
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // 2. Server Host IP Configuration
          CyberCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'HOST SERVER IP & PORT',
                  style: GoogleFonts.jetBrainsMono(
                    color: AppColors.textSecondary,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.0,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Use 10.0.2.2:5000 for Android Studio Emulator, or your PC local IP (e.g. 192.168.x.x:5000) for physical mobile.',
                  style: GoogleFonts.inter(
                    color: AppColors.textSecondary,
                    fontSize: 11.5,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _urlCtrl,
                  style: GoogleFonts.jetBrainsMono(color: AppColors.textPrimary, fontSize: 13),
                  decoration: const InputDecoration(
                    labelText: 'Server Base URL',
                    labelStyle: TextStyle(color: AppColors.accent, fontSize: 12),
                  ),
                ),
                const SizedBox(height: 10),

                // Presets
                Wrap(
                  spacing: 8,
                  children: [
                    _buildPresetChip('Emulator (10.0.2.2)', 'http://10.0.2.2:5000'),
                    _buildPresetChip('Localhost (127.0.0.1)', 'http://127.0.0.1:5000'),
                  ],
                ),
                const SizedBox(height: 14),

                Row(
                  children: [
                    Expanded(
                      child: CyberButton(
                        label: 'Save & Test Ping',
                        icon: Icons.network_check,
                        isLoading: settings.isChecking,
                        onPressed: () async {
                          await settings.updateBaseUrl(_urlCtrl.text.trim());
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(
                                  settings.isConnected
                                      ? 'Connected successfully!'
                                      : 'Could not reach server.',
                                ),
                                backgroundColor: settings.isConnected
                                    ? const Color(0xFF10B981)
                                    : const Color(0xFFE05656),
                              ),
                            );
                          }
                        },
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // 2.5. Offline Ollama Engine & Model Configuration
          CyberCard(
            borderColor: settings.activeEngine == 'ollama'
                ? AppColors.accent.withOpacity(0.6)
                : null,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        const Text('🦙', style: TextStyle(fontSize: 16)),
                        const SizedBox(width: 8),
                        Text(
                          'OFFLINE OLLAMA ENGINE',
                          style: GoogleFonts.jetBrainsMono(
                            color: AppColors.textSecondary,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1.0,
                          ),
                        ),
                      ],
                    ),
                    HudStatusBadge(
                      label: settings.isOllamaServerRunning ? 'DAEMON READY' : 'OFFLINE',
                      isActive: settings.isOllamaServerRunning,
                      activeColor: settings.isOllamaServerRunning ? AppColors.statusGreen : AppColors.amber,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  'Run local offline LLMs (LLaMA 3.2, DeepSeek-R1, Mistral, Qwen) 100% offline with zero cloud latency.',
                  style: GoogleFonts.inter(
                    color: AppColors.textSecondary,
                    fontSize: 11.5,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: 12),

                // Engine Selector Row
                Text(
                  'PRIMARY INFERENCE ENGINE',
                  style: GoogleFonts.jetBrainsMono(
                    color: AppColors.accent,
                    fontSize: 9.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 8,
                  children: [
                    _buildEngineChip('Ollama (Offline)', 'ollama', settings),
                    _buildEngineChip('V.O.I.D. Native', 'local', settings),
                    _buildEngineChip('Gemini Cloud', 'gemini', settings),
                  ],
                ),
                const SizedBox(height: 14),

                // Installed Ollama Models
                Text(
                  'ACTIVE OLLAMA MODEL',
                  style: GoogleFonts.jetBrainsMono(
                    color: AppColors.accent,
                    fontSize: 9.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 6),

                Builder(builder: (context) {
                  final list = settings.ollamaInstalledModels.isNotEmpty
                      ? settings.ollamaInstalledModels
                      : ['llama3.2', 'llama3.2:1b', 'deepseek-r1:8b', 'mistral', 'qwen2.5:7b'];

                  return Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: list.map((m) {
                      final isSelected = settings.activeEngine == 'ollama' &&
                          (settings.activeOllamaModel == m || settings.activeOllamaModel.startsWith(m));
                      return ChoiceChip(
                        label: Text(m, style: GoogleFonts.inter(fontSize: 11.5)),
                        selected: isSelected,
                        selectedColor: AppColors.accent,
                        backgroundColor: AppColors.bgApp,
                        labelStyle: TextStyle(
                          color: isSelected ? Colors.white : AppColors.textSecondary,
                          fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                        ),
                        side: BorderSide(
                          color: isSelected ? AppColors.accent : AppColors.borderHairline,
                        ),
                        onSelected: (val) {
                          if (val) settings.switchOllamaModel(m);
                        },
                      );
                    }).toList(),
                  );
                }),
                const SizedBox(height: 12),

                // Pull Model Field
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _modelPullCtrl,
                        style: GoogleFonts.jetBrainsMono(color: AppColors.textPrimary, fontSize: 12),
                        decoration: const InputDecoration(
                          hintText: 'Pull model (e.g. deepseek-r1:8b)',
                          hintStyle: TextStyle(color: AppColors.textSecondary, fontSize: 11),
                          labelText: 'Pull from Ollama Library',
                          labelStyle: TextStyle(color: AppColors.textSecondary, fontSize: 11),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    CyberButton(
                      label: 'Pull',
                      icon: Icons.download_rounded,
                      onPressed: () async {
                        final m = _modelPullCtrl.text.trim();
                        if (m.isNotEmpty) {
                          _modelPullCtrl.clear();
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text('Downloading Ollama model "$m" in background...'),
                              backgroundColor: AppColors.accent,
                            ),
                          );
                          await settings.pullOllamaModel(m);
                        }
                      },
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // 3. Voice & Speech Synthesis Settings
          CyberCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.volume_up_outlined, color: AppColors.accent, size: 16),
                    const SizedBox(width: 8),
                    Text(
                      'VOICE & AUDIO SYNTHESIS',
                      style: GoogleFonts.jetBrainsMono(
                        color: AppColors.textSecondary,
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.0,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),

                // Speed Slider
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Speech Speed',
                      style: GoogleFonts.inter(
                        color: AppColors.textPrimary,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: AppColors.bgApp,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: AppColors.borderHairline),
                      ),
                      child: Text(
                        '${_speechSpeed.toStringAsFixed(1)}x',
                        style: GoogleFonts.jetBrainsMono(
                          color: AppColors.accent,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
                Slider(
                  value: _speechSpeed,
                  min: 0.5,
                  max: 2.0,
                  divisions: 15,
                  activeColor: AppColors.accent,
                  inactiveColor: AppColors.borderHairline,
                  onChanged: (val) {
                    setState(() {
                      _speechSpeed = val;
                    });
                  },
                ),
                const SizedBox(height: 8),

                // Auto Speak Toggle Switch
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Auto-Speak Responses',
                          style: GoogleFonts.inter(
                            color: AppColors.textPrimary,
                            fontSize: 12.5,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Speak replies aloud when generation completes',
                          style: GoogleFonts.inter(
                            color: AppColors.textSecondary,
                            fontSize: 10.5,
                          ),
                        ),
                      ],
                    ),
                    Switch(
                      value: _autoSpeak,
                      activeColor: AppColors.accent,
                      activeTrackColor: AppColors.accentSubtle,
                      inactiveTrackColor: AppColors.bgApp,
                      onChanged: (val) {
                        setState(() {
                          _autoSpeak = val;
                        });
                      },
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // 4. Neural Creativity & Parameters Card
          CyberCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.psychology_outlined, color: AppColors.accent, size: 16),
                    const SizedBox(width: 8),
                    Text(
                      'NEURAL MODEL PARAMETERS',
                      style: GoogleFonts.jetBrainsMono(
                        color: AppColors.textSecondary,
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.0,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),

                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Temperature (Creativity)',
                      style: GoogleFonts.inter(
                        color: AppColors.textPrimary,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: AppColors.bgApp,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: AppColors.borderHairline),
                      ),
                      child: Text(
                        _temperature.toStringAsFixed(1),
                        style: GoogleFonts.jetBrainsMono(
                          color: AppColors.accent,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
                Slider(
                  value: _temperature,
                  min: 0.1,
                  max: 1.0,
                  divisions: 9,
                  activeColor: AppColors.accent,
                  inactiveColor: AppColors.borderHairline,
                  onChanged: (val) {
                    setState(() {
                      _temperature = val;
                    });
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // 5. System Information Card
          CyberCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'ABOUT V.O.I.D.',
                  style: GoogleFonts.jetBrainsMono(
                    color: AppColors.textSecondary,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.0,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'V.O.I.D. (Virtual Operator of Information & Development) v1.0.0.\n\nPowered by autonomous neural multi-agent architecture and 100% offline local AI inference.',
                  style: GoogleFonts.inter(
                    color: AppColors.textPrimary,
                    fontSize: 12,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPresetChip(String label, String url) {
    return InkWell(
      onTap: () {
        _urlCtrl.text = url;
      },
      borderRadius: BorderRadius.circular(6),
      child: Container(
        margin: const EdgeInsets.only(top: 4),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: AppColors.bgApp,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: AppColors.borderHairline, width: 1),
        ),
        child: Text(
          label,
          style: GoogleFonts.jetBrainsMono(
            fontSize: 10.5,
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
    );
  }

  Widget _buildEngineChip(String label, String value, SettingsProvider settings) {
    final isSelected = settings.activeEngine == value;
    return ChoiceChip(
      label: Text(label, style: GoogleFonts.inter(fontSize: 11.5)),
      selected: isSelected,
      selectedColor: AppColors.accent,
      backgroundColor: AppColors.bgApp,
      labelStyle: TextStyle(
        color: isSelected ? Colors.white : AppColors.textSecondary,
        fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
      ),
      side: BorderSide(
        color: isSelected ? AppColors.accent : AppColors.borderHairline,
      ),
      onSelected: (val) {
        if (val) settings.selectEngine(value);
      },
    );
  }
}
