import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/constants.dart';
import '../core/hud_painters.dart';
import '../core/theme.dart';
import '../state/studio_state.dart';

class NeuralMonitorView extends StatelessWidget {
  const NeuralMonitorView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<StudioState>();
    final m = state.metrics;

    return LayoutBuilder(
      builder: (context, constraints) {
        final isCompact = constraints.maxWidth < 900;
        final isMobile = constraints.maxWidth < 600;
        final padding = isMobile ? 12.0 : 20.0;

        // Radial Gauges widget
        final radialGauges = Row(
          children: [
            Expanded(
              child: HudPanel(
                technicalTag: 'GPU_CORE_LOAD',
                child: Column(
                  children: [
                    SizedBox(
                      width: isMobile ? 84 : 110,
                      height: isMobile ? 84 : 110,
                      child: CustomPaint(
                        painter: HudRadialGaugePainter(
                          value: m.gpuPercent / 100.0,
                          primaryColor: VoidTokens.voidOrange,
                        ),
                        child: Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                '${m.gpuPercent.toStringAsFixed(0)}%',
                                style: VoidTheme.mono(
                                  fontSize: isMobile ? 15 : 18,
                                  fontWeight: FontWeight.w700,
                                  color: VoidTokens.textHigh,
                                ),
                              ),
                              Text('GPU COMPUTE',
                                  style: VoidTheme.mono(fontSize: isMobile ? 7 : 8, color: VoidTokens.textMuted)),
                            ],
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text('RTX 3050 GPU',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: VoidTheme.mono(fontSize: 9, color: VoidTokens.voidOrangeBright)),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: HudPanel(
                technicalTag: 'VRAM_SATURATION',
                child: Column(
                  children: [
                    SizedBox(
                      width: isMobile ? 84 : 110,
                      height: isMobile ? 84 : 110,
                      child: CustomPaint(
                        painter: HudRadialGaugePainter(
                          value: (m.vramUsedGb / m.vramTotalGb).clamp(0.0, 1.0),
                          primaryColor: VoidTokens.statusCyan,
                        ),
                        child: Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                '${m.vramUsedGb.toStringAsFixed(1)}G',
                                style: VoidTheme.mono(
                                  fontSize: isMobile ? 15 : 18,
                                  fontWeight: FontWeight.w700,
                                  color: VoidTokens.textHigh,
                                ),
                              ),
                              Text('VRAM USAGE',
                                  style: VoidTheme.mono(fontSize: isMobile ? 7 : 8, color: VoidTokens.textMuted)),
                            ],
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text('${m.vramUsedGb.toStringAsFixed(1)} / ${m.vramTotalGb.toStringAsFixed(0)} GB',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: VoidTheme.mono(fontSize: 9, color: VoidTokens.statusCyan)),
                  ],
                ),
              ),
            ),
          ],
        );

        // Token velocity & Latency card
        final velocityCard = HudPanel(
          technicalTag: 'TOKEN_LATENCY_METRICS',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('THROUGHPUT & INFERENCE VELOCITY', style: VoidTheme.hudLabel(fontSize: 10)),
              const SizedBox(height: 14),
              _buildProgressGauge(
                'TOKEN STREAM VELOCITY',
                '${m.tokensPerSec.toStringAsFixed(1)} tok/s',
                m.tokensPerSec / 80.0,
                VoidTokens.voidOrangeBright,
              ),
              const SizedBox(height: 12),
              _buildProgressGauge(
                'FIRST-TOKEN LATENCY',
                '${m.latencyMs.toStringAsFixed(0)} ms',
                1.0 - (m.latencyMs / 300.0).clamp(0.0, 1.0),
                VoidTokens.statusGreen,
              ),
              const SizedBox(height: 12),
              _buildProgressGauge(
                'KV CACHE RETENTION',
                '24.5% (2048/8192)',
                0.245,
                VoidTokens.statusPurple,
              ),
            ],
          ),
        );

        // Architecture & specs card
        final specCard = HudPanel(
          technicalTag: 'MODEL_SPECIFICATION',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('ACTIVE NEURAL SPECIFICATIONS', style: VoidTheme.hudLabel(fontSize: 10)),
              const SizedBox(height: 10),
              _buildSpecItem('MODEL ARCHITECTURE', 'GPT-o200k Custom Transformer'),
              _buildSpecItem('PARAMETER COUNT', '183,123,200 (183M)'),
              _buildSpecItem('CHECKPOINT STEP', 'Step 5002 (Resumed)'),
              _buildSpecItem('VOCABULARY SIZE', '200,025 (o200k_base)'),
              _buildSpecItem('EMBEDDING DIMENSION', '768'),
              _buildSpecItem('ATTENTION HEADS', '12'),
              _buildSpecItem('TRANSFORMER LAYERS', '12'),
              _buildSpecItem('PRECISION / DTYPE', 'FP16 CUDA Stream'),
              _buildSpecItem('VRAM DYNAMIC MANAGER', 'ON-DEMAND ACTIVE'),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: VoidTokens.voidGraphite,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: VoidTokens.voidSurfaceBorder),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.bolt, size: 16, color: VoidTokens.statusGreen),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Cognitive Engine running 100% offline & locally on RTX GPU.',
                        style: VoidTheme.mono(fontSize: 9.5, color: VoidTokens.textHigh),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );

        return Padding(
          padding: EdgeInsets.all(padding),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header Bar
              HudPanel(
                technicalTag: 'SYS.NEURAL_MONITOR',
                child: Row(
                  children: [
                    const Icon(Icons.memory, size: 16, color: VoidTokens.voidOrange),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'NEURAL COGNITION & MODEL TELEMETRY',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: VoidTheme.hudLabel(fontSize: isMobile ? 10.5 : 12, letterSpacing: isMobile ? 1.0 : 1.5),
                          ),
                          if (!isMobile)
                            Text(
                              'TRANSFORMER ATTENTION / KV CACHE DYNAMICS / VRAM BUFFER',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: VoidTheme.mono(fontSize: 9, color: VoidTokens.textMuted),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: VoidTokens.voidSurface,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: VoidTokens.voidOrangeDim),
                      ),
                      child: Text(
                        isMobile ? 'o200k' : 'o200k_base (200K)',
                        style: VoidTheme.mono(fontSize: 9.5, color: VoidTokens.voidOrangeBright),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 14),

              // Main Telemetry Gauges Grid
              Expanded(
                child: isCompact
                    ? SingleChildScrollView(
                        physics: const BouncingScrollPhysics(),
                        child: Column(
                          children: [
                            radialGauges,
                            const SizedBox(height: 12),
                            velocityCard,
                            const SizedBox(height: 12),
                            specCard,
                          ],
                        ),
                      )
                    : Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          // Left Column: Radial Gauges & Live Velocity
                          Expanded(
                            flex: 3,
                            child: SingleChildScrollView(
                              physics: const BouncingScrollPhysics(),
                              child: Column(
                                children: [
                                  radialGauges,
                                  const SizedBox(height: 14),
                                  velocityCard,
                                ],
                              ),
                            ),
                          ),

                          const SizedBox(width: 16),

                          // Right Column: Architecture & Parameters Specs
                          Expanded(
                            flex: 2,
                            child: SingleChildScrollView(
                              physics: const BouncingScrollPhysics(),
                              child: specCard,
                            ),
                          ),
                        ],
                      ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildProgressGauge(String title, String value, double progress, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Text(
                title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: VoidTheme.mono(fontSize: 9.5, color: VoidTokens.textMuted),
              ),
            ),
            const SizedBox(width: 8),
            Text(value, style: VoidTheme.mono(fontSize: 10.5, fontWeight: FontWeight.w700, color: color)),
          ],
        ),
        const SizedBox(height: 6),
        LinearProgressIndicator(
          value: progress.clamp(0.0, 1.0),
          backgroundColor: VoidTokens.voidSurface,
          valueColor: AlwaysStoppedAnimation(color),
          minHeight: 5,
        ),
      ],
    );
  }

  Widget _buildSpecItem(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.5),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.textMuted)),
          const SizedBox(height: 1),
          Text(value, style: VoidTheme.mono(fontSize: 11, color: VoidTokens.textHigh, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
