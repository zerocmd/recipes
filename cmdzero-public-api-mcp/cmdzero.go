package mcpcmdzero

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"runtime/debug"
	"strings"
	"sync"

	"github.com/mark3labs/mcp-go/server"
)

const (
	defaultCmdZeroURL = "https://api.cmdzero.io/public/v1"

	cmdZeroURLEnvVar    = "CMDZERO_URL"
	cmdZeroAPIKeyEnvVar = "CMDZERO_API_KEY"
	cmdZeroOrgIDEnvVar  = "CMDZERO_ORG_ID"
)

// CmdZeroConfig holds configuration for the Command Zero Public API client.
type CmdZeroConfig struct {
	URL    string
	APIKey string
	OrgID  string
}

type cmdZeroConfigKey struct{}

// WithCmdZeroConfig adds Command Zero configuration to the context.
func WithCmdZeroConfig(ctx context.Context, config CmdZeroConfig) context.Context {
	return context.WithValue(ctx, cmdZeroConfigKey{}, config)
}

// CmdZeroConfigFromContext extracts Command Zero configuration from the context.
func CmdZeroConfigFromContext(ctx context.Context) CmdZeroConfig {
	if config, ok := ctx.Value(cmdZeroConfigKey{}).(CmdZeroConfig); ok {
		return config
	}
	return CmdZeroConfig{}
}

// CmdZeroClient wraps an HTTP client for Command Zero Public API calls.
type CmdZeroClient struct {
	httpClient *http.Client
	baseURL    string
	orgID      string
	authHeader string
}

type cmdZeroClientKey struct{}

// WithCmdZeroClient sets the Command Zero client in the context.
func WithCmdZeroClient(ctx context.Context, client *CmdZeroClient) context.Context {
	return context.WithValue(ctx, cmdZeroClientKey{}, client)
}

// CmdZeroClientFromContext retrieves the Command Zero client from the context.
func CmdZeroClientFromContext(ctx context.Context) *CmdZeroClient {
	c, ok := ctx.Value(cmdZeroClientKey{}).(*CmdZeroClient)
	if !ok {
		return nil
	}
	return c
}

// NewCmdZeroClient creates a Command Zero Public API client from config.
func NewCmdZeroClient(config CmdZeroConfig) *CmdZeroClient {
	url := config.URL
	if url == "" {
		url = defaultCmdZeroURL
	}
	url = strings.TrimRight(url, "/")

	return &CmdZeroClient{
		httpClient: &http.Client{},
		baseURL:    url,
		orgID:      config.OrgID,
		authHeader: "Bearer " + config.APIKey,
	}
}

// orgURL returns the base URL for org-scoped API calls.
func (c *CmdZeroClient) orgURL() string {
	return fmt.Sprintf("%s/organizations/%s", c.baseURL, c.orgID)
}

// do executes an HTTP request against the Command Zero API.
func (c *CmdZeroClient) do(ctx context.Context, method, url string, body io.Reader) (json.RawMessage, error) {
	// Capture request body for debug logging
	var reqBodyBytes []byte
	if body != nil {
		var err error
		reqBodyBytes, err = io.ReadAll(body)
		if err != nil {
			return nil, fmt.Errorf("read request body: %w", err)
		}
		body = bytes.NewReader(reqBodyBytes)
	}

	slog.Debug("Command Zero API request", "method", method, "url", url, "body", string(reqBodyBytes))

	req, err := http.NewRequestWithContext(ctx, method, url, body)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Authorization", c.authHeader)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		slog.Error("Command Zero API request failed", "method", method, "url", url, "error", err)
		return nil, fmt.Errorf("http request: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response: %w", err)
	}

	slog.Debug("Command Zero API response", "method", method, "url", url, "status", resp.StatusCode, "body", string(respBody))

	if resp.StatusCode >= 400 {
		slog.Error("Command Zero API error", "method", method, "url", url, "status", resp.StatusCode, "body", string(respBody))
		return nil, fmt.Errorf("Command Zero API error (HTTP %d): %s", resp.StatusCode, string(respBody))
	}

	return json.RawMessage(respBody), nil
}

// Get performs a GET request to an org-scoped path.
func (c *CmdZeroClient) Get(ctx context.Context, path string) (json.RawMessage, error) {
	return c.do(ctx, http.MethodGet, c.orgURL()+path, nil)
}

// Post performs a POST request to an org-scoped path.
func (c *CmdZeroClient) Post(ctx context.Context, path string, body io.Reader) (json.RawMessage, error) {
	return c.do(ctx, http.MethodPost, c.orgURL()+path, body)
}

// Patch performs a PATCH request to an org-scoped path.
func (c *CmdZeroClient) Patch(ctx context.Context, path string, body io.Reader) (json.RawMessage, error) {
	return c.do(ctx, http.MethodPatch, c.orgURL()+path, body)
}

// Put performs a PUT request to an org-scoped path.
func (c *CmdZeroClient) Put(ctx context.Context, path string, body io.Reader) (json.RawMessage, error) {
	return c.do(ctx, http.MethodPut, c.orgURL()+path, body)
}

// Delete performs a DELETE request to an org-scoped path.
func (c *CmdZeroClient) Delete(ctx context.Context, path string) (json.RawMessage, error) {
	return c.do(ctx, http.MethodDelete, c.orgURL()+path, nil)
}

