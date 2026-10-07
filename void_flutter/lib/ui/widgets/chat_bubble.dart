import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../core/constants/app_colors.dart';
import '../../core/models/chat_message.dart';
import 'void_logo.dart';

class ChatBubble extends StatelessWidget {
  final ChatMessage message;
  final VoidCallback? onSpeak;
  final VoidCallback? onDelete;

  const ChatBubble({
    super.key,
    required this.message,
    this.onSpeak,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final isUser = message.sender == MessageSender.user;
    final timeStr = DateFormat('HH:mm').format(message.timestamp);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isUser) ...[
            const VoidLogo(
              size: 28,
              showBackgroundSquircle: true,
              enableGlow: false,
            ),
            const SizedBox(width: 10),
          ],
          Flexible(
            child: isUser
                ? _buildUserBubble(context, timeStr)
                : _buildVoidBubble(context, timeStr),
          ),
          if (isUser) ...[
            const SizedBox(width: 10),
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                color: AppColors.surfaceContainer,
                shape: BoxShape.circle,
                border: Border.all(color: AppColors.borderHairline, width: 1),
              ),
              child: const Center(
                child: Text(
                  'U',
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildUserBubble(BuildContext context, String timeStr) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.surfaceContainer,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.borderHairline, width: 1.0),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          SelectableText(
            message.text,
            style: GoogleFonts.inter(
              color: AppColors.textPrimary,
              fontSize: 14,
              height: 1.45,
            ),
          ),
          const SizedBox(height: 6),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                timeStr,
                style: GoogleFonts.jetBrainsMono(
                  color: AppColors.textSecondary,
                  fontSize: 10,
                ),
              ),
              if (onDelete != null) ...[
                const SizedBox(width: 8),
                InkWell(
                  onTap: onDelete,
                  borderRadius: BorderRadius.circular(8),
                  child: const Padding(
                    padding: EdgeInsets.all(2),
                    child: Icon(
                      Icons.delete_outline,
                      size: 13,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildVoidBubble(BuildContext context, String timeStr) {
    final text = message.text;
    final hasCodeBlock = text.contains('```');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (message.skillUsed != null && message.skillUsed!.isNotEmpty) ...[
          Container(
            margin: const EdgeInsets.only(bottom: 6),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: AppColors.accentSubtle,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: AppColors.accent.withOpacity(0.3),
                width: 1,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.flash_on, size: 11, color: AppColors.accent),
                const SizedBox(width: 4),
                Text(
                  message.skillUsed!.toUpperCase(),
                  style: GoogleFonts.jetBrainsMono(
                    color: AppColors.accent,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.8,
                  ),
                ),
              ],
            ),
          ),
        ],

        if (!hasCodeBlock)
          SelectableText(
            text,
            style: GoogleFonts.inter(
              color: AppColors.textPrimary,
              fontSize: 14,
              height: 1.45,
            ),
          )
        else
          _buildFormattedContent(context, text),

        const SizedBox(height: 8),

        // Action controls toolbar
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              timeStr,
              style: GoogleFonts.jetBrainsMono(
                color: AppColors.textSecondary,
                fontSize: 10,
              ),
            ),
            const SizedBox(width: 10),
            // Copy action
            InkWell(
              onTap: () {
                Clipboard.setData(ClipboardData(text: message.text));
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Message copied to clipboard'),
                    duration: Duration(seconds: 1),
                  ),
                );
              },
              borderRadius: BorderRadius.circular(12),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.surfaceContainer,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.borderHairline, width: 1),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.copy, size: 11, color: AppColors.textSecondary),
                    SizedBox(width: 4),
                    Text(
                      'Copy',
                      style: TextStyle(color: AppColors.textSecondary, fontSize: 10),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 8),
            // Speak action
            InkWell(
              onTap: onSpeak ??
                  () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Speaking response...'),
                        duration: Duration(seconds: 1),
                      ),
                    );
                  },
              borderRadius: BorderRadius.circular(12),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.accentSubtle,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: AppColors.accent.withOpacity(0.3),
                    width: 1,
                  ),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.volume_up, size: 11, color: AppColors.accent),
                    SizedBox(width: 4),
                    Text(
                      'Speak',
                      style: TextStyle(
                        color: AppColors.accent,
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if (onDelete != null) ...[
              const SizedBox(width: 8),
              // Delete individual message action
              InkWell(
                onTap: onDelete,
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  padding: const EdgeInsets.all(5),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceContainer,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.borderHairline, width: 1),
                  ),
                  child: const Icon(
                    Icons.delete_outline,
                    size: 12,
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
            ],
          ],
        ),
      ],
    );
  }

  Widget _buildFormattedContent(BuildContext context, String content) {
    final parts = content.split('```');
    final widgets = <Widget>[];

    for (int i = 0; i < parts.length; i++) {
      final part = parts[i];
      if (part.isEmpty) continue;

      if (i % 2 == 1) {
        // Code Block
        var code = part;
        String? language;
        final lines = code.split('\n');
        if (lines.isNotEmpty && lines.first.trim().isNotEmpty && !lines.first.contains(' ')) {
          language = lines.first.trim();
          code = lines.skip(1).join('\n');
        }

        widgets.add(
          Container(
            margin: const EdgeInsets.symmetric(vertical: 8),
            decoration: BoxDecoration(
              color: AppColors.bgApp,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppColors.borderHairline, width: 1.0),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: const BoxDecoration(
                    color: AppColors.surfaceContainer,
                    borderRadius: BorderRadius.only(
                      topLeft: Radius.circular(13),
                      topRight: Radius.circular(13),
                    ),
                    border: Border(
                      bottom: BorderSide(color: AppColors.borderHairline, width: 1),
                    ),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        (language ?? 'CODE').toUpperCase(),
                        style: GoogleFonts.jetBrainsMono(
                          color: AppColors.textSecondary,
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.8,
                        ),
                      ),
                      InkWell(
                        onTap: () {
                          Clipboard.setData(ClipboardData(text: code.trim()));
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Code copied to clipboard'),
                              duration: Duration(seconds: 1),
                            ),
                          );
                        },
                        child: const Row(
                          children: [
                            Icon(Icons.copy, size: 11, color: AppColors.textSecondary),
                            SizedBox(width: 4),
                            Text(
                              'Copy',
                              style: TextStyle(color: AppColors.textSecondary, fontSize: 10),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: SelectableText(
                    code.trim(),
                    style: GoogleFonts.jetBrainsMono(
                      color: AppColors.textPrimary,
                      fontSize: 12.5,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      } else {
        // Regular Text
        widgets.add(
          SelectableText(
            part.trim(),
            style: GoogleFonts.inter(
              color: AppColors.textPrimary,
              fontSize: 14,
              height: 1.45,
            ),
          ),
        );
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: widgets,
    );
  }
}
