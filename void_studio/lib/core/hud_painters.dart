import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'constants.dart';

/// Renders an exoskeleton HUD panel surface with 45-degree corner chamfers,
/// technical perimeter lines, corner brackets, and optional header accents.
class HudPanelPainter extends CustomPainter {
  final Color backgroundColor;
  final Color borderColor;
  final Color accentColor;
  final double cornerCut;
  final bool hasTopRightCut;
  final bool hasBottomLeftCut;
  final bool showCornerBrackets;
  final String? technicalTag;

  HudPanelPainter({
    this.backgroundColor = VoidTokens.voidGraphite,
    this.borderColor = VoidTokens.voidSurfaceBorder,
    this.accentColor = VoidTokens.voidOrange,
    this.cornerCut = 12.0,
    this.hasTopRightCut = true,
    this.hasBottomLeftCut = false,
    this.showCornerBrackets = true,
    this.technicalTag,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final bgPaint = Paint()
      ..color = backgroundColor
      ..style = PaintingStyle.fill;

    final borderPaint = Paint()
      ..color = borderColor
      ..strokeWidth = 1.0
      ..style = PaintingStyle.stroke;

    final accentPaint = Paint()
      ..color = accentColor
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;

    final path = Path();

    // Start at top-left
    path.moveTo(0, 0);

    // Top edge to top-right cut
    if (hasTopRightCut) {
      path.lineTo(size.width - cornerCut, 0);
      path.lineTo(size.width, cornerCut);
    } else {
      path.lineTo(size.width, 0);
    }

    // Right edge to bottom-right
    path.lineTo(size.width, size.height);

    // Bottom edge to bottom-left cut
    if (hasBottomLeftCut) {
      path.lineTo(cornerCut, size.height);
      path.lineTo(0, size.height - cornerCut);
    } else {
      path.lineTo(0, size.height);
    }

    path.close();

    // Draw panel background
    canvas.drawPath(path, bgPaint);

    // Draw panel outline
    canvas.drawPath(path, borderPaint);

    // Draw technical corner brackets
    if (showCornerBrackets) {
      const bLen = 8.0;

      // Top-Left bracket
      canvas.drawLine(const Offset(0, 0), const Offset(bLen, 0), accentPaint);
      canvas.drawLine(const Offset(0, 0), const Offset(0, bLen), accentPaint);

      // Bottom-Right bracket
      canvas.drawLine(
        Offset(size.width, size.height),
        Offset(size.width - bLen, size.height),
        accentPaint,
      );
      canvas.drawLine(
        Offset(size.width, size.height),
        Offset(size.width, size.height - bLen),
        accentPaint,
      );
    }

    // Optional technical tag text
    if (technicalTag != null && technicalTag!.isNotEmpty) {
      final textSpan = TextSpan(
        text: technicalTag,
        style: const TextStyle(
          color: VoidTokens.textMuted,
          fontSize: 8.5,
          fontFamily: 'Consolas',
          letterSpacing: 1.0,
        ),
      );
      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
      )..layout();
      textPainter.paint(canvas, const Offset(10, 4));
    }
  }

  @override
  bool shouldRepaint(covariant HudPanelPainter oldDelegate) {
    return oldDelegate.backgroundColor != backgroundColor ||
        oldDelegate.borderColor != borderColor ||
        oldDelegate.accentColor != accentColor ||
        oldDelegate.technicalTag != technicalTag;
  }
}

/// HUD container widget that wraps child with HudPanelPainter
class HudPanel extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color backgroundColor;
  final Color borderColor;
  final Color accentColor;
  final double cornerCut;
  final bool hasTopRightCut;
  final bool hasBottomLeftCut;
  final bool showCornerBrackets;
  final String? technicalTag;

  const HudPanel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(12.0),
    this.backgroundColor = const Color(0xCC0E1117),
    this.borderColor = VoidTokens.voidSurfaceBorder,
    this.accentColor = VoidTokens.voidOrange,
    this.cornerCut = 12.0,
    this.hasTopRightCut = true,
    this.hasBottomLeftCut = false,
    this.showCornerBrackets = true,
    this.technicalTag,
  });

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: HudPanelPainter(
        backgroundColor: backgroundColor,
        borderColor: borderColor,
        accentColor: accentColor,
        cornerCut: cornerCut,
        hasTopRightCut: hasTopRightCut,
        hasBottomLeftCut: hasBottomLeftCut,
        showCornerBrackets: showCornerBrackets,
        technicalTag: technicalTag,
      ),
      child: Padding(
        padding: padding,
        child: child,
      ),
    );
  }
}

/// Technical grid background with crosshairs
class HudGridPainter extends CustomPainter {
  final Color gridColor;
  final double spacing;
  final double crosshairSize;

  HudGridPainter({
    this.gridColor = VoidTokens.hudGrid,
    this.spacing = 32.0,
    this.crosshairSize = 4.0,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final linePaint = Paint()
      ..color = gridColor
      ..strokeWidth = 0.5
      ..style = PaintingStyle.stroke;

    final crossPaint = Paint()
      ..color = gridColor.withOpacity(0.08)
      ..strokeWidth = 1.0
      ..style = PaintingStyle.stroke;

    for (double x = 0; x <= size.width; x += spacing) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), linePaint);
    }

    for (double y = 0; y <= size.height; y += spacing) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), linePaint);
    }

    // Intersecting crosshairs
    for (double x = spacing; x < size.width; x += spacing * 2) {
      for (double y = spacing; y < size.height; y += spacing * 2) {
        canvas.drawLine(
          Offset(x - crosshairSize, y),
          Offset(x + crosshairSize, y),
          crossPaint,
        );
        canvas.drawLine(
          Offset(x, y - crosshairSize),
          Offset(x, y + crosshairSize),
          crossPaint,
        );
      }
    }
  }

  @override
  bool shouldRepaint(covariant HudGridPainter oldDelegate) => false;
}

/// Radial segmented circular gauge
class HudRadialGaugePainter extends CustomPainter {
  final double value; // 0.0 to 1.0
  final Color primaryColor;
  final Color trackColor;
  final int segments;
  final double thickness;

  HudRadialGaugePainter({
    required this.value,
    this.primaryColor = VoidTokens.voidOrange,
    this.trackColor = VoidTokens.voidSurfaceBorder,
    this.segments = 24,
    this.thickness = 5.0,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (math.min(size.width, size.height) - thickness) / 2;

    const startAngle = -math.pi * 1.25;
    const sweepTotal = math.pi * 1.5;
    final activeSegments = (value.clamp(0.0, 1.0) * segments).round();

    const gapAngle = 0.04;
    final segAngle = (sweepTotal - (segments - 1) * gapAngle) / segments;

    for (int i = 0; i < segments; i++) {
      final segStart = startAngle + i * (segAngle + gapAngle);
      final isActive = i < activeSegments;

      final paint = Paint()
        ..color = isActive ? primaryColor : trackColor
        ..style = PaintingStyle.stroke
        ..strokeWidth = thickness
        ..strokeCap = StrokeCap.round;

      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        segStart,
        segAngle,
        false,
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant HudRadialGaugePainter oldDelegate) {
    return oldDelegate.value != value || oldDelegate.primaryColor != primaryColor;
  }
}
