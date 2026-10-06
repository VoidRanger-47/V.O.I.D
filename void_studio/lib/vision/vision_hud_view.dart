import 'package:flutter/material.dart';
import '../core/constants.dart';
import '../core/hud_painters.dart';
import '../core/theme.dart';

class VisionHudView extends StatefulWidget {
  const VisionHudView({super.key});

  @override
  State<VisionHudView> createState() => _VisionHudViewState();
}

class _VisionHudViewState extends State<VisionHudView> {
  bool _cameraActive = true;

  final List<_DetectedTarget> _detectedObjects = [
    _DetectedTarget(
      label: 'NEURAL USER (PRIMARY)',
      confidence: 0.984,
      trackId: 'TRK-01',
      rect: const Rect.fromLTWH(0.28, 0.20, 0.32, 0.50),
      color: VoidTokens.statusCyan,
    ),
    _DetectedTarget(
      label: 'WORKSPACE TERMINAL',
      confidence: 0.926,
      trackId: 'TRK-02',
      rect: const Rect.fromLTWH(0.08, 0.55, 0.26, 0.35),
      color: VoidTokens.voidOrange,
    ),
    _DetectedTarget(
      label: 'HARDWARE SENSOR ARRAY',
      confidence: 0.887,
      trackId: 'TRK-03',
      rect: const Rect.fromLTWH(0.66, 0.48, 0.25, 0.38),
      color: VoidTokens.statusGreen,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isMobile = constraints.maxWidth < 600;
        final padding = isMobile ? 12.0 : 20.0;

        return Padding(
          padding: EdgeInsets.all(padding),
          child: Column(
            children: [
              // Vision HUD Header
              HudPanel(
                technicalTag: 'SYS.OPTICAL_PERCEPTION // HUD_v2',
                child: Row(
                  children: [
                    Icon(
                      Icons.videocam_outlined,
                      size: 16,
                      color: _cameraActive ? VoidTokens.statusCyan : VoidTokens.textMuted,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'OPTICAL PERCEPTION & TARGET HUD',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: VoidTheme.hudLabel(
                              fontSize: isMobile ? 10 : 11,
                              letterSpacing: isMobile ? 1.0 : 1.5,
                              color: VoidTokens.statusCyan,
                            ),
                          ),
                          if (!isMobile)
                            Text(
                              'SPATIAL SCENE RECONSTRUCTION // 1080p @ 60FPS WASAPI LINK',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: VoidTheme.mono(fontSize: 9, color: VoidTokens.textMuted),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    InkWell(
                      onTap: () => setState(() => _cameraActive = !_cameraActive),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: _cameraActive ? VoidTokens.statusCyan.withOpacity(0.15) : VoidTokens.voidGraphite,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(
                            color: _cameraActive ? VoidTokens.statusCyan : VoidTokens.voidSurfaceBorder,
                          ),
                        ),
                        child: Text(
                          _cameraActive ? 'FEED: ON' : 'FEED: OFF',
                          style: VoidTheme.mono(
                            fontSize: 9.5,
                            fontWeight: FontWeight.w700,
                            color: _cameraActive ? VoidTokens.statusCyan : VoidTokens.textMuted,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),

          const SizedBox(height: 16),

          // Main Feed Area with Tactical HUD Overlays
          Expanded(
            child: HudPanel(
              padding: EdgeInsets.zero,
              technicalTag: 'LIVE_FEED_01',
              backgroundColor: VoidTokens.voidBlack,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  // Camera Simulation Surface
                  Container(
                    decoration: const BoxDecoration(
                      gradient: RadialGradient(
                        colors: [Color(0xFF0F1722), Color(0xFF06090D)],
                        radius: 0.9,
                      ),
                    ),
                    child: CustomPaint(
                      painter: HudGridPainter(spacing: 50, gridColor: const Color(0x0600E5FF)),
                    ),
                  ),

                  // Center Optical Reticle
                  Center(
                    child: Container(
                      width: 120,
                      height: 120,
                      decoration: BoxDecoration(
                        border: Border.all(color: VoidTokens.statusCyan.withOpacity(0.2), width: 1),
                        shape: BoxShape.circle,
                      ),
                      child: Center(
                        child: Container(
                          width: 4,
                          height: 4,
                          decoration: const BoxDecoration(
                            color: VoidTokens.statusCyan,
                            shape: BoxShape.circle,
                          ),
                        ),
                      ),
                    ),
                  ),

                  // Detected Target Bounding Boxes & Dynamic Brackets
                  if (_cameraActive)
                    LayoutBuilder(
                      builder: (context, constraints) {
                        return Stack(
                          children: _detectedObjects.map((target) {
                            final rect = Rect.fromLTWH(
                              target.rect.left * constraints.maxWidth,
                              target.rect.top * constraints.maxHeight,
                              target.rect.width * constraints.maxWidth,
                              target.rect.height * constraints.maxHeight,
                            );

                            return Positioned.fromRect(
                              rect: rect,
                              child: _buildTacticalBoundingBox(target),
                            );
                          }).toList(),
                        );
                      },
                    ),

                  // Bottom Left Optical Telemetry
                  Positioned(
                    bottom: 16,
                    left: 16,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: VoidTokens.voidObsidian.withOpacity(0.85),
                        border: Border.all(color: VoidTokens.statusCyan.withOpacity(0.4)),
                        borderRadius: BorderRadius.circular(2),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('OPTICAL TELEMETRY', style: VoidTheme.hudLabel(fontSize: 8, color: VoidTokens.statusCyan)),
                          const SizedBox(height: 2),
                          Text('RESOLUTION: 1920x1080 | FOV: 84°', style: VoidTheme.mono(fontSize: 9.5, color: VoidTokens.textHigh)),
                          Text('TARGETS ACQUIRED: 3 OBJECTS', style: VoidTheme.mono(fontSize: 9.5, color: VoidTokens.statusGreen)),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
      },
    );
  }

  Widget _buildTacticalBoundingBox(_DetectedTarget target) {
    return Stack(
      children: [
        // Bounding Border with glowing corners
        Container(
          decoration: BoxDecoration(
            border: Border.all(color: target.color.withOpacity(0.6), width: 1.0),
          ),
        ),

        // Corner Accent Ticks
        Positioned(
          top: 0,
          left: 0,
          child: Container(width: 8, height: 2, color: target.color),
        ),
        Positioned(
          top: 0,
          left: 0,
          child: Container(width: 2, height: 8, color: target.color),
        ),

        // Tactical Label Pill
        Positioned(
          top: 2,
          left: 2,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: VoidTokens.voidObsidian.withOpacity(0.9),
              border: Border.all(color: target.color),
              borderRadius: BorderRadius.circular(2),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  target.label,
                  style: VoidTheme.hudLabel(fontSize: 8.5, color: VoidTokens.textHigh),
                ),
                const SizedBox(width: 6),
                Text(
                  '${(target.confidence * 100).toStringAsFixed(1)}%',
                  style: VoidTheme.mono(fontSize: 8.5, color: target.color, fontWeight: FontWeight.w700),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _DetectedTarget {
  final String label;
  final double confidence;
  final String trackId;
  final Rect rect;
  final Color color;

  _DetectedTarget({
    required this.label,
    required this.confidence,
    required this.trackId,
    required this.rect,
    required this.color,
  });
}
