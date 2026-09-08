package rtsp

import (
	"bufio"
	"encoding/base64"
	"net"
	"strings"
	"testing"
	"time"
)

func TestRemoteListenerRequiresCredentials(t *testing.T) {
	for _, host := range []string{"0.0.0.0", "192.0.2.1", "::"} {
		s := NewRTSPServer(0, nil)
		s.ListenHost = host
		if s.validateAccess() == nil {
			t.Fatal("remote listener without credentials")
		}
		s.Username = "viewer"
		s.Password = "short"
		if s.validateAccess() == nil {
			t.Fatal("short remote password accepted")
		}
		s.Password = "synthetic-test-password"
		if err := s.validateAccess(); err != nil {
			t.Fatal(err)
		}
	}
}

func TestBasicAuthentication(t *testing.T) {
	s := NewRTSPServer(0, nil)
	s.Username = "viewer"
	s.Password = "synthetic-test-password"
	for _, value := range []string{"", "Basic ???", "Bearer test", "Basic " + base64.StdEncoding.EncodeToString([]byte("viewer:wrong"))} {
		if s.authorized(&RTSPRequest{Headers: map[string]string{"Authorization": value}}) {
			t.Fatal("unauthenticated request accepted")
		}
	}
	header := "Basic " + base64.StdEncoding.EncodeToString([]byte(s.Username+":"+s.Password))
	if !s.authorized(&RTSPRequest{Headers: map[string]string{"authorization": header}}) {
		t.Fatal("valid credentials rejected")
	}
}

func TestInitialAuthChallengeBeforeCameraLookup(t *testing.T) {
	s := NewRTSPServer(0, nil)
	s.Username = "viewer"
	s.Password = "synthetic-test-password"
	server, client := net.Pipe()
	defer client.Close()
	client.SetDeadline(time.Now().Add(2 * time.Second))
	done := make(chan struct{})
	go func() { s.handleConnection(server); close(done) }()
	client.Write([]byte("DESCRIBE rtsp://localhost/bm04_1 RTSP/1.0\r\nCSeq: 1\r\n\r\n"))
	reader := bufio.NewReader(client)
	line, err := reader.ReadString('\n')
	if err != nil || !strings.Contains(line, "401") {
		t.Fatalf("missing auth challenge: %s %v", line, err)
	}
	for {
		line, err = reader.ReadString('\n')
		if err != nil {
			t.Fatal(err)
		}
		if line == "\r\n" {
			break
		}
	}
	client.Close()
	select {
	case <-done:
	case <-time.After(2 * time.Second):
		t.Fatal("connection did not close")
	}
}

func TestParserRemovesURLCredentials(t *testing.T) {
	s := NewRTSPServer(0, nil)
	r, err := s.parseRTSPRequestFromReader(bufio.NewReader(strings.NewReader("OPTIONS rtsp://viewer:secret@localhost/bm04_1 RTSP/1.0\r\nauthorization: Basic dGVzdA==\r\nCSeq: 7\r\n\r\n")))
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(r.URL, "secret") || r.CSeq != 7 || r.Headers["Authorization"] == "" {
		t.Fatal("unsafe URL or broken headers")
	}
}
