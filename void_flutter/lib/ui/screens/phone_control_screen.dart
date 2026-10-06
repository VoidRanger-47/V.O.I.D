import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/providers/system_provider.dart';
import '../widgets/cyber_card.dart';
import '../widgets/cyber_button.dart';

class PhoneControlScreen extends StatefulWidget {
  const PhoneControlScreen({super.key});

  @override
  State<PhoneControlScreen> createState() => _PhoneControlScreenState();
}

class _PhoneControlScreenState extends State<PhoneControlScreen> {
  final TextEditingController _cmdCtrl = TextEditingController();
  String _lastOutput = '';

  void _runAction(String cmd, SystemProvider provider) async {
    final res = await provider.executePhoneAction(cmd);
    setState(() {
      _lastOutput = res;
    });
  }

  @override
  Widget build(BuildContext context) {
    final system = context.watch<SystemProvider>();

    return Scaffold(
      backgroundColor: AppColors.bgApp,
      appBar: AppBar(
        backgroundColor: AppColors.bgApp,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        title: Row(
          children: [
            const Icon(Icons.phone_android, color: AppColors.accent, size: 18),
            const SizedBox(width: 8),
            Text(
              'PHONE AUTOMATION BRIDGE',
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
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. Overview Card
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
                    child: const Icon(Icons.hub_outlined, color: AppColors.accent, size: 20),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'CROSS-DEVICE BRIDGE',
                          style: GoogleFonts.jetBrainsMono(
                            color: AppColors.textSecondary,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.8,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Control connected Android mobile device directly via local ADB bridge.',
                          style: GoogleFonts.inter(
                            color: AppColors.textPrimary,
                            fontSize: 12.5,
                            height: 1.4,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // 2. Quick Action Grid
            Text(
              'DEVICE ACTIONS',
              style: GoogleFonts.jetBrainsMono(
                color: AppColors.textSecondary,
                fontSize: 10,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.0,
              ),
            ),
            const SizedBox(height: 10),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 8,
              crossAxisSpacing: 8,
              childAspectRatio: 2.4,
              children: [
                _buildActionTile('Unlock Phone', Icons.lock_open, () => _runAction('unlock phone', system)),
                _buildActionTile('Lock Screen', Icons.lock_outline, () => _runAction('lock phone', system)),
                _buildActionTile('Volume Up', Icons.volume_up, () => _runAction('volume up', system)),
                _buildActionTile('Volume Down', Icons.volume_down, () => _runAction('volume down', system)),
                _buildActionTile('Launch YouTube', Icons.play_circle_outline, () => _runAction('open youtube on phone', system)),
                _buildActionTile('Launch WhatsApp', Icons.chat_bubble_outline, () => _runAction('open whatsapp on phone', system)),
              ],
            ),
            const SizedBox(height: 18),

            // 3. Custom Command Input
            Text(
              'CUSTOM ADB COMMAND',
              style: GoogleFonts.jetBrainsMono(
                color: AppColors.textSecondary,
                fontSize: 10,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.0,
              ),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _cmdCtrl,
                    style: GoogleFonts.inter(color: AppColors.textPrimary, fontSize: 13),
                    decoration: InputDecoration(
                      hintText: 'e.g. call Mom, send sms to Alex, open camera...',
                      hintStyle: GoogleFonts.inter(color: AppColors.textSecondary, fontSize: 12),
                      filled: true,
                      fillColor: AppColors.surfaceContainer,
                      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(color: AppColors.borderHairline, width: 1.0),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(color: AppColors.borderHairline, width: 1.0),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(color: AppColors.accent, width: 1.0),
                      ),
                    ),
                    onSubmitted: (val) {
                      if (val.trim().isNotEmpty) {
                        _runAction(val.trim(), system);
                      }
                    },
                  ),
                ),
                const SizedBox(width: 8),
                CyberButton(
                  label: 'Send',
                  icon: Icons.send,
                  borderRadius: 8,
                  isLoading: system.isLoading,
                  onPressed: () {
                    if (_cmdCtrl.text.trim().isNotEmpty) {
                      _runAction(_cmdCtrl.text.trim(), system);
                    }
                  },
                ),
              ],
            ),
            const SizedBox(height: 18),

            // 4. Output Card
            if (_lastOutput.isNotEmpty) ...[
              Text(
                'EXECUTION RESPONSE',
                style: GoogleFonts.jetBrainsMono(
                  color: AppColors.textSecondary,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.0,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.surfaceContainer,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppColors.borderHairline, width: 1.0),
                ),
                child: SelectableText(
                  _lastOutput,
                  style: GoogleFonts.jetBrainsMono(
                    color: AppColors.accent,
                    fontSize: 12,
                    height: 1.4,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildActionTile(String title, IconData icon, VoidCallback onTap) {
    return CyberCard(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      borderRadius: 8,
      onTap: onTap,
      child: Row(
        children: [
          Icon(icon, color: AppColors.accent, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              title,
              style: GoogleFonts.inter(
                color: AppColors.textPrimary,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
