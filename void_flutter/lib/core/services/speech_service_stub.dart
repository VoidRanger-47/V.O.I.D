import 'dart:convert';
import 'package:http/http.dart' as http;
import 'speech_service.dart';

SpeechService getSpeechService() => NativeSpeechService();

class NativeSpeechService implements SpeechService {
  bool _isSpeaking = false;

  @override
  bool get isSpeaking => _isSpeaking;

  String _cleanText(String text) {
    String cleaned = text.replaceAll(RegExp(r'<thinking>[\s\S]*?</thinking>', caseSensitive: false), '');
    cleaned = cleaned.replaceAll(RegExp(r'```[\s\S]*?```'), ' Code block omitted. ');
    cleaned = cleaned.replaceAll(RegExp(r'`[^`]+`'), ' ');
    cleaned = cleaned.replaceAll(RegExp(r'\[([^\]]+)\]\([^\)]+\)'), r'$1');
    cleaned = cleaned.replaceAll(RegExp(r'[*#_~`\[\]()<>]'), ' ');
    return cleaned.replaceAll(RegExp(r'\s+'), ' ').trim();
  }

  @override
  Future<void> speak(String text, {String? baseUrl, double rate = 1.0}) async {
    final clean = _cleanText(text);
    if (clean.isEmpty) return;

    _isSpeaking = true;
    if (baseUrl != null && baseUrl.isNotEmpty) {
      try {
        await http.post(
          Uri.parse('$baseUrl/api/voice/speak'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'text': clean}),
        ).timeout(const Duration(seconds: 10));
      } catch (_) {}
    }
    _isSpeaking = false;
  }

  @override
  Future<void> stop() async {
    _isSpeaking = false;
  }
}
