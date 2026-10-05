// Vercel Serverless Function: /api/chat/stream
// Provides real-time SSE streaming for V.O.I.D. on Vercel / Cloud deployments.

export const config = {
  runtime: 'nodejs',
  maxDuration: 60,
};

export default async function handler(req, res) {
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, x-gemini-api-key');
    return res.status(200).end();
  }

  // Set SSE streaming headers
  res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  res.setHeader('Access-Control-Allow-Origin', '*');

  let body = {};
  try {
    body = typeof req.body === 'string' ? JSON.parse(req.body) : (req.body || {});
  } catch (e) {
    body = {};
  }

  const userMessage = body.message || (req.query && req.query.message) || '';
  const apiKey = body.gemini_api_key || req.headers['x-gemini-api-key'] || process.env.GEMINI_API_KEY;

  const sendEvent = (obj) => {
    res.write(`data: ${JSON.stringify(obj)}\n\n`);
    if (typeof res.flush === 'function') {
      res.flush();
    }
  };

  if (!userMessage.trim()) {
    sendEvent({ token: "Please provide a query or message for V.O.I.D.", done: true });
    return res.end();
  }

  // 1. If Gemini API key is configured, stream directly from Google Gemini 2.0 Flash
  if (apiKey && apiKey.trim().length > 5) {
    try {
      const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:streamGenerateContent?alt=sse&key=${encodeURIComponent(apiKey.trim())}`;
      
      const systemInstruction = "You are V.O.I.D. (Versatile Omnipresent Intelligent Device), an ultra-advanced cybernetic AI companion and autonomous assistant. You provide precise, highly knowledgeable, articulate, and structured responses with an elegant cyberpunk aesthetic.";

      const contents = [
        {
          role: "user",
          parts: [{ text: userMessage }]
        }
      ];

      const geminiRes = await fetch(geminiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          systemInstruction: { parts: [{ text: systemInstruction }] },
          contents: contents,
          generationConfig: {
            temperature: (body.settings && body.settings.temperature) ? parseFloat(body.settings.temperature) : 0.7,
            maxOutputTokens: (body.settings && body.settings.maxTokens) ? parseInt(body.settings.maxTokens) : 1024,
          }
        })
      });

      if (!geminiRes.ok) {
        const errText = await geminiRes.text();
        sendEvent({ 
          error: `Gemini API returned status ${geminiRes.status}: ${errText}` 
        });
        sendEvent({ done: true });
        return res.end();
      }

      const reader = geminiRes.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data:')) continue;
          const jsonStr = trimmed.replace(/^data:\s*/, '').trim();
          if (!jsonStr || jsonStr === '[DONE]') continue;

          try {
            const parsed = JSON.parse(jsonStr);
            const candidate = parsed.candidates && parsed.candidates[0];
            if (candidate && candidate.content && candidate.content.parts) {
              for (const part of candidate.content.parts) {
                if (part.text) {
                  sendEvent({ token: part.text, done: false });
                }
              }
            }
          } catch (pe) {
            // Partial JSON chunk, continue
          }
        }
      }

      sendEvent({ token: "", done: true });
      return res.end();

    } catch (err) {
      sendEvent({ error: `Cloud streaming failure: ${err.message || err}` });
      sendEvent({ done: true });
      return res.end();
    }
  }

  // 2. Default Edge mode: Stream structured V.O.I.D. assistant response explaining edge setup
  const messageChunks = [
    "**[V.O.I.D. Cybernetic Core // Vercel Edge Node Online]**\n\n",
    `I have received your command: *"${userMessage}"*.\n\n`,
    "You are currently connected to the **Vercel Serverless Cloud Deployment** of V.O.I.D.\n\n",
    "### ⚡ Streaming Options:\n",
    "1. **Cloud Intelligence (Gemini 2.0)**: Add your **Google Gemini API Key** in **Chat Settings** (`⚙️`) to enable full real-time multimodal LLM streaming and visual comprehension on Vercel.\n",
    "2. **Local Workstation (Offline PyTorch & CUDA)**: Run `python app.py` on your desktop/laptop (with NVIDIA RTX GPU) to execute 100% offline neural synthesis and local computer vision.\n\n",
    "*(Vision feeds and WebRTC camera telemetry are fully operational in the Vision tab!)*"
  ];

  for (const chunk of messageChunks) {
    sendEvent({ token: chunk, done: false });
    // Small pacing delay for smooth streaming effect
    await new Promise((r) => setTimeout(r, 40));
  }

  sendEvent({ token: "", done: true });
  res.end();
}
