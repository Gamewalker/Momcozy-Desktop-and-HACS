package rtsp

import (
	"bytes"
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"os/exec"
	"strconv"
	"sync"

	"github.com/pion/rtp"
)

const audioQueueSize = 128
const maxAudioInput = 4096

// AudioEncoder converts G.711 RTP payloads to AAC-LC MPEG4-GENERIC RTP.
// emit must return promptly and must not call Close from inside the callback.
// A full input queue stops encoding instead of silently accumulating audio drift.
type AudioEncoder struct {
	cmd             *exec.Cmd
	input           io.WriteCloser
	output          io.ReadCloser
	queue           chan *rtp.Packet
	done            chan struct{}
	once            sync.Once
	wg              sync.WaitGroup
	mu              sync.Mutex
	err             error
	firstTimestamp  uint32
	ssrc            uint32
	started         bool
	emit            func(*rtp.Packet)
	cleanup         func()
	silence         byte
	inputSampleRate int
}

func NewAudioEncoder(ffmpegPath string, alaw bool, emit func(*rtp.Packet)) (*AudioEncoder, error) {
	return NewAudioEncoderAtRate(ffmpegPath, alaw, 8000, emit)
}

// NewAudioEncoderAtRate distinguishes the G.711 sample rate from the fixed
// 8 kHz source RTP clock. BM04 sends 16 kHz samples using that 8 kHz clock.
func NewAudioEncoderAtRate(ffmpegPath string, alaw bool, inputSampleRate int, emit func(*rtp.Packet)) (*AudioEncoder, error) {
	if inputSampleRate != 8000 && inputSampleRate != 16000 {
		return nil, errors.New("AAC encoder input sample rate must be 8000 or 16000")
	}
	format := "mulaw"
	if alaw {
		format = "alaw"
	}
	cmd := exec.Command(ffmpegPath, "-hide_banner", "-loglevel", "error", "-nostdin",
		"-probesize", "32", "-analyzeduration", "0", "-f", format, "-ar", strconv.Itoa(inputSampleRate), "-ac", "1", "-i", "pipe:0",
		"-vn", "-c:a", "aac", "-profile:a", "aac_low", "-ar", "16000", "-ac", "1", "-b:a", "32k",
		"-flush_packets", "1", "-f", "adts", "pipe:1")
	a, err := startAudioEncoderAtRate(cmd, inputSampleRate, emit)
	if err == nil {
		a.silence = 0xff
		if alaw {
			a.silence = 0xd5
		}
	}
	return a, err
}

func startAudioEncoder(cmd *exec.Cmd, emit func(*rtp.Packet)) (*AudioEncoder, error) {
	return startAudioEncoderAtRate(cmd, 8000, emit)
}

func startAudioEncoderAtRate(cmd *exec.Cmd, inputSampleRate int, emit func(*rtp.Packet)) (*AudioEncoder, error) {
	if emit == nil {
		return nil, errors.New("AAC encoder needs an output callback")
	}
	configureAudioProcess(cmd)
	// FFmpeg receives only media on stdin, never a camera URL or credentials.
	cmd.Stderr = io.Discard
	input, err := cmd.StdinPipe()
	if err != nil {
		return nil, errors.New("cannot open AAC encoder input")
	}
	output, err := cmd.StdoutPipe()
	if err != nil {
		input.Close()
		return nil, errors.New("cannot open AAC encoder output")
	}
	if err = cmd.Start(); err != nil {
		input.Close()
		output.Close()
		return nil, errors.New("cannot start FFmpeg AAC encoder; check ffmpeg-path")
	}
	cleanup, err := attachAudioProcess(cmd)
	if err != nil {
		cmd.Process.Kill()
		cmd.Wait()
		input.Close()
		output.Close()
		return nil, errors.New("cannot supervise FFmpeg AAC encoder")
	}
	a := &AudioEncoder{cmd: cmd, input: input, output: output, queue: make(chan *rtp.Packet, audioQueueSize), done: make(chan struct{}), emit: emit, cleanup: cleanup, inputSampleRate: inputSampleRate}
	a.wg.Add(2)
	go a.writeLoop()
	go a.readLoop()
	return a, nil
}

// Write never waits for FFmpeg; payloads are copied because callers reuse packets.
func (a *AudioEncoder) Write(packet *rtp.Packet) {
	if packet == nil || len(packet.Payload) == 0 {
		return
	}
	select {
	case <-a.done:
		return
	default:
	}
	if len(packet.Payload) > maxAudioInput {
		a.stop(errors.New("AAC encoder input packet too large"))
		return
	}
	p := &rtp.Packet{Header: packet.Header, Payload: append([]byte(nil), packet.Payload...)}
	a.mu.Lock()
	if !a.started {
		a.firstTimestamp = packet.Timestamp * 2
		a.ssrc = packet.SSRC
		a.started = true
	}
	a.mu.Unlock()
	select {
	case <-a.done:
	case a.queue <- p:
	default:
		a.stop(errors.New("AAC encoder input queue overflow"))
	}
}

