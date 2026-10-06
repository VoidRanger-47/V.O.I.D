import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../core/models/chat_message.dart';
import '../../core/providers/chat_provider.dart';
import '../../core/providers/settings_provider.dart';
import '../../core/services/speech_service.dart';
import '../widgets/void_logo.dart';
import '../widgets/void_attachment_action_menu.dart';

// ─────────────────────────────────────────────────────────────────────────────
// Strict V.O.I.D. Neural Chat palette — DO NOT adjust these tokens
// ─────────────────────────────────────────────────────────────────────────────
class _NC {
  static const scaffold      = Color(0xFF111111); // main background
  static const surface       = Color(0xFF1E1E1E); // containers / chips
  static const orange        = Color(0xFFFF5F15); // primary accent
  static const white         = Color(0xFFFFFFFF); // primary text
  static const grey          = Color(0xFF9CA3AF); // secondary text/icons
  static const neonGreen     = Color(0xFF22C55E); // active status dot
  static const borderThin    = Color(0xFF2A2A2A); // default borders
  static const avatarBg      = orange;
}

/// Full-screen V.O.I.D. Neural Chat interface.
///
/// Drop-in replacement/companion for [ChatScreen]. Wire it into [HomeScreen]'s
/// screen list at index 0, or push it directly from any route.
///
/// Example:
/// ```dart
/// VoidNeuralChatScreen(
///   onOpenDrawer: () => scaffoldKey.currentState?.openDrawer(),
/// )
/// ```
class VoidNeuralChatScreen extends StatefulWidget {
  final VoidCallback? onOpenDrawer;

  const VoidNeuralChatScreen({super.key, this.onOpenDrawer});

  @override
  State<VoidNeuralChatScreen> createState() => _VoidNeuralChatScreenState();
}

