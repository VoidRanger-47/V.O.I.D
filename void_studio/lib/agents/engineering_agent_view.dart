import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/constants.dart';
import '../core/hud_painters.dart';
import '../core/theme.dart';
import '../state/studio_state.dart';

class EngineeringAgentView extends StatefulWidget {
  const EngineeringAgentView({super.key});

  @override
  State<EngineeringAgentView> createState() => _EngineeringAgentViewState();
}

class _EngineeringAgentViewState extends State<EngineeringAgentView> {
  final List<_PlanStep> _plan = [
    _PlanStep(number: '01', title: 'Inspect memory architecture', isDone: true, isCurrent: false),
    _PlanStep(number: '02', title: 'Profile vector retrieval latency', isDone: true, isCurrent: false),
    _PlanStep(number: '03', title: 'Locate embedding dimension bottleneck', isDone: false, isCurrent: true),
    _PlanStep(number: '04', title: 'Generate batch optimization patch', isDone: false, isCurrent: false),
    _PlanStep(number: '05', title: 'Run empirical verification & unit tests', isDone: false, isCurrent: false),
  ];

  final List<String> _affectedFiles = [
    'void_memory/experience_memory.py',
    'core/router.py',
    'core/vram_manager.py',
  ];

  @override
  Widget build(BuildContext context) {
    final state = context.watch<StudioState>();

    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final isNarrow = width < 900;
        final isMobile = width < 600;

        return Padding(
          padding: EdgeInsets.all(isMobile ? 12.0 : 18.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header Bar
              HudPanel(
                technicalTag: 'SYS.ENGINEERING_AGENT // MK-IV',
                child: isMobile
                    ? Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                width: 10,
                                height: 10,
                                decoration: const BoxDecoration(
                                  color: VoidTokens.statusPurple,
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  'V.O.I.D. ENGINEERING AGENT',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: VoidTheme.hudLabel(
                                    fontSize: 11,
                                    color: VoidTokens.voidOrangeBright,
                                    letterSpacing: 1.5,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: VoidTokens.statusPurple.withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(4),
                                  border: Border.all(color: VoidTokens.statusPurple),
                                ),
                                child: Text(
                                  'ANALYZING',
                                  style: VoidTheme.mono(
                                    fontSize: 9,
                                    fontWeight: FontWeight.w700,
                                    color: VoidTokens.statusPurple,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'AUTONOMOUS SYSTEM LEVEL REASONING',
                            style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.textMuted),
                          ),
                        ],
                      )
                    : Row(
                        children: [
                          Container(
                            width: 12,
                            height: 12,
                            decoration: const BoxDecoration(
                              color: VoidTokens.statusPurple,
                              shape: BoxShape.circle,
                              boxShadow: [
                                BoxShadow(
                                  color: VoidTokens.statusPurpleGlow,
                                  blurRadius: 8,
                                  spreadRadius: 2,
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'V.O.I.D. ENGINEERING AGENT',
                                  style: VoidTheme.hudLabel(
                                    fontSize: 12,
                                    color: VoidTokens.voidOrangeBright,
                                    letterSpacing: 1.8,
                                  ),
                                ),
                                Text(
                                  'AUTONOMOUS SYSTEM LEVEL CODE SYNTHESIS & ARCHITECTURE REASONING',
                                  overflow: TextOverflow.ellipsis,
                                  style: VoidTheme.mono(fontSize: 9.5, color: VoidTokens.textMuted),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 12),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: VoidTokens.statusPurple.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(color: VoidTokens.statusPurple),
                            ),
                            child: Text(
                              'STATUS: ANALYZING',
                              style: VoidTheme.mono(
                                fontSize: 10,
                                fontWeight: FontWeight.w700,
                                color: VoidTokens.statusPurple,
                              ),
                            ),
                          ),
                        ],
                      ),
              ),

              const SizedBox(height: 14),

              // Main Workspace Split or Single Scrollable Stream
              Expanded(
                child: isNarrow
                    ? SingleChildScrollView(
                        physics: const BouncingScrollPhysics(),
                        child: Column(
                          children: [
                            _buildObjectiveCard(),
                            const SizedBox(height: 14),
                            _buildPlanPanel(isFlexible: false),
                            const SizedBox(height: 14),
                            _buildTouchedFilesPanel(),
                            const SizedBox(height: 14),
                            _buildMetricsPanel(state, isFlexible: false),
                          ],
                        ),
                      )
                    : Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Left Plan & Execution Column
                          Expanded(
                            flex: 3,
                            child: Column(
                              children: [
                                _buildObjectiveCard(),
                                const SizedBox(height: 14),
                                Expanded(child: _buildPlanPanel(isFlexible: true)),
                              ],
                            ),
                          ),

                          const SizedBox(width: 16),

                          // Right Telemetry & Context Column
                          Expanded(
                            flex: 2,
                            child: Column(
                              children: [
                                _buildTouchedFilesPanel(),
                                const SizedBox(height: 14),
                                Expanded(child: _buildMetricsPanel(state, isFlexible: true)),
                              ],
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

  Widget _buildObjectiveCard() {
    return HudPanel(
      technicalTag: 'EXECUTION_TASK',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'CURRENT OBJECTIVE',
            style: VoidTheme.mono(fontSize: 9, color: VoidTokens.textMuted),
          ),
          const SizedBox(height: 4),
          Text(
            'Optimize memory retrieval pipeline for o200k_base embedding cache',
            style: VoidTheme.mono(
              fontSize: 12.5,
              fontWeight: FontWeight.w600,
              color: VoidTokens.textHigh,
            ),
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: VoidTokens.voidObsidian,
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: VoidTokens.voidSurfaceBorder),
            ),
            child: Row(
              children: [
                const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation(VoidTokens.voidOrange),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Analyzing vector cosine similarity in void_memory/experience_memory.py...',
                    style: VoidTheme.mono(
                      fontSize: 10.5,
                      color: VoidTokens.voidOrangeBright,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPlanPanel({required bool isFlexible}) {
    final list = ListView.builder(
      physics: isFlexible ? null : const NeverScrollableScrollPhysics(),
      shrinkWrap: !isFlexible,
      itemCount: _plan.length,
      itemBuilder: (context, index) {
        final step = _plan[index];
        return _buildStepRow(step);
      },
    );

    return HudPanel(
      technicalTag: 'PHASE_PLAN',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: isFlexible ? MainAxisSize.max : MainAxisSize.min,
        children: [
          Text(
            'SYNTHESIS & RESOLUTION PLAN',
            style: VoidTheme.hudLabel(fontSize: 10),
          ),
          const SizedBox(height: 10),
          if (isFlexible) Expanded(child: list) else list,
        ],
      ),
    );
  }

  Widget _buildTouchedFilesPanel() {
    return HudPanel(
      technicalTag: 'AFFECTED_FILES',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'TOUCHED WORKSPACE REPOSITORIES',
            style: VoidTheme.hudLabel(fontSize: 9.5),
          ),
          const SizedBox(height: 8),
          ..._affectedFiles.map((file) => Container(
                margin: const EdgeInsets.symmetric(vertical: 3),
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                decoration: BoxDecoration(
                  color: VoidTokens.voidObsidian,
                  borderRadius: BorderRadius.circular(3),
                  border: Border.all(color: VoidTokens.voidSurfaceBorder),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.description_outlined,
                        size: 13, color: VoidTokens.voidOrange),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        file,
                        overflow: TextOverflow.ellipsis,
                        style: VoidTheme.mono(
                          fontSize: 10.5,
                          color: VoidTokens.textHigh,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                      decoration: BoxDecoration(
                        color: VoidTokens.statusGreen.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(2),
                      ),
                      child: Text(
                        'MODIFIED',
                        style: VoidTheme.mono(fontSize: 8.5, color: VoidTokens.statusGreen),
                      ),
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }

  Widget _buildMetricsPanel(StudioState state, {required bool isFlexible}) {
    final content = SingleChildScrollView(
      physics: isFlexible ? const BouncingScrollPhysics() : const NeverScrollableScrollPhysics(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildMetricBar('CPU LOAD', state.metrics.cpuPercent, 100, '%', VoidTokens.voidOrange),
          const SizedBox(height: 10),
          _buildMetricBar('GPU COMPUTE', state.metrics.gpuPercent, 100, '%', VoidTokens.statusPurple),
          const SizedBox(height: 10),
          _buildMetricBar('VRAM ALLOCATION', state.metrics.vramUsedGb, state.metrics.vramTotalGb, ' GB', VoidTokens.statusCyan),
          const SizedBox(height: 10),
          _buildMetricBar('SYSTEM RAM', state.metrics.ramUsedGb, state.metrics.ramTotalGb, ' GB', VoidTokens.statusYellow),
        ],
      ),
    );

    return HudPanel(
      technicalTag: 'ENGINEERING_SYSTEM_METRICS',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: isFlexible ? MainAxisSize.max : MainAxisSize.min,
        children: [
          Text(
            'SYSTEM COMPUTATIONAL FOOTPRINT',
            style: VoidTheme.hudLabel(fontSize: 9.5),
          ),
          const SizedBox(height: 12),
          if (isFlexible) Expanded(child: content) else content,
        ],
      ),
    );
  }

  Widget _buildStepRow(_PlanStep step) {
    Color color = VoidTokens.textMuted;
    Widget statusIcon = const Icon(Icons.radio_button_unchecked, size: 14, color: VoidTokens.textMuted);

    if (step.isDone) {
      color = VoidTokens.statusGreen;
      statusIcon = const Icon(Icons.check_circle, size: 15, color: VoidTokens.statusGreen);
    } else if (step.isCurrent) {
      color = VoidTokens.voidOrangeBright;
      statusIcon = const SizedBox(
        width: 14,
        height: 14,
        child: CircularProgressIndicator(strokeWidth: 2, valueColor: AlwaysStoppedAnimation(VoidTokens.voidOrangeBright)),
      );
    }

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: step.isCurrent ? VoidTokens.voidSurface : VoidTokens.voidObsidian,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(
          color: step.isCurrent ? VoidTokens.voidOrange : VoidTokens.voidSurfaceBorder,
        ),
      ),
      child: Row(
        children: [
          Text(
            step.number,
            style: VoidTheme.mono(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              step.title,
              style: VoidTheme.mono(
                fontSize: 11.5,
                color: step.isCurrent ? VoidTokens.textHigh : VoidTokens.textMedium,
              ),
            ),
          ),
          statusIcon,
        ],
      ),
    );
  }

  Widget _buildMetricBar(String label, double value, double max, String unit, Color color) {
    final pct = (value / max).clamp(0.0, 1.0);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: VoidTheme.mono(fontSize: 9.5, color: VoidTokens.textMuted),
              ),
            ),
            const SizedBox(width: 8),
            Text(
              '${value.toStringAsFixed(1)}$unit / ${max.toStringAsFixed(0)}$unit',
              style: VoidTheme.mono(fontSize: 10, color: VoidTokens.textHigh, fontWeight: FontWeight.w600),
            ),
          ],
        ),
        const SizedBox(height: 4),
        LinearProgressIndicator(
          value: pct,
          backgroundColor: VoidTokens.voidSurface,
          valueColor: AlwaysStoppedAnimation<Color>(color),
          minHeight: 4,
        ),
      ],
    );
  }
}

class _PlanStep {
  final String number;
  final String title;
  final bool isDone;
  final bool isCurrent;

  _PlanStep({
    required this.number,
    required this.title,
    required this.isDone,
    required this.isCurrent,
  });
}
