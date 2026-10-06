import 'dart:math' as math;
import 'package:flutter/material.dart';

/// Fast zero-gravity bootup splash screen widget for V.O.I.D.
///
/// Implements a snappy, 1.5-second cold-start physics sequence:
///
/// **Phase 1 — Magnetic Snap** (0.0s – 0.6s):
///   The logo rapidly pulls into frame from an off-axis zero-g state
///   (initial scale 0.7x, rotation -12 degrees, opacity 0.0) snapping firmly
///   into 1.0x scale and 0.0 degrees alignment via [Curves.easeOutBack].
///
/// **Phase 2 — Weightless Drift** (0.6s – 1.5s):
///   Immediately upon snapping, the emblem enters an ambient weightless state.
///   A harmonic sine-wave drift `sin(progress * 2 * pi)` drives vertical floating
///   by ±4px and a gentle micro-sway (±1.0 degree). At the exact 1.5s mark, the
///   drift returns smoothly to 0.0px and 0.0° alignment.
///
/// **Phase 3 — High-Energy Pulse** (0.0s – 1.5s):
///   Behind the logo, a crisp `#FF5F15` radial bloom flashes brightly at the 0.6s
///   snap lock-in with dual outward shockwave rings, then settles into a low-intensity
///   ambient neon aura for the drift phase.
class VoidBootScreen extends StatefulWidget {
  /// Asset path for the emblem logo (e.g. `'assets/images/void_symbol.png'`).
  final String logoAssetPath;

  /// Called at the exact 1.5-second mark when the boot sequence completes.
  final VoidCallback? onBootComplete;

  /// Size of the logo emblem in logical pixels. Defaults to 180.
  final double logoSize;

  const VoidBootScreen({
    super.key,
    required this.logoAssetPath,
    this.onBootComplete,
    this.logoSize = 180.0,
  });

  @override
  State<VoidBootScreen> createState() => _VoidBootScreenState();
}

/// Backwards-compatible alias for [VoidBootScreen].
typedef ZeroGravityBootScreen = VoidBootScreen;