// Query performs an HTTP QUERY request to an org-scoped path.
// The QUERY method is used for complex filter operations on list endpoints.
func (c *CmdZeroClient) Query(ctx context.Context, path string, body io.Reader) (json.RawMessage, error) {
	return c.do(ctx, "QUERY", c.orgURL()+path, body)
}

// GetGlobal performs a GET request to a non-org-scoped path (e.g., /ok, /organizations).
func (c *CmdZeroClient) GetGlobal(ctx context.Context, path string) (json.RawMessage, error) {
	return c.do(ctx, http.MethodGet, c.baseURL+path, nil)
}

// QueryGlobal performs an HTTP QUERY request to a non-org-scoped path
// (e.g. /organizations). Used for complex filter expressions too long to
// fit in a URL.
func (c *CmdZeroClient) QueryGlobal(ctx context.Context, path string, body io.Reader) (json.RawMessage, error) {
	return c.do(ctx, "QUERY", c.baseURL+path, body)
}

// Version returns the version of the cmdzero-public-api-mcp binary.
var Version = sync.OnceValue(func() string {
	v := "(devel)"
	if bi, ok := debug.ReadBuildInfo(); ok && bi.Main.Version != "" {
		v = bi.Main.Version
	}
	return v
})

// ExtractCmdZeroConfigFromEnv reads Command Zero configuration from environment variables.
var ExtractCmdZeroConfigFromEnv server.StdioContextFunc = func(ctx context.Context) context.Context {
	url := os.Getenv(cmdZeroURLEnvVar)
	if url == "" {
		url = defaultCmdZeroURL
	}

	apiKey := os.Getenv(cmdZeroAPIKeyEnvVar)
	orgID := os.Getenv(cmdZeroOrgIDEnvVar)

	slog.Info("Using Command Zero configuration",
		"url", url,
		"api_key_set", apiKey != "",
		"org_id", orgID,
	)

	config := CmdZeroConfigFromContext(ctx)
	config.URL = url
	config.APIKey = apiKey
	config.OrgID = orgID
	return WithCmdZeroConfig(ctx, config)
}

// ExtractCmdZeroClientFromEnv creates a Command Zero client from context config.
var ExtractCmdZeroClientFromEnv server.StdioContextFunc = func(ctx context.Context) context.Context {
	config := CmdZeroConfigFromContext(ctx)
	client := NewCmdZeroClient(config)
	return WithCmdZeroClient(ctx, client)
}

type httpContextFunc func(ctx context.Context, req *http.Request) context.Context

// ExtractCmdZeroConfigFromHeaders reads Command Zero config from HTTP headers with env fallback.
var ExtractCmdZeroConfigFromHeaders httpContextFunc = func(ctx context.Context, req *http.Request) context.Context {
	config := CmdZeroConfigFromContext(ctx)

	if url := req.Header.Get("X-CmdZero-URL"); url != "" {
		config.URL = url
	}
	if apiKey := req.Header.Get("X-CmdZero-API-Key"); apiKey != "" {
		config.APIKey = apiKey
	}
	if orgID := req.Header.Get("X-CmdZero-Org-ID"); orgID != "" {
		config.OrgID = orgID
	}

	return WithCmdZeroConfig(ctx, config)
}

// ExtractCmdZeroClientFromHeaders creates a Command Zero client from header-based config.
var ExtractCmdZeroClientFromHeaders httpContextFunc = func(ctx context.Context, req *http.Request) context.Context {
	config := CmdZeroConfigFromContext(ctx)
	client := NewCmdZeroClient(config)
	return WithCmdZeroClient(ctx, client)
}

// ComposeStdioContextFuncs composes multiple StdioContextFuncs.
func ComposeStdioContextFuncs(funcs ...server.StdioContextFunc) server.StdioContextFunc {
	return func(ctx context.Context) context.Context {
		for _, f := range funcs {
			ctx = f(ctx)
		}
		return ctx
	}
}

// ComposeHTTPContextFuncs composes multiple HTTPContextFuncs.
func ComposeHTTPContextFuncs(funcs ...httpContextFunc) server.HTTPContextFunc {
	return func(ctx context.Context, req *http.Request) context.Context {
		for _, f := range funcs {
			ctx = f(ctx, req)
		}
		return ctx
	}
}

// ComposedStdioContextFunc returns the full stdio context setup.
func ComposedStdioContextFunc(config CmdZeroConfig) server.StdioContextFunc {
	return ComposeStdioContextFuncs(
		func(ctx context.Context) context.Context {
			return WithCmdZeroConfig(ctx, config)
		},
		ExtractCmdZeroConfigFromEnv,
		ExtractCmdZeroClientFromEnv,
	)
}

// ComposedHTTPContextFunc returns the full HTTP context setup.
func ComposedHTTPContextFunc(config CmdZeroConfig) server.HTTPContextFunc {
	return ComposeHTTPContextFuncs(
		func(ctx context.Context, _ *http.Request) context.Context {
			return WithCmdZeroConfig(ctx, config)
		},
		ExtractCmdZeroConfigFromHeaders,
		ExtractCmdZeroClientFromHeaders,
	)
}
