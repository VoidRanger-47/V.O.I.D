import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/providers/vision_provider.dart';
import '../widgets/cyber_card.dart';

class MemoryScreen extends StatefulWidget {
  const MemoryScreen({super.key});

  @override
  State<MemoryScreen> createState() => _MemoryScreenState();
}

class _MemoryScreenState extends State<MemoryScreen> {
  final TextEditingController _searchCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<VisionProvider>().loadVisualMemory();
    });
  }

  void _onSearch(String query) {
    context.read<VisionProvider>().loadVisualMemory(objectFilter: query.trim());
  }

  @override
  Widget build(BuildContext context) {
    final vision = context.watch<VisionProvider>();
    final memories = vision.visualMemories;

    return Scaffold(
      backgroundColor: AppColors.bgApp,
      appBar: AppBar(
        backgroundColor: AppColors.bgApp,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        title: Row(
          children: [
            const Icon(Icons.auto_awesome_motion, color: AppColors.accent, size: 18),
            const SizedBox(width: 8),
            Text(
              'VISUAL MEMORY VAULT',
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
            tooltip: 'Refresh Memories',
            onPressed: () => _onSearch(_searchCtrl.text),
          ),
          const SizedBox(width: 6),
        ],
        bottom: const PreferredSize(
          preferredSize: Size.fromHeight(1),
          child: Divider(color: AppColors.borderHairline, height: 1),
        ),
      ),
      body: Column(
        children: [
          // Search Input Bar
          Padding(
            padding: const EdgeInsets.all(14),
            child: TextField(
              controller: _searchCtrl,
              style: GoogleFonts.inter(color: AppColors.textPrimary, fontSize: 13),
              decoration: InputDecoration(
                hintText: 'Search visual observations (e.g. laptop, phone, book)...',
                hintStyle: GoogleFonts.inter(color: AppColors.textSecondary, fontSize: 12.5),
                prefixIcon: const Icon(Icons.search, color: AppColors.accent, size: 18),
                suffixIcon: _searchCtrl.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 16, color: AppColors.textSecondary),
                        onPressed: () {
                          _searchCtrl.clear();
                          _onSearch('');
                        },
                      )
                    : null,
                filled: true,
                fillColor: AppColors.surfaceContainer,
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: AppColors.borderHairline, width: 1.0),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: AppColors.borderHairline, width: 1.0),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: AppColors.accent, width: 1.0),
                ),
              ),
              onSubmitted: _onSearch,
            ),
          ),

          // Memories List
          Expanded(
            child: memories.isEmpty
                ? Center(
                    child: Text(
                      'No visual observations recorded yet',
                      style: GoogleFonts.inter(
                        color: AppColors.textSecondary,
                        fontStyle: FontStyle.italic,
                        fontSize: 13,
                      ),
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                    itemCount: memories.length,
                    itemBuilder: (context, index) {
                      final item = memories[index];
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: CyberCard(
                          padding: const EdgeInsets.all(12),
                          borderRadius: 8,
                          child: Row(
                            children: [
                              Container(
                                width: 36,
                                height: 36,
                                decoration: BoxDecoration(
                                  color: AppColors.accentSubtle,
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: AppColors.accent.withOpacity(0.3)),
                                ),
                                child: const Icon(Icons.visibility, color: AppColors.accent, size: 18),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Text(
                                          item.objectName.toUpperCase(),
                                          style: GoogleFonts.inter(
                                            color: AppColors.textPrimary,
                                            fontSize: 13,
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                        const SizedBox(width: 6),
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: AppColors.bgApp,
                                            borderRadius: BorderRadius.circular(4),
                                            border: Border.all(color: AppColors.borderHairline),
                                          ),
                                          child: Text(
                                            item.context,
                                            style: GoogleFonts.jetBrainsMono(
                                              color: AppColors.textSecondary,
                                              fontSize: 9.5,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 3),
                                    Text(
                                      '${item.isoTime} • Event: ${item.eventType}',
                                      style: GoogleFonts.jetBrainsMono(
                                        color: AppColors.textSecondary,
                                        fontSize: 10.5,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  color: AppColors.accentSubtle,
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: AppColors.accent.withOpacity(0.3)),
                                ),
                                child: Text(
                                  'IMP ${(item.importance * 100).toInt()}%',
                                  style: GoogleFonts.jetBrainsMono(
                                    color: AppColors.accent,
                                    fontSize: 10,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