class _VoidBootScreenState extends State<VoidBootScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  static const Color _neonOrange = Color(0xFFFF5F15);
  static const Color _electricGold = Color(0xFFFFD54F);
  static const Color _pureBlack = Color(0xFF000000);

  // Time boundary: Phase 1 ends at 0.6s out of 1.5s (0.4 normalized)
  static const double _snapEnd = 0.40;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    _controller.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        if (!mounted) return;
        widget.onBootComplete?.call();
      }
    });

    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _pureBlack,
      body: AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          final t = _controller.value; // 0.0 -> 1.0 over exactly 1500 ms

          // ── Phase 1: Magnetic Snap (0.0s – 0.6s, t: 0.0 -> _snapEnd) ──
          final double snapProgress = (t / _snapEnd).clamp(0.0, 1.0);
          final double snapCurveValue = Curves.easeOutBack.transform(snapProgress);

          // Scale: 0.7x -> 1.0x with snappy easeOutBack overshoot
          final double scale = t <= _snapEnd
              ? 0.7 + (1.0 - 0.7) * snapCurveValue
              : 1.0;

          // Rotation: -12 degrees -> 0.0 degrees
          const double startRotRad = -12.0 * math.pi / 180.0;
          final double snapRotation = t <= _snapEnd
              ? startRotRad * (1.0 - snapCurveValue)
              : 0.0;

          // Opacity: 0.0 -> 1.0 (reaches 1.0 slightly before lock-in)
          final double opacity = t <= _snapEnd
              ? Curves.easeOut.transform((snapProgress / 0.85).clamp(0.0, 1.0))
              : 1.0;

          // ── Phase 2: Weightless Drift (0.6s – 1.5s, t: _snapEnd -> 1.0) ─
          double floatDy = 0.0;
          double swayRad = 0.0;

          if (t > _snapEnd) {
            final double driftProgress =
                ((t - _snapEnd) / (1.0 - _snapEnd)).clamp(0.0, 1.0);

            // Exactly sin(progress * 2 * pi): starts at 0, floats ±4px, ends at 0
            final double driftSine = math.sin(driftProgress * 2.0 * math.pi);
            floatDy = driftSine * 4.0; // ±4 px vertical float
            swayRad = driftSine * (1.0 * math.pi / 180.0); // ±1.0° micro-sway
          }

          final double totalRotation = snapRotation + swayRad;

          // ── Phase 3: High-Energy Pulse & Bloom ────────────────────────
          double bloomIntensity;
          if (t <= _snapEnd) {
            // Flash: rapid cubic surge peaking at 1.0 right at lock-in
            bloomIntensity = math.pow(snapProgress, 2.2).toDouble();
          } else {
            // Decay: falls smoothly from 1.0 to ambient aura (0.20)
            final double decayProgress =
                ((t - _snapEnd) / (1.0 - _snapEnd)).clamp(0.0, 1.0);
            bloomIntensity = 0.20 + 0.80 * math.pow(1.0 - decayProgress, 2.5);
          }

          // Shockwave ring: expands during 0.52s – 0.85s (t: 0.35 -> 0.57)
          const double shockStart = 0.35;
          const double shockEnd = 0.57;
          final bool showShockwave = t >= shockStart && t <= shockEnd;
          final double shockProgress = showShockwave
              ? ((t - shockStart) / (shockEnd - shockStart)).clamp(0.0, 1.0)
              : 0.0;

          final double logoS = widget.logoSize;

          return Stack(
            alignment: Alignment.center,
            children: [
              // ── Background Ambient Radial Bloom (GPU Fragment Shader) ──
              if (bloomIntensity > 0.02)
                Center(
                  child: Container(
                    width: logoS * (1.9 + bloomIntensity * 0.9),
                    height: logoS * (1.9 + bloomIntensity * 0.9),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          _neonOrange.withOpacity(
                            (bloomIntensity * 0.40).clamp(0.0, 0.40),
                          ),
                          _neonOrange.withOpacity(
                            (bloomIntensity * 0.16).clamp(0.0, 0.16),
                          ),
                          const Color(0xFFFF8A50).withOpacity(
                            (bloomIntensity * 0.05).clamp(0.0, 0.05),
                          ),
                          Colors.transparent,
                        ],
                        stops: const [0.0, 0.35, 0.65, 1.0],
                      ),
                    ),
                  ),
                ),

              // ── Lock-in Shockwave Rings (Vector Antialiased) ───────────
              if (showShockwave)
                CustomPaint(
                  size: Size(logoS * 2.8, logoS * 2.8),
                  painter: _ShockwavePainter(
                    progress: shockProgress,
                    primaryColor: _neonOrange,
                    secondaryColor: _electricGold,
                    maxRadius: logoS * 1.3,
                  ),
                ),

              // ── The Floating Emblem (Unified Transform Hierarchy) ──────
              Transform.translate(
                offset: Offset(0, floatDy),
                child: Transform.rotate(
                  angle: totalRotation,
                  child: Transform.scale(
                    scale: scale,
                    child: Opacity(
                      opacity: opacity.clamp(0.0, 1.0),
                      child: Stack(
                        alignment: Alignment.center,
                        children: [
                          // Inner Core Glow behind emblem
                          if (bloomIntensity > 0.05)
                            Container(
                              width: logoS * 0.9,
                              height: logoS * 0.9,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                gradient: RadialGradient(
                                  colors: [
                                    _neonOrange.withOpacity(
                                      (bloomIntensity * 0.45).clamp(0.0, 0.45),
                                    ),
                                    _neonOrange.withOpacity(
                                      (bloomIntensity * 0.15).clamp(0.0, 0.15),
                                    ),
                                    Colors.transparent,
                                  ],
                                  stops: const [0.0, 0.50, 1.0],
                                ),
                              ),
                            ),

                          // The V.O.I.D. Logo Emblem
                          Image.asset(
                            widget.logoAssetPath,
                            width: logoS,
                            height: logoS,
                            fit: BoxFit.contain,
                            filterQuality: FilterQuality.high,
                            errorBuilder: (context, error, stackTrace) {
                              return _VoidTextEmblem(size: logoS);
                            },
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// High-performance shockwave painter (GPU antialiased vector strokes)
// ═══════════════════════════════════════════════════════════════════════════

class _ShockwavePainter extends CustomPainter {
  final double progress;
  final Color primaryColor;
  final Color secondaryColor;
  final double maxRadius;

  _ShockwavePainter({
    required this.progress,
    required this.primaryColor,
    required this.secondaryColor,
    required this.maxRadius,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    // Quadratic alpha decay for snappy falloff
    final alpha = (1.0 - progress) * (1.0 - progress);

    // Primary neon orange shockwave ring
    final r1 = progress * maxRadius;
    final w1 = (1.0 - progress) * 6.0 + 1.2;
    final paint1 = Paint()
      ..color = primaryColor.withOpacity((alpha * 0.90).clamp(0.0, 1.0))
      ..style = PaintingStyle.stroke
      ..strokeWidth = w1;
    canvas.drawCircle(center, r1, paint1);

    // Secondary electric gold inner ripple
    final r2 = progress * maxRadius * 0.76;
    final w2 = (1.0 - progress) * 3.5 + 0.8;
    final paint2 = Paint()
      ..color = secondaryColor.withOpacity((alpha * 0.70).clamp(0.0, 1.0))
      ..style = PaintingStyle.stroke
      ..strokeWidth = w2;
    canvas.drawCircle(center, r2, paint2);

    // Initial white energy burst (first 30% of shockwave)
    if (progress < 0.30) {
      final burstAlpha = (1.0 - progress / 0.30).clamp(0.0, 1.0);
      final paintBurst = Paint()
        ..color = Colors.white.withOpacity(burstAlpha * 0.65)
        ..style = PaintingStyle.fill;
      canvas.drawCircle(center, 18.0 * (1.0 + progress * 2.0), paintBurst);
    }
  }

  @override
  bool shouldRepaint(covariant _ShockwavePainter old) =>
      old.progress != progress;
}

// ═══════════════════════════════════════════════════════════════════════════
// Vector fallback emblem in case asset fails to load
// ═══════════════════════════════════════════════════════════════════════════

class _VoidTextEmblem extends StatelessWidget {
  final double size;

  const _VoidTextEmblem({required this.size});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Center(
        child: CustomPaint(
          size: Size(size * 0.72, size * 0.72),
          painter: _VoidEmblemVectorPainter(color: const Color(0xFFFF5F15)),
        ),
      ),
    );
  }
}

class _VoidEmblemVectorPainter extends CustomPainter {
  final Color color;

  _VoidEmblemVectorPainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    final strokePaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = w * 0.08
      ..strokeCap = StrokeCap.square
      ..strokeJoin = StrokeJoin.miter;

    // Outer inverted chevron
    final outerPath = Path()
      ..moveTo(w * 0.5, h * 0.06)
      ..lineTo(w * 0.06, h * 0.06)
      ..lineTo(w * 0.5, h * 0.88)
      ..lineTo(w * 0.94, h * 0.06)
      ..close();
    canvas.drawPath(outerPath, strokePaint);

    // Inner inverted chevron
    final innerPath = Path()
      ..moveTo(w * 0.5, h * 0.30)
      ..lineTo(w * 0.26, h * 0.30)
      ..lineTo(w * 0.5, h * 0.68)
      ..lineTo(w * 0.74, h * 0.30)
      ..close();
    canvas.drawPath(innerPath, strokePaint..color = color.withOpacity(0.8));
  }

  @override
  bool shouldRepaint(covariant _VoidEmblemVectorPainter old) =>
      old.color != color;
}