// Done closes when encoding terminates. Err reports a sanitized terminal error.
func (a *AudioEncoder) Done() <-chan struct{} { return a.done }
func (a *AudioEncoder) Err() error            { a.mu.Lock(); defer a.mu.Unlock(); return a.err }
func (a *AudioEncoder) stop(err error) {
	a.once.Do(func() {
		a.mu.Lock()
		a.err = err
		a.mu.Unlock()
		close(a.done)
		a.cmd.Process.Kill()
		a.input.Close()
	})
}

// Close stops the subprocess and joins both workers; it is safe to call repeatedly.
func (a *AudioEncoder) Close() { a.stop(nil); a.wg.Wait() }

func (a *AudioEncoder) writeLoop() {
	defer a.wg.Done()
	var expected uint32
	var started bool
	for {
		select {
		case <-a.done:
			return
		case p := <-a.queue:
			samplesPerTick := a.inputSampleRate / 8000
			if samplesPerTick == 0 {
				samplesPerTick = 1
			}
			if len(p.Payload)%samplesPerTick != 0 {
				a.stop(errors.New("AAC encoder packet has incomplete RTP clock interval"))
				return
			}
			if !started {
				expected = p.Timestamp
				started = true
			}
			// Signed subtraction handles RTP rollover. Late/duplicate packets have
			// already been replaced by silence and cannot be appended to the clock.
			delta := int32(p.Timestamp - expected)
			if delta < 0 {
				continue
			}
			if delta > 8000 {
				a.stop(errors.New("AAC encoder RTP clock discontinuity"))
				return
			}
			if delta > 0 {
				if _, err := a.input.Write(bytes.Repeat([]byte{a.silence}, int(delta)*samplesPerTick)); err != nil {
					a.stop(errors.New("AAC encoder input closed"))
					return
				}
			}
			if _, err := a.input.Write(p.Payload); err != nil {
				a.stop(errors.New("AAC encoder input closed"))
				return
			}
			expected = p.Timestamp + uint32(len(p.Payload)/samplesPerTick)
		}
	}
}

func (a *AudioEncoder) readLoop() {
	defer a.wg.Done()
	defer a.cleanup()
	defer a.cmd.Wait()
	defer a.output.Close()
	defer a.stop(errors.New("AAC encoder stopped"))
	var frameIndex uint32
	for {
		frame, err := readADTSFrame(a.output)
		if err != nil {
			a.stop(errors.New("AAC encoder returned invalid or incomplete audio"))
			return
		}
		a.mu.Lock()
		ts, ssrc := a.firstTimestamp, a.ssrc
		a.mu.Unlock()
		// FFmpeg's native AAC encoder adds one 1024-sample priming frame.
		// Timestamp that frame before the first source sample to retain sync.
		p := packetizeAAC(frame, uint16(frameIndex), ts+(frameIndex-1)*1024, ssrc)
		select {
		case <-a.done:
			return
		default:
			a.emit(p)
		}
		frameIndex++
	}
}

// readADTSFrame accepts exactly AAC-LC, 16 kHz, mono, one raw data block.
// ADTS length is 13 bits, bounding all allocations regardless of subprocess output.
func readADTSFrame(r io.Reader) ([]byte, error) {
	var h [7]byte
	if _, err := io.ReadFull(r, h[:]); err != nil {
		return nil, err
	}
	if h[0] != 0xff || h[1]&0xf6 != 0xf0 || h[2]>>6 != 1 || (h[2]>>2)&15 != 8 || ((h[2]&1)<<2|h[3]>>6) != 1 || h[6]&3 != 0 {
		return nil, errors.New("unsupported ADTS header")
	}
	headerSize := 7
	if h[1]&1 == 0 {
		headerSize = 9
	}
	length := int(h[3]&3)<<11 | int(h[4])<<3 | int(h[5]>>5)
	if length <= headerSize {
		return nil, fmt.Errorf("invalid ADTS frame length")
	}
	if headerSize == 9 {
		var crc [2]byte
		if _, err := io.ReadFull(r, crc[:]); err != nil {
			return nil, err
		}
	}
	frame := make([]byte, length-headerSize)
	_, err := io.ReadFull(r, frame)
	return frame, err
}

func packetizeAAC(frame []byte, sequence uint16, timestamp, ssrc uint32) *rtp.Packet {
	payload := make([]byte, 4+len(frame))
	binary.BigEndian.PutUint16(payload[:2], 16)                     // one 16-bit AU header
	binary.BigEndian.PutUint16(payload[2:4], uint16(len(frame))<<3) // sizeLength=13, indexLength=3
	copy(payload[4:], frame)
	return &rtp.Packet{Header: rtp.Header{Version: 2, PayloadType: 97, Marker: true, SequenceNumber: sequence, Timestamp: timestamp, SSRC: ssrc}, Payload: payload}
}
