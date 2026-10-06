import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/network/api_service.dart';
import 'core/providers/chat_provider.dart';
import 'core/providers/vision_provider.dart';
import 'core/providers/system_provider.dart';
import 'core/providers/settings_provider.dart';
import 'ui/theme/app_theme.dart';
import 'ui/screens/home_screen.dart';
import 'ui/widgets/zero_gravity_boot_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  
  final apiService = ApiService();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => SettingsProvider(apiService)),
        ChangeNotifierProvider(create: (_) => ChatProvider(apiService)),
        ChangeNotifierProvider(create: (_) => VisionProvider(apiService)),
        ChangeNotifierProvider(create: (_) => SystemProvider(apiService)),
      ],
      child: const VoidApp(),
    ),
  );
}

class VoidApp extends StatelessWidget {
  const VoidApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'V.O.I.D.',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: const _VoidBootEntry(),
    );
  }
}

/// Hosts [ZeroGravityBootScreen] and transitions to [HomeScreen] on completion.
class _VoidBootEntry extends StatefulWidget {
  const _VoidBootEntry();

  @override
  State<_VoidBootEntry> createState() => _VoidBootEntryState();
}

class _VoidBootEntryState extends State<_VoidBootEntry> {
  bool _navigated = false;

  void _onBootComplete() {
    if (_navigated || !mounted) return;
    _navigated = true;
    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        transitionDuration: const Duration(milliseconds: 600),
        pageBuilder: (_, __, ___) => const HomeScreen(),
        transitionsBuilder: (_, animation, __, child) {
          final fade = CurvedAnimation(
            parent: animation,
            curve: Curves.easeInOutQuad,
          );
          final scale = Tween<double>(begin: 0.96, end: 1.0).animate(
            CurvedAnimation(parent: animation, curve: Curves.easeOutCubic),
          );
          return FadeTransition(
            opacity: fade,
            child: ScaleTransition(scale: scale, child: child),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ZeroGravityBootScreen(
      logoAssetPath: 'assets/images/void_symbol.png',
      onBootComplete: _onBootComplete,
      logoSize: 180,
    );
  }
}
