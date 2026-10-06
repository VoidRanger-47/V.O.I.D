import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/theme.dart';
import 'shell/studio_shell.dart';
import 'startup/startup_sequence.dart';
import 'state/studio_state.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const VoidStudioApp());
}

class VoidStudioApp extends StatefulWidget {
  const VoidStudioApp({super.key});

  @override
  State<VoidStudioApp> createState() => _VoidStudioAppState();
}

class _VoidStudioAppState extends State<VoidStudioApp> {
  bool _bootCompleted = false;

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => StudioState(),
      child: MaterialApp(
        title: 'V.O.I.D. STUDIO — Autonomous AI Engineering IDE',
        debugShowCheckedModeBanner: false,
        theme: VoidTheme.darkTheme,
        home: _bootCompleted
            ? const StudioShell()
            : StartupSequence(
                onComplete: () {
                  setState(() => _bootCompleted = true);
                },
              ),
      ),
    );
  }
}
