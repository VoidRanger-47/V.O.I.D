/**
 * Microphone Testing Script
 * Paste this into the browser console to test microphone access
 */

console.log('🎤 Starting Microphone Diagnostics...\n');

// 1. Check browser capabilities
console.log('📋 Browser Capabilities:');
console.log('  - getUserMedia:', !!navigator.mediaDevices?.getUserMedia);
console.log('  - MediaRecorder:', !!window.MediaRecorder);
console.log('  - AudioContext:', !!(window.AudioContext || window.webkitAudioContext));
console.log('  - getUserEnumerateDevices:', !!navigator.mediaDevices?.enumerateDevices);

// 2. List available audio devices
if (navigator.mediaDevices?.enumerateDevices) {
    console.log('\n🔍 Available Audio Devices:');
    navigator.mediaDevices.enumerateDevices()
        .then(devices => {
            devices.forEach((device, index) => {
                console.log(`  ${index + 1}. ${device.label || 'Unknown'} (${device.deviceId})`);
                console.log(`     Type: ${device.kind}`);
            });
        })
        .catch(err => console.error('❌ Error enumerating devices:', err));
}

// 3. Test microphone access
console.log('\n🎙️ Testing Microphone Access...');
console.log('Please allow microphone access when prompted!\n');

navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
        console.log('✅ SUCCESS! Microphone access granted!');
        console.log('📊 Stream Details:');
        console.log('  - Audio Tracks:', stream.getAudioTracks().length);
        
        const audioTrack = stream.getAudioTracks()[0];
        if (audioTrack) {
            console.log('  - Track State:', audioTrack.readyState);
            console.log('  - Track Settings:', audioTrack.getSettings());
            console.log('  - Track Constraints:', audioTrack.getConstraints());
        }

        // Try to create MediaRecorder
        try {
            const recorder = new MediaRecorder(stream);
            console.log('\n✅ MediaRecorder created successfully!');
            console.log('  - Mime Type:', recorder.mimeType);
            console.log('  - State:', recorder.state);
            
            // Start recording for 3 seconds
            console.log('\n⏱️ Recording for 3 seconds...');
            let chunks = [];
            recorder.ondataavailable = (e) => chunks.push(e.data);
            recorder.start();
            
            setTimeout(() => {
                recorder.stop();
                console.log('✅ Recording completed!');
                console.log('  - Total chunks:', chunks.length);
                console.log('  - Total size:', chunks.reduce((sum, c) => sum + c.size, 0), 'bytes');
                
                // Stop tracks
                stream.getTracks().forEach(track => track.stop());
            }, 3000);
            
        } catch (err) {
            console.error('❌ MediaRecorder Error:', err);
        }
    })
    .catch(error => {
        console.error('❌ FAILED! Microphone access denied!');
        console.error('Error Name:', error.name);
        console.error('Error Message:', error.message);
        console.error('Full Error:', error);
        
        if (error.name === 'NotAllowedError') {
            console.log('\n💡 FIX: You denied microphone permission.');
            console.log('   - Check browser settings');
            console.log('   - Reset site permissions for localhost');
            console.log('   - Try in Incognito mode');
        } else if (error.name === 'NotFoundError') {
            console.log('\n💡 FIX: No microphone found on this device.');
            console.log('   - Check if microphone is plugged in');
            console.log('   - Check Device Manager (Windows) or System Preferences (Mac)');
        } else if (error.name === 'SecurityError') {
            console.log('\n💡 FIX: Security restriction on microphone access.');
            console.log('   - HTTPS is required (except localhost)');
            console.log('   - Check browser security policies');
        }
    });

console.log('\n✨ Diagnostics complete!');
