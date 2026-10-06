import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/providers/system_provider.dart';
import '../widgets/telemetry_gauge.dart';
import '../widgets/cyber_card.dart';

class TelemetryScreen extends StatefulWidget {
  const TelemetryScreen({super.key});

  @override
  State<TelemetryScreen> createState() => _TelemetryScreenState();
}

class _TelemetryScreenState extends State<TelemetryScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<SystemProvider>().startTelemetryPolling();
    });
  }

  @override
  void deactivate() {
    context.read<SystemProvider>().stopTelemetryPolling();
    super.deactivate();
  }

  @override
  Widget build(BuildContext context) {
    final system = context.watch<SystemProvider>();
    final telemetry = system.telemetry;

    return Scaffold(
      backgroundColor: AppColors.bgApp,
      appBar: AppBar(
        backgroundColor: AppColors.bgApp,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        title: Row(
          children: [
            const Icon(Icons.monitor_heart, color: AppColors.accent, size: 18),
            const SizedBox(width: 8),
            Text(
              'HARDWARE TELEMETRY',
              style: GoogleFonts.inter(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.5,
                color: AppColors.textPrimary,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, size: 18, color: AppColors.textSecondary),
            tooltip: 'Refresh Telemetry',
            onPressed: () => system.fetchStats(),
          ),
          const SizedBox(width: 6),
        ],
        bottom: const PreferredSize(
          preferredSize: Size.fromHeight(1),
          child: Divider(color: AppColors.borderHairline, height: 1),
        ),
      ),
      body: RefreshIndicator(
        color: AppColors.accent,
        backgroundColor: AppColors.surfaceContainer,
        onRefresh: () => system.fetchStats(),
        child: ListView(
          padding: const EdgeInsets.all(14),
          children: [
            // Live Status Banner
            Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: AppColors.surfaceContainer,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.borderHairline, width: 1.0),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 7,
                        height: 7,
                        decoration: const BoxDecoration(
                          color: AppColors.accent,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Live Telemetry Active',
                        style: GoogleFonts.inter(
                          color: AppColors.textPrimary,
                          fontSize: 12.5,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                  Text(
                    'Auto-update 2s',
                    style: GoogleFonts.jetBrainsMono(
                      color: AppColors.textSecondary,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),

            // 1. Host OS Card
            CyberCard(
              borderRadius: 8,
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: AppColors.accentSubtle,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppColors.accent.withOpacity(0.3)),
                    ),
                    child: const Icon(Icons.computer, color: AppColors.accent, size: 20),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'HOST SYSTEM PLATFORM',
                          style: GoogleFonts.jetBrainsMono(
                            color: AppColors.textSecondary,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1.0,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          telemetry.osName,
                          style: GoogleFonts.inter(
                            color: AppColors.textPrimary,
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Text(
                    telemetry.currentTime.split(' ').first,
                    style: GoogleFonts.jetBrainsMono(
                      color: AppColors.textSecondary,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            // 2. CPU Load Gauge
            TelemetryGauge(
              title: 'CPU Processor Load',
              value: telemetry.cpuPercent,
              valueText: '${telemetry.cpuPercent.toStringAsFixed(1)}%',
              subtitle: 'Host processor multi-core utilization',
              icon: Icons.memory,
              color: telemetry.cpuPercent > 80 ? AppColors.statusRed : AppColors.accent,
            ),
            const SizedBox(height: 12),

            // 3. RAM Memory Gauge
            TelemetryGauge(
              title: 'System RAM Utilization',
              value: telemetry.ramPercent,
              valueText: '${telemetry.ramPercent.toStringAsFixed(1)}%',
              subtitle: '${telemetry.ramUsedMb.toStringAsFixed(0)} MB used of ${telemetry.ramTotalMb.toStringAsFixed(0)} MB',
              icon: Icons.storage,
              color: telemetry.ramPercent > 85 ? AppColors.accentLight : AppColors.accent,
            ),
            const SizedBox(height: 12),

            // 4. GPU & VRAM Gauge
            CyberCard(
              borderRadius: 8,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.videogame_asset_outlined, size: 14, color: AppColors.textSecondary),
                          const SizedBox(width: 6),
                          Text(
                            'GRAPHICS ACCELERATION (GPU)',
                            style: GoogleFonts.jetBrainsMono(
                              color: AppColors.textSecondary,
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1.0,
                            ),
                          ),
                        ],
                      ),
                      Text(
                        telemetry.gpuName,
                        style: GoogleFonts.jetBrainsMono(
                          color: AppColors.accent,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  if (telemetry.gpuVramTotalMb > 0) ...[
                    TelemetryGauge(
                      title: 'GPU Dedicated VRAM',
                      value: (telemetry.gpuVramUsedMb / telemetry.gpuVramTotalMb) * 100,
                      valueText: '${telemetry.gpuVramUsedMb.toStringAsFixed(0)} / ${telemetry.gpuVramTotalMb.toStringAsFixed(0)} MB',
                      color: AppColors.accent,
                    ),
                  ] else ...[
                    Text(
                      'Running in CPU Inference Mode',
                      style: GoogleFonts.inter(
                        color: AppColors.textSecondary,
                        fontSize: 12,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
