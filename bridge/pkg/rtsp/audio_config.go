package rtsp

import (
	"avent-webrtc-bridge/pkg/tuya"
	"errors"
	"fmt"
	"os/exec"
)

func (s *RTSPServer) validateAudio() error {
	if s.AudioFormat == "" {
		s.AudioFormat = "copy"
	}
	if s.AudioFormat != "copy" && s.AudioFormat != "aac" {
		return errors.New("audio-format must be copy or aac")
	}
	if s.AudioFormat == "aac" {
		if s.FFmpegPath == "" {
			s.FFmpegPath = "ffmpeg"
		}
		path, err := exec.LookPath(s.FFmpegPath)
		if err != nil {
			return errors.New("AAC audio requires FFmpeg; install it and set ffmpeg-path to its executable")
		}
		s.FFmpegPath = path
	}
	return nil
}

// copyAudioDescription keeps G.711 samples intact. BM04 sends 16 kHz
// samples on an 8 kHz source RTP clock; the RTSP clock must match the samples.
// Static PCMA/PCMU payload types are reserved for 8 kHz audio.
func copyAudioDescription(skill *tuya.Skill) (payload uint8, rate int, sdp string) {
	codec := "PCMU"
	rate = 8000
	if skill != nil && len(skill.Audios) > 0 {
		audio := skill.Audios[0]
		if audio.CodecType == 106 {
			codec, payload = "PCMA", 8
		}
		if (audio.CodecType == 105 || audio.CodecType == 106) && audio.SampleRate == 16000 {
			rate, payload = 16000, 98
		}
	}
	mapping := fmt.Sprintf("%s/%d", codec, rate)
	if rate != 8000 {
		mapping += "/1"
	}
	return payload, rate, fmt.Sprintf("m=audio 0 RTP/AVP %d\r\na=rtpmap:%d %s\r\n", payload, payload, mapping)
}