class _VoidNeuralChatScreenState extends State<VoidNeuralChatScreen>
    with TickerProviderStateMixin {
  // ── Controllers ────────────────────────────────────────────────────────────
  final TextEditingController _textCtrl = TextEditingController();
  final ScrollController _scrollCtrl = ScrollController();
  final FocusNode _inputFocus = FocusNode();
  final SpeechService _speech = SpeechService();

  // ── State ──────────────────────────────────────────────────────────────────
  bool _isRecording = false;
  bool _hasText = false;

  // ── Animation: pulsing dots (thinking indicator) ───────────────────────────
  late final AnimationController _dotCtrl;

  // ── Animation: logo idle glow ─────────────────────────────────────────────
  late final AnimationController _glowCtrl;
  late final Animation<double> _glowAnim;

  // ── Animation: Attachment action menu & '+' button rotation ─────────────────
  late final AnimationController _menuAnimCtrl;
  late final Animation<double> _menuAnim;
  late final Animation<double> _menuScaleAnim;
  bool _isAttachmentMenuOpen = false;

  // ── Greeting ───────────────────────────────────────────────────────────────
  String get _greeting {
    final h = DateTime.now().hour;
    if (h < 12) return 'Good morning,';
    if (h < 17) return 'Good afternoon,';
    return 'Good evening,';
  }

  // ─────────────────────────────────────────────────────────────────────────
  @override
  void initState() {
    super.initState();

    _dotCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();

    _glowCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2600),
    )..repeat(reverse: true);

    _glowAnim = Tween<double>(begin: 0.35, end: 1.0).animate(
      CurvedAnimation(parent: _glowCtrl, curve: Curves.easeInOut),
    );

    _menuAnimCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 220),
      reverseDuration: const Duration(milliseconds: 180),
    );

    final menuCurve = CurvedAnimation(
      parent: _menuAnimCtrl,
      curve: Curves.easeOutCubic,
      reverseCurve: Curves.easeInCubic,
    );

    _menuAnim = Tween<double>(begin: 0.0, end: 1.0).animate(menuCurve);
    _menuScaleAnim = Tween<double>(begin: 0.88, end: 1.0).animate(menuCurve);

    _inputFocus.addListener(() {
      if (_inputFocus.hasFocus && _isAttachmentMenuOpen) {
        _closeAttachmentMenu();
      }
    });

    _textCtrl.addListener(() {
      final hasText = _textCtrl.text.trim().isNotEmpty;
      if (hasText != _hasText) setState(() => _hasText = hasText);
    });
  }

  @override
  void dispose() {
    _dotCtrl.dispose();
    _glowCtrl.dispose();
    _menuAnimCtrl.dispose();
    _textCtrl.dispose();
    _scrollCtrl.dispose();
    _inputFocus.dispose();
    _speech.stop();
    super.dispose();
  }

  // ── Attachment Menu Actions ───────────────────────────────────────────────

  void _toggleAttachmentMenu() {
    if (_isAttachmentMenuOpen) {
      _closeAttachmentMenu();
    } else {
      _openAttachmentMenu();
    }
  }

  void _openAttachmentMenu() {
    _inputFocus.unfocus();
    setState(() => _isAttachmentMenuOpen = true);
    _menuAnimCtrl.forward();
  }

  void _closeAttachmentMenu() {
    if (!_isAttachmentMenuOpen && !_menuAnimCtrl.isAnimating) return;
    _menuAnimCtrl.reverse().then((_) {
      if (mounted) {
        setState(() => _isAttachmentMenuOpen = false);
      }
    });
  }

  void _handleVisionAttachment(ChatProvider chat) {
    HapticFeedback.mediumImpact();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.add_a_photo_outlined, color: _NC.orange, size: 18),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Vision Input: Select or drop image for neural perception analysis.',
                style: GoogleFonts.inter(fontSize: 12.5),
              ),
            ),
          ],
        ),
        backgroundColor: _NC.surface,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: const BorderSide(color: _NC.borderThin),
        ),
        duration: const Duration(seconds: 3),
      ),
    );
  }

  void _handleFilesAttachment() {
    HapticFeedback.lightImpact();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.folder_open_rounded, color: _NC.orange, size: 18),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Files & Docs: Local filesystem bridge active. Ready to ingest files.',
                style: GoogleFonts.inter(fontSize: 12.5),
              ),
            ),
          ],
        ),
        backgroundColor: _NC.surface,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: const BorderSide(color: _NC.borderThin),
        ),
        duration: const Duration(seconds: 3),
      ),
    );
  }

  void _handleGenerateImage() {
    HapticFeedback.lightImpact();
    setState(() {
      _textCtrl.text = '/imagine ';
      _textCtrl.selection = TextSelection.fromPosition(
        TextPosition(offset: _textCtrl.text.length),
      );
    });
    _inputFocus.requestFocus();
  }

  void _handleNeuralMemory() {
    HapticFeedback.lightImpact();
    setState(() {
      _textCtrl.text = 'Inspect neural memory status and active context.';
      _textCtrl.selection = TextSelection.fromPosition(
        TextPosition(offset: _textCtrl.text.length),
      );
    });
    _inputFocus.requestFocus();
  }

  void _handleWebSearch(ChatProvider chat) {
    HapticFeedback.lightImpact();
    if (!chat.forceSearch) {
      chat.toggleForceSearch();
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.language_rounded, color: _NC.orange, size: 18),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Web Search & Live Network query enabled for upcoming prompt.',
                style: GoogleFonts.inter(fontSize: 12.5),
              ),
            ),
          ],
        ),
        backgroundColor: _NC.surface,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: const BorderSide(color: _NC.borderThin),
        ),
        duration: const Duration(seconds: 2),
      ),
    );
    _inputFocus.requestFocus();
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 280),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _handleSend(ChatProvider provider, SettingsProvider settings) {
    final text = _textCtrl.text.trim();
    if (text.isEmpty || provider.isLoading) return;
    HapticFeedback.lightImpact();
    _textCtrl.clear();
    setState(() => _hasText = false);
    provider.sendMessage(
      text,
      provider: settings.activeEngine,
      model: settings.activeEngine == 'ollama' ? settings.activeOllamaModel : null,
    );
    _scrollToBottom();
  }

  void _handleSuggestion(ChatProvider provider, SettingsProvider settings, String text) {
    HapticFeedback.selectionClick();
    provider.sendMessage(
      text,
      provider: settings.activeEngine,
      model: settings.activeEngine == 'ollama' ? settings.activeOllamaModel : null,
    );
    _scrollToBottom();
  }

  // ─────────────────────────────────────────────────────────────────────────
  // BUILD
  // ─────────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final chat = context.watch<ChatProvider>();
    final settings = context.watch<SettingsProvider>();
    final keyboardH = MediaQuery.of(context).viewInsets.bottom;
    final isEmpty = chat.messages.isEmpty ||
        (chat.messages.length == 1 &&
            chat.messages.first.sender == MessageSender.voidAgent &&
            chat.messages.first.skillUsed == 'system_info');

    return PopScope(
      canPop: !_isAttachmentMenuOpen,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop && _isAttachmentMenuOpen) {
          _closeAttachmentMenu();
        }
      },
      child: Scaffold(
        backgroundColor: _NC.scaffold,
        // ── TOP APP BAR ────────────────────────────────────────────────────
        appBar: AppBar(
          backgroundColor: _NC.scaffold,
          elevation: 0,
          scrolledUnderElevation: 0,
          surfaceTintColor: Colors.transparent,
          systemOverlayStyle: const SystemUiOverlayStyle(
            statusBarColor: Colors.transparent,
            statusBarIconBrightness: Brightness.light,
          ),
          leading: widget.onOpenDrawer != null
              ? IconButton(
                  icon: const Icon(Icons.menu_rounded,
                      color: _NC.grey, size: 22),
                  onPressed: widget.onOpenDrawer,
                  splashRadius: 20,
                )
              : null,
          // ── Center title (Interactive Model Selector) ───────────────────
          title: _buildAppBarCenter(settings),
          centerTitle: true,
          // ── Right avatar ───────────────────────────────────────────────
          actions: const [
            Padding(
              padding: EdgeInsets.only(right: 14),
              child: _UserAvatar(initial: 'A'),
            ),
          ],
        ),

        // ── BODY ────────────────────────────────────────────────────────────
        body: Column(
          children: [
            // Hairline separator below app bar
            Container(height: 1, color: _NC.borderThin),

            // Message area / empty state (Dismisses attachment menu on tap outside)
            Expanded(
              child: GestureDetector(
                behavior: _isAttachmentMenuOpen
                    ? HitTestBehavior.opaque
                    : HitTestBehavior.deferToChild,
                onTap: () {
                  if (_isAttachmentMenuOpen) {
                    _closeAttachmentMenu();
                  }
                },
                child: isEmpty
                    ? _buildEmptyState(chat, settings)
                    : _buildMessageList(chat, settings),
              ),
            ),

            // Bottom input — floats above keyboard
            AnimatedPadding(
              duration: const Duration(milliseconds: 180),
              curve: Curves.easeOut,
              padding: EdgeInsets.only(
                bottom: keyboardH > 0 ? keyboardH : 0,
              ),
              child: _buildBottomInputArea(chat, settings),
            ),
          ],
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────────────────
  // APP BAR WIDGETS
  // ─────────────────────────────────────────────────────────────────────────

  Widget _buildAppBarCenter(SettingsProvider settings) {
    final isOnline = settings.isConnected;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Status dot
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: isOnline ? _NC.neonGreen : Colors.redAccent,
            shape: BoxShape.circle,
            boxShadow: isOnline
                ? [
                    BoxShadow(
                      color: _NC.neonGreen.withOpacity(0.6),
                      blurRadius: 6,
                      spreadRadius: 1,
                    ),
                  ]
                : null,
          ),
        ),
        const SizedBox(width: 8),
        // Interactive Engine & Model Pill badge
        _EngineSelectorPill(
          isOnline: isOnline,
          activeEngine: settings.activeEngine,
          activeModel: settings.activeOllamaModel,
          isOllamaRunning: settings.isOllamaServerRunning,
          onTap: () => _showModelSelectorSheet(context, settings),
        ),
      ],
    );
  }

  void _showModelSelectorSheet(BuildContext context, SettingsProvider settings) {
    HapticFeedback.mediumImpact();
    final pullCtrl = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: _NC.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            final isOllamaActive = settings.activeEngine == 'ollama';
            final isLocalActive = settings.activeEngine == 'local';
            final isGeminiActive = settings.activeEngine == 'gemini';

            return SafeArea(
              child: SingleChildScrollView(
                padding: EdgeInsets.only(
                  left: 20,
                  right: 20,
                  top: 12,
                  bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Top drag pill
                    Center(
                      child: Container(
                        width: 40,
                        height: 4,
                        margin: const EdgeInsets.only(bottom: 16),
                        decoration: BoxDecoration(
                          color: _NC.grey.withOpacity(0.35),
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ),

                    // Header
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: _NC.orange.withOpacity(0.16),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Icon(Icons.memory_rounded, color: _NC.orange, size: 20),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'NEURAL INFERENCE ENGINE',
                                style: GoogleFonts.inter(
                                  color: _NC.white,
                                  fontSize: 14.5,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 0.8,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                'Select local offline LLM or cloud assistant',
                                style: GoogleFonts.inter(
                                  color: _NC.grey,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                        if (settings.isOllamaLoading)
                          const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor: AlwaysStoppedAnimation<Color>(_NC.orange),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 18),

                    // ── 1. OLLAMA OFFLINE MODELS CARD ────────────────────────
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: isOllamaActive ? _NC.orange.withOpacity(0.08) : const Color(0xFF181818),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                          color: isOllamaActive ? _NC.orange : _NC.borderThin,
                          width: isOllamaActive ? 1.5 : 1,
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Text('🦙', style: TextStyle(fontSize: 18)),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  'Ollama Offline Models',
                                  style: GoogleFonts.inter(
                                    color: _NC.white,
                                    fontSize: 14,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: settings.isOllamaServerRunning
                                      ? _NC.neonGreen.withOpacity(0.15)
                                      : Colors.amber.withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(
                                    color: settings.isOllamaServerRunning
                                        ? _NC.neonGreen.withOpacity(0.5)
                                        : Colors.amber.withOpacity(0.5),
                                  ),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      Icons.circle,
                                      size: 7,
                                      color: settings.isOllamaServerRunning
                                          ? _NC.neonGreen
                                          : Colors.amber,
                                    ),
                                    const SizedBox(width: 4),
                                    Text(
                                      settings.isOllamaServerRunning ? 'DAEMON READY' : 'OFFLINE',
                                      style: GoogleFonts.inter(
                                        fontSize: 10,
                                        fontWeight: FontWeight.w700,
                                        color: settings.isOllamaServerRunning
                                            ? _NC.neonGreen
                                            : Colors.amber,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            '100% private, zero-cloud offline intelligence running locally on hardware.',
                            style: GoogleFonts.inter(color: _NC.grey, fontSize: 11.5),
                          ),
                          const SizedBox(height: 12),

                          Text(
                            'SELECT MODEL:',
                            style: GoogleFonts.inter(
                              color: _NC.grey,
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 0.6,
                            ),
                          ),
                          const SizedBox(height: 8),

                          Builder(builder: (context) {
                            final modelList = settings.ollamaInstalledModels.isNotEmpty
                                ? settings.ollamaInstalledModels
                                : ['llama3.2', 'llama3.2:1b', 'deepseek-r1:8b', 'mistral', 'qwen2.5:7b'];

                            return Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: modelList.map((m) {
                                final isSelected = isOllamaActive && (settings.activeOllamaModel == m || settings.activeOllamaModel.startsWith(m));
                                return GestureDetector(
                                  onTap: () async {
                                    HapticFeedback.selectionClick();
                                    await settings.switchOllamaModel(m);
                                    setSheetState(() {});
                                  },
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                    decoration: BoxDecoration(
                                      color: isSelected ? _NC.orange : const Color(0xFF262626),
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(
                                        color: isSelected ? _NC.orange : const Color(0xFF383838),
                                      ),
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        if (isSelected) ...[
                                          const Icon(Icons.check_rounded, size: 13, color: _NC.white),
                                          const SizedBox(width: 4),
                                        ],
                                        Text(
                                          m,
                                          style: GoogleFonts.inter(
                                            color: isSelected ? _NC.white : const Color(0xFFD1D5DB),
                                            fontSize: 12,
                                            fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                );
                              }).toList(),
                            );
                          }),

                          const SizedBox(height: 12),

                          Row(
                            children: [
                              Expanded(
                                child: SizedBox(
                                  height: 36,
                                  child: TextField(
                                    controller: pullCtrl,
                                    style: GoogleFonts.inter(color: _NC.white, fontSize: 12),
                                    decoration: InputDecoration(
                                      hintText: 'Pull new model (e.g. llama3.2:1b)',
                                      hintStyle: GoogleFonts.inter(color: _NC.grey.withOpacity(0.7), fontSize: 11.5),
                                      filled: true,
                                      fillColor: const Color(0xFF262626),
                                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 0),
                                      border: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(8),
                                        borderSide: const BorderSide(color: Color(0xFF383838)),
                                      ),
                                      enabledBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(8),
                                        borderSide: const BorderSide(color: Color(0xFF383838)),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              GestureDetector(
                                onTap: () async {
                                  final name = pullCtrl.text.trim();
                                  if (name.isNotEmpty) {
                                    HapticFeedback.lightImpact();
                                    pullCtrl.clear();
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Text('Downloading Ollama model "$name" in background...'),
                                        backgroundColor: _NC.orange,
                                        duration: const Duration(seconds: 3),
                                      ),
                                    );
                                    await settings.pullOllamaModel(name);
                                    setSheetState(() {});
                                  }
                                },
                                child: Container(
                                  height: 36,
                                  padding: const EdgeInsets.symmetric(horizontal: 12),
                                  decoration: BoxDecoration(
                                    color: _NC.orange.withOpacity(0.2),
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(color: _NC.orange.withOpacity(0.5)),
                                  ),
                                  child: Center(
                                    child: Text(
                                      'Pull',
                                      style: GoogleFonts.inter(
                                        color: _NC.orange,
                                        fontSize: 12,
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),

                    // ── 2. V.O.I.D. NATIVE PYTORCH TRANSFORMER ───────────────
                    GestureDetector(
                      onTap: () async {
                        HapticFeedback.selectionClick();
                        await settings.selectEngine('local');
                        setSheetState(() {});
                      },
                      child: Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: isLocalActive ? _NC.orange.withOpacity(0.08) : const Color(0xFF181818),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: isLocalActive ? _NC.orange : _NC.borderThin,
                            width: isLocalActive ? 1.5 : 1,
                          ),
                        ),
                        child: Row(
                          children: [
                            const Text('⚡', style: TextStyle(fontSize: 18)),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'V.O.I.D. Native Transformer (103M Offline)',
                                    style: GoogleFonts.inter(
                                      color: _NC.white,
                                      fontSize: 13.5,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    'Built-in PyTorch GPT decoder checkpoint (checkpoint.pt)',
                                    style: GoogleFonts.inter(color: _NC.grey, fontSize: 11),
                                  ),
                                ],
                              ),
                            ),
                            if (isLocalActive)
                              const Icon(Icons.check_circle_rounded, color: _NC.orange, size: 20),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),

                    // ── 3. GEMINI 2.0 FLASH (CLOUD) ──────────────────────────
                    GestureDetector(
                      onTap: () async {
                        HapticFeedback.selectionClick();
                        await settings.selectEngine('gemini');
                        setSheetState(() {});
                      },
                      child: Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: isGeminiActive ? _NC.orange.withOpacity(0.08) : const Color(0xFF181818),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: isGeminiActive ? _NC.orange : _NC.borderThin,
                            width: isGeminiActive ? 1.5 : 1,
                          ),
                        ),
                        child: Row(
                          children: [
                            const Text('✦', style: TextStyle(fontSize: 18, color: Colors.lightBlueAccent)),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Gemini 2.0 Flash (Hybrid Cloud)',
                                    style: GoogleFonts.inter(
                                      color: _NC.white,
                                      fontSize: 13.5,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    'Live web grounding & deep reasoning synthesis',
                                    style: GoogleFonts.inter(color: _NC.grey, fontSize: 11),
                                  ),
                                ],
                              ),
                            ),
                            if (isGeminiActive)
                              const Icon(Icons.check_circle_rounded, color: _NC.orange, size: 20),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  // ─────────────────────────────────────────────────────────────────────────
  // EMPTY STATE
  // ─────────────────────────────────────────────────────────────────────────

  Widget _buildEmptyState(ChatProvider chat, SettingsProvider settings) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(24, 32, 24, 24),
      child: Column(
        children: [
          // Glowing V.O.I.D. emblem
          _buildGlowingEmblem(),
          const SizedBox(height: 28),

          // Greeting headline
          RichText(
            textAlign: TextAlign.center,
            text: TextSpan(
              style: GoogleFonts.inter(
                fontSize: 30,
                fontWeight: FontWeight.w800,
                height: 1.18,
                letterSpacing: -0.8,
              ),
              children: [
                TextSpan(
                  text: '$_greeting ',
                  style: const TextStyle(color: _NC.white),
                ),
                const TextSpan(
                  text: 'Abhinav.',
                  style: TextStyle(color: _NC.orange),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // Subtitle
          Text(
            'Your local, private, offline AI system\n& Neural Cognitive Engine.',
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(
              color: _NC.grey,
              fontSize: 13.5,
              height: 1.55,
            ),
          ),
          const SizedBox(height: 32),

          // Suggestion chips
          _buildSuggestionGrid(chat, settings),
          const SizedBox(height: 12),
        ],
      ),
    );
  }

  Widget _buildGlowingEmblem() {
    return AnimatedBuilder(
      animation: _glowAnim,
      builder: (context, child) {
        return Container(
          width: 92,
          height: 92,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: _NC.orange.withOpacity(0.30 * _glowAnim.value),
                blurRadius: 36,
                spreadRadius: 8,
              ),
              BoxShadow(
                color: _NC.orange.withOpacity(0.12 * _glowAnim.value),
                blurRadius: 72,
                spreadRadius: 16,
              ),
            ],
          ),
          child: child,
        );
      },
      child: const VoidLogo(
        size: 72,
        showBackgroundSquircle: true,
        enableGlow: false,
      ),
    );
  }

  Widget _buildSuggestionGrid(ChatProvider chat, SettingsProvider settings) {
    const chips = [
      (Icons.remove_red_eye_outlined, 'Activate Vision',
          'V.O.I.D., activate vision and describe what you see.'),
      (Icons.visibility, 'What do you see?',
          'Describe everything you can see right now.'),
      (Icons.code, 'Open VS Code',
          'Open VS Code and switch to the current project.'),
      (Icons.speed, 'System Stats',
          'Show CPU, RAM, GPU and storage utilization.'),
      (Icons.psychology_outlined, 'Reasoning Status',
          'Show the current reasoning depth and active neural pathways.'),
      (Icons.language, 'Web Research',
          'Search the web for the latest AI breakthroughs.'),
    ];

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      alignment: WrapAlignment.center,
      children: chips
          .map((c) => _SuggestionChip(
                icon: c.$1,
                label: c.$2,
                onTap: () => _handleSuggestion(chat, settings, c.$3),
              ))
          .toList(),
    );
  }

  // ─────────────────────────────────────────────────────────────────────────
  // MESSAGE LIST
  // ─────────────────────────────────────────────────────────────────────────

  Widget _buildMessageList(ChatProvider chat, SettingsProvider settings) {
    return ListView.builder(
      controller: _scrollCtrl,
      padding: const EdgeInsets.symmetric(vertical: 16),
      itemCount: chat.messages.length + (chat.isLoading ? 1 : 0),
      itemBuilder: (context, i) {
        if (i == chat.messages.length) {
          return _buildThinkingBubble();
        }
        final msg = chat.messages[i];
        return _MessageBubble(
          message: msg,
          onSpeak: () => _speech.speak(
            msg.text,
            baseUrl: settings.baseUrl,
          ),
          onCopy: () {
            Clipboard.setData(ClipboardData(text: msg.text));
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Copied to clipboard'),
                duration: Duration(seconds: 1),
                behavior: SnackBarBehavior.floating,
              ),
            );
          },
          onDelete: () => chat.deleteMessage(msg.id),
          pulseCtrl: _dotCtrl,
        );
      },
    );
  }

  Widget _buildThinkingBubble() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          // Small emblem avatar
          const VoidLogo(
            size: 26,
            showBackgroundSquircle: true,
            enableGlow: false,
          ),
          const SizedBox(width: 10),
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: const BoxDecoration(
              color: _NC.surface,
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(18),
                topRight: Radius.circular(18),
                bottomRight: Radius.circular(18),
                bottomLeft: Radius.circular(4),
              ),
            ),
            child: _ThinkingDots(controller: _dotCtrl),
          ),
        ],
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────────────────
  // BOTTOM INPUT AREA
  // ─────────────────────────────────────────────────────────────────────────

  Widget _buildBottomInputArea(ChatProvider chat, SettingsProvider settings) {
    return SafeArea(
      top: false,
      child: Container(
        color: _NC.scaffold,
        padding: const EdgeInsets.fromLTRB(14, 8, 14, 4),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Floating Action Menu (Anchored directly above input capsule) ──
            if (_isAttachmentMenuOpen || _menuAnimCtrl.isAnimating)
              AnimatedBuilder(
                animation: _menuAnim,
                builder: (context, child) {
                  return Opacity(
                    opacity: _menuAnim.value.clamp(0.0, 1.0),
                    child: Transform.scale(
                      scale: _menuScaleAnim.value,
                      alignment: Alignment.bottomLeft,
                      child: child,
                    ),
                  );
                },
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 8, left: 4),
                  child: VoidAttachmentActionMenu(
                    onVisionTap: () {
                      _closeAttachmentMenu();
                      _handleVisionAttachment(chat);
                    },
                    onFilesTap: () {
                      _closeAttachmentMenu();
                      _handleFilesAttachment();
                    },
                    onGenerateImageTap: () {
                      _closeAttachmentMenu();
                      _handleGenerateImage();
                    },
                    onNeuralMemoryTap: () {
                      _closeAttachmentMenu();
                      _handleNeuralMemory();
                    },
                    onWebSearchTap: () {
                      _closeAttachmentMenu();
                      _handleWebSearch(chat);
                    },
                    onClose: _closeAttachmentMenu,
                  ),
                ),
              ),

            // ── Voice recording banner ────────────────────────────────
            AnimatedSize(
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeOut,
              child: _isRecording
                  ? _RecordingBanner(
                      onCancel: () =>
                          setState(() => _isRecording = false),
                    )
                  : const SizedBox.shrink(),
            ),

            // ── Main input capsule ────────────────────────────────────
            Container(
              decoration: BoxDecoration(
                color: _NC.surface,
                borderRadius: BorderRadius.circular(28),
                border: Border.all(
                  color: _NC.orange,
                  width: 1.0,
                ),
                boxShadow: [
                  BoxShadow(
                    color: _NC.orange.withOpacity(0.08),
                    blurRadius: 16,
                    spreadRadius: 0,
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // ── Icon row + text field ─────────────────────────
                  Padding(
                    padding: const EdgeInsets.fromLTRB(6, 4, 6, 0),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        // ── Interactive Attachment '+' Button ────────────────
                        VoidAttachmentButton(
                          animation: _menuAnim,
                          onTap: _toggleAttachmentMenu,
                        ),

                        const SizedBox(width: 4),

                        // Microphone icon
                        _BarIconBtn(
                          icon: _isRecording
                              ? Icons.mic_rounded
                              : Icons.mic_none_rounded,
                          color: _isRecording
                              ? _NC.orange
                              : _NC.grey,
                          onTap: () {
                            HapticFeedback.mediumImpact();
                            setState(
                                () => _isRecording = !_isRecording);
                          },
                        ),

                        const SizedBox(width: 2),

                        // Think chip
                        _ActionChip(
                          label: 'Think',
                          icon: Icons.psychology_outlined,
                          isActive: chat.thinkingMode,
                          onTap: () => chat.toggleThinkingMode(),
                        ),
                        const SizedBox(width: 5),

                        // Search chip
                        _ActionChip(
                          label: 'Search',
                          icon: Icons.language_rounded,
                          isActive: chat.forceSearch,
                          onTap: () => chat.toggleForceSearch(),
                        ),
                        const SizedBox(width: 6),

                        // Text field — expands to fill remaining space
                        Expanded(
                          child: TextField(
                            controller: _textCtrl,
                            focusNode: _inputFocus,
                            onTap: () {
                              if (_isAttachmentMenuOpen) {
                                _closeAttachmentMenu();
                              }
                            },
                            minLines: 1,
                            maxLines: 5,
                            textInputAction: TextInputAction.newline,
                            cursorColor: _NC.orange,
                            cursorWidth: 2,
                            style: GoogleFonts.inter(
                              color: _NC.white,
                              fontSize: 14.5,
                              height: 1.4,
                            ),
                            decoration: InputDecoration(
                              hintText: 'Ask V.O.I.D. anything...',
                              hintStyle: GoogleFonts.inter(
                                color: _NC.grey,
                                fontSize: 14,
                              ),
                              border: InputBorder.none,
                              enabledBorder: InputBorder.none,
                              focusedBorder: InputBorder.none,
                              filled: false,
                              contentPadding: const EdgeInsets.symmetric(
                                vertical: 10,
                              ),
                            ),
                          ),
                        ),

                        const SizedBox(width: 6),

                        // Send button — solid orange circle
                        _SendButton(
                          hasText: _hasText,
                          isLoading: chat.isLoading,
                          onTap: () => _handleSend(chat, settings),
                        ),
                        const SizedBox(width: 4),
                      ],
                    ),
                  ),
                  const SizedBox(height: 6),
                ],
              ),
            ),

            const SizedBox(height: 7),

            // ── Footer caption ────────────────────────────────────────
            Text(
              'V.O.I.D. runs 100% locally  •  Voice  •  Vision  •  AGI Cognitive Engine Active',
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(
                color: _NC.grey.withOpacity(0.55),
                fontSize: 10,
                letterSpacing: 0.1,
              ),
            ),
            const SizedBox(height: 2),
          ],
        ),
      ),
    );
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// COMPONENT WIDGETS
// ═════════════════════════════════════════════════════════════════════════════

