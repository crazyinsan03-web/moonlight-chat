// static/js/calls/webrtc.js

let localStream;
let remoteStream;
let peerConnection;

const iceServers = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' } // Ek extra backup STUN server
    ]
};

const incomingModal = document.getElementById('incomingCallModal');
const callerNameDisplay = document.getElementById('callerName');
const videoScreen = document.getElementById('video-call-screen');

// --- UI CONTROLS ---

function toggleCallScreen(show) {
    if (videoScreen) {
        videoScreen.style.display = show ? 'flex' : 'none';
    }
}

// --- CORE WEBRTC LOGIC ---

async function startLocalStream(type) {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({
            video: type === 'video',
            audio: true
        });
        
        const localVid = document.getElementById('localVideo');
        if (localVid) localVid.srcObject = localStream;
        
        toggleCallScreen(true);
        
    } catch (error) {
        console.error("Media Error:", error);
        alert("Camera ya Mic access nahi mila! Setting mein jaakar allow karein.");
    }
}

async function createPeerConnection(targetUser) {
    peerConnection = new RTCPeerConnection(iceServers);

    remoteStream = new MediaStream();
    const remoteVid = document.getElementById('remoteVideo');
    if (remoteVid) remoteVid.srcObject = remoteStream;

    localStream.getTracks().forEach(track => {
        peerConnection.addTrack(track, localStream);
    });

    peerConnection.ontrack = (event) => {
        event.streams[0].getTracks().forEach(track => {
            remoteStream.addTrack(track);
        });
    };

    peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
            socket.emit('ice-candidate', {
                to: targetUser,
                from: username,
                candidate: event.candidate
            });
        }
    };

    // Connection state check karne ke liye
    peerConnection.onconnectionstatechange = () => {
        console.log("Connection State:", peerConnection.connectionState);
        if (peerConnection.connectionState === 'connected') {
            document.querySelector('#call-info p').innerText = "Connected";
        }
    };
}

// --- CALL ACTIONS ---

async function initiateCall(type) {
    await startLocalStream(type);
    await createPeerConnection(friend);

    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);

    socket.emit('call-user', {
        to: friend,
        from: username,
        offer: offer,
        type: type
    });
    
    document.querySelector('#call-info p').innerText = "Calling " + friend + "...";
}

function endCall() {
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
    }
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }
    toggleCallScreen(false);
    socket.emit('end-call', { to: friend });
}

// --- SOCKET EVENTS ---

socket.on('incoming-call', async (data) => {
    incomingModal.style.display = 'flex';
    callerNameDisplay.innerText = data.from + " is calling...";

    document.getElementById('acceptCall').onclick = async () => {
        incomingModal.style.display = 'none';
        await startLocalStream(data.type);
        await createPeerConnection(data.from);

        await peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));
        const answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);

        socket.emit('answer-call', {
            to: data.from,
            from: username,
            answer: answer
        });
    };

    document.getElementById('rejectCall').onclick = () => {
        incomingModal.style.display = 'none';
        socket.emit('reject-call', { to: data.from });
    };
});

socket.on('call-accepted', async (data) => {
    if (peerConnection) {
        await peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
    }
});

socket.on('ice-candidate', async (data) => {
    if (peerConnection && peerConnection.remoteDescription) {
        try {
            await peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
        } catch (e) { 
            console.error("Error adding ice candidate", e); 
        }
    }
});

socket.on('call-ended', () => {
    endCall();
});

// --- BUTTON LISTENERS ---

const voiceBtn = document.getElementById('makeVoiceCall');
const videoBtn = document.getElementById('makeVideoCall');

if (voiceBtn) voiceBtn.onclick = () => initiateCall('voice');
if (videoBtn) videoBtn.onclick = () => initiateCall('video');

document.getElementById('muteBtn').onclick = () => {
    if (localStream) {
        const audioTrack = localStream.getAudioTracks()[0];
        audioTrack.enabled = !audioTrack.enabled;
        document.getElementById('muteBtn').innerText = audioTrack.enabled ? '🎤' : '🔇';
    }
};

document.getElementById('cameraBtn').onclick = () => {
    if (localStream) {
        const videoTrack = localStream.getVideoTracks()[0];
        videoTrack.enabled = !videoTrack.enabled;
        document.getElementById('cameraBtn').innerText = videoTrack.enabled ? '📷' : '🚫';
    }
};