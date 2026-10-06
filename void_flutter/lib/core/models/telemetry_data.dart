class TelemetryData {
  final double cpuPercent;
  final double ramUsedMb;
  final double ramTotalMb;
  final double ramPercent;
  final String gpuName;
  final double gpuVramUsedMb;
  final double gpuVramTotalMb;
  final String osName;
  final String currentTime;
  final bool isOnline;

  TelemetryData({
    this.cpuPercent = 0.0,
    this.ramUsedMb = 0.0,
    this.ramTotalMb = 0.0,
    this.ramPercent = 0.0,
    this.gpuName = 'N/A',
    this.gpuVramUsedMb = 0.0,
    this.gpuVramTotalMb = 0.0,
    this.osName = 'Windows',
    this.currentTime = '',
    this.isOnline = true,
  });

  factory TelemetryData.fromJson(Map<String, dynamic> json) {
    return TelemetryData(
      cpuPercent: (json['cpu_percent'] ?? json['cpu'] ?? 0.0).toDouble(),
      ramUsedMb: (json['ram_used_mb'] ?? json['ram_used'] ?? 0.0).toDouble(),
      ramTotalMb: (json['ram_total_mb'] ?? json['ram_total'] ?? 0.0).toDouble(),
      ramPercent: (json['ram_percent'] ?? 0.0).toDouble(),
      gpuName: json['gpu_name'] ?? json['gpu'] ?? 'CPU Mode',
      gpuVramUsedMb: (json['gpu_vram_used_mb'] ?? json['vram_used'] ?? 0.0).toDouble(),
      gpuVramTotalMb: (json['gpu_vram_total_mb'] ?? json['vram_total'] ?? 0.0).toDouble(),
      osName: json['os'] ?? json['platform'] ?? 'Host Machine',
      currentTime: json['current_time'] ?? json['timestamp'] ?? '',
      isOnline: json['online'] ?? true,
    );
  }
}
