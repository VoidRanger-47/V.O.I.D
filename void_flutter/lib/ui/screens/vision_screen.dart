import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/api_endpoints.dart';
import '../../core/models/vision_context.dart';
import '../../core/providers/vision_provider.dart';
import '../../core/providers/settings_provider.dart';
import '../widgets/cyber_card.dart';
import '../widgets/cyber_button.dart';
import '../widgets/hud_status_badge.dart';

class VisionScreen extends StatefulWidget {
  const VisionScreen({super.key});

  @override
  State<VisionScreen> createState() => _VisionScreenState();
}

class _VisionScreenState extends State<VisionScreen> {
  final TextEditingController _qaController = TextEditingController();
  String? _qaResponse;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<VisionProvider>().startPolling();
    });
  }

  @override
  void deactivate() {
    context.read<VisionProvider>().stopPolling();
    super.deactivate();
  }

  @override
  void dispose() {
    _qaController.dispose();
    super.dispose();
  }

  void _showEnrollDialog(BuildContext context, VisionProvider visionProvider) {
    final nameCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surfaceContainer,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: const BorderSide(color: AppColors.borderHairline, width: 1.0),
        ),
        title: Row(
          children: [
            const Icon(Icons.face, color: AppColors.accent, size: 20),
            const SizedBox(width: 8),
            Text(
              'Face Profile Enrollment',
              style: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'V.O.I.D. will capture face samples and store a local vector embedding safely on your computer without persisting raw video.',
              style: GoogleFonts.inter(color: AppColors.textSecondary, fontSize: 12.5, height: 1.4),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: nameCtrl,
              style: GoogleFonts.inter(color: AppColors.textPrimary, fontSize: 13),
              decoration: const InputDecoration(
                labelText: 'Full Name (e.g. Abhinav)',
                labelStyle: TextStyle(color: AppColors.accent, fontSize: 12),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('Cancel', style: GoogleFonts.inter(color: AppColors.textSecondary)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.accent,
              foregroundColor: AppColors.bgApp,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
              elevation: 0,
            ),
            onPressed: () async {
              final name = nameCtrl.text.trim();
              Navigator.pop(ctx);
              if (name.isNotEmpty) {
                final res = await visionProvider.enrollFace(name);
                if (context.mounted) {
                  final msg = res['result']?['message'] ?? res['result']?['error'] ?? 'Enrollment executed';
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
                }
              }
            },
            child: Text('Enroll Face', style: GoogleFonts.inter(fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final vision = context.watch<VisionProvider>();
    final settings = context.watch<SettingsProvider>();
    final ctxData = vision.contextData;
    final scene = ctxData?.scene;

    final streamUrl = '${settings.baseUrl}${ApiEndpoints.visionFeed}?hud=${vision.hudOverlayEnabled}&t=${DateTime.now().millisecondsSinceEpoch}';

    return Scaffold(
      backgroundColor: AppColors.bgApp,
      appBar: AppBar(
        backgroundColor: AppColors.bgApp,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        title: Row(
          children: [
            const Icon(Icons.remove_red_eye, color: AppColors.accent, size: 18),
            const SizedBox(width: 8),
            Text(
              'VISION HUD',
              style: GoogleFonts.inter(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.5,
                color: AppColors.textPrimary,
              ),
            ),
            const Spacer(),
            HudStatusBadge(
              label: vision.isCameraActive ? 'ACTIVE' : 'STANDBY',
              isActive: vision.isCameraActive,
              activeColor: AppColors.accent,
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.person_add_alt, size: 18, color: AppColors.textSecondary),
            tooltip: 'Enroll Face Profile',
            onPressed: () => _showEnrollDialog(context, vision),
          ),
          const SizedBox(width: 6),
        ],
        bottom: const PreferredSize(
          preferredSize: Size.fromHeight(1),
          child: Divider(color: AppColors.borderHairline, height: 1),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. Live Feed Viewport Container
            AspectRatio(
              aspectRatio: 4 / 3,
              child: Container(
                decoration: BoxDecoration(
                  color: AppColors.surfaceContainer,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: vision.isCameraActive ? AppColors.accent : AppColors.borderHairline,
                    width: 1.0,
                  ),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(9),
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      if (vision.isCameraActive) ...[
                        Image.network(
                          streamUrl,
                          fit: BoxFit.cover,
                          width: double.infinity,
                          height: double.infinity,
                          errorBuilder: (_, __, ___) => Center(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(Icons.videocam_off, color: AppColors.textSecondary, size: 36),
                                const SizedBox(height: 8),
                                Text(
                                  'Connecting to video stream...',
                                  style: GoogleFonts.inter(color: AppColors.textSecondary, fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ] else ...[
                        Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.visibility_off, color: AppColors.textSecondary, size: 40),
                            const SizedBox(height: 10),
                            Text(
                              'Visual Perception Standby',
                              style: GoogleFonts.inter(
                                color: AppColors.textPrimary,
                                fontWeight: FontWeight.w700,
                                fontSize: 14,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Camera hardware safely decoupled',
                              style: GoogleFonts.inter(color: AppColors.textSecondary, fontSize: 12),
                            ),
                            const SizedBox(height: 14),
                            CyberButton(
                              label: 'Activate Camera',
                              icon: Icons.power_settings_new,
                              onPressed: () => vision.toggleCamera(),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),

            // 2. Control Action Bar
            Row(
              children: [
                Expanded(
                  child: CyberButton(
                    label: vision.isCameraActive ? 'Stop Camera' : 'Start Camera',
                    icon: Icons.power_settings_new,
                    isPrimary: !vision.isCameraActive,
                    customColor: vision.isCameraActive ? AppColors.statusRed : AppColors.accent,
                    isLoading: vision.isLoading,
                    onPressed: () => vision.toggleCamera(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  style: IconButton.styleFrom(
                    backgroundColor: AppColors.surfaceContainer,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    side: const BorderSide(color: AppColors.borderHairline),
                  ),
                  icon: const Icon(Icons.camera_alt_outlined, color: AppColors.accent, size: 18),
                  tooltip: 'Capture Snapshot',
                  onPressed: () async {
                    final res = await vision.triggerSnapshot();
                    if (context.mounted) {
                      final count = (res['objects'] as List?)?.length ?? 0;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Snapshot analyzed: $count objects detected')),
                      );
                    }
                  },
                ),
                const SizedBox(width: 8),
                IconButton(
                  style: IconButton.styleFrom(
                    backgroundColor: AppColors.surfaceContainer,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    side: const BorderSide(color: AppColors.borderHairline),
                  ),
                  icon: const Icon(Icons.document_scanner_outlined, color: AppColors.textPrimary, size: 18),
                  tooltip: 'Deep Scan Scene',
                  onPressed: () async {
                    final res = await vision.triggerScan();
                    if (context.mounted) {
                      final text = res['result']?['natural_response'] ?? 'Scan complete';
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
                    }
                  },
                ),
              ],
            ),
            const SizedBox(height: 14),

            // 3. Performance Mode Selector Pills
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'PERFORMANCE MODE',
                  style: GoogleFonts.jetBrainsMono(
                    color: AppColors.textSecondary,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.0,
                  ),
                ),
                Row(
                  children: ['ECO', 'BALANCED', 'TURBO'].map((m) {
                    final isActive = (ctxData?.mode ?? 'BALANCED') == m;
                    return Container(
                      margin: const EdgeInsets.only(left: 6),
                      child: InkWell(
                        onTap: () => vision.setMode(m),
                        borderRadius: BorderRadius.circular(6),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: isActive ? AppColors.accent : AppColors.surfaceContainer,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: isActive ? AppColors.accent : AppColors.borderHairline,
                            ),
                          ),
                          child: Text(
                            m,
                            style: GoogleFonts.jetBrainsMono(
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              color: isActive ? AppColors.bgApp : AppColors.textPrimary,
                            ),
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ],
            ),
            const SizedBox(height: 14),

            // 4. Recognized Identity Card
            CyberCard(
              borderRadius: 8,
              child: Row(
                children: [
                  Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                      color: AppColors.accentSubtle,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppColors.accent.withOpacity(0.3)),
                    ),
                    child: const Icon(Icons.person_outline, color: AppColors.accent, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'REAL-TIME IDENTITY',
                          style: GoogleFonts.jetBrainsMono(
                            color: AppColors.textSecondary,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.8,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _getIdentityName(ctxData),
                          style: GoogleFonts.inter(
                            color: AppColors.textPrimary,
                            fontSize: 13.5,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  HudStatusBadge(
                    label: _getIdentityBadge(ctxData),
                    isActive: ctxData?.faces.any((f) => f.identity == 'owner') ?? false,
                    activeColor: AppColors.accent,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            // 5. Detected Objects Card
            CyberCard(
              borderRadius: 8,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'DETECTED OBJECTS',
                        style: GoogleFonts.jetBrainsMono(
                          color: AppColors.textSecondary,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.8,
                        ),
                      ),
                      Text(
                        '${ctxData?.objects.length ?? 0} ITEMS',
                        style: GoogleFonts.jetBrainsMono(
                          color: AppColors.accent,
                          fontSize: 10.5,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  if (ctxData == null || ctxData.objects.isEmpty) ...[
                    Text(
                      'No objects highlighted in current frame',
                      style: GoogleFonts.inter(
                        color: AppColors.textSecondary,
                        fontSize: 12,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ] else ...[
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: ctxData.objects.map((obj) {
                        return Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppColors.accentSubtle,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: AppColors.accent.withOpacity(0.3)),
                          ),
                          child: Text(
                            '${obj.label.toUpperCase()} ${((obj.confidence) * 100).toInt()}%',
                            style: GoogleFonts.jetBrainsMono(
                              color: AppColors.accent,
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 12),

            // 6. Scene Diagnostics Card
            CyberCard(
              borderRadius: 8,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'SCENE UNDERSTANDING',
                    style: GoogleFonts.jetBrainsMono(
                      color: AppColors.textSecondary,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.8,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _buildDiagItem('Environment', scene?.environment ?? 'Indoor'),
                      _buildDiagItem('Lighting', scene?.lighting ?? 'Normal'),
                      _buildDiagItem('Activity', scene?.activityLevel ?? 'Static'),
                      _buildDiagItem('People', '${scene?.peopleCount ?? 0}'),
                    ],
                  ),
                  if (scene != null && scene.summary.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    Text(
                      '"${scene.summary}"',
                      style: GoogleFonts.inter(
                        color: AppColors.textPrimary,
                        fontSize: 12,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 12),

            // 7. Visual Reasoning & Q&A Assistant
            CyberCard(
              borderRadius: 8,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.psychology_outlined, color: AppColors.accent, size: 16),
                      const SizedBox(width: 8),
                      Text(
                        'COGNITIVE VISUAL REASONING',
                        style: GoogleFonts.jetBrainsMono(
                          color: AppColors.textSecondary,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.8,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _qaController,
                          style: GoogleFonts.inter(color: AppColors.textPrimary, fontSize: 12.5),
                          decoration: InputDecoration(
                            hintText: 'Ask what camera sees...',
                            hintStyle: GoogleFonts.inter(color: AppColors.textSecondary, fontSize: 12),
                            filled: true,
                            fillColor: AppColors.bgApp,
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(6),
                              borderSide: const BorderSide(color: AppColors.borderHairline),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(6),
                              borderSide: const BorderSide(color: AppColors.borderHairline),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(6),
                              borderSide: const BorderSide(color: AppColors.accent),
                            ),
                          ),
                          onSubmitted: (q) => _runVisualQuery(q, vision),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton(
                        style: IconButton.styleFrom(
                          backgroundColor: AppColors.accent,
                          foregroundColor: AppColors.bgApp,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                        ),
                        icon: const Icon(Icons.send, size: 16),
                        onPressed: () => _runVisualQuery(_qaController.text, vision),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        _buildQueryChip('What am I holding?', vision),
                        _buildQueryChip('Describe scene', vision),
                        _buildQueryChip('Who is here?', vision),
                        _buildQueryChip('Desk items', vision),
                      ],
                    ),
                  ),
                  if (_qaResponse != null) ...[
                    const SizedBox(height: 10),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: AppColors.bgApp,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: AppColors.accent.withOpacity(0.3)),
                      ),
                      child: Text(
                        _qaResponse!,
                        style: GoogleFonts.inter(color: AppColors.textPrimary, fontSize: 12, height: 1.4),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQueryChip(String text, VisionProvider vision) {
    return Container(
      margin: const EdgeInsets.only(right: 6),
      child: InkWell(
        onTap: () {
          _qaController.text = text;
          _runVisualQuery(text, vision);
        },
        borderRadius: BorderRadius.circular(6),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
          decoration: BoxDecoration(
            color: AppColors.bgApp,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: AppColors.borderHairline),
          ),
          child: Text(
            text,
            style: GoogleFonts.inter(color: AppColors.textSecondary, fontSize: 11),
          ),
        ),
      ),
    );
  }

  Future<void> _runVisualQuery(String query, VisionProvider vision) async {
    final clean = query.trim();
    if (clean.isEmpty) return;
    setState(() {
      _qaResponse = 'Analyzing visual scene...';
    });
    final res = await vision.triggerScan();
    setState(() {
      _qaResponse = res['result']?['natural_response'] ?? 'Visual query complete.';
    });
  }

  String _getIdentityName(VisionContextData? data) {
    if (data == null || data.faces.isEmpty) return 'No Face Detected';
    final owner = data.faces.firstWhere(
      (f) => f.identity == 'owner',
      orElse: () => data.faces.first,
    );
    return owner.name;
  }

  String _getIdentityBadge(VisionContextData? data) {
    if (data == null || data.faces.isEmpty) return 'STANDBY';
    final isOwner = data.faces.any((f) => f.identity == 'owner');
    return isOwner ? 'OWNER' : 'UNKNOWN';
  }

  Widget _buildDiagItem(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label.toUpperCase(),
          style: GoogleFonts.jetBrainsMono(color: AppColors.textSecondary, fontSize: 9.5),
        ),
        const SizedBox(height: 2),
        Text(
          value.toUpperCase(),
          style: GoogleFonts.inter(color: AppColors.textPrimary, fontSize: 12, fontWeight: FontWeight.w600),
        ),
      ],
    );
  }
}
