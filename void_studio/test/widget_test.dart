import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:void_studio/main.dart';
import 'package:void_studio/state/studio_state.dart';
import 'package:void_studio/core/constants.dart';
import 'package:void_studio/shell/studio_shell.dart';
import 'package:void_studio/services/backend_service.dart';

void main() {
  testWidgets('V.O.I.D. Studio bootloader smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const VoidStudioApp());
    expect(find.text('V.O.I.D.'), findsOneWidget);
    expect(find.text('SKIP INITIALIZATION [ESC]'), findsOneWidget);
    BackendService.instance.stopMonitoring();
  });

  testWidgets('Renders flawlessly on mobile portrait (360x640) without overflow', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(360, 640);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    await tester.pumpWidget(const VoidStudioApp());
    expect(find.text('V.O.I.D.'), findsOneWidget);
    expect(find.text('SKIP [ESC]'), findsOneWidget);

    // Skip bootloader into Studio Shell
    await tester.tap(find.text('SKIP [ESC]'));
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 200));

    // Verify bottom exoskeleton nav rendered for mobile
    expect(find.byIcon(Icons.blur_circular), findsWidgets);
    expect(find.byIcon(Icons.terminal), findsWidgets);

    // Check state switching to other modes on mobile
    final BuildContext context = tester.element(find.byType(StudioShell));
    final StudioState state = Provider.of<StudioState>(context, listen: false);

    // Switch across each mode and verify zero exceptions
    for (final mode in WorkspaceMode.values) {
      state.setActiveMode(mode);
      await tester.pump(const Duration(milliseconds: 100));
      expect(tester.takeException(), isNull);
    }

    BackendService.instance.stopMonitoring();
  });

  testWidgets('Renders on ultra-compact mobile (320x568) without overflow', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(320, 568);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    await tester.pumpWidget(const VoidStudioApp());
    await tester.tap(find.text('SKIP [ESC]'));
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 200));

    final BuildContext context = tester.element(find.byType(StudioShell));
    final StudioState state = Provider.of<StudioState>(context, listen: false);

    for (final mode in WorkspaceMode.values) {
      state.setActiveMode(mode);
      await tester.pump(const Duration(milliseconds: 100));
      expect(tester.takeException(), isNull);
    }

    BackendService.instance.stopMonitoring();
  });

  testWidgets('Renders on compact tablet (768x1024) without overflow', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(768, 1024);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    await tester.pumpWidget(const VoidStudioApp());
    await tester.tap(find.text('SKIP INITIALIZATION [ESC]'));
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 200));

    final BuildContext context = tester.element(find.byType(StudioShell));
    final StudioState state = Provider.of<StudioState>(context, listen: false);

    for (final mode in WorkspaceMode.values) {
      state.setActiveMode(mode);
      await tester.pump(const Duration(milliseconds: 100));
      expect(tester.takeException(), isNull);
    }

    BackendService.instance.stopMonitoring();
  });

  testWidgets('Renders on constrained height (800x420) without vertical overflow', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(800, 420);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    await tester.pumpWidget(const VoidStudioApp());
    await tester.tap(find.text('SKIP INITIALIZATION [ESC]'));
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 200));

    final BuildContext context = tester.element(find.byType(StudioShell));
    final StudioState state = Provider.of<StudioState>(context, listen: false);

    // Test with bottom panel opened
    state.toggleBottomPanel();
    await tester.pump(const Duration(milliseconds: 100));

    for (final mode in WorkspaceMode.values) {
      state.setActiveMode(mode);
      await tester.pump(const Duration(milliseconds: 100));
      expect(tester.takeException(), isNull);
    }

    BackendService.instance.stopMonitoring();
  });

  testWidgets('Renders on ultrawide (2560x1080) desktop display', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(2560, 1080);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    await tester.pumpWidget(const VoidStudioApp());
    await tester.tap(find.text('SKIP INITIALIZATION [ESC]'));
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 200));

    final BuildContext context = tester.element(find.byType(StudioShell));
    final StudioState state = Provider.of<StudioState>(context, listen: false);

    for (final mode in WorkspaceMode.values) {
      state.setActiveMode(mode);
      await tester.pump(const Duration(milliseconds: 100));
      expect(tester.takeException(), isNull);
    }

    BackendService.instance.stopMonitoring();
  });
}
