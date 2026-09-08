package rtsp

import (
	"avent-webrtc-bridge/pkg/storage"
	"strings"
	"testing"
)

func TestAudioConfiguration(t *testing.T) {
	s := &RTSPServer{}
	if err := s.validateAudio(); err != nil || s.AudioFormat != "copy" {
		t.Fatal("default must copy audio", err)
	}
	s.AudioFormat = "mp3"
	if s.validateAudio() == nil {
		t.Fatal("unsupported format accepted")
	}
	s.AudioFormat, s.FFmpegPath = "aac", "missing-momcozy-ffmpeg-executable"
	if s.validateAudio() == nil {
		t.Fatal("missing FFmpeg accepted")
	}
}

func TestAACSDPAndBridgePropagation(t *testing.T) {
	camera := &storage.CameraInfo{DeviceID: "test", Skill: `{"videos":[{"streamType":2,"codecType":4,"width":1920,"height":1080}],"audios":[{"codecType":106}]}`}
	s := &RTSPServer{AudioFormat: "aac", FFmpegPath: "configured-ffmpeg", Talkback: true}
	sdp := s.generateSDP(camera, "rtsp://localhost:8554/test")
	for _, want := range []string{"H265/90000", "MPEG4-GENERIC/16000/1", "config=1408", "SizeLength=13", "a=rtpmap:8 PCMA/8000"} {
		if !strings.Contains(sdp, want) {
			t.Errorf("SDP missing %s", want)
		}
	}
	stream := NewCameraStream(camera, "hd", nil, nil, s)
	if stream.webrtcBridge.AudioFormat != "aac" || stream.webrtcBridge.FFmpegPath != "configured-ffmpeg" {
		t.Fatal("audio configuration not propagated")
	}
	stream.replaceBridge()
	if stream.webrtcBridge.AudioFormat != "aac" || stream.webrtcBridge.FFmpegPath != "configured-ffmpeg" {
		t.Fatal("reconnect lost audio configuration")
	}
	s.AudioFormat = "copy"
	sdp = s.generateSDP(camera, "rtsp://localhost:8554/test")
	if strings.Contains(sdp, "MPEG4-GENERIC") || !strings.Contains(sdp, "PCMA/8000") {
		t.Fatal("copy mode changed the original codec")
	}
}
