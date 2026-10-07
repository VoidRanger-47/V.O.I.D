import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/providers/chat_provider.dart';
import '../../core/providers/settings_provider.dart';
import '../widgets/void_logo.dart';
import 'void_neural_chat_screen.dart';
import 'vision_screen.dart';
import 'telemetry_screen.dart';
import 'memory_screen.dart';
import 'phone_control_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  @override
  Widget build(BuildContext context) {
    final chatProvider = context.watch<ChatProvider>();
    final settingsProvider = context.watch<SettingsProvider>();

    final List<Widget> screens = [
      VoidNeuralChatScreen(
        onOpenDrawer: () => _scaffoldKey.currentState?.openDrawer(),
      ),
      const VisionScreen(),
      const TelemetryScreen(),
      const MemoryScreen(),
      const PhoneControlScreen(),
      const SettingsScreen(),
    ];

    return Scaffold(
      key: _scaffoldKey,
      backgroundColor: AppColors.bgApp,
      drawer: _buildModernDrawer(context, chatProvider, settingsProvider),
      body: IndexedStack(
        index: _currentIndex,
        children: screens,
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: AppColors.surfaceContainer,
          border: Border(
            top: BorderSide(color: AppColors.borderHairline, width: 1.0),
          ),
        ),
        child: BottomNavigationBar(
          backgroundColor: AppColors.surfaceContainer,
          elevation: 0,
          type: BottomNavigationBarType.fixed,
          selectedItemColor: AppColors.accent,
          unselectedItemColor: AppColors.textMuted,
          selectedLabelStyle: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w600),
          unselectedLabelStyle: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w400),
          currentIndex: _currentIndex > 4 ? 4 : _currentIndex,
          onTap: (index) {
            setState(() {
              _currentIndex = index;
            });
          },
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.chat_bubble_outline, size: 19),
              activeIcon: Icon(Icons.chat_bubble, color: AppColors.accent, size: 19),
              label: 'Chat',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.remove_red_eye_outlined, size: 19),
              activeIcon: Icon(Icons.remove_red_eye, color: AppColors.accent, size: 19),
              label: 'Vision',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.speed, size: 19),
              activeIcon: Icon(Icons.speed, color: AppColors.accent, size: 19),
              label: 'Telemetry',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.auto_awesome_motion_outlined, size: 19),
              activeIcon: Icon(Icons.auto_awesome_motion, color: AppColors.accent, size: 19),
              label: 'Memory',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.phone_android, size: 19),
              activeIcon: Icon(Icons.phone_android, color: AppColors.accent, size: 19),
              label: 'Phone',
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildModernDrawer(
    BuildContext context,
    ChatProvider chatProvider,
    SettingsProvider settingsProvider,
  ) {
    return Drawer(
      backgroundColor: AppColors.bgApp,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 16, 14, 12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const VoidLogo(size: 26, showBackgroundSquircle: true),
                      const SizedBox(width: 10),
                      Text(
                        'V.O.I.D.',
                        style: GoogleFonts.inter(
                          color: AppColors.textPrimary,
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.5,
                        ),
                      ),
                    ],
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded, color: AppColors.textMuted, size: 20),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
            ),

            // "+ New Conversation" Button — Smooth rounded pill
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              child: InkWell(
                onTap: () {
                  chatProvider.newSession();
                  setState(() {
                    _currentIndex = 0;
                  });
                  Navigator.pop(context);
                },
                borderRadius: BorderRadius.circular(24),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceContainer,
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(
                      color: AppColors.accent.withOpacity(0.35),
                      width: 1.0,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.accent.withOpacity(0.06),
                        blurRadius: 10,
                        spreadRadius: 0,
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        width: 22,
                        height: 22,
                        decoration: BoxDecoration(
                          color: AppColors.accent.withOpacity(0.16),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.add_rounded, size: 15, color: AppColors.accent),
                      ),
                      const SizedBox(width: 10),
                      Text(
                        'NEW CONVERSATION',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: AppColors.textPrimary,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),

            // Section: Recent Conversations with Individual Deletion
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 6),
              child: Text(
                'RECENT CONVERSATIONS',
                style: GoogleFonts.jetBrainsMono(
                  color: AppColors.textMuted,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.2,
                ),
              ),
            ),

            // List of actual chat sessions with individual deletion
            Expanded(
              flex: 3,
              child: chatProvider.sessions.isEmpty
                  ? Center(
                      child: Text(
                        'No previous chats',
                        style: GoogleFonts.inter(color: AppColors.textMuted, fontSize: 12),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 10),
                      itemCount: chatProvider.sessions.length,
                      itemBuilder: (context, idx) {
                        final session = chatProvider.sessions[idx];
                        final isSelected = session.id == chatProvider.currentSessionId && _currentIndex == 0;

                        return Container(
                          margin: const EdgeInsets.symmetric(vertical: 3),
                          decoration: BoxDecoration(
                            color: isSelected ? AppColors.accentSubtle : AppColors.surfaceContainer,
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(
                              color: isSelected ? AppColors.accent.withOpacity(0.6) : AppColors.borderHairline,
                              width: 1.0,
                            ),
                          ),
                          child: InkWell(
                            borderRadius: BorderRadius.circular(14),
                            onTap: () {
                              chatProvider.switchSession(session.id);
                              setState(() {
                                _currentIndex = 0;
                              });
                              Navigator.pop(context);
                            },
                            child: Padding(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                              child: Row(
                                children: [
                                  Icon(
                                    Icons.chat_bubble_outline,
                                    size: 15,
                                    color: isSelected ? AppColors.accent : AppColors.textSecondary,
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      session.title,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: GoogleFonts.inter(
                                        fontSize: 12.5,
                                        fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                                        color: isSelected ? AppColors.accent : AppColors.textPrimary,
                                      ),
                                    ),
                                  ),
                                  // Individual Chat Deletion Button
                                  InkWell(
                                    onTap: () => _confirmDeleteSession(context, chatProvider, session.id, session.title),
                                    borderRadius: BorderRadius.circular(4),
                                    child: const Padding(
                                      padding: EdgeInsets.all(4),
                                      child: Icon(
                                        Icons.delete_outline,
                                        size: 15,
                                        color: AppColors.textSecondary,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        );
                      },
                    ),
            ),

            const Divider(color: AppColors.borderHairline, height: 1),

            // Section: Tools & Modules
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: Text(
                'NEURAL MODULES',
                style: GoogleFonts.jetBrainsMono(
                  color: AppColors.textSecondary,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.2,
                ),
              ),
            ),

            Expanded(
              flex: 2,
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                children: [
                  _buildDrawerModuleItem(
                    icon: Icons.remove_red_eye_outlined,
                    title: 'Vision HUD & Perception',
                    index: 1,
                  ),
                  _buildDrawerModuleItem(
                    icon: Icons.speed,
                    title: 'System Telemetry',
                    index: 2,
                  ),
                  _buildDrawerModuleItem(
                    icon: Icons.auto_awesome_motion_outlined,
                    title: 'Visual Memory Vault',
                    index: 3,
                  ),
                  _buildDrawerModuleItem(
                    icon: Icons.phone_android,
                    title: 'Phone Automation Bridge',
                    index: 4,
                  ),
                  _buildDrawerModuleItem(
                    icon: Icons.settings_outlined,
                    title: 'System Configuration',
                    index: 5,
                  ),
                ],
              ),
            ),

            const Divider(color: AppColors.borderHairline, height: 1),

            // Footer Actions
            Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  TextButton.icon(
                    style: TextButton.styleFrom(
                      foregroundColor: AppColors.textSecondary,
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                    ),
                    onPressed: () {
                      chatProvider.clearHistory();
                      Navigator.pop(context);
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Chat messages cleared')),
                      );
                    },
                    icon: const Icon(Icons.cleaning_services_outlined, size: 15),
                    label: Text(
                      'Clear Chat',
                      style: GoogleFonts.inter(fontSize: 11.5),
                    ),
                  ),
                  TextButton.icon(
                    style: TextButton.styleFrom(
                      foregroundColor: AppColors.textSecondary,
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                    ),
                    onPressed: () {
                      setState(() {
                        _currentIndex = 5;
                      });
                      Navigator.pop(context);
                    },
                    icon: const Icon(Icons.tune, size: 15),
                    label: Text(
                      'Settings',
                      style: GoogleFonts.inter(fontSize: 11.5),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _confirmDeleteSession(
    BuildContext context,
    ChatProvider chatProvider,
    String sessionId,
    String sessionTitle,
  ) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surfaceContainer,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: const BorderSide(color: AppColors.borderHairline, width: 1),
        ),
        title: Text(
          'Delete Conversation',
          style: GoogleFonts.inter(
            color: AppColors.textPrimary,
            fontSize: 15,
            fontWeight: FontWeight.w700,
          ),
        ),
        content: Text(
          'Are you sure you want to delete "$sessionTitle"? This cannot be undone.',
          style: GoogleFonts.inter(
            color: AppColors.textSecondary,
            fontSize: 13,
            height: 1.4,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(
              'Cancel',
              style: GoogleFonts.inter(color: AppColors.textSecondary),
            ),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.statusRed,
              foregroundColor: Colors.white,
              elevation: 0,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
              ),
            ),
            onPressed: () {
              Navigator.pop(ctx);
              chatProvider.deleteSession(sessionId);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Conversation deleted'),
                  duration: Duration(seconds: 1),
                ),
              );
            },
            child: Text(
              'Delete',
              style: GoogleFonts.inter(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDrawerModuleItem({
    required IconData icon,
    required String title,
    required int index,
  }) {
    final isActive = _currentIndex == index;

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 2),
      decoration: BoxDecoration(
        color: isActive ? AppColors.surfaceContainer : Colors.transparent,
        borderRadius: BorderRadius.circular(14),
        border: isActive
            ? Border.all(color: AppColors.borderHairline, width: 1)
            : null,
      ),
      child: ListTile(
        dense: true,
        visualDensity: const VisualDensity(horizontal: -2, vertical: -3),
        leading: Icon(
          icon,
          size: 16,
          color: isActive ? AppColors.accent : AppColors.textSecondary,
        ),
        title: Text(
          title,
          style: GoogleFonts.inter(
            fontSize: 12.5,
            fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
            color: isActive ? AppColors.textPrimary : AppColors.textSecondary,
          ),
        ),
        onTap: () {
          setState(() {
            _currentIndex = index;
          });
          Navigator.pop(context);
        },
      ),
    );
  }
}
