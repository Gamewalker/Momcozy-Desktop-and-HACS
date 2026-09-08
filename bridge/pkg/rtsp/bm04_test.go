package rtsp

import (
	"avent-webrtc-bridge/pkg/storage"
	"bytes"
	"github.com/pion/rtp"
	"net"
	"strings"
	"testing"
	"time"
)

type captureConn struct{ bytes.Buffer }

func (c *captureConn) Close() error                     { return nil }
func (c *captureConn) LocalAddr() net.Addr              { return nil }
func (c *captureConn) RemoteAddr() net.Addr             { return nil }
func (c *captureConn) SetDeadline(time.Time) error      { return nil }
func (c *captureConn) SetReadDeadline(time.Time) error  { return nil }
func (c *captureConn) SetWriteDeadline(time.Time) error { return nil }
func TestBM04RTPWaitsForPlayAndPreservesFrameTiming(t *testing.T) {
	f := NewRTPForwarder()
	f.isHEVC = true
	c := &captureConn{}
	f.AddTCPClient("test", c, 0, 2, 4)
	p := &rtp.Packet{Header: rtp.Header{Version: 2, PayloadType: 108, SequenceNumber: 50, Timestamp: 123456, SSRC: 10}, Payload: []byte{0x62, 1, 0x81, 0xaa}}
	f.ForwardVideoPacket(p)
	if c.Len() != 0 {
		t.Fatal("RTP sent before PLAY")
	}
	f.PlayClient("test")
	for i := 0; i < 2; i++ {
		c.Reset()
		p.SequenceNumber = uint16(50 + i)
		f.ForwardVideoPacket(p)
		b := c.Bytes()
		if len(b) < 4 || b[0] != '$' {
			t.Fatal("missing interleaved RTP")
		}
		got := &rtp.Packet{}
		if err := got.Unmarshal(b[4:]); err != nil {
			t.Fatal(err)
		}
		if got.Timestamp != 123456 || got.SequenceNumber != p.SequenceNumber || got.PayloadType != 96 {
			t.Fatal("fragment timing, sequence or payload mapping changed")
		}
		if p.PayloadType != 108 {
			t.Fatal("mutated source packet")
		}
	}
}
func TestBM04SDPAdvertisesCameraCodecs(t *testing.T) {
	s := NewRTSPServer(0, nil)
	camera := &storage.CameraInfo{Skill: `{"videos":[{"streamType":2,"codecType":4,"width":1920,"height":1080}],"audios":[{"codecType":106}]}`}
	got := s.generateSDP(camera, "rtsp://localhost/bm04")
	if !strings.Contains(got, "H265/90000") || !strings.Contains(got, "PCMA/8000") || strings.Contains(got, "H264/90000") {
		t.Fatal(got)
	}
}

func TestCopyAudioClockMatchesSamples(t *testing.T) {
	for _, tc := range []struct {
		name  string
		scale uint32
		aac   bool
	}{
		{"BM04", 2, false}, {"legacy8k", 1, false}, {"AACAlreadyScaled", 2, true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			f := NewRTPForwarder()
			f.audioClockScale, f.audioAAC = tc.scale, tc.aac
			c := &captureConn{}
			f.AddTCPClient("test", c, 0, 2, 4)
			f.PlayClient("test")
			var prev uint32
			// Cross the 32-bit source timestamp boundary without changing elapsed time.
			for i := uint32(0); i < 3; i++ {
				stamp := uint32(0xffffff80) + i*128
				p := &rtp.Packet{Header: rtp.Header{Version: 2, Timestamp: stamp, SequenceNumber: uint16(i), SSRC: 42}, Payload: bytes.Repeat([]byte{0xd5}, 256)}
				c.Reset()
				f.forwardAudioPacket(p)
				var got rtp.Packet
				if err := got.Unmarshal(c.Bytes()[4:]); err != nil {
					t.Fatal(err)
				}
				wantDelta := uint32(128)
				if !tc.aac {
					wantDelta *= tc.scale
				}
				if i > 0 && got.Timestamp-prev != wantDelta {
					t.Fatal("incorrect output audio duration")
				}
				if !bytes.Equal(got.Payload, p.Payload) || p.Timestamp != stamp || got.SequenceNumber != p.SequenceNumber || got.SSRC != p.SSRC {
					t.Fatal("modified audio samples or source packet")
				}
				prev = got.Timestamp
			}
		})
	}
}