/// Interactive Engine & Model Selector Pill badge in the App Bar.
class _EngineSelectorPill extends StatelessWidget {
  final bool isOnline;
  final String activeEngine;
  final String activeModel;
  final bool isOllamaRunning;
  final VoidCallback onTap;

  const _EngineSelectorPill({
    required this.isOnline,
    required this.activeEngine,
    required this.activeModel,
    required this.isOllamaRunning,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    String label;
    IconData icon;
    Color accentColor;

    if (activeEngine == 'ollama') {
      label = 'Ollama: $activeModel';
      icon = Icons.terminal_rounded;
      accentColor = isOllamaRunning ? _NC.orange : Colors.amber;
    } else if (activeEngine == 'gemini') {
      label = 'Gemini 2.0';
      icon = Icons.cloud_done_rounded;
      accentColor = Colors.lightBlueAccent;
    } else {
      label = 'V.O.I.D. Native';
      icon = Icons.bolt_rounded;
      accentColor = _NC.orange;
    }

    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: _NC.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: accentColor.withOpacity(0.55),
            width: 1,
          ),
          boxShadow: [
            BoxShadow(
              color: accentColor.withOpacity(0.08),
              blurRadius: 8,
              spreadRadius: 0,
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 13,
              color: accentColor,
            ),
            const SizedBox(width: 5),
            Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 11.5,
                fontWeight: FontWeight.w600,
                color: _NC.white,
                letterSpacing: 0.1,
              ),
            ),
            const SizedBox(width: 2),
            Icon(
              Icons.arrow_drop_down_rounded,
              size: 16,
              color: _NC.grey.withOpacity(0.8),
            ),
          ],
        ),
      ),
    );
  }
}

