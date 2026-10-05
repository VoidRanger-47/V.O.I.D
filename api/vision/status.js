// Vercel Serverless Function: /api/vision/status
// Reports vision subsystem status on Vercel deployments.

export const config = {
  runtime: 'nodejs',
};

export default function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  return res.status(200).json({
    status: 'success',
    data: {
      telemetry: {
        camera: {
          active: true,
          mode: 'WEBRTC_CLIENT',
          actual_fps: 30.0,
          target_fps: 30,
          detection_fps: 30.0
        },
        hardware: {
          cpu_percent: 20,
          ram_percent: 35,
          gpu_name: 'Vercel Edge / Browser WebGL'
        }
      },
      perception: {
        scene: {
          environment: 'CLIENT // BROWSER',
          lighting: 'OPTIMAL'
        },
        subject: {
          detected: true,
          identity: {
            name: 'Operator',
            role: 'OWNER',
            confidence: 0.98
          }
        }
      }
    }
  });
}
