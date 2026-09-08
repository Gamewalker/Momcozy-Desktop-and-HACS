package rtsp

import (
	"avent-webrtc-bridge/pkg/storage"
	"avent-webrtc-bridge/pkg/tuya"
	"fmt"
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

// BM04 emits 256 G.711 samples per 128 source RTP ticks. Advertising
// 8 kHz makes VLC continuously restart its audio resampler during playback.
func TestBM04CopyAudioSampleRate(t *testing.T) {
	camera := &storage.CameraInfo{Skill: `{"audios":[{"codecType":106,"sampleRate":16000}]}`}
	s := &RTSPServer{AudioFormat: "copy"}
	sdp := s.generateSDP(camera, "rtsp://localhost/test")
	if !strings.Contains(sdp, "a=rtpmap:98 PCMA/16000/1") {
		t.Fatal("BM04 copy audio must advertise its actual sample rate with a dynamic payload type")
	}
}

func TestCopyAudioPayloadMatchesSDP(t *testing.T) {
	for _, codec := range []int{105, 106} {
		for _, rate := range []int{0, 8000, 16000} {
			skill := &tuya.Skill{Audios: []tuya.AudioSkill{{CodecType: codec, SampleRate: rate}}}
			payload, clock, sdp := copyAudioDescription(skill)
			if !strings.Contains(sdp, fmt.Sprintf("a=rtpmap:%d ", payload)) {
				t.Fatal("payload mapping mismatch")
			}
			if rate == 16000 {
				if payload < 96 || clock != 16000 || !strings.Contains(sdp, "/16000/1") {
					t.Fatal("16 kHz requires dynamic payload and matching clock")
				}
			} else if clock != 8000 || (codec == 105 && payload != 0) || (codec == 106 && payload != 8) {
				t.Fatal("legacy mapping changed")
			}
		}
	}
}
