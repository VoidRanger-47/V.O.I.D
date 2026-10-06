// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;
import 'speech_service.dart';

SpeechService getSpeechService() => WebSpeechService();

class WebSpeechService implements SpeechService {
  bool _isSpeaking = false;
  html.AudioElement? _currentAudio;

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

    await stop();
    _isSpeaking = true;

    // First try Web Speech Synthesis (instant, zero network latency, robust across browsers)
    try {
      if (html.window.speechSynthesis != null) {
        final utterance = html.SpeechSynthesisUtterance(clean);
        utterance.rate = rate;
        utterance.lang = 'en-US';
        utterance.onEnd.listen((_) {
          _isSpeaking = false;
        });
        utterance.onError.listen((_) {
          _fallbackAudioStream(clean, baseUrl, rate);
        });
        html.window.speechSynthesis?.cancel();
        html.window.speechSynthesis?.speak(utterance);
        return;
      }
    } catch (_) {}

    // Fallback: Stream WAV audio from VOID Python backend
    _fallbackAudioStream(clean, baseUrl, rate);
  }

  void _fallbackAudioStream(String text, String? baseUrl, double rate) {
    if (baseUrl == null || baseUrl.isEmpty) {
      _isSpeaking = false;
      return;
    }
    try {
      final audioUrl = '$baseUrl/api/voice/speak?text=${Uri.encodeComponent(text)}';
      final audio = html.AudioElement(audioUrl);
      _currentAudio = audio;
      audio.playbackRate = rate;
      audio.onEnded.listen((_) {
        _isSpeaking = false;
      });
      audio.onError.listen((_) {
        _isSpeaking = false;
      });
      audio.play();
    } catch (_) {
      _isSpeaking = false;
    }
  }

  @override
  Future<void> stop() async {
    _isSpeaking = false;
    try {
      if (_currentAudio != null) {
        _currentAudio?.pause();
        _currentAudio?.currentTime = 0;
        _currentAudio = null;
      }
      html.window.speechSynthesis?.cancel();
    } catch (_) {}
  }
}
