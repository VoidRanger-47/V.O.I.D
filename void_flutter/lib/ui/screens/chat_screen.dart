import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/providers/chat_provider.dart';
import '../../core/providers/settings_provider.dart';
import '../../core/services/speech_service.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/hud_status_badge.dart';
import '../widgets/void_logo.dart';

class ChatScreen extends StatefulWidget {
  final VoidCallback? onOpenDrawer;

  const ChatScreen({super.key, this.onOpenDrawer});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> with SingleTickerProviderStateMixin {
  final TextEditingController _textController = TextEditingController();
  final TextEditingController _nameController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final SpeechService _speechService = SpeechService();
  String _userName = 'User';
  bool _isVoiceRecording = false;

  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _speechService.stop();
    _pulseController.dispose();
    _textController.dispose();
    _nameController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _handleSend(ChatProvider provider) {
    final text = _textController.text.trim();
    if (text.isEmpty) return;
    _textController.clear();
    provider.sendMessage(text);
    _scrollToBottom();
  }

  @override
  Widget build(BuildContext context) {
    final chatProvider = context.watch<ChatProvider>();
    final settingsProvider = context.watch<SettingsProvider>();

    return Scaffold(
      backgroundColor: AppColors.bgApp,
      appBar: AppBar(
        backgroundColor: AppColors.bgApp,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        leading: widget.onOpenDrawer != null
            ? IconButton(
                icon: const Icon(Icons.menu, color: AppColors.textPrimary, size: 20),
                onPressed: widget.onOpenDrawer,
              )
            : null,
        title: Row(
          children: [
            Container(
              width: 7,
              height: 7,
              decoration: BoxDecoration(
                color: settingsProvider.isConnected ? AppColors.accent : AppColors.statusRed,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                chatProvider.currentSession.title,
                overflow: TextOverflow.ellipsis,
                style: GoogleFonts.inter(
                  color: AppColors.textPrimary,
                  fontSize: 13.5,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.2,
                ),
              ),
            ),
            HudStatusBadge(
              label: 'LOCAL 100%',
              isActive: settingsProvider.isConnected,
              isShieldBadge: true,
              activeColor: AppColors.accent,
            ),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
            child: InkWell(
              onTap: () => chatProvider.newSession(),
              borderRadius: BorderRadius.circular(20),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.surfaceContainer,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppColors.borderHairline, width: 1),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.add_rounded, size: 16, color: AppColors.accent),
                    const SizedBox(width: 4),
                    Text(
                      'New',
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 4),
        ],
        bottom: const PreferredSize(
          preferredSize: Size.fromHeight(1),
          child: Divider(color: AppColors.borderHairline, height: 1),
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: chatProvider.messages.isEmpty
                ? _buildWelcomeScreen(chatProvider)
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.only(top: 12, bottom: 12),
                    itemCount: chatProvider.messages.length + (chatProvider.isLoading ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index == chatProvider.messages.length) {
                        return _buildThinkingIndicator();
                      }
                      final msg = chatProvider.messages[index];
                      return ChatBubble(
                        message: msg,
                        onDelete: () => chatProvider.deleteMessage(msg.id),
                        onSpeak: () {
                          _speechService.speak(
                            msg.text,
                            baseUrl: settingsProvider.baseUrl,
                          );
                        },
                      );
                    },
                  ),
          ),
          _buildInputSection(chatProvider),
        ],
      ),
    );
  }

  Widget _buildWelcomeScreen(ChatProvider provider) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 28),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(height: 20),
          const VoidLogo(
            size: 68,
            showBackgroundSquircle: true,
            enableGlow: false,
          ),
          const SizedBox(height: 20),
          Text(
            'Hello, $_userName.',
            style: GoogleFonts.inter(
              fontSize: 28,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Your Local, Private, Autonomous AI & Cognitive Cortex.',
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(
              color: AppColors.textSecondary,
              fontSize: 13.5,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 24),

          // Name Customizer Card
          Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: AppColors.surfaceContainer,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.borderHairline, width: 1.0),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(left: 12),
                    child: TextField(
                      controller: _nameController,
                      style: GoogleFonts.inter(color: AppColors.textPrimary, fontSize: 13),
                      decoration: InputDecoration(
                        hintText: 'Enter your preferred name',
                        hintStyle: GoogleFonts.inter(color: AppColors.textSecondary, fontSize: 12),
                        border: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        focusedBorder: InputBorder.none,
                        filled: false,
                        contentPadding: EdgeInsets.zero,
                      ),
                    ),
                  ),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.accent,
                    foregroundColor: AppColors.bgApp,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    elevation: 0,
                  ),
                  onPressed: () {
                    final name = _nameController.text.trim();
                    if (name.isNotEmpty) {
                      setState(() {
                        _userName = name;
                      });
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Name updated to $name')),
                      );
                    }
                  },
                  child: Text(
                    'Save',
                    style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w700),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 28),

          // Suggestion Prompt Chips
          Wrap(
            spacing: 8,
            runSpacing: 8,
            alignment: WrapAlignment.center,
            children: [
              _buildSuggestionChip('Activate Vision', () {
                _textController.text = 'V.O.I.D., activate vision.';
                _handleSend(provider);
              }),
              _buildSuggestionChip('Cognitive System Status', () {
                _textController.text = 'Show cognitive architecture and system stats';
                _handleSend(provider);
              }),
              _buildSuggestionChip('Research AI Architectures', () {
                _textController.text = 'Search the web for latest reasoning agent designs';
                _handleSend(provider);
              }),
              _buildSuggestionChip('Memory Inspection', () {
                _textController.text = 'Inspect your knowledge graph and memories';
                _handleSend(provider);
              }),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSuggestionChip(String label, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        decoration: BoxDecoration(
          color: AppColors.surfaceContainer,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.borderHairline, width: 1.0),
        ),
        child: Text(
          label,
          style: GoogleFonts.inter(
            color: AppColors.textPrimary,
            fontSize: 12.5,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
    );
  }

  Widget _buildThinkingIndicator() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const VoidLogo(
            size: 28,
            showBackgroundSquircle: true,
            enableGlow: false,
          ),
          const SizedBox(width: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: AppColors.surfaceContainer,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.borderHairline, width: 1.0),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(3, (i) {
                return AnimatedBuilder(
                  animation: _pulseController,
                  builder: (context, child) {
                    final delay = i * 0.2;
                    final animVal = (_pulseController.value + delay) % 1.0;
                    final scale = 0.6 + (animVal * 0.5);
                    final opacity = 0.4 + (animVal * 0.6);

                    return Container(
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      width: 6 * scale,
                      height: 6 * scale,
                      decoration: BoxDecoration(
                        color: AppColors.accent.withOpacity(opacity.clamp(0.0, 1.0)),
                        shape: BoxShape.circle,
                      ),
                    );
                  },
                );
              }),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInputSection(ChatProvider provider) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 6, 12, 10),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (_isVoiceRecording) ...[
            Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: AppColors.accentSubtle,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.accent.withOpacity(0.3)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.mic, size: 14, color: AppColors.accent),
                  const SizedBox(width: 6),
                  Text(
                    'LISTENING TO VOICE...',
                    style: GoogleFonts.jetBrainsMono(
                      color: AppColors.accent,
                      fontSize: 10.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.8,
                    ),
                  ),
                ],
              ),
            ),
          ],

          // Geometric Input Box (0xFF161616 Container with 0xFF262626 border)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.surfaceContainer,
              borderRadius: BorderRadius.circular(22),
              border: Border.all(
                color: _textController.text.isNotEmpty ? AppColors.accent : AppColors.borderHairline,
                width: 1.0,
              ),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.attach_file, color: AppColors.textSecondary, size: 19),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(minWidth: 30, minHeight: 30),
                      tooltip: 'Attach file',
                      onPressed: () {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('File attachment ready for analysis')),
                        );
                      },
                    ),
                    IconButton(
                      icon: Icon(
                        _isVoiceRecording ? Icons.mic : Icons.mic_none,
                        color: _isVoiceRecording ? AppColors.accent : AppColors.textSecondary,
                        size: 19,
                      ),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(minWidth: 30, minHeight: 30),
                      tooltip: 'Voice Input',
                      onPressed: () {
                        setState(() {
                          _isVoiceRecording = !_isVoiceRecording;
                        });
                        if (_isVoiceRecording) {
                          Future.delayed(const Duration(seconds: 3), () {
                            if (mounted && _isVoiceRecording) {
                              setState(() {
                                _isVoiceRecording = false;
                                _textController.text = 'Analyze system status';
                              });
                            }
                          });
                        }
                      },
                    ),
                    const SizedBox(width: 2),
                    _buildTogglePill(
                      icon: Icons.psychology_outlined,
                      label: 'THINK',
                      isActive: provider.thinkingMode,
                      onTap: () => provider.toggleThinkingMode(),
                    ),
                    const SizedBox(width: 4),
                    _buildTogglePill(
                      icon: Icons.language,
                      label: 'SEARCH',
                      isActive: provider.forceSearch,
                      onTap: () => provider.toggleForceSearch(),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: TextField(
                        controller: _textController,
                        style: GoogleFonts.inter(color: AppColors.textPrimary, fontSize: 13.5),
                        minLines: 1,
                        maxLines: 4,
                        decoration: InputDecoration(
                          hintText: 'Ask V.O.I.D. anything...',
                          hintStyle: GoogleFonts.inter(color: AppColors.textSecondary, fontSize: 13),
                          border: InputBorder.none,
                          enabledBorder: InputBorder.none,
                          focusedBorder: InputBorder.none,
                          filled: false,
                          contentPadding: const EdgeInsets.symmetric(vertical: 8),
                        ),
                        onSubmitted: (_) => _handleSend(provider),
                      ),
                    ),
                    const SizedBox(width: 4),
                    // Smooth Primary Send Button
                    Container(
                      width: 32,
                      height: 32,
                      decoration: const BoxDecoration(
                        color: AppColors.accent,
                        shape: BoxShape.circle,
                      ),
                      child: IconButton(
                        icon: const Icon(Icons.arrow_upward, color: AppColors.bgApp, size: 18),
                        padding: EdgeInsets.zero,
                        onPressed: () => _handleSend(provider),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 6),

          Text(
            'V.O.I.D. NEURAL SYSTEM • PRIVACY PRESERVED • 100% LOCAL',
            textAlign: TextAlign.center,
            style: GoogleFonts.jetBrainsMono(
              color: AppColors.textSecondary,
              fontSize: 9.5,
              letterSpacing: 1.0,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTogglePill({
    required IconData icon,
    required String label,
    required bool isActive,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
        decoration: BoxDecoration(
          color: isActive ? AppColors.accentSubtle : Colors.transparent,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isActive ? AppColors.accent : AppColors.borderHairline,
            width: 1.0,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 12,
              color: isActive ? AppColors.accent : AppColors.textSecondary,
            ),
            const SizedBox(width: 3),
            Text(
              label,
              style: GoogleFonts.jetBrainsMono(
                fontSize: 9.5,
                fontWeight: FontWeight.w700,
                color: isActive ? AppColors.accent : AppColors.textSecondary,
                letterSpacing: 0.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
