import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

/// V.O.I.D. Design System Palette Tokens
class _VoidMenuTokens {
  static const Color surfaceMenu = Color(0xFF1E1E1E);
  static const Color borderSubtle = Color(0xFF2A2A2A);
  static const Color orangeAccent = Color(0xFFFF5F15);
  static const Color textPrimary = Color(0xFFFFFFFF);
  static const Color textSecondary = Color(0xFF9CA3AF);
  static const Color buttonDefaultBg = Color(0xFF252525);
  static const Color tileHoverBg = Color(0xFF282828);
}

/// Circular or rounded "+" (add) button placed on the far left of the bottom input capsule.
///
/// Default state: Muted grey icon inside a subtle `#252525` circular container.
/// When active/tapped: Smoothly rotates 45 degrees into an "x" close icon and turns V.O.I.D. Orange (`#FF5F15`).
class VoidAttachmentButton extends StatefulWidget {
  final Animation<double> animation;
  final VoidCallback onTap;
  final double size;

  const VoidAttachmentButton({
    super.key,
    required this.animation,
    required this.onTap,
    this.size = 34.0,
  });

  @override
  State<VoidAttachmentButton> createState() => _VoidAttachmentButtonState();
}

class _VoidAttachmentButtonState extends State<VoidAttachmentButton> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.animation,
      builder: (context, child) {
        final t = widget.animation.value;
        final rotationAngle = t * (math.pi / 4); // 45 degrees rotation into "x"

        // Smooth color interpolations
        final iconColor = Color.lerp(
          _VoidMenuTokens.textSecondary,
          _VoidMenuTokens.orangeAccent,
          t,
        )!;

        final containerBg = Color.lerp(
          _isHovered ? const Color(0xFF2E2E2E) : _VoidMenuTokens.buttonDefaultBg,
          const Color(0xFF2B1F1A),
          t,
        )!;

        final borderColor = Color.lerp(
          _isHovered ? const Color(0xFF3F3F3F) : const Color(0xFF303030),
          _VoidMenuTokens.orangeAccent.withOpacity(0.65),
          t,
        )!;

        return MouseRegion(
          cursor: SystemMouseCursors.click,
          onEnter: (_) => setState(() => _isHovered = true),
          onExit: (_) => setState(() => _isHovered = false),
          child: GestureDetector(
            onTap: () {
              HapticFeedback.lightImpact();
              widget.onTap();
            },
            behavior: HitTestBehavior.opaque,
            child: Container(
              width: widget.size,
              height: widget.size,
              decoration: BoxDecoration(
                color: containerBg,
                shape: BoxShape.circle,
                border: Border.all(
                  color: borderColor,
                  width: 1.0,
                ),
                boxShadow: t > 0.05
                    ? [
                        BoxShadow(
                          color: _VoidMenuTokens.orangeAccent.withOpacity(0.35 * t),
                          blurRadius: 10 * t,
                          spreadRadius: 0,
                        ),
                      ]
                    : null,
              ),
              child: Center(
                child: Transform.rotate(
                  angle: rotationAngle,
                  child: Icon(
                    Icons.add_rounded,
                    size: 20,
                    color: iconColor,
                    shadows: t > 0.1
                        ? [
                            Shadow(
                              color: _VoidMenuTokens.orangeAccent.withOpacity(0.6 * t),
                              blurRadius: 6 * t,
                            ),
                          ]
                        : null,
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

/// Floating Popup Action Menu anchored directly above the chat input bar.
///
/// Features:
/// - Rounded corners (`BorderRadius.circular(16)`)
/// - Surface `#1E1E1E` with subtle border `#2A2A2A` and soft V.O.I.D. Orange ambient glow
/// - Menu items with title, descriptive subtitle, and glowing leading icon on hover/tap
class VoidAttachmentActionMenu extends StatelessWidget {
  final VoidCallback onVisionTap;
  final VoidCallback onFilesTap;
  final VoidCallback onGenerateImageTap;
  final VoidCallback onNeuralMemoryTap;
  final VoidCallback onWebSearchTap;
  final VoidCallback? onClose;

  const VoidAttachmentActionMenu({
    super.key,
    required this.onVisionTap,
    required this.onFilesTap,
    required this.onGenerateImageTap,
    required this.onNeuralMemoryTap,
    required this.onWebSearchTap,
    this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(
        maxWidth: 320,
        minWidth: 280,
      ),
      decoration: BoxDecoration(
        color: _VoidMenuTokens.surfaceMenu,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: _VoidMenuTokens.borderSubtle,
          width: 1.0,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.7),
            blurRadius: 28,
            offset: const Offset(0, 10),
            spreadRadius: 2,
          ),
          BoxShadow(
            color: _VoidMenuTokens.orangeAccent.withOpacity(0.10),
            blurRadius: 24,
            spreadRadius: 0,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // ── Menu Header Badge ──────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 12, 12, 10),
              child: Row(
                children: [
                  Container(
                    width: 7,
                    height: 7,
                    decoration: const BoxDecoration(
                      color: _VoidMenuTokens.orangeAccent,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: _VoidMenuTokens.orangeAccent,
                          blurRadius: 6,
                          spreadRadius: 1,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'V.O.I.D. NEURAL ACTIONS',
                      style: GoogleFonts.jetBrainsMono(
                        color: _VoidMenuTokens.textSecondary,
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.0,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (onClose != null) ...[
                    const SizedBox(width: 6),
                    GestureDetector(
                      onTap: onClose,
                      child: const Icon(
                        Icons.close_rounded,
                        size: 16,
                        color: _VoidMenuTokens.textSecondary,
                      ),
                    ),
                  ],
                ],
              ),
            ),

            const Divider(
              color: _VoidMenuTokens.borderSubtle,
              height: 1,
              thickness: 1,
            ),

            // ── Menu Items List ────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _VoidActionTile(
                    title: 'Vision Input / Attach Photo',
                    subtitle: 'Upload image for neural analysis',
                    icon: Icons.add_a_photo_outlined,
                    onTap: onVisionTap,
                  ),
                  const SizedBox(height: 4),
                  _VoidActionTile(
                    title: 'Files & Docs',
                    subtitle: 'Browse local system files',
                    icon: Icons.folder_open_rounded,
                    onTap: onFilesTap,
                  ),
                  const SizedBox(height: 4),
                  _VoidActionTile(
                    title: 'Generate Image',
                    subtitle: 'SD-Turbo offline canvas',
                    icon: Icons.auto_awesome_rounded,
                    onTap: onGenerateImageTap,
                  ),
                  const SizedBox(height: 4),
                  _VoidActionTile(
                    title: 'Neural Memory',
                    subtitle: 'Inspect local context memory',
                    icon: Icons.memory_rounded,
                    onTap: onNeuralMemoryTap,
                  ),
                  const SizedBox(height: 4),
                  _VoidActionTile(
                    title: 'Web Search / Network',
                    subtitle: 'Query external web data',
                    icon: Icons.language_rounded,
                    onTap: onWebSearchTap,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Interactive Action Menu Tile with hover highlight and glowing V.O.I.D. Orange icon.
class _VoidActionTile extends StatefulWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback onTap;

  const _VoidActionTile({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.onTap,
  });

  @override
  State<_VoidActionTile> createState() => _VoidActionTileState();
}

class _VoidActionTileState extends State<_VoidActionTile> {
  bool _isHovered = false;
  bool _isPressed = false;

  bool get _isActive => _isHovered || _isPressed;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTapDown: (_) => setState(() => _isPressed = true),
        onTapUp: (_) => setState(() => _isPressed = false),
        onTapCancel: () => setState(() => _isPressed = false),
        onTap: () {
          HapticFeedback.selectionClick();
          widget.onTap();
        },
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 140),
          curve: Curves.easeOut,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          decoration: BoxDecoration(
            color: _isActive
                ? _VoidMenuTokens.tileHoverBg
                : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: _isActive
                  ? const Color(0xFF383838)
                  : Colors.transparent,
              width: 1.0,
            ),
          ),
          child: Row(
            children: [
              // ── Glowing Leading Icon Container ─────────────────────────
              AnimatedContainer(
                duration: const Duration(milliseconds: 140),
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: _isActive
                      ? const Color(0x28FF5F15)
                      : _VoidMenuTokens.buttonDefaultBg,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _isActive
                        ? _VoidMenuTokens.orangeAccent.withOpacity(0.55)
                        : const Color(0xFF2E2E2E),
                    width: 1.0,
                  ),
                  boxShadow: _isActive
                      ? [
                          BoxShadow(
                            color: _VoidMenuTokens.orangeAccent.withOpacity(0.38),
                            blurRadius: 10,
                            spreadRadius: 1,
                          ),
                        ]
                      : null,
                ),
                child: Center(
                  child: Icon(
                    widget.icon,
                    size: 18,
                    color: _isActive
                        ? _VoidMenuTokens.orangeAccent
                        : _VoidMenuTokens.textSecondary,
                    shadows: _isActive
                        ? [
                            Shadow(
                              color: _VoidMenuTokens.orangeAccent.withOpacity(0.7),
                              blurRadius: 8,
                            ),
                          ]
                        : null,
                  ),
                ),
              ),

              const SizedBox(width: 12),

              // ── Title & Description ────────────────────────────────────
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      widget.title,
                      style: GoogleFonts.inter(
                        color: _VoidMenuTokens.textPrimary,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -0.2,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      widget.subtitle,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.inter(
                        color: _VoidMenuTokens.textSecondary,
                        fontSize: 11,
                        fontWeight: FontWeight.w400,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(width: 6),

              // ── Trailing subtle indicator ──────────────────────────────
              Icon(
                Icons.arrow_forward_ios_rounded,
                size: 11,
                color: _isActive
                    ? _VoidMenuTokens.orangeAccent
                    : const Color(0xFF4B5563),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