/// Circular user avatar with orange background and initial letter.
class _UserAvatar extends StatelessWidget {
  final String initial;

  const _UserAvatar({required this.initial});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 34,
      height: 34,
      decoration: const BoxDecoration(
        color: _NC.avatarBg,
        shape: BoxShape.circle,
      ),
      child: Center(
        child: Text(
          initial.toUpperCase(),
          style: GoogleFonts.inter(
            color: _NC.white,
            fontSize: 14,
            fontWeight: FontWeight.w700,
            height: 1,
          ),
        ),
      ),
    );
  }
}

/// Suggestion chip on the empty-state canvas.
class _SuggestionChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _SuggestionChip({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        splashColor: _NC.orange.withOpacity(0.12),
        highlightColor: _NC.orange.withOpacity(0.06),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: _NC.surface,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: const Color(0xFF3A3A3A),
              width: 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 14, color: _NC.grey),
              const SizedBox(width: 7),
              Text(
                label,
                style: GoogleFonts.inter(
                  color: _NC.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Individual chat message bubble — handles both user and V.O.I.D. messages.
class _MessageBubble extends StatelessWidget {
  final ChatMessage message;
  final VoidCallback onSpeak;
  final VoidCallback onCopy;
  final VoidCallback onDelete;
  final AnimationController pulseCtrl;

  const _MessageBubble({
    required this.message,
    required this.onSpeak,
    required this.onCopy,
    required this.onDelete,
    required this.pulseCtrl,
  });

  bool get _isUser => message.sender == MessageSender.user;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        _isUser ? 60 : 16,
        4,
        _isUser ? 16 : 60,
        4,
      ),
      child: Column(
        crossAxisAlignment:
            _isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          // Skill badge (V.O.I.D. only)
          if (!_isUser && message.skillUsed != null)
            Padding(
              padding: const EdgeInsets.only(left: 40, bottom: 4),
              child: _SkillBadge(skill: message.skillUsed!),
            ),

          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            mainAxisAlignment: _isUser
                ? MainAxisAlignment.end
                : MainAxisAlignment.start,
            children: [
              // V.O.I.D. avatar
              if (!_isUser) ...[
                const Padding(
                  padding: EdgeInsets.only(top: 2),
                  child: VoidLogo(
                    size: 26,
                    showBackgroundSquircle: true,
                    enableGlow: false,
                  ),
                ),
                const SizedBox(width: 8),
              ],

              // Bubble body
              Flexible(
                child: GestureDetector(
                  onLongPress: () => _showContextMenu(context),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 11),
                    decoration: BoxDecoration(
                      color: _isUser
                          ? _NC.orange
                          : _NC.surface,
                      borderRadius: BorderRadius.only(
                        topLeft: const Radius.circular(18),
                        topRight: const Radius.circular(18),
                        bottomLeft: _isUser
                            ? const Radius.circular(18)
                            : const Radius.circular(4),
                        bottomRight: _isUser
                            ? const Radius.circular(4)
                            : const Radius.circular(18),
                      ),
                    ),
                    child: message.isStreaming && message.text.isEmpty
                        ? _ThinkingDots(controller: pulseCtrl)
                        : SelectableText(
                            message.text,
                            style: GoogleFonts.inter(
                              color: _isUser ? _NC.white : _NC.white,
                              fontSize: 14,
                              height: 1.5,
                            ),
                          ),
                  ),
                ),
              ),

              // User avatar
              if (_isUser) ...[
                const SizedBox(width: 8),
                const _UserAvatar(initial: 'A'),
              ],
            ],
          ),

          // Timestamp
          Padding(
            padding: EdgeInsets.only(
              top: 3,
              left: _isUser ? 0 : 38,
              right: _isUser ? 6 : 0,
            ),
            child: Text(
              _formatTime(message.timestamp),
              style: GoogleFonts.inter(
                color: _NC.grey.withOpacity(0.55),
                fontSize: 10,
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showContextMenu(BuildContext context) {
    HapticFeedback.mediumImpact();
    showModalBottomSheet(
      context: context,
      backgroundColor: _NC.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 36,
              height: 4,
              margin: const EdgeInsets.only(top: 10, bottom: 14),
              decoration: BoxDecoration(
                color: _NC.grey.withOpacity(0.3),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            _ContextMenuItem(
              icon: Icons.copy_rounded,
              label: 'Copy text',
              onTap: () {
                Navigator.pop(context);
                onCopy();
              },
            ),
            if (!_isUser)
              _ContextMenuItem(
                icon: Icons.volume_up_rounded,
                label: 'Read aloud',
                onTap: () {
                  Navigator.pop(context);
                  onSpeak();
                },
              ),
            _ContextMenuItem(
              icon: Icons.delete_outline_rounded,
              label: 'Delete message',
              color: Colors.redAccent,
              onTap: () {
                Navigator.pop(context);
                onDelete();
              },
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  String _formatTime(DateTime dt) {
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }
}

/// Animated "typing / thinking" three-dot indicator.
class _ThinkingDots extends StatelessWidget {
  final AnimationController controller;

  const _ThinkingDots({required this.controller});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(3, (i) {
            final phase = (controller.value + i * 0.22) % 1.0;
            final scale = 0.55 + math.sin(phase * math.pi) * 0.45;
            final opacity = 0.35 + math.sin(phase * math.pi) * 0.65;
            return Container(
              margin: const EdgeInsets.symmetric(horizontal: 3),
              width: 7 * scale,
              height: 7 * scale,
              decoration: BoxDecoration(
                color: _NC.orange.withOpacity(opacity.clamp(0.0, 1.0)),
                shape: BoxShape.circle,
              ),
            );
          }),
        );
      },
    );
  }
}

/// Skill/tool badge shown above V.O.I.D. message bubbles.
class _SkillBadge extends StatelessWidget {
  final String skill;

  const _SkillBadge({required this.skill});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: _NC.orange.withOpacity(0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: _NC.orange.withOpacity(0.25),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.bolt_rounded, size: 10, color: _NC.orange.withOpacity(0.8)),
          const SizedBox(width: 4),
          Text(
            skill.toUpperCase().replaceAll('_', ' '),
            style: GoogleFonts.inter(
              color: _NC.orange,
              fontSize: 9.5,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.6,
            ),
          ),
        ],
      ),
    );
  }
}

