import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/constants.dart';
import '../core/hud_painters.dart';
import '../core/theme.dart';
import '../state/studio_state.dart';

class HardwareDiagnosticsView extends StatelessWidget {
  const HardwareDiagnosticsView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<StudioState>();
    final m = state.metrics;

    return LayoutBuilder(
      builder: (context, constraints) {
        final isCompact = constraints.maxWidth < 960;
        final isMobile = constraints.maxWidth < 600;
        final padding = isMobile ? 12.0 : 20.0;

        final thermalCard = HudPanel(
          technicalTag: 'THERMAL_ENVELOPE',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('THERMAL STATUS & SENSORS', style: VoidTheme.hudLabel(fontSize: 10)),
              const SizedBox(height: 12),
              _buildGaugeTile('CPU CORE DIE', '58°C', 0.58, VoidTokens.statusGreen),
              _buildGaugeTile('GPU HOTSPOT', '66°C', 0.66, VoidTokens.statusYellow),
              _buildGaugeTile('NVMe TEMPERATURE', '42°C', 0.42, VoidTokens.statusCyan),
              _buildGaugeTile('CHASSIS SENSOR 01', '36°C', 0.36, VoidTokens.statusGreen),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: VoidTokens.voidGraphite,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text('FAN CONTROLLER: DYNAMIC SMART CURVE (2,400 RPM)',
                    style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.textMuted)),
              ),
            ],
          ),
        );

        final computeCard = HudPanel(
          technicalTag: 'COMPUTE_SILICON',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('COMPUTE LOAD & VRAM', style: VoidTheme.hudLabel(fontSize: 10)),
              const SizedBox(height: 12),
              _buildGaugeTile('CPU FREQUENCY (12 THREADS)', '4.2 GHz', 0.70, VoidTokens.voidOrange),
              _buildGaugeTile('RTX GPU TENSOR CORES', '${m.gpuPercent.toStringAsFixed(0)}%', m.gpuPercent / 100, VoidTokens.statusPurple),
              _buildGaugeTile('VRAM DYNAMIC CACHE', '${m.vramUsedGb.toStringAsFixed(1)} GB', m.vramUsedGb / m.vramTotalGb, VoidTokens.statusCyan),
              _buildGaugeTile('HOST SYSTEM RAM', '${m.ramUsedGb.toStringAsFixed(1)} GB', m.ramUsedGb / m.ramTotalGb, VoidTokens.statusGreen),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: VoidTokens.voidGraphite,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text('POWER DRAW: 68W / 95W TGP (OPTIMAL RANGE)',
                    style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.textMuted)),
              ),
            ],
          ),
        );

        final busCard = HudPanel(
          technicalTag: 'BUS_IO_CHANNELS',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('I/O CHANNELS & PERIPHERALS', style: VoidTheme.hudLabel(fontSize: 10)),
              const SizedBox(height: 12),
              _buildGaugeTile('NVMe READ BANDWIDTH', '3,450 MB/s', 0.82, VoidTokens.statusCyan),
              _buildGaugeTile('PCIe GEN 4 x16 LINK', '16.0 GT/s', 0.95, VoidTokens.voidOrangeBright),
              _buildGaugeTile('LOCAL SOCKET IPC', '0.04 ms', 0.98, VoidTokens.statusGreen),
              _buildGaugeTile('AUDIO WASAPI BUFFER', '30 ms', 0.90, VoidTokens.statusPurple),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: VoidTokens.voidGraphite,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text('BATTERY / AC: AC DIRECT HIGH PERFORMANCE',
                    style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.statusGreen)),
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
                technicalTag: 'EXOSKELETON_HARDWARE_LAYER',
                child: Row(
                  children: [
                    const Icon(Icons.precision_manufacturing_outlined, size: 16, color: VoidTokens.voidOrange),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('EXOSKELETON CHASSIS DIAGNOSTICS',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: VoidTheme.hudLabel(fontSize: isMobile ? 10.5 : 12, letterSpacing: isMobile ? 1.0 : 1.6)),
                          if (!isMobile)
                            Text('POWER BUS / THERMAL ENVELOPE / COMPUTE SILICON INTEGRITY',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: VoidTheme.mono(fontSize: 9, color: VoidTokens.textMuted)),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: VoidTokens.statusGreen.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(3),
                        border: Border.all(color: VoidTokens.statusGreen.withOpacity(0.3)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.shield_outlined, size: 12, color: VoidTokens.statusGreen),
                          const SizedBox(width: 6),
                          Text(isMobile ? '99.8%' : 'SYSTEM INTEGRITY: 99.8%',
                              style: VoidTheme.mono(fontSize: 9.5, color: VoidTokens.statusGreen)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 14),

              // Diagnostic Modules Grid
              Expanded(
                child: isCompact
                    ? SingleChildScrollView(
                        physics: const BouncingScrollPhysics(),
                        child: Column(
                          children: [
                            thermalCard,
                            const SizedBox(height: 12),
                            computeCard,
                            const SizedBox(height: 12),
                            busCard,
                          ],
                        ),
                      )
                    : Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Expanded(
                            child: SingleChildScrollView(
                              physics: const BouncingScrollPhysics(),
                              child: thermalCard,
                            ),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: SingleChildScrollView(
                              physics: const BouncingScrollPhysics(),
                              child: computeCard,
                            ),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: SingleChildScrollView(
                              physics: const BouncingScrollPhysics(),
                              child: busCard,
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

  Widget _buildGaugeTile(String title, String val, double progress, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: Column(
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
                  style: VoidTheme.mono(fontSize: 9, color: VoidTokens.textMuted),
                ),
              ),
              const SizedBox(width: 8),
              Text(val, style: VoidTheme.mono(fontSize: 10, fontWeight: FontWeight.w700, color: color)),
            ],
          ),
          const SizedBox(height: 4),
          LinearProgressIndicator(
            value: progress.clamp(0.0, 1.0),
            backgroundColor: VoidTokens.voidSurface,
            valueColor: AlwaysStoppedAnimation(color),
            minHeight: 4,
          ),
        ],
      ),
    );
  }
}
