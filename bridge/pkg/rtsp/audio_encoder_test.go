package rtsp

import (
	"bytes"
	"encoding/binary"
	"github.com/pion/rtp"
	"io"
	"os"
	"os/exec"
	"testing"
	"time"
)

func adtsFixture(payload []byte, crc bool) []byte {
	header := []byte{0xff, 0xf1, 0x60, 0x40, 0, 0x1f, 0xfc}
	if crc {
		header[1] = 0xf0
		header = append(header, 0, 0)
	}
	n := len(header) + len(payload)
	header[3] |= byte(n >> 11)
	header[4] = byte(n >> 3)
	header[5] |= byte(n&7) << 5
	return append(header, payload...)
}

func TestADTSFrames(t *testing.T) {
	for _, crc := range []bool{false, true} {
		want := []byte{1, 2, 3, 4}
		encoded := append(adtsFixture(want, crc), adtsFixture(want, crc)...)
		r := bytes.NewReader(encoded)
		for range 2 {
			got, err := readADTSFrame(r)
			if err != nil || !bytes.Equal(got, want) {
				t.Fatalf("frame=%v err=%v", got, err)
			}
		}
		if _, err := readADTSFrame(r); err != io.EOF {
			t.Fatalf("EOF: %v", err)
		}
	}
}

func TestADTSRejectsMalformed(t *testing.T) {
	valid := adtsFixture([]byte{1, 2, 3}, false)
	cases := [][]byte{nil, valid[:6], valid[:8]}
	for _, index := range []int{0, 2, 3, 6} {
		b := append([]byte(nil), valid...)
		b[index] ^= 0xff
		cases = append(cases, b)
	}
	for _, b := range cases {
		if _, err := readADTSFrame(bytes.NewReader(b)); err == nil {
			t.Fatalf("accepted %x", b)
		}
	}
}

func TestAACPacketization(t *testing.T) {
	frame := bytes.Repeat([]byte{0xa5}, 300)
	p := packetizeAAC(frame, 65535, 0xfffffc00, 123)
	if p.PayloadType != 97 || !p.Marker || p.Version != 2 || p.SequenceNumber != 65535 || p.Timestamp != 0xfffffc00 || p.SSRC != 123 {
		t.Fatalf("header: %+v", p.Header)
	}
	if binary.BigEndian.Uint16(p.Payload[:2]) != 16 || binary.BigEndian.Uint16(p.Payload[2:4]) != 300<<3 || !bytes.Equal(p.Payload[4:], frame) {
		t.Fatal("invalid RFC3640 AU headers")
	}
}

func TestAudioEncoderHelper(t *testing.T) {
	if os.Getenv("MOMCOZY_ENCODER_TEST_HELPER") != "1" {
		return
	}
	var sample [1]byte
	if _, err := io.ReadFull(os.Stdin, sample[:]); err != nil {
		os.Exit(1)
	}
	os.Stdout.Write(adtsFixture([]byte{sample[0], 2, 3}, false))
	io.Copy(io.Discard, os.Stdin)
	os.Exit(0)
}

