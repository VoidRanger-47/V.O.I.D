import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

/// V.O.I.D. Vector Brand Logo Widget
/// Renders the official geometric inverted triangle with nested inner triangle,
/// top-right white accent cut, and amber-gold orbital halo ring.
class VoidLogo extends StatelessWidget {
  final double size;
  final bool showBackgroundSquircle;
  final bool enableGlow;
  final Color? primaryColor;
  final Color? ringColor;

  const VoidLogo({
    super.key,
    this.size = 36,
    this.showBackgroundSquircle = false,
    this.enableGlow = true,
    this.primaryColor,
    this.ringColor,
  });

  @override
  Widget build(BuildContext context) {
    final effectiveColor = primaryColor ?? AppColors.accent;

    if (showBackgroundSquircle) {
      Widget squircleIcon = ClipRRect(
        borderRadius: BorderRadius.circular(size * 0.22),
        child: Image.asset(
          'assets/images/void_icon.png',
          width: size,
          height: size,
          fit: BoxFit.contain,
          filterQuality: FilterQuality.high,
          errorBuilder: (context, error, stackTrace) {
            return Container(
              width: size,
              height: size,
              decoration: BoxDecoration(
                color: const Color(0xFF16171A),
                borderRadius: BorderRadius.circular(size * 0.22),
                border: Border.all(
                  color: const Color(0xFF272832),
                  width: 1.5,
                ),
              ),
              padding: EdgeInsets.all(size * 0.12),
              child: _buildVectorFallback(size * 0.76, effectiveColor),
            );
          },
        ),
      );

      if (enableGlow) {
        return Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(size * 0.22),
            boxShadow: [
              BoxShadow(
                color: effectiveColor.withOpacity(0.35),
                blurRadius: size * 0.25,
                spreadRadius: 1,
              ),
            ],
          ),
          child: squircleIcon,
        );
      }

      return squircleIcon;
    }

    Widget mark = Image.asset(
      'assets/images/void_symbol.png',
      width: size,
      height: size,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.high,
      errorBuilder: (context, error, stackTrace) {
        return _buildVectorFallback(size, effectiveColor);
      },
    );

    if (enableGlow) {
      return Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: effectiveColor.withOpacity(0.3),
              blurRadius: size * 0.3,
              spreadRadius: 1,
            ),
          ],
        ),
        child: mark,
      );
    }

    return mark;
  }

  Widget _buildVectorFallback(double fallbackSize, Color color) {
    return CustomPaint(
      size: Size(fallbackSize, fallbackSize),
      painter: _VoidLogoPainter(
        primaryColor: color,
        ringColor: ringColor ?? const Color(0xFFFFD54F),
        enableGlow: enableGlow,
      ),
    );
  }
}

class _VoidLogoPainter extends CustomPainter {
  final Color primaryColor;
  final Color ringColor;
  final bool enableGlow;

  _VoidLogoPainter({
    required this.primaryColor,
    required this.ringColor,
    required this.enableGlow,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final scale = size.width / 512.0;

    canvas.save();
    canvas.scale(scale, scale);

    final goldRingPaint = Paint()
      ..color = ringColor.withOpacity(0.9)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 14
      ..strokeCap = StrokeCap.round;

    final orangePaint = Paint()
      ..color = primaryColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 24
      ..strokeJoin = StrokeJoin.miter
      ..strokeCap = StrokeCap.square;

    final whiteAccentPaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = 24
      ..strokeJoin = StrokeJoin.miter
      ..strokeCap = StrokeCap.square;

    final innerOrangePaint = Paint()
      ..color = primaryColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 13
      ..strokeJoin = StrokeJoin.miter;

    final innerGoldPaint = Paint()
      ..color = ringColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 5
      ..strokeCap = StrokeCap.round;

    // Optional Glow Filter
    if (enableGlow) {
      final glowPaint = Paint()
        ..color = primaryColor.withOpacity(0.35)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 32
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 12);
      
      final glowPath = Path()
        ..moveTo(126, 150)
        ..lineTo(386, 150)
        ..lineTo(256, 396)
        ..close();
      canvas.drawPath(glowPath, glowPaint);
    }

    // 1. Orbital Halo Ring (Back Arc)
    final backRingRect = Rect.fromCenter(
      center: const Offset(256, 260),
      width: 332,
      height: 104,
    );
    canvas.drawArc(backRingRect, math.pi, math.pi, false, goldRingPaint);

    // 2. Inner Inverted Triangle
    final innerPath = Path()
      ..moveTo(184, 212)
      ..lineTo(328, 212)
      ..lineTo(256, 334)
      ..close();
    canvas.drawPath(innerPath, innerOrangePaint);

    // 3. Inner Triangle Upper Gold Highlight Arc
    final innerGoldRect = Rect.fromCenter(
      center: const Offset(256, 228),
      width: 112,
      height: 24,
    );
    canvas.drawArc(innerGoldRect, math.pi, math.pi, false, innerGoldPaint);

    // 4. Outer Inverted Triangle (Main Orange Body)
    final outerOrangePath = Path()
      ..moveTo(126, 150)
      ..lineTo(324, 150)
      ..moveTo(356, 182)
      ..lineTo(256, 396)
      ..lineTo(126, 150);
    canvas.drawPath(outerOrangePath, orangePaint);

    // 5. Outer Triangle Top-Right White Geometric Accent Cut
    final outerWhitePath = Path()
      ..moveTo(324, 150)
      ..lineTo(386, 150)
      ..lineTo(356, 182);
    canvas.drawPath(outerWhitePath, whiteAccentPaint);

    // 6. Orbital Halo Ring (Front Flanks)
    final frontRingRect = Rect.fromCenter(
      center: const Offset(256, 262),
      width: 344,
      height: 104,
    );
    // Left front flank: from ~165 to 195 deg
    canvas.drawArc(frontRingRect, math.pi * 0.9, math.pi * 0.18, false, goldRingPaint);
    // Right front flank: from ~345 to 15 deg
    canvas.drawArc(frontRingRect, -math.pi * 0.08, math.pi * 0.18, false, goldRingPaint);

    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _VoidLogoPainter oldDelegate) {
    return oldDelegate.primaryColor != primaryColor ||
        oldDelegate.ringColor != ringColor ||
        oldDelegate.enableGlow != enableGlow;
  }
}
