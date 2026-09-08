package rtsp

import (
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"errors"
	"net"
	"strconv"
	"strings"
)

func (s *RTSPServer) validateAccess() error {
	if s.ListenHost == "" {
		s.ListenHost = "127.0.0.1"
	}
	ip := net.ParseIP(s.ListenHost)
	if ip == nil {
		return errors.New("listen-host must be an IP address")
	}
	if (s.Username == "") != (s.Password == "") {
		return errors.New("both RTSP username and password are required")
	}
	if strings.ContainsAny(s.Username, ":\r\n") || strings.ContainsAny(s.Password, "\r\n") {
		return errors.New("invalid RTSP credentials")
	}
	if !ip.IsLoopback() && (s.Username == "" || len(s.Password) < 16) {
		return errors.New("non-loopback RTSP requires a username and a password of at least 16 characters")
	}
	return nil
}

func (s *RTSPServer) authorized(request *RTSPRequest) bool {
	if s.Username == "" && s.Password == "" {
		return true
	}
	var header string
	for key, value := range request.Headers {
		if strings.EqualFold(key, "Authorization") {
			header = value
			break
		}
	}
	parts := strings.Fields(header)
	if len(parts) != 2 || !strings.EqualFold(parts[0], "Basic") {
		return false
	}
	raw, err := base64.StdEncoding.DecodeString(parts[1])
	if err != nil {
		return false
	}
	expected := sha256.Sum256([]byte(s.Username + ":" + s.Password))
	supplied := sha256.Sum256(raw)
	return subtle.ConstantTimeCompare(expected[:], supplied[:]) == 1
}

func (s *RTSPServer) challenge(conn net.Conn, cseq int) error {
	return sendRTSPResponse(conn, 401, "Unauthorized", map[string]string{
		"CSeq": strconv.Itoa(cseq), "WWW-Authenticate": `Basic realm="Momcozy"`,
	}, "")
}