func TestAudioEncoderLifecycle(t *testing.T) {
	cmd := exec.Command(os.Args[0], "-test.run=^TestAudioEncoderHelper$")
	cmd.Env = append(os.Environ(), "MOMCOZY_ENCODER_TEST_HELPER=1")
	packets := make(chan *rtp.Packet, 1)
	a, err := startAudioEncoder(cmd, func(p *rtp.Packet) { packets <- p })
	if err != nil {
		t.Fatal(err)
	}
	defer a.Close()
	a.Write(&rtp.Packet{Header: rtp.Header{Timestamp: 10000, SSRC: 42}, Payload: []byte{7}})
	select {
	case p := <-packets:
		if p.Timestamp != 20000-1024 || p.SSRC != 42 || p.Payload[4] != 7 {
			t.Fatalf("bad output: %+v", p)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("no encoded output")
	}
	closed := make(chan struct{})
	go func() { a.Close(); a.Close(); close(closed) }()
	select {
	case <-closed:
	case <-time.After(5 * time.Second):
		t.Fatal("Close blocked")
	}
	if a.cmd.ProcessState == nil {
		t.Fatal("child not reaped")
	}
	a.Write(&rtp.Packet{Payload: []byte{8}})
}

// Optional real-codec smoke test; CI can supply an installed FFmpeg executable.
func TestAudioEncoderFFmpeg(t *testing.T) {
	path := os.Getenv("MOMCOZY_TEST_FFMPEG")
	if path == "" {
		t.Skip("set MOMCOZY_TEST_FFMPEG for real codec test")
	}
	for _, alaw := range []bool{true, false} {
		packets := make(chan *rtp.Packet, 256)
		a, err := NewAudioEncoder(path, alaw, func(p *rtp.Packet) { packets <- p })
		if err != nil {
			t.Fatal(err)
		}
		for i := range 150 {
			a.Write(&rtp.Packet{Header: rtp.Header{Timestamp: uint32(8000 + i*160), SSRC: 12}, Payload: bytes.Repeat([]byte{0xd5}, 160)})
			time.Sleep(10 * time.Millisecond)
		}
		select {
		case p := <-packets:
			if p.PayloadType != 97 || p.Timestamp != 16000-1024 || len(p.Payload) <= 4 {
				t.Errorf("invalid AAC RTP output: %+v", p.Header)
			}
		case <-a.Done():
			t.Errorf("FFmpeg failed: %v", a.Err())
		case <-time.After(5 * time.Second):
			t.Error("FFmpeg produced no AAC")
		}
		a.Close()
	}
}

func TestAudioEncoderOversizedInput(t *testing.T) {
	cmd := exec.Command(os.Args[0], "-test.run=^TestAudioEncoderHelper$")
	cmd.Env = append(os.Environ(), "MOMCOZY_ENCODER_TEST_HELPER=1")
	a, err := startAudioEncoder(cmd, func(*rtp.Packet) {})
	if err != nil {
		t.Fatal(err)
	}
	defer a.Close()
	a.Write(&rtp.Packet{Payload: make([]byte, maxAudioInput+1)})
	select {
	case <-a.Done():
	case <-time.After(time.Second):
		t.Fatal("oversized packet did not stop encoder")
	}
	if a.Err() == nil {
		t.Fatal("missing failure reason")
	}
}

type recordingAudioInput struct{ writes chan []byte }

func (r recordingAudioInput) Write(p []byte) (int, error) {
	r.writes <- append([]byte(nil), p...)
	return len(p), nil
}
func (r recordingAudioInput) Close() error { return nil }

func TestAudioEncoderPreservesClockAcrossLossAndRollover(t *testing.T) {
	r := recordingAudioInput{writes: make(chan []byte, 8)}
	a := &AudioEncoder{input: r, queue: make(chan *rtp.Packet, 8), done: make(chan struct{}), silence: 0xd5}
	a.wg.Add(1)
	go a.writeLoop()
	defer func() { close(a.done); a.wg.Wait() }()
	a.queue <- &rtp.Packet{Header: rtp.Header{Timestamp: 0xfffffffe}, Payload: []byte{1, 2}}
	a.queue <- &rtp.Packet{Header: rtp.Header{Timestamp: 0xfffffffe}, Payload: []byte{1, 2}}
	a.queue <- &rtp.Packet{Header: rtp.Header{Timestamp: 2}, Payload: []byte{3, 4}}
	for _, want := range [][]byte{{1, 2}, {0xd5, 0xd5}, {3, 4}} {
		select {
		case got := <-r.writes:
			if !bytes.Equal(got, want) {
				t.Fatalf("write=%x want=%x", got, want)
			}
		case <-time.After(time.Second):
			t.Fatal("missing audio write")
		}
	}
}
