import 'speech_service_stub.dart'
    if (dart.library.html) 'speech_service_web.dart';

abstract class SpeechService {
  factory SpeechService() => getSpeechService();

  bool get isSpeaking;
  Future<void> speak(String text, {String? baseUrl, double rate = 1.0});
  Future<void> stop();
}