/// Small icon button in the input bar.
class _BarIconBtn extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  final Color color;

  const _BarIconBtn({
    required this.icon,
    required this.onTap,
    this.color = _NC.grey,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: SizedBox(
        width: 36,
        height: 36,
        child: Icon(icon, size: 20, color: color),
      ),
    );
  }
}

/// Toggleable "Think" / "Search" action chip inside the input bar.
class _ActionChip extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool isActive;
  final VoidCallback onTap;

  const _ActionChip({
    required this.label,
    required this.icon,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        HapticFeedback.selectionClick();
        onTap();
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
        decoration: BoxDecoration(
          color: isActive
              ? _NC.orange.withOpacity(0.18)
              : const Color(0xFF2C2C2C),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isActive
                ? _NC.orange.withOpacity(0.6)
                : const Color(0xFF3C3C3C),
            width: 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 11,
              color: isActive ? _NC.orange : _NC.grey,
            ),
            const SizedBox(width: 4),
            Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 11.5,
                fontWeight: FontWeight.w600,
                color: isActive ? _NC.orange : _NC.grey,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Orange circle send button (arrow up), disabled during loading.
class _SendButton extends StatelessWidget {
  final bool hasText;
  final bool isLoading;
  final VoidCallback onTap;

  const _SendButton({
    required this.hasText,
    required this.isLoading,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final canSend = hasText && !isLoading;

    return GestureDetector(
      onTap: canSend ? onTap : null,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: canSend
              ? _NC.orange
              : _NC.orange.withOpacity(0.28),
          shape: BoxShape.circle,
          boxShadow: canSend
              ? [
                  BoxShadow(
                    color: _NC.orange.withOpacity(0.4),
                    blurRadius: 10,
                    spreadRadius: 0,
                  )
                ]
              : null,
        ),
        child: Center(
          child: isLoading
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor:
                        AlwaysStoppedAnimation<Color>(_NC.white),
                  ),
                )
              : const Icon(
                  Icons.arrow_upward_rounded,
                  color: _NC.white,
                  size: 20,
                ),
        ),
      ),
    );
  }
}

/// Red voice recording banner that slides in above the input capsule.
class _RecordingBanner extends StatelessWidget {
  final VoidCallback onCancel;

  const _RecordingBanner({required this.onCancel});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: _NC.orange.withOpacity(0.14),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: _NC.orange.withOpacity(0.4),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          const Icon(Icons.mic_rounded, size: 16, color: _NC.orange),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Listening… tap × to cancel',
              style: GoogleFonts.inter(
                color: _NC.orange,
                fontSize: 12.5,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          GestureDetector(
            onTap: onCancel,
            child: const Icon(Icons.close_rounded,
                size: 18, color: _NC.grey),
          ),
        ],
      ),
    );
  }
}

/// Context menu item row for the long-press bottom sheet.
class _ContextMenuItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final Color color;

  const _ContextMenuItem({
    required this.icon,
    required this.label,
    required this.onTap,
    this.color = _NC.white,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding:
            const EdgeInsets.symmetric(horizontal: 22, vertical: 12),
        child: Row(
          children: [
            Icon(icon, size: 20, color: color),
            const SizedBox(width: 16),
            Text(
              label,
              style: GoogleFonts.inter(
                color: color,
                fontSize: 14.5,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}


