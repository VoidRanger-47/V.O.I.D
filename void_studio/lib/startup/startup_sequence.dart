import 'dart:async';
import 'package:flutter/material.dart';
import '../core/constants.dart';
import '../core/hud_painters.dart';
import '../core/theme.dart';

class StartupSequence extends StatefulWidget {
  final VoidCallback onComplete;

  const StartupSequence({super.key, required this.onComplete});

  @override
  State<StartupSequence> createState() => _StartupSequenceState();
}

class _StartupSequenceState extends State<StartupSequence> with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  final List<String> _bootLog = [];
  Timer? _stepTimer;
  int _step = 0;

  final List<String> _steps = [
    'INITIALIZING V.O.I.D. STUDIO COCKPIT...',
    'EXOSKELETON HUD WIREFRAME ...... STABILIZED',
    'CORE COMPUTATIONAL REACTOR ..... ONLINE',
    'MEMORY OBSERVATORY ............. ONLINE (VECTOR INDEX)',
    'NEURAL MODEL MONITOR ........... ONLINE (o200k_base)',
    'SPECIALIZED AGENT MESH ......... 6 AGENTS READY',
    'OPTICAL VISION SUBSYSTEM ....... STANDBY',
    'NVIDIA TENSOR SILICON .......... ENGAGED (RTX 3050)',
    'SYSTEM READY // OPERATING ENVIRONMENT UNCLOAKED',
  ];

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat();

    _runSequence();
  }

  void _runSequence() {
    _stepTimer = Timer.periodic(const Duration(milliseconds: 350), (timer) {
      if (_step < _steps.length) {
        setState(() {
          _bootLog.add(_steps[_step]);
          _step++;
        });
      } else {
        timer.cancel();
        Future.delayed(const Duration(milliseconds: 600), () {
          if (mounted) widget.onComplete();
        });
      }
    });
  }

  @override
  void dispose() {
    _stepTimer?.cancel();
    _animController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: VoidTokens.voidBlack,
      body: LayoutBuilder(
        builder: (context, constraints) {
          final isMobile = constraints.maxWidth < 600;

          return Stack(
            children: [
              // Background Grid
              Positioned.fill(
                child: CustomPaint(
                  painter: HudGridPainter(spacing: 36),
                ),
              ),

              // Center Boot Visualization
              Center(
                child: SingleChildScrollView(
                  physics: const BouncingScrollPhysics(),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // Animated Startup Core Ring
                      SizedBox(
                        width: isMobile ? 110 : 140,
                        height: isMobile ? 110 : 140,
                        child: AnimatedBuilder(
                          animation: _animController,
                          builder: (context, child) {
                            return CustomPaint(
                              painter: HudRadialGaugePainter(
                                value: (_step / _steps.length).clamp(0.1, 1.0),
                                primaryColor: VoidTokens.voidOrange,
                                thickness: 4.0,
                              ),
                              child: Center(
                                child: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Text(
                                      'V.O.I.D.',
                                      style: VoidTheme.hudLabel(
                                        fontSize: isMobile ? 14 : 16,
                                        fontWeight: FontWeight.w900,
                                        letterSpacing: 3.0,
                                      ),
                                    ),
                                    Text(
                                      '${((_step / _steps.length) * 100).toInt()}%',
                                      style: VoidTheme.mono(
                                        fontSize: 11,
                                        color: VoidTokens.textHigh,
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                      ),

                      const SizedBox(height: 24),

                      // Sequential Telemetry Terminal Box
                      ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 440, maxHeight: 200),
                        child: HudPanel(
                          technicalTag: 'SYS.BOOTLOADER // COCKPIT_v4',
                          backgroundColor: VoidTokens.voidObsidian,
                          child: ListView.builder(
                            itemCount: _bootLog.length,
                            itemBuilder: (context, index) {
                              return Padding(
                                padding: const EdgeInsets.symmetric(vertical: 2.0),
                                child: Text(
                                  _bootLog[index],
                                  style: VoidTheme.mono(
                                    fontSize: 10.0,
                                    color: index == _bootLog.length - 1
                                        ? VoidTokens.voidOrangeBright
                                        : VoidTokens.textMedium,
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              // Skip Button Top Right
              Positioned(
                top: isMobile ? 12 : 24,
                right: isMobile ? 12 : 24,
                child: TextButton(
                  onPressed: widget.onComplete,
                  style: TextButton.styleFrom(
                    backgroundColor: VoidTokens.voidGraphite,
                    padding: EdgeInsets.symmetric(horizontal: isMobile ? 10 : 16, vertical: isMobile ? 6 : 8),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(4),
                      side: const BorderSide(color: VoidTokens.voidSurfaceBorder),
                    ),
                  ),
                  child: Text(
                    isMobile ? 'SKIP [ESC]' : 'SKIP INITIALIZATION [ESC]',
                    style: VoidTheme.mono(fontSize: isMobile ? 9 : 10, color: VoidTokens.textHigh, letterSpacing: 1.0),
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
