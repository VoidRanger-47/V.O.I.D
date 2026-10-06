import 'package:flutter/material.dart';
import '../core/constants.dart';
import '../core/hud_painters.dart';
import '../core/theme.dart';
import '../services/telemetry_service.dart';

class TelemetryStreamView extends StatefulWidget {
  final double? width;
  const TelemetryStreamView({super.key, this.width});

  @override
  State<TelemetryStreamView> createState() => _TelemetryStreamViewState();
}

class _TelemetryStreamViewState extends State<TelemetryStreamView> {
  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: widget.width,
      decoration: const BoxDecoration(
        color: VoidTokens.voidBlack,
        border: Border(
          left: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 1.0),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: const BoxDecoration(
              color: VoidTokens.voidObsidian,
              border: Border(
                bottom: BorderSide(color: VoidTokens.voidSurfaceBorder, width: 1.0),
              ),
            ),
            child: Row(
              children: [
                const Icon(Icons.stream, size: 14, color: VoidTokens.voidOrange),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'V.O.I.D. TELEMETRY',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: VoidTheme.hudLabel(fontSize: 10, letterSpacing: 1.2),
                  ),
                ),
                const SizedBox(width: 6),
                Container(
                  width: 6,
                  height: 6,
                  decoration: const BoxDecoration(
                    color: VoidTokens.statusGreen,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  'LIVE',
                  style: VoidTheme.mono(fontSize: 9, color: VoidTokens.statusGreen),
                ),
              ],
            ),
          ),

          // Stream Content
          Expanded(
            child: StreamBuilder<TelemetryEvent>(
              stream: TelemetryService.instance.stream,
              builder: (context, snapshot) {
                final events = TelemetryService.instance.events.reversed.toList();

                if (events.isEmpty) {
                  return Center(
                    child: Text(
                      '// WAITING FOR TELEMETRY...',
                      style: VoidTheme.mono(color: VoidTokens.textMuted, fontSize: 11),
                    ),
                  );
                }

                return ListView.builder(
                  controller: _scrollController,
                  padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
                  itemCount: events.length,
                  itemBuilder: (context, index) {
                    final e = events[index];
                    return _buildTelemetryRow(e);
                  },
                );
              },
            ),
          ),

          // Bottom Telemetry Summary Card
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: HudPanel(
              padding: const EdgeInsets.all(8.0),
              technicalTag: 'SYS.EVENT_BUS',
              backgroundColor: VoidTokens.voidGraphite,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('BUFFER OCCUPANCY', style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.textMuted)),
                      Text('${TelemetryService.instance.events.length} / 500',
                          style: VoidTheme.mono(fontSize: 9, color: VoidTokens.textHigh)),
                    ],
                  ),
                  const SizedBox(height: 4),
                  LinearProgressIndicator(
                    value: (TelemetryService.instance.events.length / 500.0).clamp(0.0, 1.0),
                    backgroundColor: VoidTokens.voidSurface,
                    valueColor: const AlwaysStoppedAnimation<Color>(VoidTokens.voidOrange),
                    minHeight: 2,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTelemetryRow(TelemetryEvent e) {
    Color badgeColor = VoidTokens.voidOrange;
    switch (e.level) {
      case TelemetryLevel.info:
        badgeColor = VoidTokens.textMedium;
        break;
      case TelemetryLevel.warning:
        badgeColor = VoidTokens.statusYellow;
        break;
      case TelemetryLevel.critical:
        badgeColor = VoidTokens.statusRed;
        break;
      case TelemetryLevel.neural:
        badgeColor = VoidTokens.statusPurple;
        break;
      case TelemetryLevel.sensor:
        badgeColor = VoidTokens.statusCyan;
        break;
    }

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 2.5),
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: VoidTokens.voidObsidian,
        borderRadius: BorderRadius.circular(2),
        border: Border(
          left: BorderSide(color: badgeColor, width: 2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                e.shortTime,
                style: VoidTheme.mono(fontSize: 9, color: VoidTokens.textMuted),
              ),
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                decoration: BoxDecoration(
                  color: badgeColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(2),
                ),
                child: Text(
                  e.source,
                  style: VoidTheme.hudLabel(fontSize: 8, color: badgeColor),
                ),
              ),
            ],
          ),
          const SizedBox(height: 3),
          Text(
            e.message,
            style: VoidTheme.mono(fontSize: 10.5, color: VoidTokens.textHigh),
          ),
        ],
      ),
    );
  }
}
