package rtsp

import (
	"errors"
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
