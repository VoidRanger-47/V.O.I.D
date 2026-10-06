import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/constants/app_colors.dart';
import '../widgets/animated_void_assembly_logo.dart';
import 'home_screen.dart';

/// Pure cinematic launch screen.
///
/// Starts in pristine dark void where the FIRST and ONLY thing the user sees
/// is the dramatic assembly of the official V.O.I.D. logo.
/// No distracting UI elements, grids, or progress bars are shown before or during the assembly.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  bool _hasNavigated = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2800),
    );

    _controller.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        _navigateToHome();
      }
    });

    // Immediately launch the assembly animation as the first thing
    _controller.forward();
  }

  void _navigateToHome() {
    if (_hasNavigated || !mounted) return;
    _hasNavigated = true;

    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        transitionDuration: const Duration(milliseconds: 650),
        pageBuilder: (context, animation, secondaryAnimation) =>
            const HomeScreen(),
        transitionsBuilder: (context, animation, secondaryAnimation, child) {
          final fadeCurve = CurvedAnimation(
            parent: animation,
            curve: Curves.easeInOutQuad,
          );
          final scaleCurve = Tween<double>(begin: 0.95, end: 1.0).animate(
            CurvedAnimation(
              parent: animation,
              curve: Curves.easeOutCubic,
            ),
          );

          return FadeTransition(
            opacity: fadeCurve,
            child: ScaleTransition(
              scale: scaleCurve,
              child: child,
            ),
          );
        },
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final logoSize = math.min(size.width * 0.70, 260.0);

    return Scaffold(
      backgroundColor: AppColors.bgApp,
      body: Stack(
        alignment: Alignment.center,
        children: [
          // 1. Ambient Background Aura (Only fades in as pieces converge, 0.40 -> 0.80)
          AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              final t = _controller.value;
              final auraOpacity = (t >= 0.40)
                  ? ((t - 0.40) / 0.40).clamp(0.0, 1.0) * 0.18
                  : 0.0;

              if (auraOpacity <= 0.001) return const SizedBox.shrink();

              return Positioned.fill(
                child: Container(
                  decoration: BoxDecoration(
                    gradient: RadialGradient(
                      center: Alignment.center,
                      radius: 0.85,
                      colors: [
                        AppColors.accent.withOpacity(auraOpacity),
                        AppColors.surfaceContainer.withOpacity(auraOpacity * 0.6),
                        AppColors.bgApp,
                      ],
                      stops: const [0.0, 0.55, 1.0],
                    ),
                  ),
                ),
              );
            },
          ),

          // 2. The Hero: Multi-Part Assembling Logo
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                AnimatedVoidAssemblyLogo(
                  animation: _controller,
                  size: logoSize,
                  showBackgroundSquircle: true,
                  enableGlow: true,
                ),

                const SizedBox(height: 32),

                // Typographic Brand Reveal (Only reveals after assembly lock-in, t >= 0.80)
                AnimatedBuilder(
                  animation: _controller,
                  builder: (context, child) {
                    final t = _controller.value;
                    final textOpacity = (t >= 0.80)
                        ? ((t - 0.80) / 0.20).clamp(0.0, 1.0)
                        : 0.0;

                    if (textOpacity <= 0.001) {
                      return const SizedBox(height: 52); // reserve space to avoid jump
                    }

                    final letterSpacing = 8.0 + (1.0 - textOpacity) * 8.0;

                    return Opacity(
                      opacity: textOpacity,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            'V . O . I . D .',
                            style: GoogleFonts.orbitron(
                              color: AppColors.textPrimary,
                              fontSize: 26,
                              fontWeight: FontWeight.w800,
                              letterSpacing: letterSpacing,
                              shadows: [
                                Shadow(
                                  color: AppColors.accent.withOpacity(0.65),
                                  blurRadius: 20,
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'NEURAL PERCEPTION SYSTEM',
                            style: GoogleFonts.shareTechMono(
                              color: AppColors.accentLight,
                              fontSize: 11,
                              letterSpacing: 3.5,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ],
            ),
          ),

          // 3. Subtle Skip Action (Only available after initial assembly phase, t >= 0.60)
          SafeArea(
            child: Align(
              alignment: Alignment.topRight,
              child: AnimatedBuilder(
                animation: _controller,
                builder: (context, child) {
                  final t = _controller.value;
                  final skipOpacity = (t >= 0.60)
                      ? ((t - 0.60) / 0.25).clamp(0.0, 1.0)
                      : 0.0;

                  if (skipOpacity <= 0.001) return const SizedBox.shrink();

                  return Opacity(
                    opacity: skipOpacity,
                    child: Padding(
                      padding: const EdgeInsets.only(top: 12, right: 16),
                      child: TextButton(
                        onPressed: _navigateToHome,
                        style: TextButton.styleFrom(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 5,
                          ),
                          backgroundColor: Colors.white.withOpacity(0.06),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(6),
                            side: BorderSide(
                              color: Colors.white.withOpacity(0.12),
                              width: 0.8,
                            ),
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              'SKIP',
                              style: GoogleFonts.shareTechMono(
                                color: AppColors.textMuted,
                                fontSize: 10,
                                letterSpacing: 1.5,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(width: 3),
                            const Icon(
                              Icons.chevron_right,
                              size: 13,
                              color: AppColors.textMuted,
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}
