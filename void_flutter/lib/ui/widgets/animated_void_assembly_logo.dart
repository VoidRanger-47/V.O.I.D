import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

/// High-impact cinematic assembly of the official V.O.I.D. logo.
///
/// Moves the authentic segmented parts of the official 1080p logo with true
/// centers of mass, 3D perspective, dynamic velocity curves, and an explosive
/// lock-in shockwave:
/// - Left Wing (`void_part_left.png`): High-speed swoop from top-left with 3D rotation
/// - Right Wing (`void_part_right.png`): Dynamic glide from bottom-right with 3D rotation
/// - Quantum Core (`void_part_core.png`): Zooms from z-depth with spinning momentum into cavity
/// - Golden Halo (`void_part_halo.png`): Sweeps from outer orbit, clamping the wings
/// - Top Bar (`void_part_top.png`): Slam-locks from above, completing the emblem
/// - Lock-in Flash & Shockwaves: Dual-ring energy ripples and mechanical recoil bounce
class AnimatedVoidAssemblyLogo extends StatelessWidget {
  final Animation<double> animation;
  final double size;
  final bool showBackgroundSquircle;
  final bool enableGlow;

  const AnimatedVoidAssemblyLogo({
    super.key,
    required this.animation,
    this.size = 220,
    this.showBackgroundSquircle = true,
    this.enableGlow = true,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: animation,
      builder: (context, child) {
        final t = animation.value;

        // Mechanical recoil settle bounce on lock-in (0.78 to 1.0)
        double recoilScale = 1.0;
        if (t >= 0.78) {
          final p = (t - 0.78) / 0.22;
          // Spring overshoot bounce
          recoilScale = 1.0 + math.sin(p * math.pi) * 0.08 * math.exp(-p * 2.5);
        }

        // Staggered intervals with weighted physics curves:
        // 1. Initial Singularity Core Glow (0.00 -> 0.25)
        final tSpark = _interval(t, 0.00, 0.25, Curves.easeOut);
        // 2. Wings Entry (Left: 0.12 -> 0.55, Right: 0.18 -> 0.58)
        final tLeft = _interval(t, 0.12, 0.55, Curves.easeOutCubic);
        final tRight = _interval(t, 0.18, 0.58, Curves.easeOutCubic);
        // 3. Core Triangle Insertion (0.30 -> 0.65)
        final tCore = _interval(t, 0.30, 0.65, Curves.easeOutBack);
        // 4. Gold Orbital Halo (0.45 -> 0.74)
        final tHalo = _interval(t, 0.45, 0.74, Curves.easeOutCubic);
        // 5. Top Bar Clamp (0.55 -> 0.79)
        final tTop = _interval(t, 0.55, 0.79, Curves.easeOutBack);
        // 6. Impact Lock-In & Shockwave (0.78 -> 1.00)
        final tLock = _interval(t, 0.78, 1.00, Curves.easeOutQuad);
        // 7. Background Squircle Reveal (fades in as parts assemble, 0.40 -> 0.80)
        final tSquircle = _interval(t, 0.40, 0.80, Curves.easeOut);

        // Volumetric squircle neon glow that ignites at lock-in
        final glowOpacity = (t >= 0.76)
            ? ((t - 0.76) / 0.24).clamp(0.0, 1.0) * 0.5
            : (t * 0.12).clamp(0.0, 0.12);

        return Transform.scale(
          scale: recoilScale,
          child: Container(
            width: size,
            height: size,
            decoration: enableGlow && glowOpacity > 0.01
                ? BoxDecoration(
                    borderRadius: showBackgroundSquircle
                        ? BorderRadius.circular(size * 0.22)
                        : null,
                    shape: showBackgroundSquircle
                        ? BoxShape.rectangle
                        : BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.accent.withOpacity(glowOpacity),
                        blurRadius: size * 0.35,
                        spreadRadius: 3,
                      ),
                      BoxShadow(
                        color: const Color(0xFFFFD54F).withOpacity(glowOpacity * 0.4),
                        blurRadius: size * 0.18,
                        spreadRadius: 1,
                      ),
                    ],
                  )
                : null,
            child: Stack(
              alignment: Alignment.center,
              children: [
                // 0. Energy Singularity Core Spark in Center Void (0.00 -> 0.30)
                if (tSpark > 0.0 && t < 0.45)
                  Opacity(
                    opacity: (1.0 - (t / 0.45)).clamp(0.0, 1.0),
                    child: Container(
                      width: size * (0.08 + 0.25 * tSpark),
                      height: size * (0.08 + 0.25 * tSpark),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: RadialGradient(
                          colors: [
                            Colors.white,
                            AppColors.accentLight,
                            AppColors.accent.withOpacity(0.0),
                          ],
                          stops: const [0.0, 0.4, 1.0],
                        ),
                      ),
                    ),
                  ),

                // 1. Background Squircle Container (Fades in with dark metallic depth)
                if (showBackgroundSquircle && tSquircle > 0.0)
                  Opacity(
                    opacity: tSquircle,
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(size * 0.22),
                      child: Image.asset(
                        'assets/images/void_part_bg.png',
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
                                width: 2,
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                  ),

                // 2. Left Wing & Chevrons (`void_part_left.png`)
                // Center of mass: (0.28, 0.55). Launches from top-left with 3D angle.
                if (tLeft > 0.0)
                  _buildDynamicPiece(
                    assetPath: 'assets/images/void_part_left.png',
                    size: size,
                    progress: tLeft,
                    pivot: const FractionalOffset(0.28, 0.55),
                    startTranslation: Offset(-size * 0.9, -size * 0.55),
                    startRotationZ: -0.65, // ~ -37 degrees
                    startRotationY: 0.35,  // 3D yaw tilt
                    startScale: 0.55,
                  ),

                // 3. Right Wing & Chevrons (`void_part_right.png`)
                // Center of mass: (0.72, 0.55). Launches from bottom-right with 3D angle.
                if (tRight > 0.0)
                  _buildDynamicPiece(
                    assetPath: 'assets/images/void_part_right.png',
                    size: size,
                    progress: tRight,
                    pivot: const FractionalOffset(0.72, 0.55),
                    startTranslation: Offset(size * 0.9, size * 0.55),
                    startRotationZ: 0.65, // ~ +37 degrees
                    startRotationY: -0.35, // 3D yaw tilt
                    startScale: 0.55,
                  ),

                // 4. Quantum Core Triangle (`void_part_core.png`)
                // Center of mass: (0.50, 0.42). Bursts out from z-plane with spin.
                if (tCore > 0.0)
                  _buildDynamicPiece(
                    assetPath: 'assets/images/void_part_core.png',
                    size: size,
                    progress: tCore,
                    pivot: const FractionalOffset(0.50, 0.42),
                    startTranslation: Offset.zero,
                    startRotationZ: math.pi * 1.5, // 270 deg spin
                    startRotationY: 0.0,
                    startScale: 0.05,
                  ),

                // 5. Amber-Gold Orbital Ring (`void_part_halo.png`)
                // Center of mass: (0.50, 0.50). Sweeps in from planetary orbit.
                if (tHalo > 0.0)
                  _buildDynamicPiece(
                    assetPath: 'assets/images/void_part_halo.png',
                    size: size,
                    progress: tHalo,
                    pivot: const FractionalOffset(0.50, 0.50),
                    startTranslation: Offset(0, size * 0.25),
                    startRotationZ: -0.45,
                    startRotationY: 0.25,
                    startScale: 2.2, // zooms in from large space
                  ),

                // 6. Top Bar & White Geometric Notch (`void_part_top.png`)
                // Center of mass: (0.50, 0.20). Slam-locks down from above.
                if (tTop > 0.0)
                  _buildDynamicPiece(
                    assetPath: 'assets/images/void_part_top.png',
                    size: size,
                    progress: tTop,
                    pivot: const FractionalOffset(0.50, 0.20),
                    startTranslation: Offset(0, -size * 0.85),
                    startRotationZ: 0.0,
                    startRotationY: 0.0,
                    startScale: 1.3,
                  ),

                // 7. Impact Lock-In Shockwaves & Electrical Energy Pulse
                if (tLock > 0.0 && tLock < 1.0)
                  CustomPaint(
                    size: Size(size * 1.5, size * 1.5),
                    painter: _ExplosiveShockwavePainter(progress: tLock),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  /// Builds a dynamic 3D-perspected piece that converges precisely to (0, 0)
  Widget _buildDynamicPiece({
    required String assetPath,
    required double size,
    required double progress,
    required FractionalOffset pivot,
    required Offset startTranslation,
    required double startRotationZ,
    required double startRotationY,
    required double startScale,
  }) {
    final inv = 1.0 - progress;
    final dx = startTranslation.dx * inv;
    final dy = startTranslation.dy * inv;
    final rotZ = startRotationZ * inv;
    final rotY = startRotationY * inv;
    final scale = startScale + (1.0 - startScale) * progress;

    final matrix = Matrix4.identity()
      ..setEntry(3, 2, 0.0018) // Realistic 3D perspective depth
      ..translate(dx, dy)
      ..rotateY(rotY)
      ..rotateZ(rotZ)
      ..scale(scale, scale);

    return Opacity(
      opacity: progress.clamp(0.0, 1.0),
      child: Transform(
        alignment: pivot,
        transform: matrix,
        child: Image.asset(
          assetPath,
          width: size,
          height: size,
          fit: BoxFit.contain,
          filterQuality: FilterQuality.high,
        ),
      ),
    );
  }

  double _interval(double value, double begin, double end, Curve curve) {
    if (value <= begin) return 0.0;
    if (value >= end) return 1.0;
    final t = (value - begin) / (end - begin);
    return curve.transform(t);
  }
}

/// High-energy multi-tier shockwave flare bursting outwards when pieces slam together
class _ExplosiveShockwavePainter extends CustomPainter {
  final double progress; // 0.0 to 1.0

  _ExplosiveShockwavePainter({required this.progress});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = size.width * 0.65;
    final alpha = (1.0 - progress) * (1.0 - progress); // Rapid quadratic fade

    // 1. Center Flash Flare (Quick 0.0 -> 0.3 burst)
    if (progress < 0.35) {
      final flashAlpha = ((0.35 - progress) / 0.35);
      final flashPaint = Paint()
        ..color = Colors.white.withOpacity(flashAlpha * 0.9)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 18);
      canvas.drawCircle(center, 35 * (1.0 + progress * 2), flashPaint);
    }

    // 2. Primary Cyber-Orange Sonic Shockwave Ring
    final ring1Radius = progress * maxRadius;
    final ring1Paint = Paint()
      ..color = AppColors.accent.withOpacity(alpha * 0.95)
      ..style = PaintingStyle.stroke
      ..strokeWidth = (1.0 - progress) * 10 + 1.5;
    canvas.drawCircle(center, ring1Radius, ring1Paint);

    // 3. Electric Gold Orbital Ripple
    final ring2Radius = progress * maxRadius * 0.82;
    final ring2Paint = Paint()
      ..color = const Color(0xFFFFD54F).withOpacity(alpha * 0.9)
      ..style = PaintingStyle.stroke
      ..strokeWidth = (1.0 - progress) * 6 + 1;
    canvas.drawCircle(center, ring2Radius, ring2Paint);

    // 4. Cyan Quantum Wave Ripple
    final ring3Radius = progress * maxRadius * 0.58;
    final ring3Paint = Paint()
      ..color = AppColors.visionCyan.withOpacity(alpha * 0.7)
      ..style = PaintingStyle.stroke
      ..strokeWidth = (1.0 - progress) * 4 + 1;
    canvas.drawCircle(center, ring3Radius, ring3Paint);
  }

  @override
  bool shouldRepaint(covariant _ExplosiveShockwavePainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}
